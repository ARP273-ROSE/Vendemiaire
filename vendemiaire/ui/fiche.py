# -*- coding: utf-8 -*-
"""Fiche d'un vin : pochette, identité, fenêtres de dégustation, critiques,
valeurs, et la liste de ses bouteilles avec leurs actions."""
from __future__ import annotations

from datetime import date

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QAbstractItemView, QFormLayout, QGroupBox, QHBoxLayout,
                             QLabel, QPushButton, QScrollArea, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from .. import regles
from ..i18n import argent, date_affichee, lib, nombre, tr
from .pochette import pochette


def _cellule(texte) -> QTableWidgetItem:
    it = QTableWidgetItem("" if texte is None else str(texte))
    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return it


class FicheVin(QScrollArea):
    modifier = pyqtSignal(int)
    ajouter_bouteilles = pyqtSignal(int)
    choisir_photo = pyqtSignal(int)
    sortir = pyqtSignal(int)
    modifier_bouteille = pyqtSignal(int)
    recevoir = pyqtSignal(int)
    voir_plan = pyqtSignal(int)

    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        self.vin_id: int | None = None
        self.setWidgetResizable(True)
        corps = QWidget()
        self.setWidget(corps)
        racine = QVBoxLayout(corps)

        haut = QHBoxLayout()
        self.image = QLabel()
        self.image.setFixedSize(150, 200)
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        haut.addWidget(self.image)
        identite = QVBoxLayout()
        self.titre = QLabel()
        self.titre.setObjectName("titre")
        self.titre.setWordWrap(True)
        self.sous_titre = QLabel()
        self.sous_titre.setObjectName("sous_titre")
        self.sous_titre.setWordWrap(True)
        identite.addWidget(self.titre)
        identite.addWidget(self.sous_titre)
        self.formulaire = QFormLayout()
        identite.addLayout(self.formulaire)
        identite.addStretch(1)
        boutons = QHBoxLayout()
        self.b_modifier = QPushButton(tr("fiche.modifier"))
        self.b_photo = QPushButton(tr("fiche.photo"))
        boutons.addWidget(self.b_modifier)
        boutons.addWidget(self.b_photo)
        boutons.addStretch(1)
        identite.addLayout(boutons)
        haut.addLayout(identite, 1)
        racine.addLayout(haut)

        self.g_fenetres = QGroupBox(tr("fiche.fenetres"))
        lf = QVBoxLayout(self.g_fenetres)
        self.t_fenetres = self._table(["fiche.f_source", "fiche.f_debut", "fiche.f_apogee",
                                       "fiche.f_fin", "fiche.f_pourquoi"])
        self.calcul = QLabel()
        self.calcul.setWordWrap(True)
        self.calcul.setObjectName("legende")
        lf.addWidget(self.t_fenetres)
        lf.addWidget(self.calcul)
        racine.addWidget(self.g_fenetres)

        self.g_critiques = QGroupBox(tr("fiche.critiques"))
        lc = QVBoxLayout(self.g_critiques)
        self.t_critiques = self._table(["fiche.c_critique", "fiche.c_note", "fiche.c_date"])
        lc.addWidget(self.t_critiques)
        racine.addWidget(self.g_critiques)

        self.g_bouteilles = QGroupBox(tr("fiche.bouteilles"))
        lb = QVBoxLayout(self.g_bouteilles)
        self.t_bouteilles = self._table(["fiche.b_statut", "fiche.b_format", "fiche.b_emplacement",
                                         "fiche.b_prix", "fiche.b_entree", "fiche.b_niveau",
                                         "fiche.b_etat"])
        self.t_bouteilles.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        lb.addWidget(self.t_bouteilles)
        actions = QHBoxLayout()
        self.b_ajouter = QPushButton(tr("fiche.ajouter_bouteilles"))
        self.b_sortir = QPushButton(tr("fiche.sortir"))
        self.b_sortir.setObjectName("principal")
        self.b_modif_b = QPushButton(tr("fiche.modifier_bouteille"))
        self.b_recevoir = QPushButton(tr("fiche.recevoir"))
        self.b_plan = QPushButton(tr("fiche.voir_plan"))
        for b in (self.b_ajouter, self.b_sortir, self.b_modif_b, self.b_recevoir, self.b_plan):
            actions.addWidget(b)
        actions.addStretch(1)
        lb.addLayout(actions)
        racine.addWidget(self.g_bouteilles)
        self.valeurs = QLabel()
        self.valeurs.setWordWrap(True)
        racine.addWidget(self.valeurs)
        racine.addStretch(1)

        self.b_modifier.clicked.connect(lambda: self.vin_id and self.modifier.emit(self.vin_id))
        self.b_photo.clicked.connect(lambda: self.vin_id and self.choisir_photo.emit(self.vin_id))
        self.b_ajouter.clicked.connect(lambda: self.vin_id and self.ajouter_bouteilles.emit(self.vin_id))
        self.b_sortir.clicked.connect(lambda: self._sur_bouteille(self.sortir))
        self.b_modif_b.clicked.connect(lambda: self._sur_bouteille(self.modifier_bouteille))
        self.b_recevoir.clicked.connect(lambda: self._sur_bouteille(self.recevoir))
        self.b_plan.clicked.connect(lambda: self._sur_bouteille(self.voir_plan))
        self.t_bouteilles.itemSelectionChanged.connect(self._etat_boutons)
        self.afficher(None)

    def _table(self, entetes: list[str]) -> QTableWidget:
        t = QTableWidget(0, len(entetes))
        t.setHorizontalHeaderLabels([tr(e) for e in entetes])
        t.verticalHeader().setVisible(False)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.horizontalHeader().setStretchLastSection(True)
        t.setAlternatingRowColors(True)
        t.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._ajuster(t)
        return t

    @staticmethod
    def _ajuster(t: QTableWidget, maxi: int = 6) -> None:
        """Hauteur à la mesure du contenu (au plus `maxi` lignes visibles)."""
        n = min(maxi, t.rowCount())
        corps = sum(t.rowHeight(i) for i in range(n)) if n else t.verticalHeader().defaultSectionSize()
        barre = t.horizontalScrollBar().sizeHint().height()
        h = t.horizontalHeader().sizeHint().height() + corps + barre
        t.setFixedHeight(h + 2 * t.frameWidth() + 2)

    def bouteille_choisie(self) -> int | None:
        lignes = self.t_bouteilles.selectionModel().selectedRows()
        if not lignes:
            return None
        return self.t_bouteilles.item(lignes[0].row(), 0).data(Qt.ItemDataRole.UserRole)

    def _sur_bouteille(self, signal) -> None:
        bid = self.bouteille_choisie()
        if bid is not None:
            signal.emit(bid)

    def _etat_boutons(self) -> None:
        bid = self.bouteille_choisie()
        b = self.cave.bouteille(bid) if bid else None
        statut = b["statut"] if b else None
        self.b_sortir.setEnabled(statut == "en_cave")
        self.b_modif_b.setEnabled(b is not None)
        self.b_recevoir.setEnabled(statut in ("primeur", "en_attente"))
        self.b_plan.setEnabled(bool(b and b["emplacement_id"]))

    def afficher(self, vin_id: int | None) -> None:
        self.vin_id = vin_id
        v = self.cave.vin(vin_id) if vin_id else None
        for w in (self.b_modifier, self.b_photo, self.b_ajouter, self.g_fenetres,
                  self.g_critiques, self.g_bouteilles):
            w.setEnabled(v is not None)
        while self.formulaire.rowCount():
            self.formulaire.removeRow(0)
        if v is None:
            self.titre.setText(tr("fiche.aucun"))
            self.sous_titre.setText(tr("fiche.aucun_aide"))
            self.image.clear()
            for t in (self.t_fenetres, self.t_critiques, self.t_bouteilles):
                t.setRowCount(0)
            self.valeurs.clear()
            self.calcul.clear()
            self._etat_boutons()
            return
        d = dict(v)
        self.image.setPixmap(pochette(d, 150, 200, self.cave.image_principale(vin_id)))
        mil = str(v["millesime"]) if v["millesime"] else (tr("vin.nm") if v["non_millesime"] else "")
        self.titre.setText(" ".join(x for x in (v["producteur"], mil) if x))
        self.sous_titre.setText(" · ".join(x for x in (v["cuvee"], v["appellation"],
                                                        v["classement"]) if x))
        cepages = ", ".join(f"{c} {nombre(p, 0)} %" if p is not None else c
                            for c, p in self.cave.cepages(vin_id))
        lignes = [
            ("vin.region", " › ".join(x for x in (v["pays"], v["region"], v["sous_region"]) if x)),
            ("vin.couleur_type", " · ".join(x for x in (lib("couleur", v["couleur"]),
                                                         lib("type", v["type"])) if x)),
            ("vin.cepages", cepages),
            ("vin.degre", f"{nombre(v['degre'])} %" if v["degre"] else ""),
            ("vin.lwin", v["lwin"] or ""),
            ("vin.seuil", str(v["seuil_reassort"]) if v["seuil_reassort"] else ""),
            ("vin.notes", v["notes"] or ""),
        ]
        for cle, valeur in lignes:
            if valeur:
                etiquette = QLabel(valeur)
                etiquette.setWordWrap(True)
                self.formulaire.addRow(tr(cle), etiquette)

        # fenêtres de dégustation : la mienne, critiques, calculée (phase 3)
        fen = self.cave.fenetres(vin_id)
        self.t_fenetres.setRowCount(len(fen))
        for r, f in enumerate(fen):
            source = lib("source_fenetre", f["source"])
            if f["detail_source"]:
                source += f" ({f['detail_source']})"
            apogee = "–".join(str(x) for x in (f["apogee_debut"], f["apogee_fin"]) if x)
            for c, val in enumerate((source, f["debut"], apogee, f["fin"], f["explication"])):
                self.t_fenetres.setItem(r, c, _cellule(val))
        if not regles.disponibles():
            self.calcul.setText(tr("fiche.regles_a_venir"))
        else:
            self.calcul.clear()

        notes = self.cave.notes_critiques(vin_id)
        self.t_critiques.setRowCount(len(notes))
        for r, n in enumerate(notes):
            note = nombre(n["note"])
            if n["note_max"]:
                note += f"–{nombre(n['note_max'])}"
            note += " " + lib("echelle", n["echelle"])
            for c, val in enumerate((n["critique"], note, date_affichee(n["date"]))):
                self.t_critiques.setItem(r, c, _cellule(val))

        bouteilles = self.cave.bouteilles(vin_id)
        self.t_bouteilles.setRowCount(len(bouteilles))
        for r, b in enumerate(bouteilles):
            present = b["statut"] == "en_cave"
            chemin = " › ".join(self.cave.chemin_emplacement(b["emplacement_id"])) if present else ""
            if present and b["rangee"] and b["colonne"]:
                chemin += " " + tr("plan.case", r=b["rangee"], c=b["colonne"])
            etats = ", ".join(x for x in (lib("etat_etiquette", b["etat_etiquette"]),
                                           lib("caisse", b["caisse"]) if b["caisse"] not in
                                           (None, "aucune") else "") if x)
            date_ref = b["date_entree"] if b["statut"] == "en_cave" else (
                b["date_livraison_prevue"] if b["statut"] in ("primeur", "en_attente")
                else b["date_sortie"])
            cellules = (lib("statut", b["statut"]), lib("format", b["format"]), chemin,
                        argent(b["prix_achat"], b["devise"]), date_affichee(date_ref),
                        lib("niveau", b["niveau"]) or (f"{nombre(b['niveau_cm'])} cm"
                                                        if b["niveau_cm"] else ""), etats)
            for c, val in enumerate(cellules):
                it = _cellule(val)
                if c == 0:
                    it.setData(Qt.ItemDataRole.UserRole, b["id"])
                self.t_bouteilles.setItem(r, c, it)
        self.t_bouteilles.resizeColumnsToContents()
        for t in (self.t_fenetres, self.t_critiques, self.t_bouteilles):
            self._ajuster(t, 8 if t is self.t_bouteilles else 4)
        if bouteilles:
            premiere = next((r for r, b in enumerate(bouteilles) if b["statut"] == "en_cave"), 0)
            self.t_bouteilles.selectRow(premiere)
        valeurs = self.cave.valeurs(vin_id)
        if valeurs:
            dv = valeurs[0]
            self.valeurs.setText(tr("fiche.valeur", montant=argent(dv["montant"], dv["devise"]),
                                    date=date_affichee(dv["date"]), source=dv["source"]))
        else:
            self.valeurs.setText("")
        age = date.today().year - v["millesime"] if v["millesime"] else None
        self.g_bouteilles.setTitle(tr("fiche.bouteilles_age", n=len(bouteilles), age=age)
                                   if age is not None else tr("fiche.bouteilles"))
        self._etat_boutons()
