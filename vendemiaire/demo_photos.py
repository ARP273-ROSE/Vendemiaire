# -*- coding: utf-8 -*-
"""Photos d'étiquette de DÉMONSTRATION, dessinées ici (libres de droits) :
une étiquette inventée, posée de travers sur un fond sombre, comme une photo
prise au téléphone. Servent aux essais (détection des bords, OCR) et aux
captures d'écran — jamais une vraie étiquette ni une image protégée.
"""
from __future__ import annotations

import random
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (QColor, QFont, QImage, QLinearGradient, QPainter, QPen, QPolygonF,
                         QTransform)

from . import style


def dessiner_etiquette(vin: dict, largeur: int = 900, hauteur: int = 1200) -> QImage:
    """Étiquette plate, lisible (gros caractères), aux couleurs du vin."""
    img = QImage(largeur, hauteur, QImage.Format.Format_RGB32)
    img.fill(QColor("#F7F0DC"))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    teinte = QColor(style.TEINTES_VIN.get(vin.get("couleur"), style.TEINTES_VIN[None]))
    p.setPen(QPen(QColor(style.OR), 6))
    p.drawRect(QRectF(30, 30, largeur - 60, hauteur - 60))
    p.setPen(QPen(teinte, 3))
    p.drawRect(QRectF(48, 48, largeur - 96, hauteur - 96))

    def texte(y, h, chaine, taille, gras=False, couleur=None, famille=None):
        f = QFont(famille or "DejaVu Serif")
        f.setPixelSize(taille)
        f.setBold(gras)
        p.setFont(f)
        p.setPen(QColor(couleur or style.ENCRE))
        p.drawText(QRectF(70, y, largeur - 140, h),
                   Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, chaine)

    texte(110, 200, (vin.get("producteur") or "").upper(), 74, True, style.BORDEAUX)
    if vin.get("cuvee"):
        texte(330, 110, vin["cuvee"], 62)
    p.fillRect(QRectF(240, 470, largeur - 480, 6), QColor(style.OR))
    texte(510, 120, vin.get("appellation") or "", 66, True)
    texte(630, 70, "APPELLATION " + (vin.get("appellation") or "").upper() + " CONTRÔLÉE", 30)
    if vin.get("millesime"):
        texte(740, 170, str(vin["millesime"]), 140, True, style.BORDEAUX)
    texte(940, 70, "MIS EN BOUTEILLE À LA PROPRIÉTÉ", 30)
    texte(1030, 70, f"{str(vin.get('degre') or 13).replace('.', ',')} % vol        75 cl", 40)
    p.end()
    return img


def photographier(etiquette: QImage, largeur: int = 1600, hauteur: int = 1200,
                  graine: int = 7, coins: list[tuple[float, float]] | None = None) -> tuple[QImage, list]:
    """Pose l'étiquette en perspective sur un fond sombre bruité. Renvoie la
    photo et les vrais coins (haut-gauche, haut-droit, bas-droit, bas-gauche)."""
    hasard = random.Random(graine)
    photo = QImage(largeur, hauteur, QImage.Format.Format_RGB32)
    p = QPainter(photo)
    degrade = QLinearGradient(0, 0, largeur, hauteur)
    degrade.setColorAt(0, QColor("#2B1A1E"))
    degrade.setColorAt(1, QColor("#120B0D"))
    p.fillRect(QRectF(0, 0, largeur, hauteur), degrade)
    for _ in range(1500):                             # grain du capteur
        g = hasard.randint(20, 70)
        p.fillRect(QRectF(hasard.uniform(0, largeur), hauteur * hasard.random(), 2, 2),
                   QColor(g, g - 8 if g > 8 else g, g - 5 if g > 5 else g))
    if coins is None:
        coins = [(largeur * 0.30 + hasard.uniform(-20, 20), hauteur * 0.10),
                 (largeur * 0.71, hauteur * 0.14 + hasard.uniform(-15, 15)),
                 (largeur * 0.68, hauteur * 0.90),
                 (largeur * 0.27, hauteur * 0.86 + hasard.uniform(-15, 15))]
    t = QTransform()
    QTransform.quadToQuad(
        QPolygonF([QPointF(0, 0), QPointF(etiquette.width(), 0),
                   QPointF(etiquette.width(), etiquette.height()), QPointF(0, etiquette.height())]),
        QPolygonF([QPointF(x, y) for x, y in coins]), t)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setTransform(t)
    p.drawImage(0, 0, etiquette)
    p.end()
    return photo, coins


def generer(vin: dict, chemin: str | Path, graine: int = 7) -> tuple[Path, list]:
    photo, coins = photographier(dessiner_etiquette(vin), graine=graine)
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    photo.save(str(chemin), "JPG", 92)
    return chemin, coins
