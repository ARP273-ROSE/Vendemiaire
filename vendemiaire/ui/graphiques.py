# -*- coding: utf-8 -*-
"""Graphiques des statistiques (QPainter, sans dépendance).

Règles suivies : un seul axe des ordonnées ; deux séries au plus, couleurs
vérifiées (bordeaux #8E2A3D et or #B8862E : écart perceptuel et contraste
suffisants, y compris pour les daltoniens), toujours avec une légende ; traits
fins, textes à l'encre (jamais à la couleur de la série) ; infobulle au survol."""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QSizePolicy, QToolTip, QWidget

from .. import style
from ..i18n import nombre

SERIES = ("#8E2A3D", "#B8862E")


def _police(p: QPainter, taille: int = 11) -> None:
    f = QFont(style.FAMILLE)
    f.setPixelSize(taille)
    p.setFont(f)


def _graduation(maxi: float) -> list[float]:
    if maxi <= 0:
        return [0.0]
    import math
    brut = maxi / 4
    puissance = 10 ** math.floor(math.log10(brut))
    pas = min((m * puissance for m in (1, 2, 2.5, 5, 10) if m * puissance >= brut), default=brut)
    return [pas * i for i in range(int(maxi / pas) + 2)]


class _Base(QWidget):
    def __init__(self, parent=None, hauteur: int = 230):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumHeight(hauteur)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.noms: list[str] = []
        self.format_valeur = lambda v: nombre(v, 0)

    def _zone(self) -> QRectF:
        return QRectF(self.rect()).adjusted(52, 26 if len(self.noms) > 1 else 10, -10, -24)

    def _legende(self, p: QPainter) -> None:
        if len(self.noms) < 2:
            return
        _police(p, 11)
        x = 52.0
        for i, nom in enumerate(self.noms):
            p.fillRect(QRectF(x, 6, 12, 12), QColor(SERIES[i]))
            p.setPen(QColor(style.ENCRE))
            l = p.fontMetrics().horizontalAdvance(nom)
            p.drawText(QRectF(x + 16, 2, l + 4, 20), Qt.AlignmentFlag.AlignVCenter, nom)
            x += l + 36

    def _axe_y(self, p: QPainter, zone: QRectF, maxi: float) -> float:
        ticks = _graduation(maxi)
        haut = ticks[-1] if ticks[-1] > 0 else 1
        _police(p, 10)
        for t in ticks:
            y = zone.bottom() - zone.height() * t / haut
            p.setPen(QPen(QColor(style.LIGNE), 1))
            p.drawLine(QPointF(zone.left(), y), QPointF(zone.right(), y))
            p.setPen(QColor(style.GRIS))
            p.drawText(QRectF(0, y - 8, zone.left() - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       self.format_valeur(t))
        return haut


class Courbes(_Base):
    """Une ou deux séries dans le temps : etiquettes (abscisses) et valeurs."""

    def definir(self, etiquettes: list[str], series: list[list[float]], noms: list[str]) -> None:
        self.etiquettes, self.series, self.noms = etiquettes, series, noms
        self.update()

    def paintEvent(self, _ev):
        if not getattr(self, "etiquettes", None):
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        zone = self._zone()
        haut = self._axe_y(p, zone, max(max(s) for s in self.series if s) or 1)
        n = len(self.etiquettes)
        pas = zone.width() / max(1, n - 1)
        for i, s in enumerate(self.series):
            chemin = QPainterPath()
            for j, v in enumerate(s):
                pt = QPointF(zone.left() + j * pas, zone.bottom() - zone.height() * v / haut)
                chemin.moveTo(pt) if j == 0 else chemin.lineTo(pt)
            p.setPen(QPen(QColor(SERIES[i]), 2))
            p.drawPath(chemin)
        _police(p, 10)
        p.setPen(QColor(style.GRIS))
        tous = max(1, n // 8)
        for j, e in enumerate(self.etiquettes):
            if j % tous == 0 or j == n - 1:
                x = zone.left() + j * pas
                p.drawText(QRectF(x - 34, zone.bottom() + 4, 68, 16), Qt.AlignmentFlag.AlignCenter, e)
        self._legende(p)
        p.end()

    def mouseMoveEvent(self, ev):
        if not getattr(self, "etiquettes", None):
            return
        zone = self._zone()
        pas = zone.width() / max(1, len(self.etiquettes) - 1)
        j = round((ev.position().x() - zone.left()) / pas)
        if 0 <= j < len(self.etiquettes):
            lignes = [self.etiquettes[j]] + [f"{n} : {self.format_valeur(s[j])}" for n, s in zip(self.noms, self.series)]
            QToolTip.showText(ev.globalPosition().toPoint(), "\n".join(lignes), self)


class BarresGroupees(_Base):
    """Une ou deux séries par catégorie (colonnes côte à côte, 2 px d'écart)."""

    def definir(self, etiquettes: list[str], series: list[list[float]], noms: list[str]) -> None:
        self.etiquettes, self.series, self.noms = etiquettes, series, noms
        self.update()

    def paintEvent(self, _ev):
        if not getattr(self, "etiquettes", None):
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        zone = self._zone()
        haut = self._axe_y(p, zone, max((max(s) for s in self.series if s), default=1) or 1)
        n, k = len(self.etiquettes), len(self.series)
        pas = zone.width() / n
        larg = min(28.0, (pas * 0.7 - 2 * (k - 1)) / k)
        for j in range(n):
            x0 = zone.left() + j * pas + (pas - (larg * k + 2 * (k - 1))) / 2
            for i, s in enumerate(self.series):
                h = zone.height() * s[j] / haut
                if h > 0:
                    r = QRectF(x0 + i * (larg + 2), zone.bottom() - h, larg, h)
                    chemin = QPainterPath()
                    chemin.addRoundedRect(r, 3, 3)
                    p.fillPath(chemin, QColor(SERIES[i]))
            _police(p, 10)
            p.setPen(QColor(style.GRIS))
            p.drawText(QRectF(zone.left() + j * pas, zone.bottom() + 4, pas, 16), Qt.AlignmentFlag.AlignCenter,
                       self.etiquettes[j])
        self._legende(p)
        p.end()

    def mouseMoveEvent(self, ev):
        if not getattr(self, "etiquettes", None):
            return
        zone = self._zone()
        j = int((ev.position().x() - zone.left()) // (zone.width() / len(self.etiquettes)))
        if 0 <= j < len(self.etiquettes):
            lignes = [self.etiquettes[j]] + [f"{n} : {self.format_valeur(s[j])}" for n, s in zip(self.noms, self.series)]
            QToolTip.showText(ev.globalPosition().toPoint(), "\n".join(lignes), self)
