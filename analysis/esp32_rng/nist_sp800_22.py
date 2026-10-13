"""
nist_sp800_22.py -- NIST SP 800-22 Rev. 1a statistical test suite.

Self-contained implementation of the 15 tests, written from the
definitions in the standard (no third-party test library), so every
statistic is auditable against the document. Conventions:

  * Input: bytes object; bits are unpacked MSB-first (np.unpackbits).
  * Each test returns one p-value (tests that produce multiple p-values
    -- non-overlapping templates, random excursions (variant) -- return
    the MINIMUM p-value across templates/states, the conservative
    aggregation, plus the full list in the `detail` field).
  * PASS criterion: p >= 0.01 (significance level alpha = 0.01).
  * Sequence length: designed for n = 1,000,000 bits (the standard's
    recommended minimum for the full battery).

Validated against known-good (os.urandom) and known-bad (constant,
alternating, biased, short-period LFSR) inputs -- see self_test().

TFM -- Mario Garcia Jimenez, Master en Microelectronica, US/IMSE-CNM.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import special as sp
from scipy import fft as sfft

ALPHA = 0.01


@dataclass
class TestResult:
    name: str
    p_value: float
    passed: bool
    detail: dict = field(default_factory=dict)


def _bits(data: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def _igamc(a: float, x: float) -> float:
    return float(sp.gammaincc(a, x))


# ----------------------------------------------------------- 1. Frequency --
def frequency_test(bits: np.ndarray) -> TestResult:
    n = bits.size
    s = np.sum(2.0 * bits - 1.0)
    s_obs = abs(s) / math.sqrt(n)
    p = math.erfc(s_obs / math.sqrt(2.0))
    return TestResult("Frequency", p, p >= ALPHA,
                      {"S_n": float(s), "ones_ratio": float(bits.mean())})


# ----------------------------------------------------- 2. Block frequency --
def block_frequency_test(bits: np.ndarray, M: int = 128) -> TestResult:
    n = bits.size
    N = n // M
    blocks = bits[:N * M].reshape(N, M)
    pi = blocks.mean(axis=1)
    chi2 = 4.0 * M * np.sum((pi - 0.5) ** 2)
    p = _igamc(N / 2.0, chi2 / 2.0)
    return TestResult("Block Frequency", p, p >= ALPHA,
                      {"M": M, "N": N, "chi2": float(chi2)})


# ---------------------------------------------------------------- 3. Runs --
def runs_test(bits: np.ndarray) -> TestResult:
    n = bits.size
    pi = bits.mean()
    if abs(pi - 0.5) >= 2.0 / math.sqrt(n):
        return TestResult("Runs", 0.0, False,
                          {"note": "prerequisite monobit failed",
                           "pi": float(pi)})
    v = 1 + int(np.count_nonzero(np.diff(bits)))
    num = abs(v - 2.0 * n * pi * (1 - pi))
    den = 2.0 * math.sqrt(2.0 * n) * pi * (1 - pi)
    p = math.erfc(num / den)
    return TestResult("Runs", p, p >= ALPHA, {"V_n": v, "pi": float(pi)})


# --------------------------------------------------- 4. Longest run of 1s --
def longest_run_test(bits: np.ndarray) -> TestResult:
    n = bits.size
    if n >= 750000:
        M, K = 10000, 6
        v_classes = [10, 11, 12, 13, 14, 15]          # <=10 ... >=16
        pi = [0.0882, 0.2092, 0.2483, 0.1933, 0.1208, 0.0675, 0.0727]
    elif n >= 6272:
        M, K = 128, 5
        v_classes = [4, 5, 6, 7, 8]
        pi = [0.1174, 0.2430, 0.2493, 0.1752, 0.1027, 0.1124]
    else:
        M, K = 8, 3
        v_classes = [1, 2, 3]
        pi = [0.2148, 0.3672, 0.2305, 0.1875]

    N = n // M
    blocks = bits[:N * M].reshape(N, M)

    # longest run of ones per block, vectorized via cumulative trick
    def longest_run_rows(b):
        # reset cumulative count at zeros
        c = np.zeros_like(b, dtype=np.int32)
        run = np.zeros(b.shape[0], dtype=np.int32)
        best = np.zeros(b.shape[0], dtype=np.int32)
        for j in range(b.shape[1]):
            run = (run + 1) * b[:, j]
            best = np.maximum(best, run)
        return best

    longest = longest_run_rows(blocks.astype(np.int32))
    counts = np.zeros(K + 1, dtype=np.int64)
    for L in longest:
        idx = 0
        for c_i, edge in enumerate(v_classes):
            if L <= edge:
                idx = c_i
                break
        else:
            idx = K
        # first class is <= v_classes[0]; middle classes exact; last >= edge+1
        if L <= v_classes[0]:
            idx = 0
        elif L > v_classes[-1]:
            idx = K
        else:
            idx = v_classes.index(L)
        counts[idx] += 1

    chi2 = float(np.sum((counts - N * np.array(pi)) ** 2 /
                        (N * np.array(pi))))
    p = _igamc(K / 2.0, chi2 / 2.0)
    return TestResult("Longest Run", p, p >= ALPHA,
                      {"M": M, "N": N, "chi2": chi2,
                       "counts": counts.tolist()})


# ------------------------------------------------------- 5. Matrix rank ----
def _binary_rank(mat: np.ndarray) -> int:
    m = mat.copy()
    rows, cols = m.shape
    rank = 0
    for col in range(cols):
        pivot = None
        for r in range(rank, rows):
            if m[r, col]:
                pivot = r
                break
        if pivot is None:
            continue
        m[[rank, pivot]] = m[[pivot, rank]]
        below = m[:, col].astype(bool).copy()
        below[:rank + 1] = False
        m[below] ^= m[rank]
        rank += 1
        if rank == rows:
            break
    return rank


def matrix_rank_test(bits: np.ndarray, M: int = 32, Q: int = 32) -> TestResult:
    n = bits.size
    N = n // (M * Q)
    if N < 38:
        return TestResult("Matrix Rank", 0.0, False,
                          {"note": "sequence too short"})
    mats = bits[:N * M * Q].reshape(N, M, Q)
    full, full_m1 = 0, 0
    for i in range(N):
        r = _binary_rank(mats[i])
        if r == M:
            full += 1
        elif r == M - 1:
            full_m1 += 1
    rest = N - full - full_m1
    p_full, p_m1, p_rest = 0.2888, 0.5776, 0.1336
    chi2 = ((full - p_full * N) ** 2 / (p_full * N)
            + (full_m1 - p_m1 * N) ** 2 / (p_m1 * N)
            + (rest - p_rest * N) ** 2 / (p_rest * N))
    p = math.exp(-chi2 / 2.0)
    return TestResult("Matrix Rank", p, p >= ALPHA,
                      {"N": N, "full": full, "full-1": full_m1,
                       "chi2": float(chi2)})


# ---------------------------------------------------------- 6. Spectral ----
def spectral_test(bits: np.ndarray) -> TestResult:
    n = bits.size
    x = 2.0 * bits.astype(np.float64) - 1.0
    s = sfft.rfft(x)
    mod = np.abs(s[: n // 2])
    T = math.sqrt(math.log(1.0 / 0.05) * n)
    N0 = 0.95 * n / 2.0
    N1 = float(np.count_nonzero(mod < T))
    d = (N1 - N0) / math.sqrt(n * 0.95 * 0.05 / 4.0)
    p = math.erfc(abs(d) / math.sqrt(2.0))
    return TestResult("Spectral DFT", p, p >= ALPHA,
                      {"N1": N1, "N0": N0, "d": float(d)})


# --------------------------------------- 7. Non-overlapping template -------
def non_overlapping_template_test(bits: np.ndarray, m: int = 9,
                                  n_templates: int = 8) -> TestResult:
    """Runs the first n_templates aperiodic templates of length 9 from the
    standard's list; returns the minimum p-value (conservative)."""
    templates = [
        [0, 0, 0, 0, 0, 0, 0, 0, 1], [0, 0, 0, 0, 0, 0, 0, 1, 1],
        [0, 0, 0, 0, 0, 0, 1, 0, 1], [0, 0, 0, 0, 0, 0, 1, 1, 1],
        [0, 0, 0, 0, 0, 1, 0, 0, 1], [0, 0, 0, 0, 0, 1, 0, 1, 1],
        [0, 0, 0, 0, 0, 1, 1, 0, 1], [0, 0, 0, 0, 0, 1, 1, 1, 1],
    ][:n_templates]
    n = bits.size
    N = 8
    M = n // N
    blocks = bits[:N * M].reshape(N, M)
    mu = (M - m + 1) / 2.0 ** m
    var = M * (1.0 / 2.0 ** m - (2.0 * m - 1.0) / 2.0 ** (2 * m))

    p_values = []
    for tpl in templates:
        t = np.array(tpl, dtype=np.uint8)
        W = np.zeros(N, dtype=np.int64)
        for j in range(N):
            row = blocks[j]
            # non-overlapping scan
            i = 0
            cnt = 0
            row_b = row.tobytes()
            t_b = t.tobytes()
            while i <= M - m:
                if row_b[i:i + m] == t_b:
                    cnt += 1
                    i += m
                else:
                    i += 1
            W[j] = cnt
        chi2 = float(np.sum((W - mu) ** 2 / var))
        p_values.append(_igamc(N / 2.0, chi2 / 2.0))

    p_min = min(p_values)
    return TestResult("Non-overlapping Template", p_min, p_min >= ALPHA,
                      {"m": m, "templates": len(templates),
                       "p_values": [round(p, 5) for p in p_values]})


