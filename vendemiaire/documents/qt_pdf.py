# -*- coding: utf-8 -*-
"""Repli sans LaTeX : HTML -> PDF par Qt (`QTextDocument` + `QPdfWriter`).

Toujours disponible, hors ligne, sur les trois systèmes. Qt ne lit qu'un
sous-ensemble du HTML et du CSS (tableaux, polices, couleurs, images) : les
documents sont écrits pour ce sous-ensemble. Les images SVG (petites cartes)
sont rendues en PNG et données au document comme ressources."""
from __future__ import annotations

from pathlib import Path


def _image_svg(svg_txt: str, echelle: float = 2.0):
    from PyQt6.QtCore import QByteArray, QRectF, Qt
    from PyQt6.QtGui import QImage, QPainter
    from PyQt6.QtSvg import QSvgRenderer
    r = QSvgRenderer(QByteArray(svg_txt.encode("utf-8")))
    taille = r.defaultSize()
    img = QImage(int(taille.width() * echelle), int(taille.height() * echelle), QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r.render(p, QRectF(0, 0, img.width(), img.height()))
    p.end()
    img.setDevicePixelRatio(echelle)
    return img


def document(html: str, images: dict | None = None):
    """QTextDocument prêt (images : {nom: svg (texte) | QImage | chemin})."""
    from PyQt6.QtCore import QUrl
    from PyQt6.QtGui import QImage, QTextDocument
    doc = QTextDocument()
    for nom, contenu in (images or {}).items():
        if isinstance(contenu, str) and contenu.lstrip().startswith("<svg"):
            img = _image_svg(contenu)
        elif isinstance(contenu, QImage):
            img = contenu
        else:
            img = QImage(str(contenu))
        doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(nom), img)
    doc.setHtml(html)
    return doc


def html_vers_pdf(html: str, chemin: str | Path, images: dict | None = None, a5: bool = False,
                  paysage: bool = False) -> None:
    from PyQt6.QtCore import QMarginsF
    from PyQt6.QtGui import QPageLayout, QPageSize, QPdfWriter
    doc = document(html, images)
    w = QPdfWriter(str(chemin))
    w.setResolution(300)
    w.setPageSize(QPageSize(QPageSize.PageSizeId.A5 if a5 else QPageSize.PageSizeId.A4))
    w.setPageOrientation(QPageLayout.Orientation.Landscape if paysage else QPageLayout.Orientation.Portrait)
    w.setPageMargins(QMarginsF(14, 14, 14, 14), QPageLayout.Unit.Millimeter)
    w.setCreator("Vendémiaire")
    doc.print(w)
