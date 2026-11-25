"""Compara las cifras, etiquetas, referencias y citas de la memoria EN y ES.

Uso: python3 memoria/cmp_cifras.py  (desde la raiz del repositorio)
Quita los comentarios, normaliza el decimal ({,} y , -> .) y compara, por
capitulo, el multiconjunto de numeros y las listas de \\label, \\ref y \\cite.
Sale con 1 si algo difiere.
"""
import re
import sys
from collections import Counter
from pathlib import Path

MEM = Path(__file__).resolve().parent
PARES = [
    (["tfm_main.tex"], ["tfm_main_es.tex"]),
    (["chapters/ch1_intro.tex"], ["chapters_es/ch1_intro.tex"]),
    (["chapters/ch2_soa.tex"], ["chapters_es/ch2_soa.tex"]),
    (["chapters/esp32_blackbox.tex"], ["chapters_es/esp32_blackbox.tex"]),
    (["chapters/ch3_entropy.tex"], ["chapters_es/ch3_entropy.tex"]),
    (["chapters/ch4_engine.tex"], ["chapters_es/ch4_engine.tex"]),
    (["chapters/ch5_verification.tex"], ["chapters_es/ch5_verification.tex"]),
    (["chapters/ch6_asic.tex"], ["chapters_es/ch6_asic.tex"]),
    (["chapters/ch7_results.tex"],
     ["chapters_es/ch7_results_a.tex", "chapters_es/ch7_results_b.tex"]),
    (["chapters/ch8_concl.tex"], ["chapters_es/ch8_concl.tex"]),
    (["chapters/appendices.tex"], ["chapters_es/appendices.tex"]),
    (["chapters/app_fpga.tex"], ["chapters_es/app_fpga.tex"]),
]


def lee(ficheros):
    t = "".join((MEM / f).read_text(encoding="utf-8") for f in ficheros)
    return re.sub(r"(?<!\\)%.*", "", t)


def numeros(t):
    t = t.replace("{,}", ".")
    t = re.sub(r"(\d)\\,(\d)", r"\1\2", t)           # separador de miles
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)            # coma decimal
    return Counter(re.findall(r"\d+(?:\.\d+)?", t))


def lista(t, orden):
    out = []
    for m in re.findall(r"\\" + orden + r"\{([^}]*)\}", t):
        out.extend(x.strip() for x in m.split(","))
    return out


fallos = 0
for en, es in PARES:
    a, b = lee(en), lee(es)
    na, nb = numeros(a), numeros(b)
    solo_en, solo_es = na - nb, nb - na
    ok = not solo_en and not solo_es
    print(f"[{'ok ' if ok else 'DIF'}] {en[0]}: {sum(na.values())} numeros EN, "
          f"{sum(nb.values())} ES")
    if not ok:
        fallos += 1
        print(f"      solo EN: {dict(solo_en)}")
        print(f"      solo ES: {dict(solo_es)}")
    for orden in ("label", "ref", "eqref", "cite"):
        la, lb = lista(a, orden), lista(b, orden)
        if Counter(la) != Counter(lb):
            fallos += 1
            print(f"      \\{orden} distintos: solo EN "
                  f"{sorted((Counter(la) - Counter(lb)).elements())}, solo ES "
                  f"{sorted((Counter(lb) - Counter(la)).elements())}")
print(f"\ncmp_cifras: {fallos} diferencias")
sys.exit(1 if fallos else 0)
