# -*- coding: utf-8 -*-
"""Compile les manuels docs/manuel-fr.tex et docs/manuel-en.tex en PDF (format
maison), avec Tectonic s'il est là, sinon XeLaTeX (trois passes), puis efface
les fichiers temporaires (.aux, .log, .out, .toc). Contrôles : aucun « $ » ni
caractère manquant, aucune référence indéfinie, nombre de pages.

    python outils/manuel.py            # les deux langues
    python outils/manuel.py fr

La construction des paquets les régénère aussi avec le Tectonic embarqué
(kit.json « outils » › tectonic › prechauffer).
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"


def compiler(langue: str) -> int:
    tex = DOCS / f"manuel-{langue}.tex"
    tectonic = shutil.which("tectonic")
    if tectonic:
        r = subprocess.run([tectonic, "-X", "compile", "--keep-logs", tex.name], cwd=DOCS,
                           capture_output=True, text=True)
        passes = [r]
    else:
        xelatex = shutil.which("xelatex")
        if not xelatex:
            raise SystemExit("ni tectonic ni xelatex dans le PATH")
        passes = [subprocess.run([xelatex, "-interaction=nonstopmode", "-halt-on-error", tex.name], cwd=DOCS,
                                 capture_output=True, text=True) for _ in range(3)]
    log = DOCS / f"manuel-{langue}.log"
    journal = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    for ext in (".aux", ".log", ".out", ".toc"):
        (DOCS / f"manuel-{langue}{ext}").unlink(missing_ok=True)
    if any(p.returncode for p in passes):
        print(journal[-3000:] or passes[-1].stdout[-3000:])
        return 1
    pdf = DOCS / f"manuel-{langue}.pdf"
    texte = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
    pages = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    n = re.search(r"Pages:\s+(\d+)", pages)
    manquants = journal.count("Missing character")
    indefinies = len(re.findall(r"Reference .* undefined", journal))
    debord = journal.count("Overfull \\hbox")
    print(f"manuel-{langue}.pdf : {n.group(1) if n else '?'} pages, {pdf.stat().st_size / 1e6:.1f} Mo ; "
          f"dollars {texte.count('$')}, caractères manquants {manquants}, références indéfinies {indefinies}, "
          f"débordements {debord}")
    for m in re.findall(r"Overfull \\hbox \(([\d.]+)pt too wide\) in paragraph at lines (\d+--\d+)", journal):
        print(f"   débordement de {m[0]} pt, lignes {m[1]}")
    for m in sorted(set(re.findall(r"Missing character: There is no (.) ", journal))):
        print("   caractère manquant :", repr(m))
    return 0 if not (texte.count("$") or manquants or indefinies) else 1


if __name__ == "__main__":
    sys.exit(max(compiler(l) for l in (sys.argv[1:] or ["fr", "en"])))
