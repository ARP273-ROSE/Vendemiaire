# -*- coding: utf-8 -*-
"""Logo de Vendémiaire : médaillon bordeaux, liseré or, verre, grappe et feuille.

UNE seule source : `branding/logo.svg`. Tout le reste en dérive — PNG 16 → 1024
(`docs/logo_*.png`, rendus par resvg : `outils/rendre_logo.js`), `.ico`
multi-tailles de l'installeur Windows, `.icns` de macOS, icône de fenêtre,
logo de la fenêtre « À propos » et du manuel. Jamais deux dessins.

    node outils/rendre_logo.js                 (PNG, depuis le SVG)
    python -m vendemiaire.logo --assembler     (ICO et ICNS, depuis les PNG)

`docs/logo.sha256` garde l'empreinte du SVG qui a servi au rendu : un test
vérifie que les fichiers dérivés ne sont pas en retard sur la source.
"""
from __future__ import annotations

import argparse
import hashlib
import struct
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SOURCE = RACINE / "branding" / "logo.svg"
DOCS = RACINE / "docs"
TAILLES = (16, 24, 32, 48, 64, 128, 256, 512, 1024)
TAILLES_ICO = (16, 24, 32, 48, 64, 128, 256)
#: types ICNS des images PNG (macOS 10.7+) : taille en pixels
_ICNS = (("icp4", 16), ("icp5", 32), ("icp6", 64), ("ic07", 128), ("ic08", 256),
         ("ic09", 512), ("ic10", 1024), ("ic11", 32), ("ic12", 64), ("ic13", 256),
         ("ic14", 512))


def empreinte_source() -> str:
    return hashlib.sha256(SOURCE.read_bytes()).hexdigest()


def png(taille: int) -> Path:
    return DOCS / f"logo_{taille}.png"


def ecrire_ico(chemin: Path) -> None:
    """ICO multi-tailles dont chaque image est un PNG embarqué (Vista et
    après) : assemblé à la main, Qt ne sait pas écrire ce format."""
    images = [(t, png(t).read_bytes()) for t in TAILLES_ICO]
    entete = struct.pack("<HHH", 0, 1, len(images))
    decalage = 6 + 16 * len(images)
    entrees, blocs = b"", b""
    for t, data in images:
        dim = 0 if t >= 256 else t
        entrees += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), decalage)
        decalage += len(data)
        blocs += data
    chemin.write_bytes(entete + entrees + blocs)


def ecrire_icns(chemin: Path) -> None:
    """Icône macOS assemblée à la main (sans iconutil, absent hors macOS)."""
    blocs = b""
    for code, t in _ICNS:
        data = png(t).read_bytes()
        blocs += code.encode("ascii") + struct.pack(">I", 8 + len(data)) + data
    chemin.write_bytes(b"icns" + struct.pack(">I", 8 + len(blocs)) + blocs)


def assembler() -> None:
    manque = [t for t in TAILLES if not png(t).exists()]
    if manque:
        raise SystemExit(f"PNG absents {manque} : lancer d'abord outils/rendre_logo.js")
    ecrire_ico(DOCS / "logo.ico")
    ecrire_icns(DOCS / "logo.icns")
    (DOCS / "logo.sha256").write_text(empreinte_source() + "  branding/logo.svg\n",
                                      encoding="utf-8")


# -- côté interface -----------------------------------------------------------

def icone():
    """Icône de fenêtre, en plusieurs tailles (depuis les PNG dérivés)."""
    from PyQt6.QtGui import QIcon
    ic = QIcon()
    for t in TAILLES_ICO:
        if png(t).exists():
            ic.addFile(str(png(t)))
    if ic.isNull() and SOURCE.exists():
        ic = QIcon(str(SOURCE))
    return ic


def pixmap(taille: int = 96):
    """Le logo pour « À propos », l'en-tête du tableau de bord, la pochette par défaut."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QPixmap
    for t in TAILLES:
        if t >= taille and png(t).exists():
            return QPixmap(str(png(t))).scaled(
                taille, taille, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
    return rendu_svg(taille)


def rendu_svg(taille: int):
    """Rendu direct du SVG source par Qt (repli si les PNG manquent)."""
    from PyQt6.QtCore import QRectF, Qt
    from PyQt6.QtGui import QImage, QPainter, QPixmap
    from PyQt6.QtSvg import QSvgRenderer
    img = QImage(taille, taille, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    r = QSvgRenderer(str(SOURCE))
    if r.isValid():
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r.render(p, QRectF(0, 0, taille, taille))
        p.end()
    return QPixmap.fromImage(img)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Icônes dérivées de branding/logo.svg")
    ap.add_argument("--assembler", action="store_true", help="écrire logo.ico, logo.icns")
    args = ap.parse_args(argv)
    if args.assembler:
        assembler()
        print("docs/logo.ico, docs/logo.icns, docs/logo.sha256 écrits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
