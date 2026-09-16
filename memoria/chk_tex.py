"""Comprobacion estatica de un capitulo LaTeX sin compilador disponible."""
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(sys.argv[1])
CAP = RAIZ / "memoria" / "chapters" / sys.argv[2]

texto = CAP.read_text(encoding="utf-8")
fallos = 0


def chk(cond, msg):
    global fallos
    print(f"  [{'ok ' if cond else 'FALLO'}] {msg}")
    if not cond:
        fallos += 1


print(f"Comprobacion estatica de {CAP.name}\n")

ini = Counter(re.findall(r"\\begin\{(\w+\*?)\}", texto))
fin = Counter(re.findall(r"\\end\{(\w+\*?)\}", texto))
chk(ini == fin, f"entornos balanceados ({sum(ini.values())} begin / {sum(fin.values())} end)")
for k in set(ini) | set(fin):
    if ini[k] != fin[k]:
        print(f"      descuadre en '{k}': {ini[k]} begin, {fin[k]} end")

chk(texto.count("{") == texto.count("}"), f"llaves balanceadas ({texto.count('{')})")

bib = (RAIZ / "memoria" / "references.bib").read_text(encoding="utf-8", errors="replace")
claves = set(re.findall(r"^@\w+\{([^,]+),", bib, re.M))
citadas = set()
for m in re.findall(r"\\cite\{([^}]+)\}", texto):
    citadas.update(c.strip() for c in m.split(","))
faltan = sorted(citadas - claves)
chk(not faltan, f"las {len(citadas)} claves citadas existen en references.bib")
for c in faltan:
    print(f"      falta en el bib: {c}")

labels = set()
for f in (RAIZ / "memoria" / "chapters").glob("*.tex"):
    labels.update(re.findall(r"\\label\{([^}]+)\}", f.read_text(encoding="utf-8")))
refs = set(re.findall(r"\\ref\{([^}]+)\}", texto))
rotas = sorted(refs - labels)
chk(not rotas, f"las {len(refs)} referencias cruzadas resuelven")
for r in rotas:
    print(f"      referencia rota: {r}")

acs = set(re.findall(r"\\ac\{(\w+)\}", texto))
defs = set(re.findall(r"\\acro\{(\w+)\}", (RAIZ / "memoria" / "tfm_main.tex").read_text(encoding="utf-8")))
sin = sorted(acs - defs)
chk(not sin, f"los {len(acs)} acronimos usados estan definidos")
for a in sin:
    print(f"      acronimo sin definir: {a}")

patron = r"\\begin\{tabular\}\{@\{\}([^}]*)@\{\}\}(.*?)\\end\{tabular\}"
for i, (spec, cuerpo) in enumerate(re.findall(patron, texto, re.S), 1):
    ncol = len(re.findall(r"[lrcp]", re.sub(r"\{[^}]*\}", "", spec)))
    filas = [f for f in cuerpo.split("\\\\") if "&" in f and "rule" not in f]
    malas = [" ".join(f.split())[:55] for f in filas if f.count("&") + 1 != ncol]
    chk(not malas, f"tabla {i}: {ncol} columnas declaradas, {len(filas)} filas coherentes")
    for m in malas:
        print(f"      fila con otro numero de columnas: {m}")

print(f"\n{CAP.stem}: {fallos} fallos")
sys.exit(0 if fallos == 0 else 1)