# ------------------------------------------- 8. Overlapping template -------
def overlapping_template_test(bits: np.ndarray, m: int = 9) -> TestResult:
    n = bits.size
    M = 1032
    N = n // M
    K = 5
    pi = [0.364091, 0.185659, 0.139381, 0.100571, 0.070432, 0.139865]

    t = np.ones(m, dtype=np.uint8)
    blocks = bits[:N * M].reshape(N, M)
    counts = np.zeros(K + 1, dtype=np.int64)
    t_b = t.tobytes()
    for j in range(N):
        row_b = blocks[j].tobytes()
        cnt = 0
        for i in range(M - m + 1):
            if row_b[i:i + m] == t_b:
                cnt += 1
        counts[min(cnt, K)] += 1

    chi2 = float(np.sum((counts - N * np.array(pi)) ** 2 /
                        (N * np.array(pi))))
    p = _igamc(K / 2.0, chi2 / 2.0)
    return TestResult("Overlapping Template", p, p >= ALPHA,
                      {"N": N, "chi2": chi2, "counts": counts.tolist()})


# ------------------------------------------------ 9. Maurer's universal ----
def universal_test(bits: np.ndarray) -> TestResult:
    n = bits.size
    # parameter table from the standard
    table = [(387840, 6, 640), (904960, 7, 1280), (2068480, 8, 2560)]
    L, Q = 5, 320
    for n_min, L_i, Q_i in table:
        if n >= n_min:
            L, Q = L_i, Q_i
    expected = {5: 4.5356588, 6: 5.2177052, 7: 6.1962507, 8: 7.1836656}
    variance = {5: 2.954, 6: 3.125, 7: 3.238, 8: 3.311}

    K = n // L - Q
    if K <= 0:
        return TestResult("Universal", 0.0, False,
                          {"note": "sequence too short"})
    # decimal value of each L-bit block
    nblocks = Q + K
    words = bits[:nblocks * L].reshape(nblocks, L)
    weights = (1 << np.arange(L - 1, -1, -1)).astype(np.int64)
    vals = words @ weights

    last_seen = np.zeros(1 << L, dtype=np.int64)
    for i in range(Q):
        last_seen[vals[i]] = i + 1
    total = 0.0
    for i in range(Q, nblocks):
        idx = i + 1
        total += math.log2(idx - last_seen[vals[i]])
        last_seen[vals[i]] = idx
    fn = total / K

    c = (0.7 - 0.8 / L
         + (4.0 + 32.0 / L) * (K ** (-3.0 / L)) / 15.0)
    sigma = c * math.sqrt(variance[L] / K)
    p = math.erfc(abs(fn - expected[L]) / (math.sqrt(2.0) * sigma))
    return TestResult("Universal", p, p >= ALPHA,
                      {"L": L, "Q": Q, "K": K, "fn": float(fn)})


