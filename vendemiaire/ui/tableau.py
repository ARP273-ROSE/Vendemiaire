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


class CourbeApogee(QWidget):
    """« Combien de bouteilles boire chaque année » : une colonne par année (une
    seule série, une seule teinte ; valeurs en encre ; l'infobulle donne aussi
    le nombre de bouteilles à leur apogée)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.donnees: list[tuple[int, float, int]] = []
        self.setMouseTracking(True)
        self.setMinimumHeight(190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def definir(self, donnees) -> None:
        self.donnees = list(donnees)
        self.update()

    def _zone(self) -> QRectF:
        return QRectF(self.rect()).adjusted(8, 18, -8, -22)

    def paintEvent(self, _ev):
        if not self.donnees:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        zone = self._zone()
        n = len(self.donnees)
        pas = zone.width() / n
        maxi = max(b for _a, b, _n in self.donnees) or 1
        police = QFont(style.FAMILLE)
        police.setPixelSize(11)
        p.setFont(police)
        p.setPen(QColor(style.BORD))
        p.drawLine(int(zone.left()), int(zone.bottom()), int(zone.right()), int(zone.bottom()))
        for i, (annee, boire, _apogee) in enumerate(self.donnees):
            x = zone.left() + i * pas
            hauteur = zone.height() * boire / maxi
            if hauteur > 0:
                barre = QRectF(x + pas * 0.18, zone.bottom() - hauteur, pas * 0.64, hauteur)
                chemin = QPainterPath()
                chemin.addRoundedRect(barre, 3, 3)
                p.fillPath(chemin, QColor(style.BORDEAUX))
            p.setPen(QColor(style.ENCRE))
            if boire >= 0.5:
                p.drawText(QRectF(x, zone.bottom() - hauteur - 16, pas, 14), Qt.AlignmentFlag.AlignCenter,
                           nombre(boire, 0))
            if i % 2 == 0 or n <= 12:
                p.setPen(QColor(style.GRIS))
                p.drawText(QRectF(x - 6, zone.bottom() + 4, pas + 12, 16), Qt.AlignmentFlag.AlignCenter,
                           str(annee))
        p.end()

    def mouseMoveEvent(self, ev):
        zone = self._zone()
        if not self.donnees:
            return
        i = int((ev.position().x() - zone.left()) // (zone.width() / len(self.donnees)))
        if 0 <= i < len(self.donnees):
            a, b, n = self.donnees[i]
            QToolTip.showText(ev.globalPosition().toPoint(),
                              tr("tableau.courbe_info", annee=a, boire=nombre(b, 1), apogee=n), self)
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

        # garde : alertes et courbe d'apogée (règles du dossier « Le vin »)
        self.g_garde = QGroupBox(tr("tableau.garde"))
        lgarde = QVBoxLayout(self.g_garde)
        tuiles_garde = QHBoxLayout()
        for cle in ("a_boire", "declin", "trop_jeune", "ouvertes"):
            cadre, c = _tuile("–", tr({"a_boire": "tableau.t_a_boire", "declin": "tableau.t_declin",
                                       "trop_jeune": "tableau.t_trop_jeune",
                                       "ouvertes": "tableau.t_ouvertes"}[cle]))
            self.chiffres["garde_" + cle] = c
            tuiles_garde.addWidget(cadre)
        lgarde.addLayout(tuiles_garde)
        t_courbe = QLabel(tr("tableau.courbe"))
        t_courbe.setObjectName("sous_titre")
        lgarde.addWidget(t_courbe)
        self.courbe = CourbeApogee()
        lgarde.addWidget(self.courbe)
        self.legende_courbe = QLabel()
        self.legende_courbe.setObjectName("legende")
        self.legende_courbe.setWordWrap(True)
        lgarde.addWidget(self.legende_courbe)
        racine.addWidget(self.g_garde)

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
        from .. import achats
        for a in achats.alertes_prix(self.cave):
            self.alertes.addItem(tr("tableau.alerte_prix", vin=a["libelle"], prix=argent(a["prix"]),
                                    max=argent(a["prix_max"]), source=a["source"]))
        self._alertes_regles()
        if not self.alertes.count():
            self.alertes.addItem(tr("tableau.aucune_alerte"))
        self.derniers.clear()
        for m in s["derniers"]:
            vin = " · ".join(str(x) for x in (m["producteur"], m["cuvee"], m["millesime"]) if x)
            self.derniers.addItem(f"{date_affichee(m['date'])}  {lib('mouvement', m['type'])} — {vin}")
        self.apogee.setText("" if regles.disponibles() else tr("tableau.apogee_a_venir"))

    def _alertes_regles(self) -> None:
        """Alertes tirées des règles : à boire, déclin, trop jeune (par vin),
        bouteilles entamées, conditions hors plage, bouchons à contrôler."""
        from datetime import date
        from ..regles.jeu import jeu
        try:
            alertes = self.cave.alertes_garde()
            courbe = self.cave.courbe_apogee()
            ouvertes = self.cave.bouteilles_ouvertes()
            hors = self.cave.conditions_hors_plage(limite=60)
            bouchons = self.cave.bouchons_a_controler()
        except Exception as ex:                       # jeu de règles invalide : dit, pas masqué
            self.alertes.addItem(tr("fiche.regles_erreur", erreur=str(ex)))
            return
        for cle in ("a_boire", "declin", "trop_jeune"):
            self.chiffres["garde_" + cle].setText(str(len(alertes[cle])))
        self.chiffres["garde_ouvertes"].setText(str(len(ouvertes)))
        self.courbe.definir(courbe)
        total = sum(b for _a, b, _n in courbe)
        self.legende_courbe.setText(tr("tableau.courbe_legende", n=nombre(total, 0),
                                       date=date_affichee(jeu().date_audit)))
        aujourdhui = date.today().isoformat()
        for o in ouvertes:
            cle = "tableau.alerte_ouverte_passee" if (o["a_finir_avant"] or "9999") < aujourdhui \
                else "tableau.alerte_ouverte"
            self.alertes.addItem(tr(cle, vin=self.cave.nom_vin(o["vin_id"]),
                                    date=date_affichee(o["a_finir_avant"]) or "?"))
        for cle, texte in (("declin", "tableau.alerte_declin"), ("a_boire", "tableau.alerte_a_boire")):
            par_vin: dict[int, int] = {}
            for b in alertes[cle]:
                par_vin[b["vin_id"]] = par_vin.get(b["vin_id"], 0) + 1
            for vid, n in par_vin.items():
                self.alertes.addItem(tr(texte, vin=self.cave.nom_vin(vid), n=n))
        if hors:
            m, _a = hors[0]
            self.alertes.addItem(tr("tableau.alerte_conditions", n=len(hors), date=date_affichee(m["date_heure"])))
        if bouchons:
            self.alertes.addItem(tr("tableau.alerte_bouchons", n=len(bouchons)))
