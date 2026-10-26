# -*- coding: utf-8 -*-
"""Codes-barres et codes QR.

* LIRE un code sur une image (photo, trame de webcam) : bibliothèque
  `zxing-cpp` (Apache 2.0, ≈ 1 Mo, roues pour Windows, macOS et Linux, sans
  dépendance) — EAN-13/8, UPC, Code 128, QR… Rien ne part en ligne.
* ÉCRIRE un code QR (étiquettes de casier) : `segno` (BSD, Python pur).

Les deux sont facultatives au sens où l'application démarre sans elles :
`lecture_disponible()` / `ecriture_disponible()` le disent et l'interface
explique quoi installer. Le code d'une bouteille est `bouteille.code_interne`
(« V » + 10 caractères, posé à la création) ; l'étiquette QR le contient tel
quel, la douchette (lecteur qui tape au clavier) le saisit de même."""
from __future__ import annotations

import re
from dataclasses import dataclass

#: code interne Vendémiaire (bouteille) ; ancien import CellarTracker : « CT… »
MOTIF_INTERNE = re.compile(r"^(V[0-9A-F]{10}|CT\d+)$")


@dataclass
class CodeLu:
    texte: str
    format: str            # « QRCode », « EAN13 »…

    @property
    def interne(self) -> bool:
        return bool(MOTIF_INTERNE.match(self.texte.strip()))

    @property
    def ean(self) -> bool:
        return self.format.upper().replace("-", "").replace(" ", "") in ("EAN13", "EAN8", "UPCA", "UPCE") \
            and self.texte.isdigit()


def lecture_disponible() -> bool:
    import importlib.util
    return importlib.util.find_spec("zxingcpp") is not None


def ecriture_disponible() -> bool:
    import importlib.util
    return importlib.util.find_spec("segno") is not None


def lire_qimage(image) -> list[CodeLu]:
    """Codes trouvés sur une QImage (copie en niveaux de gris, sans numpy)."""
    import zxingcpp
    from PyQt6.QtGui import QImage
    gris = image.convertToFormat(QImage.Format.Format_Grayscale8)
    l, h, ligne = gris.width(), gris.height(), gris.bytesPerLine()
    if l == 0 or h == 0:
        return []
    brut = bytes(gris.constBits().asstring(ligne * h))
    if ligne != l:                                   # lignes alignées sur 4 octets : on retire le bourrage
        brut = b"".join(brut[i * ligne:i * ligne + l] for i in range(h))
    vue = memoryview(brut).cast("B", (h, l))
    sortie = []
    for r in zxingcpp.read_barcodes(vue):
        if r.text:
            sortie.append(CodeLu(r.text, str(r.format).split(".")[-1]))
    return sortie


def lire_fichier(chemin) -> list[CodeLu]:
    from PyQt6.QtGui import QImage
    img = QImage(str(chemin))
    if img.isNull():
        return []
    return lire_qimage(img)


def matrice_qr(texte: str) -> list[list[bool]]:
    """Modules du code QR (sans la marge), niveau de correction M."""
    import segno
    q = segno.make(texte, error="m", micro=False)
    return [[bool(x) for x in rangee] for rangee in q.matrix]

