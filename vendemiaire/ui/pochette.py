# -*- coding: utf-8 -*-
"""La « pochette » d'un vin : sa photo d'étiquette, ou à défaut une étiquette
dessinée (crème, liseré à la couleur du vin, producteur, cuvée, millésime).

Vignettes en cache mémoire (clé : vin, taille, fichier) ; la photo d'origine
n'est jamais modifiée.
"""
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap

from .. import style

_cache: dict = {}


def vider_cache() -> None:
    _cache.clear()


def pochette(vin: dict, largeur: int, hauteur: int, image=None, cache=None) -> QPixmap:
    """`cache` : dossier des vignettes sur disque (une photo de 12 Mpx n'est
    alors décodée qu'une fois, à la bonne taille)."""
    cle = (vin.get("id"), largeur, hauteur, str(image) if image else None,
           vin.get("producteur"), vin.get("cuvee"), vin.get("millesime"), vin.get("couleur"))
    if cle in _cache:
        return _cache[cle]
    if image and cache:
        from ..images import vignette
        v = vignette(image, largeur * 2, hauteur * 2, cache)       # ×2 : écrans haute densité
        image = v or image
    if image:
        pm = QPixmap(str(image))
        if not pm.isNull():
            pm = pm.scaled(largeur, hauteur, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            _cache[cle] = pm
            return pm
    pm = etiquette_dessinee(vin, largeur, hauteur)
    _cache[cle] = pm
    return pm


def etiquette_dessinee(vin: dict, largeur: int, hauteur: int) -> QPixmap:
    pm = QPixmap(largeur, hauteur)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    teinte = QColor(style.TEINTES_VIN.get(vin.get("couleur"), style.TEINTES_VIN[None]))
    cadre = QRectF(1.5, 1.5, largeur - 3, hauteur - 3)
    chemin = QPainterPath()
    chemin.addRoundedRect(cadre, 6, 6)
    p.fillPath(chemin, QColor("#FBF5E6"))
    p.setPen(QPen(teinte, max(2.0, largeur / 40)))
    p.drawPath(chemin)
    marge = max(4.0, largeur / 14)
    interieur = cadre.adjusted(marge, marge, -marge, -marge)
    p.setPen(QPen(QColor(style.OR), 1))
    p.drawRect(interieur)
    # bandeau de couleur en bas
    bandeau = QRectF(interieur.left(), interieur.bottom() - interieur.height() * 0.16,
                     interieur.width(), interieur.height() * 0.16)
    p.fillRect(bandeau, teinte)
    texte_zone = interieur.adjusted(3, 3, -3, -bandeau.height() - 2)
    if hauteur < 60:                     # vignette de liste : le texte serait illisible
        p.setPen(QPen(QColor(style.BORD), 1))
        for i in range(3):
            y = texte_zone.top() + texte_zone.height() * (0.3 + 0.2 * i)
            p.drawLine(int(texte_zone.left() + 2), int(y), int(texte_zone.right() - 2), int(y))
        p.end()
        return pm
    titre = QFont(style.FAMILLE_TITRES)
    titre.setBold(True)
    titre.setPixelSize(max(7, int(hauteur / 11)))
    p.setFont(titre)
    p.setPen(QColor(style.BORDEAUX))
    producteur = vin.get("producteur") or ""
    p.drawText(QRectF(texte_zone.left(), texte_zone.top(), texte_zone.width(),
                      texte_zone.height() * 0.55),
               Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, producteur)
    corps = QFont(style.FAMILLE)
    corps.setPixelSize(max(6, int(hauteur / 15)))
    p.setFont(corps)
    p.setPen(QColor(style.ENCRE))
    lignes = [x for x in (vin.get("cuvee"), vin.get("appellation")) if x]
    p.drawText(QRectF(texte_zone.left(), texte_zone.top() + texte_zone.height() * 0.55,
                      texte_zone.width(), texte_zone.height() * 0.45),
               Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
               "\n".join(lignes))
    mil = vin.get("millesime")
    if mil:
        f = QFont(style.FAMILLE_TITRES)
        f.setBold(True)
        f.setPixelSize(max(7, int(bandeau.height() * 0.75)))
        p.setFont(f)
        p.setPen(QColor("#FFFFFF") if vin.get("couleur") in ("rouge", None) else QColor(style.ENCRE))
        p.drawText(bandeau, Qt.AlignmentFlag.AlignCenter, str(mil))
    p.end()
    return pm