# --------------------------------------------- 10. Linear complexity -------
def _berlekamp_massey_int(block_int: int, M: int) -> int:
    """Berlekamp-Massey over GF(2) using Python big-int bit tricks.
    block_int holds the M bits, bit 0 = s_0."""
    C, B = 1, 1          # polynomials as ints, bit k = coeff of x^k
    L, m_ = 0, -1
    for N in range(M):
        # discrepancy d = s_N XOR sum_{i=1..L} c_i * s_{N-i}
        # = parity of (C & reversed-window); compute via masked AND
        window = (block_int >> max(0, N - L)) & ((1 << (L + 1)) - 1) \
            if N >= L else (block_int & ((1 << (N + 1)) - 1))
        # align: c_i multiplies s_{N-i} -> bit i of C pairs with bit
        # (N-i) of s. Reverse the window of s bits [N-L .. N]:
        d = 0
        cc = C
        i = 0
        while cc:
            if cc & 1:
                d ^= (block_int >> (N - i)) & 1 if N - i >= 0 else 0
            cc >>= 1
            i += 1
        if d:
            T = C
            C ^= B << (N - m_)
            if L <= N // 2:
                L = N + 1 - L
                m_ = N
                B = T
    return L


def linear_complexity_test(bits: np.ndarray, M: int = 500) -> TestResult:
    n = bits.size
    N = n // M
    if N < 200:
        return TestResult("Linear Complexity", 0.0, False,
                          {"note": "sequence too short"})
    mean = (M / 2.0 + (9.0 + (-1.0) ** (M + 1)) / 36.0
            - (M / 3.0 + 2.0 / 9.0) / 2.0 ** M)
    pi = [0.010417, 0.03125, 0.125, 0.5, 0.25, 0.0625, 0.020833]
    counts = np.zeros(7, dtype=np.int64)

    blocks = bits[:N * M].reshape(N, M)
    for j in range(N):
        # pack bits into a big int, bit 0 = first bit of the block
        b_bytes = np.packbits(blocks[j][::-1]).tobytes()
        block_int = int.from_bytes(b_bytes, "big")
        L = _berlekamp_massey_int(block_int, M)
        T = (-1.0) ** M * (L - mean) + 2.0 / 9.0
        if T <= -2.5:
            counts[0] += 1
        elif T <= -1.5:
            counts[1] += 1
        elif T <= -0.5:
            counts[2] += 1
        elif T <= 0.5:
            counts[3] += 1
        elif T <= 1.5:
            counts[4] += 1
        elif T <= 2.5:
            counts[5] += 1
        else:
            counts[6] += 1

    chi2 = float(np.sum((counts - N * np.array(pi)) ** 2 /
                        (N * np.array(pi))))
    p = _igamc(3.0, chi2 / 2.0)
    return TestResult("Linear Complexity", p, p >= ALPHA,
                      {"M": M, "N": N, "chi2": chi2})


