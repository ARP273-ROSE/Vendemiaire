# -*- coding: utf-8 -*-
"""Onglet « Statistiques » : répartitions au choix (pays, région, couleur,
cépage, millésime, prix, format, cave ; en bouteilles ou en valeur), valeur de
la cave dans le temps, entrées contre sorties par année, rythme de
consommation, courbe d'apogée couleur par couleur (petits multiples)."""
from __future__ import annotations

from PyQt6.QtWidgets import (QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QScrollArea,
                             QVBoxLayout, QWidget)

from .. import statistiques
from ..i18n import argent, lib, nombre, tr
from .graphiques import BarresGroupees, Courbes
from .tableau import Barres, CourbeApogee

AXES = {"pays": "stats.axe_pays", "region": "stats.axe_region", "couleur": "stats.axe_couleur",
        "cepage": "stats.axe_cepage", "millesime": "stats.axe_millesime", "prix": "stats.axe_prix",
        "format": "stats.axe_format", "emplacement": "stats.axe_emplacement"}


class VueStatistiques(QScrollArea):
    def __init__(self, cave, parent=None, charger: bool = True):
        super().__init__(parent)
        self.cave = cave
        self.setWidgetResizable(True)
        corps = QWidget()
        self.setWidget(corps)
        racine = QVBoxLayout(corps)

        g = QGroupBox(tr("stats.repartition"))
        lg = QVBoxLayout(g)
        choix = QHBoxLayout()
        choix.addWidget(QLabel(tr("stats.par")))
        self.axe = QComboBox()
        for code, cle in AXES.items():
            self.axe.addItem(tr(cle), code)
        choix.addWidget(self.axe)
        choix.addWidget(QLabel(tr("stats.en")))
        self.mesure = QComboBox()
        self.mesure.addItem(tr("stats.bouteilles"), "bouteilles")
        self.mesure.addItem(tr("stats.valeur"), "valeur")
        choix.addWidget(self.mesure)
        choix.addStretch(1)
        lg.addLayout(choix)
        self.barres = Barres()
        lg.addWidget(self.barres)
        racine.addWidget(g)

        grille = QGridLayout()
        g1 = QGroupBox(tr("stats.valeur_temps"))
        l1 = QVBoxLayout(g1)
        self.courbe_valeur = Courbes()
        self.courbe_valeur.format_valeur = lambda v: argent(round(v))
        l1.addWidget(self.courbe_valeur)
        self.legende_valeur = QLabel()
        self.legende_valeur.setObjectName("legende")
        self.legende_valeur.setWordWrap(True)
        l1.addWidget(self.legende_valeur)
        g2 = QGroupBox(tr("stats.conso_achats"))
        l2 = QVBoxLayout(g2)
        self.conso = BarresGroupees()
        l2.addWidget(self.conso)
        self.rythme = QLabel()
        self.rythme.setObjectName("legende")
        self.rythme.setWordWrap(True)
        l2.addWidget(self.rythme)
        grille.addWidget(g1, 0, 0)
        grille.addWidget(g2, 0, 1)
        racine.addLayout(grille)

        self.g_apogee = QGroupBox(tr("stats.apogee_couleur"))
        self.grille_apogee = QGridLayout(self.g_apogee)
        racine.addWidget(self.g_apogee)
        racine.addStretch(1)
        self.axe.currentIndexChanged.connect(lambda _i: self.rafraichir_repartition())
        self.mesure.currentIndexChanged.connect(lambda _i: self.rafraichir_repartition())
        if charger:                      # la fenêtre le charge à la première ouverture
            self.rafraichir()

    def rafraichir_repartition(self) -> None:
        axe, mesure = self.axe.currentData(), self.mesure.currentData()
        paires = statistiques.repartition(self.cave, axe, mesure)
        donnees = []
        for k, v in paires:
            if k is None or k == "?":
                nom = tr("tableau.inconnu")
            elif axe == "couleur":
                nom = lib("couleur", k)
            elif axe == "format":
                nom = lib("format", k)
            elif axe == "prix":
                nom = tr("stats.tranche", t=k)
            else:
                nom = str(k)
            donnees.append((nom, round(v, 1)))
        if len(donnees) > 25:
            reste = sum(v for _n, v in donnees[24:])
            donnees = donnees[:24] + [(tr("tableau.autres"), reste)]
        self.barres.definir(donnees)

    def rafraichir(self) -> None:
        self.rafraichir_repartition()
        points = statistiques.valeur_dans_le_temps(self.cave, 36)
        self.courbe_valeur.definir([d[:7] for d, *_ in points], [[c for _d, c, _v, _n in points],
                                                                  [v for _d, _c, v, _n in points]],
                                   [tr("stats.cout_achat"), tr("stats.valeur_retenue")])
        if points:
            d, c, v, n = points[-1]
            self.legende_valeur.setText(tr("stats.legende_valeur", n=n, cout=argent(round(c)), valeur=argent(round(v)),
                                           plus=argent(round(v - c))))
        lignes = statistiques.consommation_achats(self.cave)[-10:]
        self.conso.definir([str(a) for a, _e, _s in lignes], [[e for _a, e, _s in lignes], [s for _a, _e, s in lignes]],
                           [tr("stats.entrees"), tr("stats.sorties")])
        try:
            r = statistiques.rythme(self.cave)
            self.rythme.setText(tr("stats.rythme", sorties=nombre(r["sorties_par_an"], 0),
                                   entrees=nombre(r["entrees_par_an"], 0), boire=nombre(r["a_boire_par_an"], 0)))
            par_couleur = statistiques.apogee_par_couleur(self.cave)
        except Exception as ex:                     # jeu de règles invalide : dit, pas masqué
            self.rythme.setText(tr("fiche.regles_erreur", erreur=str(ex)))
            par_couleur = {}
        while self.grille_apogee.count():
            w = self.grille_apogee.takeAt(0).widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        for i, (couleur, courbe) in enumerate(par_couleur.items()):
            boite = QWidget()
            l = QVBoxLayout(boite)
            t = QLabel(lib("couleur", couleur) if couleur else tr("tableau.inconnu"))
            t.setObjectName("sous_titre")
            l.addWidget(t)
            c = CourbeApogee()
            c.definir(courbe)
            l.addWidget(c)
            self.grille_apogee.addWidget(boite, i // 2, i % 2)
