# -*- coding: utf-8 -*-
"""Tableau de bord simple : chiffres clés, répartitions, alertes, derniers mouvements.

Les répartitions sont des barres horizontales d'une seule teinte (une seule
série par graphique : la couleur ne porte aucune identité, le libellé si) ;
valeurs et libellés en encre, jamais à la couleur de la barre.
"""
from __future__ import annotations

from PyQt6.QtCore import QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath
from PyQt6.QtWidgets import (QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                             QListWidget, QScrollArea, QSizePolicy, QToolTip, QVBoxLayout,
                             QWidget)

from .. import logo, regles, style
from ..i18n import argent, date_affichee, lib, nombre, tr


class Barres(QWidget):
    """Barres horizontales : [(libellé, valeur)]."""

    HAUTEUR = 22

    def __init__(self, parent=None):
        super().__init__(parent)
        self.donnees: list[tuple[str, float]] = []
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def definir(self, donnees: list[tuple[str, float]]) -> None:
        self.donnees = donnees
        self.setFixedHeight(max(1, len(donnees)) * (self.HAUTEUR + 2) + 4)
        self.update()

    def sizeHint(self):
        return QSize(320, self.height())

    def _geometrie(self):
        largeur_lib = min(150, int(self.width() * 0.38))
        largeur_val = 44
        zone = self.width() - largeur_lib - largeur_val - 12
        return largeur_lib, largeur_val, max(10, zone)

    def paintEvent(self, _ev):
        if not self.donnees:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        largeur_lib, largeur_val, zone = self._geometrie()
        maxi = max(v for _l, v in self.donnees) or 1
        police = QFont(style.FAMILLE)
        police.setPixelSize(12)
        p.setFont(police)
        for i, (lib_, v) in enumerate(self.donnees):
            y = 2 + i * (self.HAUTEUR + 2)
            p.setPen(QColor(style.ENCRE))
            p.drawText(QRectF(0, y, largeur_lib - 6, self.HAUTEUR),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       p.fontMetrics().elidedText(lib_, Qt.TextElideMode.ElideRight, largeur_lib - 8))
            w = max(2.0, zone * v / maxi)
            barre = QRectF(largeur_lib, y + 4, w, self.HAUTEUR - 8)
            chemin = QPainterPath()
            chemin.addRoundedRect(barre, 4, 4)
            p.fillPath(chemin, QColor(style.BORDEAUX))
            p.setPen(QColor(style.GRIS))
            p.drawText(QRectF(largeur_lib + w + 6, y, largeur_val, self.HAUTEUR),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       nombre(v, 0))
        p.end()

    def mouseMoveEvent(self, ev):
        i = int((ev.position().y() - 2) // (self.HAUTEUR + 2))
        if 0 <= i < len(self.donnees):
            l, v = self.donnees[i]
            QToolTip.showText(ev.globalPosition().toPoint(), f"{l} : {nombre(v, 0)}", self)
        else:
            QToolTip.hideText()


def _tuile(chiffre: str, legende: str) -> tuple[QFrame, QLabel]:
    cadre = QFrame()
    cadre.setObjectName("tuile")
    l = QVBoxLayout(cadre)
    c = QLabel(chiffre)
    c.setObjectName("chiffre")
    t = QLabel(legende)
    t.setObjectName("legende")
    l.addWidget(c)
    l.addWidget(t)
    return cadre, c


def _regrouper(paires, garder: int, enum: str | None = None) -> list[tuple[str, float]]:
    paires = [(lib(enum, k) if enum else (str(k) if k is not None else tr("tableau.inconnu")), n)
              for k, n in paires]
    paires = [(k or tr("tableau.inconnu"), n) for k, n in paires]
    if len(paires) <= garder:
        return paires
    tete, reste = paires[:garder - 1], paires[garder - 1:]
    return tete + [(tr("tableau.autres"), sum(n for _k, n in reste))]


class TableauDeBord(QScrollArea):
    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        self.setWidgetResizable(True)
        corps = QWidget()
        self.setWidget(corps)
        racine = QVBoxLayout(corps)
        entete = QHBoxLayout()
        image = QLabel()
        image.setPixmap(logo.pixmap(72))
        entete.addWidget(image)
        titres = QVBoxLayout()
        t = QLabel(tr("app.nom"))
        t.setObjectName("titre")
        self.sous_titre = QLabel()
        self.sous_titre.setObjectName("sous_titre")
        titres.addWidget(t)
        titres.addWidget(self.sous_titre)
        entete.addLayout(titres, 1)
        racine.addLayout(entete)

        tuiles = QHBoxLayout()
        self.chiffres = {}
        for cle in ("bouteilles", "vins", "a_venir", "litres", "prix_total", "valeur_estimee"):
            cadre, c = _tuile("–", tr(f"tableau.{cle}"))
            self.chiffres[cle] = c
            tuiles.addWidget(cadre)
        racine.addLayout(tuiles)

        grille = QGridLayout()
        self.barres = {}
        for i, cle in enumerate(("par_couleur", "par_pays", "par_region", "par_decennie")):
            g = QGroupBox(tr(f"tableau.{cle}"))
            l = QVBoxLayout(g)
            b = Barres()
            l.addWidget(b)
            l.addStretch(1)
            self.barres[cle] = b
            grille.addWidget(g, i // 2, i % 2)
        racine.addLayout(grille)

        bas = QHBoxLayout()
        self.g_alertes = QGroupBox(tr("tableau.alertes"))
        la = QVBoxLayout(self.g_alertes)
        self.alertes = QListWidget()
        la.addWidget(self.alertes)
        self.g_derniers = QGroupBox(tr("tableau.derniers"))
        ld = QVBoxLayout(self.g_derniers)
        self.derniers = QListWidget()
        ld.addWidget(self.derniers)
        bas.addWidget(self.g_alertes)
        bas.addWidget(self.g_derniers)
        racine.addLayout(bas)
        self.apogee = QLabel()
        self.apogee.setObjectName("legende")
        self.apogee.setWordWrap(True)
        racine.addWidget(self.apogee)
        racine.addStretch(1)
        self.rafraichir()

    def rafraichir(self) -> None:
        s = self.cave.statistiques()
        self.chiffres["bouteilles"].setText(str(s["bouteilles"]))
        self.chiffres["vins"].setText(str(s["vins"]))
        self.chiffres["a_venir"].setText(str(s["a_venir"]))
        self.chiffres["litres"].setText(nombre(s["litres"], 1))
        self.chiffres["prix_total"].setText(argent(round(s["prix_total"])))
        self.chiffres["valeur_estimee"].setText(argent(round(s["valeur_estimee"])))
        self.sous_titre.setText(tr("tableau.mouvements_12", e=s["entrees_12_mois"],
                                   s=s["sorties_12_mois"]))
        self.barres["par_couleur"].definir(_regrouper(s["par_couleur"], 6, "couleur"))
        self.barres["par_pays"].definir(_regrouper(s["par_pays"], 7))
        self.barres["par_region"].definir(_regrouper(s["par_region"], 8))
        self.barres["par_decennie"].definir(
            [(tr("tableau.decennie", d=d) if d else tr("tableau.non_millesime"), n)
             for d, n in s["par_decennie"]])
        self.alertes.clear()
        for p in s["primeurs"]:
            self.alertes.addItem(tr("tableau.alerte_primeur", n=p["n"], vin=self.cave.nom_vin(p["vin_id"]),
                                    date=date_affichee(p["livraison"]) or "?"))
        for r in s["reassort"]:
            self.alertes.addItem(tr("tableau.alerte_reassort", vin=self.cave.nom_vin(r["vin_id"]),
                                    n=r["n"], seuil=r["seuil"]))
        if not self.alertes.count():
            self.alertes.addItem(tr("tableau.aucune_alerte"))
        self.derniers.clear()
        for m in s["derniers"]:
            vin = " · ".join(str(x) for x in (m["producteur"], m["cuvee"], m["millesime"]) if x)
            self.derniers.addItem(f"{date_affichee(m['date'])}  {lib('mouvement', m['type'])} — {vin}")
        self.apogee.setText("" if regles.disponibles() else tr("tableau.apogee_a_venir"))