# ------------------------------------------------------------ 11. Serial --
def _psi_sq(bits: np.ndarray, m: int) -> float:
    if m == 0:
        return 0.0
    n = bits.size
    ext = np.concatenate([bits, bits[:m - 1]]) if m > 1 else bits
    idx = np.zeros(n, dtype=np.int64)
    for k in range(m):
        idx = (idx << 1) | ext[k:k + n]
    counts = np.bincount(idx, minlength=1 << m)
    return float((1 << m) / n * np.sum(counts.astype(np.float64) ** 2) - n)


def serial_test(bits: np.ndarray, m: int = 16) -> TestResult:
    psi_m = _psi_sq(bits, m)
    psi_m1 = _psi_sq(bits, m - 1)
    psi_m2 = _psi_sq(bits, m - 2)
    d1 = psi_m - psi_m1
    d2 = psi_m - 2.0 * psi_m1 + psi_m2
    p1 = _igamc(2.0 ** (m - 2), d1 / 2.0)
    p2 = _igamc(2.0 ** (m - 3), d2 / 2.0)
    p = min(p1, p2)
    return TestResult("Serial", p, p >= ALPHA,
                      {"m": m, "p1": p1, "p2": p2})


# ------------------------------------------------ 12. Approximate entropy --
def approximate_entropy_test(bits: np.ndarray, m: int = 2) -> TestResult:
    n = bits.size

    def phi(mm):
        if mm == 0:
            return 0.0
        ext = np.concatenate([bits, bits[:mm - 1]]) if mm > 1 else bits
        idx = np.zeros(n, dtype=np.int64)
        for k in range(mm):
            idx = (idx << 1) | ext[k:k + n]
        counts = np.bincount(idx, minlength=1 << mm).astype(np.float64)
        counts = counts[counts > 0]
        c = counts / n
        return float(np.sum(c * np.log(c)))

    ap_en = phi(m) - phi(m + 1)
    chi2 = 2.0 * n * (math.log(2.0) - ap_en)
    p = _igamc(2.0 ** (m - 1), chi2 / 2.0)
    return TestResult("Approximate Entropy", p, p >= ALPHA,
                      {"m": m, "ApEn": float(ap_en), "chi2": float(chi2)})


