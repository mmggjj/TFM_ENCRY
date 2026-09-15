#!/usr/bin/env python3
r"""Sanea references.bib para pdfLaTeX/IEEEtran: escapa _ & % # en los
campos de texto y transcribe a macros LaTeX los simbolos Unicode que la
fuente T1 no tiene. No toca url ni doi.

    python saneabib.py            (in situ, guarda copia .orig la primera vez)
"""
import re
import shutil
from pathlib import Path

BIB = Path(__file__).resolve().parent / "references.bib"
CAMPOS_TEXTO = {"title", "booktitle", "journal", "note", "author", "publisher",
                "institution", "howpublished", "organization", "series",
                "address", "school", "editor"}
SUSTITUCIONES = {
    "→": r"$\rightarrow$", "≥": r"$\geq$", "≤": r"$\leq$",
    "≈": r"$\approx$", "×": r"$\times$", "·": r"$\cdot$",
    "−": "--", "–": "--", "—": "---",
    "“": "``", "”": "''", "‘": "`", "’": "'",
    "…": r"\ldots{}", "µ": r"$\mu$", "μ": r"$\mu$",
    "σ": r"$\sigma$", "²": r"$^2$", "³": r"$^3$",
    "€": r"\texteuro{}", "ı": r"{\i}", "ß": r"{\ss}",
    "ł": r"{\l}", "ø": r"{\o}", "ő": r"{\H{o}}",
    "ű": r"{\H{u}}", "č": r"{\v{c}}", "š": r"{\v{s}}",
    "ž": r"{\v{z}}", "ř": r"{\v{r}}", "ć": r"{\'c}",
    "ń": r"{\'n}", "ś": r"{\'s}", "ź": r"{\'z}",
    "ę": r"{\k{e}}", "ą": r"{\k{a}}", "ğ": r"{\u{g}}",
    "ş": r"{\c{s}}", "ţ": r"{\c{t}}", " ": "~",
    " ": r"\,", " ": r"\,", "′": "'", "≤": r"$\leq$",
}


def arregla(m: re.Match) -> str:
    nombre, val = m.group(1), m.group(2)
    nuevo = val
    if nombre.lower() in CAMPOS_TEXTO:
        nuevo = re.sub(r"(?<!\\)_", r"\\_", nuevo)
        nuevo = re.sub(r"(?<!\\)&", r"\\&", nuevo)
        nuevo = re.sub(r"(?<!\\)%", r"\\%", nuevo)
        nuevo = re.sub(r"(?<!\\)#", r"\\#", nuevo)
    for k, v in SUSTITUCIONES.items():
        nuevo = nuevo.replace(k, v)
    return f"{nombre} = {{{nuevo}}}"


def main() -> None:
    copia = BIB.with_suffix(".bib.orig")
    if not copia.exists():
        shutil.copy(BIB, copia)
    s = BIB.read_text(encoding="utf-8")
    s2 = re.sub(r"(\w+)\s*=\s*\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}", arregla, s)
    BIB.write_text(s2, encoding="utf-8")
    restantes = sorted({c for c in s2 if ord(c) > 255})
    print("cambios:", sum(a != b for a, b in zip(s.splitlines(), s2.splitlines())), "lineas")
    print("caracteres fuera de Latin-1 que quedan:", [f"{c} U+{ord(c):04X}" for c in restantes][:40])


if __name__ == "__main__":
    main()
