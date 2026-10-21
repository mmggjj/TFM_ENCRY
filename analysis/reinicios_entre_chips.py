#!/usr/bin/env python3
"""Prueba de reinicios del ESP32: ¿dos chips distintos sacan la misma
secuencia cuando el generador no recibe ruido?

Junta los bloques de varias capturas (chip y variante) y busca, como
reinicios_90b.flujo_comun, bloques que sean el mismo flujo de palabras de
32 bits leido desde otro punto: el inicio de un bloque (dos palabras)
aparece desplazado dentro de otro y el solape entero coincide. Agrupa los
bloques alineables (union-find) y cuenta, por grupo, de que captura viene
cada bloque. Si el generador arranca de un estado propio de cada chip, los
grupos de un chip no contienen bloques del otro; si arranca de un estado
fijo de diseño, los mismos grupos aparecen en los dos.

    python analysis/reinicios_entre_chips.py

Salida: results/esp32_reinicios/entre_chips.md.
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

import numpy as np

DIR = Path(__file__).resolve().parent.parent / "results" / "esp32_reinicios"
# (etiqueta, mac, variante, fichero): lecturas sin ruido de arranque
CAPTURAS = [
    ("chip a0:dd:6c:0e:fb:4c, sin_ruido", "a0dd6c0efb4c", "sin_ruido", "reinicios.bin"),
    ("chip f8:b3:b7:2a:09:28, sin_ruido", "f8b3b72a0928", "sin_ruido", "reinicios.bin"),
    ("chip a0:dd:6c:0e:fb:4c, espera_sin_ruido \"antes\"", "a0dd6c0efb4c", "espera_sin_ruido", "reinicios_antes.bin"),
    ("chip a0:dd:6c:0e:fb:4c, espera_sin_ruido \"despues\"", "a0dd6c0efb4c", "espera_sin_ruido", "reinicios.bin"),
    ("chip a0:dd:6c:0e:fb:4c, radio_sin_ruido \"antes\"", "a0dd6c0efb4c", "radio_sin_ruido", "reinicios_antes.bin"),
    ("chip f8:b3:b7:2a:09:28, fuente_control \"antes\"", "f8b3b72a0928", "fuente_control", "reinicios_antes.bin"),
    ("chip f8:b3:b7:2a:09:28, fuente_control \"despues\"", "f8b3b72a0928", "fuente_control", "reinicios.bin"),
    # con el ruido del arranque, como contraste: no debe alinearse con nada
    ("chip a0:dd:6c:0e:fb:4c, normal", "a0dd6c0efb4c", "normal", "reinicios.bin"),
    ("chip f8:b3:b7:2a:09:28, normal", "f8b3b72a0928", "normal", "reinicios.bin"),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    etq, blo = [], []
    for nombre, mac, var, fich in CAPTURAS:
        r = DIR / f"mac_{mac}" / var / fich
        if not r.exists():
            continue
        b = np.fromfile(r, dtype=np.uint8).reshape(-1, 1024)
        etq += [nombre] * len(b)
        blo.append(b)
    B = np.concatenate(blo)
    W = B.view("<u4").reshape(len(B), -1)
    n, nw = W.shape
    idx: dict = collections.defaultdict(list)
    for i in range(n):
        for p in range(nw - 1):
            idx[(W[i, p], W[i, p + 1])].append((i, p))
    padre = list(range(n))

    def raiz(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    rel = mal = 0
    rel_entre: collections.Counter = collections.Counter()
    for i in range(n):
        for j, p in idx[(W[i, 0], W[i, 1])]:
            if j == i:
                continue
            rel += 1
            if not np.array_equal(W[i, :nw - p], W[j, p:]):
                mal += 1
                continue
            padre[raiz(i)] = raiz(j)
            if etq[i] != etq[j]:
                rel_entre[tuple(sorted((etq[i], etq[j])))] += 1
    comp: dict = collections.defaultdict(collections.Counter)
    for i in range(n):
        comp[raiz(i)][etq[i]] += 1
    exactos: dict = {}
    for i in range(n):
        exactos.setdefault(B[i].tobytes(), set()).add(etq[i])

    nombres = list(dict.fromkeys(etq))
    lin = ["# Prueba de reinicios: lecturas sin ruido de dos chips", "",
           "Generado por analysis/reinicios_entre_chips.py. Un grupo es un conjunto de bloques de 1024 B "
           "que se alinean entre sí (el inicio de uno aparece desplazado dentro de otro y el solape entero "
           "coincide palabra a palabra).", "",
           f"{n} bloques; {rel} relaciones de desplazamiento, de ellas {mal} con el solape distinto; "
           f"{len(comp)} grupos.", "",
           "| Captura | Bloques | Grupos en que está | Grupos solo suyos | Bloques idénticos a alguno de otra captura |",
           "|---|---|---|---|---|"]
    for nm in nombres:
        en = [c for c in comp.values() if nm in c]
        solos = sum(1 for c in en if len(c) == 1)
        ident = sum(1 for i in range(n) if etq[i] == nm and len(exactos[B[i].tobytes()]) > 1)
        lin.append(f"| {nm} | {etq.count(nm)} | {len(en)} | {solos} | {ident} |")
    lin += ["", "Grupos compartidos entre capturas (número de grupos con bloques de las dos):", "",
            "| Captura 1 | Captura 2 | Grupos comunes | Relaciones de desplazamiento entre ellas |", "|---|---|---|---|"]
    for a in range(len(nombres)):
        for b in range(a + 1, len(nombres)):
            x, y = nombres[a], nombres[b]
            k = sum(1 for c in comp.values() if x in c and y in c)
            r = rel_entre.get(tuple(sorted((x, y))), 0)
            if k or r:
                lin.append(f"| {x} | {y} | {k} | {r} |")
    # cifras dirigidas entre las dos capturas sin ruido de los dos chips
    x, y = CAPTURAS[0][0], CAPTURAS[1][0]
    ix = [i for i in range(n) if etq[i] == x]
    iy = [i for i in range(n) if etq[i] == y]
    cx = {B[i].tobytes() for i in ix}
    cy = {B[i].tobytes() for i in iy}
    comunes = cx & cy
    lin += ["", f"Entre \"{x}\" y \"{y}\":", "",
            f"- contenidos de 1024 B distintos que salen en los dos: {len(comunes)} (de {len(cx)} y {len(cy)} distintos);",
            f"- bloques idénticos a alguno del otro chip: {sum(B[i].tobytes() in comunes for i in ix)} de {len(ix)} "
            f"y {sum(B[i].tobytes() in comunes for i in iy)} de {len(iy)};"]
    sx = set(ix)
    for a_, b_, na, nb in ((iy, sx, y, x), (ix, set(iy), x, y)):
        empiezan = set()
        cand = rel0 = relp = 0
        for i in a_:
            for j, p in idx[(W[i, 0], W[i, 1])]:
                if j not in b_:
                    continue
                cand += 1
                if np.array_equal(W[i, :nw - p], W[j, p:]):
                    empiezan.add(i)
                    rel0 += 1
                    relp += p > 0
        lin.append(f"- bloques de \"{na}\" que empiezan dentro de alguno de \"{nb}\" (desfase ≥ 0 palabras): "
                   f"{len(empiezan)} de {len(a_)}, en {rel0} relaciones ({relp} con desfase > 0); "
                   f"{cand - rel0} de {cand} con el solape distinto.")
    lin.append("")
    (DIR / "entre_chips.md").write_text("\n".join(lin) + "\n", encoding="utf-8")
    print("\n".join(lin))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