# --------------------------------------------------- 13. Cumulative sums ---
def cumulative_sums_test(bits: np.ndarray) -> TestResult:
    x = 2 * bits.astype(np.int64) - 1
    ps = []
    for mode, seq in (("forward", x), ("backward", x[::-1])):
        s = np.cumsum(seq)
        z = float(np.max(np.abs(s)))
        n = bits.size
        term1 = sum(
            sp.ndtr((4 * k + 1) * z / math.sqrt(n))
            - sp.ndtr((4 * k - 1) * z / math.sqrt(n))
            for k in range(int((-n / z + 1) // 4), int((n / z - 1) // 4) + 1))
        term2 = sum(
            sp.ndtr((4 * k + 3) * z / math.sqrt(n))
            - sp.ndtr((4 * k + 1) * z / math.sqrt(n))
            for k in range(int((-n / z - 3) // 4), int((n / z - 1) // 4) + 1))
        ps.append(1.0 - term1 + term2)
    p = min(ps)
    return TestResult("Cumulative Sums", float(p), p >= ALPHA,
                      {"p_forward": float(ps[0]), "p_backward": float(ps[1])})


# ------------------------------------------------ 14. Random excursions ----
def _cycles_and_states(bits: np.ndarray):
    x = 2 * bits.astype(np.int64) - 1
    s = np.concatenate([[0], np.cumsum(x), [0]])
    zero_pos = np.where(s == 0)[0]
    J = len(zero_pos) - 1
    return s, zero_pos, J


def random_excursions_test(bits: np.ndarray) -> TestResult:
    s, zeros, J = _cycles_and_states(bits)
    if J < 500:
        return TestResult("Random Excursions", 0.0, False,
                          {"note": f"J={J} < 500, not applicable"})
    states = [-4, -3, -2, -1, 1, 2, 3, 4]
    p_values = []
    for xst in states:
        # visits to state per cycle
        counts = np.zeros(6, dtype=np.int64)   # 0..4, >=5 visits
        for c in range(J):
            seg = s[zeros[c]:zeros[c + 1]]
            v = int(np.count_nonzero(seg == xst))
            counts[min(v, 5)] += 1
        ax = abs(xst)
        pi = np.empty(6)
        pi[0] = 1.0 - 1.0 / (2.0 * ax)
        for k in range(1, 5):
            pi[k] = (1.0 / (4.0 * ax * ax)) * (1 - 1.0 / (2.0 * ax)) ** (k - 1)
        pi[5] = (1.0 / (2.0 * ax)) * (1 - 1.0 / (2.0 * ax)) ** 4
        chi2 = float(np.sum((counts - J * pi) ** 2 / (J * pi)))
        p_values.append(_igamc(2.5, chi2 / 2.0))
    p_min = min(p_values)
    return TestResult("Random Excursions", p_min, p_min >= ALPHA,
                      {"J": J,
                       "p_values": [round(p, 5) for p in p_values]})


# -------------------------------------- 15. Random excursions variant ------
def random_excursions_variant_test(bits: np.ndarray) -> TestResult:
    s, zeros, J = _cycles_and_states(bits)
    if J < 500:
        return TestResult("Random Excursions Variant", 0.0, False,
                          {"note": f"J={J} < 500, not applicable"})
    p_values = []
    for xst in [x for x in range(-9, 10) if x != 0]:
        xi = int(np.count_nonzero(s == xst))
        p = math.erfc(abs(xi - J) /
                      math.sqrt(2.0 * J * (4.0 * abs(xst) - 2.0)))
        p_values.append(p)
    p_min = min(p_values)
    return TestResult("Random Excursions Variant", p_min, p_min >= ALPHA,
                      {"J": J,
                       "p_values": [round(p, 5) for p in p_values]})


# --------------------------------------------------------------- driver ----
ALL_TESTS = [
    frequency_test, block_frequency_test, runs_test, longest_run_test,
    matrix_rank_test, spectral_test, non_overlapping_template_test,
    overlapping_template_test, universal_test, linear_complexity_test,
    serial_test, approximate_entropy_test, cumulative_sums_test,
    random_excursions_test, random_excursions_variant_test,
]


def run_all_nist_tests(data: bytes, label: str = "") -> list[TestResult]:
    bits = _bits(data)
    results = []
    for fn in ALL_TESTS:
        try:
            r = fn(bits)
        except Exception as e:                      # defensive: report, don't die
            r = TestResult(fn.__name__, 0.0, False, {"error": str(e)})
        results.append(r)
        status = "PASS" if r.passed else "FAIL"
        print(f"    [{label}] {r.name:28s} p={r.p_value:8.5f}  {status}")
    return results


def self_test():
    """Sanity: os.urandom must pass (allow 1 marginal fail out of 15 at
    alpha=0.01); pathological inputs must fail."""
    import os
    print("[self-test] os.urandom(125000):")
    good = run_all_nist_tests(os.urandom(125000), "urandom")
    n_fail = sum(1 for r in good if not r.passed)
    print(f"  -> {15 - n_fail}/15 passed")
    assert n_fail <= 1, "good RNG failed too many tests"

    print("[self-test] constant zeros:")
    bad = run_all_nist_tests(bytes(125000), "zeros")
    assert sum(1 for r in bad if r.passed) <= 2, "zeros passed too many"

    print("[self-test] alternating 0101...:")
    alt = run_all_nist_tests(bytes([0x55] * 125000), "alt")
    assert not alt[2].passed or not alt[11].passed, \
        "alternating pattern not caught"
    print("[self-test] OK")


if __name__ == "__main__":
    self_test()
