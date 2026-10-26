# -*- coding: utf-8 -*-
"""Liste d'envies (et « cave idéale ») : ce qu'on aimerait avoir, avec un prix
maximal et une priorité ; marquée « achetée » quand l'envie est satisfaite.

Alertes de prix SANS aspirateur : on note un prix vu (marchand, salon,
catalogue : source et date obligatoires) ou on importe un CSV de prix relevés ;
une envie dont un prix récent est au plus son prix maximal passe en alerte
(ligne dorée, tableau de bord, liste d'achats) — voir achats.py."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QDialog,
                             QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView,
                             QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QSpinBox,
                             QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from .. import achats
from ..i18n import argent, date_affichee, tr
from .saisie import _ligne, _reel

FILTRE_CSV = "CSV (*.csv *.txt *.tsv)"
PRIORITES = {1: "envie.priorite_1", 2: "envie.priorite_2", 3: "envie.priorite_3"}


def _cellule(texte, donnee=None) -> QTableWidgetItem:
    it = QTableWidgetItem("" if texte is None else str(texte))
    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
    if donnee is not None:
        it.setData(Qt.ItemDataRole.UserRole, donnee)
    return it


class DialogueEnvie(QDialog):
    def __init__(self, cave, envie: dict | None = None, parent=None, vin_id: int | None = None):
        super().__init__(parent)
        self.cave = cave
        self.envie = envie
        self.setWindowTitle(tr("envie.titre_modifier") if envie else tr("envie.titre_nouvelle"))
        self.resize(520, 420)
        e = envie or {}
        v = cave.vin(vin_id or e.get("vin_id")) if (vin_id or e.get("vin_id")) else None
        self.vin_id = vin_id or e.get("vin_id")
        f = QFormLayout(self)
        dist = cave.valeurs_distinctes
        appellations = sorted(set(dist("appellation")) | set(cave.references.noms_appellations()))
        self.producteur = _ligne(e.get("producteur") or (v["producteur"] if v else None),
                                 dist("producteur"))
        self.cuvee = _ligne(e.get("cuvee") or (v["cuvee"] if v else None))
        self.appellation = _ligne(e.get("appellation") or (v["appellation"] if v else None),
                                  appellations)
        self.millesime = QSpinBox()
        self.millesime.setRange(1799, 2200)
        self.millesime.setSpecialValueText(" ")
        self.millesime.setValue(e.get("millesime") or (v["millesime"] if v and v["millesime"] else 1799))
        self.quantite = QSpinBox()
        self.quantite.setRange(0, 999)
        self.quantite.setSpecialValueText(" ")
        self.quantite.setValue(e.get("quantite") or 0)
        self.prix = _reel(e.get("prix_max"), 100000, 2, " €")
        self.priorite = QComboBox()
        for p in PRIORITES:
            self.priorite.addItem(tr(PRIORITES[p]), p)
        self.priorite.setCurrentIndex(max(0, self.priorite.findData(e.get("priorite") or 2)))
        self.notes = QPlainTextEdit(e.get("notes") or "")
        self.notes.setMaximumHeight(90)
        for cle, w in (("vin.producteur", self.producteur), ("vin.cuvee", self.cuvee),
                       ("vin.appellation", self.appellation), ("vin.millesime", self.millesime),
                       ("envie.quantite", self.quantite), ("envie.prix_max", self.prix),
                       ("envie.priorite", self.priorite), ("vin.notes", self.notes)):
            f.addRow(tr(cle), w)
        boutons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        boutons.button(QDialogButtonBox.StandardButton.Save).setText(tr("bouton.enregistrer"))
        boutons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("bouton.annuler"))
        boutons.accepted.connect(self.accepter)
        boutons.rejected.connect(self.reject)
        f.addRow(boutons)

    def donnees(self) -> dict:
        m = self.millesime.value()
        return {"vin_id": self.vin_id, "producteur": self.producteur.text(), "cuvee": self.cuvee.text(),
                "appellation": self.appellation.text(),
                "millesime": None if m == self.millesime.minimum() else m,
                "quantite": self.quantite.value() or None, "prix_max": self.prix.value() or None,
                "priorite": self.priorite.currentData(), "notes": self.notes.toPlainText()}

    def accepter(self) -> None:
        d = self.donnees()
        if not (d["producteur"].strip() or d["cuvee"].strip() or d["appellation"].strip()):
            QMessageBox.warning(self, self.windowTitle(), tr("saisie.erreur_nom"))
            return
        if self.envie:
            self.cave.modifier_envie(self.envie["id"], d)
        else:
            self.cave.ajouter_envie(d)
        self.accept()


class DialoguePrix(QDialog):
    """Prix relevés pour une envie : liste, ajout (source obligatoire), suppression."""

    def __init__(self, cave, envie: dict, parent=None):
        super().__init__(parent)
        self.cave, self.envie = cave, envie
        self.modifie = False
        libelle = " · ".join(str(x) for x in (envie["producteur"], envie["cuvee"], envie["appellation"],
                                              envie["millesime"]) if x)
        self.setWindowTitle(tr("prix.titre", vin=libelle))
        self.resize(640, 480)
        v = QVBoxLayout(self)
        aide = QLabel(tr("prix.aide", jours=achats.JOURS_VALIDITE,
                         max=argent(envie["prix_max"]) if envie["prix_max"] else "—"))
        aide.setObjectName("legende")
        aide.setWordWrap(True)
        v.addWidget(aide)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([tr("prix.c_date"), tr("prix.c_prix"), tr("prix.c_source"),
                                              tr("prix.c_note")])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setAccessibleName(tr("prix.titre", vin=libelle))
        v.addWidget(self.table, 1)
        f = QFormLayout()
        self.montant = _reel(None, 100000, 2, " €")
        self.source = QLineEdit()
        self.source.setPlaceholderText(tr("prix.source_exemple"))
        self.date = QDateEdit(QDate.currentDate())
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("dd/MM/yyyy")
        self.url = QLineEdit()
        self.note = QLineEdit()
        for cle, w in (("prix.montant", self.montant), ("prix.source", self.source), ("prix.date", self.date),
                       ("prix.url", self.url), ("prix.note", self.note)):
            f.addRow(tr(cle), w)
        v.addLayout(f)
        b = QHBoxLayout()
        self.b_ajouter = QPushButton(tr("prix.ajouter"))
        self.b_ajouter.setObjectName("principal")
        self.b_supprimer = QPushButton(tr("prix.supprimer"))
        fermer = QPushButton(tr("bouton.fermer"))
        b.addWidget(self.b_ajouter)
        b.addWidget(self.b_supprimer)
        b.addStretch(1)
        b.addWidget(fermer)
        v.addLayout(b)
        self.b_ajouter.clicked.connect(self.ajouter)
        self.b_supprimer.clicked.connect(self.supprimer)
        fermer.clicked.connect(self.accept)
        self.rafraichir()

    def rafraichir(self) -> None:
        self.releves = achats.prix_releves(self.cave, self.envie["id"])
        self.table.setRowCount(len(self.releves))
        for r, p in enumerate(self.releves):
            for c, val in enumerate((date_affichee(p["date"]), argent(p["montant"]), p["source"],
                                     " ".join(x for x in (p["note"], p["url"]) if x))):
                it = _cellule(val, p["id"] if c == 0 else None)
                if c == 1 and self.envie["prix_max"] and p["montant"] <= self.envie["prix_max"]:
                    it.setForeground(QBrush(QColor("#2E7D32")))
                self.table.setItem(r, c, it)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.b_supprimer.setEnabled(bool(self.releves))

    def ajouter(self) -> None:
        if not self.montant.value() or not self.source.text().strip():
            QMessageBox.warning(self, self.windowTitle(), tr("prix.erreur"))
            return
        achats.ajouter_prix(self.cave, self.envie["id"], self.montant.value(), self.source.text(),
                            self.date.date().toString("yyyy-MM-dd"), self.url.text(), self.note.text())
        self.modifie = True
        self.montant.setValue(0)
        self.note.clear()
        self.url.clear()
        self.rafraichir()

    def supprimer(self) -> None:
        rangs = self.table.selectionModel().selectedRows()
        if rangs:
            achats.supprimer_prix(self.cave, self.table.item(rangs[0].row(), 0).data(Qt.ItemDataRole.UserRole))
            self.modifie = True
            self.rafraichir()


class VueEnvies(QWidget):
    modifie = pyqtSignal()

    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        racine = QVBoxLayout(self)
        aide = QLabel(tr("envie.aide"))
        aide.setObjectName("legende")
        aide.setWordWrap(True)
        racine.addWidget(aide)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([tr("envie.c_priorite"), tr("vin.producteur"),
                                              tr("vin.cuvee"), tr("vin.appellation"),
                                              tr("vin.millesime"), tr("envie.c_quantite_prix"),
                                              tr("envie.c_releve"), tr("envie.c_etat")])
        self.table.setAccessibleName(tr("onglet.envies"))
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        racine.addWidget(self.table, 1)
        b = QHBoxLayout()
        self.b_ajouter = QPushButton(tr("envie.ajouter"))
        self.b_ajouter.setObjectName("principal")
        self.b_modifier = QPushButton(tr("envie.modifier"))
        self.b_achetee = QPushButton(tr("envie.achetee"))
        self.b_supprimer = QPushButton(tr("envie.supprimer"))
        self.b_prix = QPushButton(tr("envie.prix_vu"))
        self.b_importer = QPushButton(tr("envie.importer_prix"))
        self.toutes = QCheckBox(tr("envie.montrer_satisfaites"))
        for w in (self.b_ajouter, self.b_modifier, self.b_achetee, self.b_prix, self.b_importer,
                  self.b_supprimer):
            b.addWidget(w)
        b.addStretch(1)
        b.addWidget(self.toutes)
        racine.addLayout(b)
        self.b_ajouter.clicked.connect(self.ajouter)
        self.b_modifier.clicked.connect(self.modifier)
        self.b_achetee.clicked.connect(self.achetee)
        self.b_supprimer.clicked.connect(self.supprimer)
        self.b_prix.clicked.connect(self.prix_vu)
        self.b_importer.clicked.connect(self.importer_prix)
        self.toutes.toggled.connect(lambda _b: self.rafraichir())
        self.table.itemSelectionChanged.connect(self._etat)
        self.table.itemDoubleClicked.connect(lambda _i: self.modifier())
        self.rafraichir()

    def rafraichir(self) -> None:
        self.lignes = self.cave.envies(self.toutes.isChecked())
        meilleurs = achats.meilleurs_prix(self.cave)
        alertes = {a["envie_id"]: a for a in achats.alertes_prix(self.cave)}
        self.table.setRowCount(len(self.lignes))
        fond = QBrush(QColor("#F3D58A"))
        for r, e in enumerate(self.lignes):
            qp = " · ".join(x for x in (str(e["quantite"]) if e["quantite"] else None,
                                         tr("envie.max", prix=argent(e["prix_max"])) if e["prix_max"]
                                         else None) if x)
            m = meilleurs.get(e["id"])
            releve = tr("envie.releve", prix=argent(m["montant"]), source=m["source"],
                        date=date_affichee(m["date"])) if m else ""
            a = alertes.get(e["id"]) if not e["satisfaite_le"] else None
            etat = (tr("envie.satisfaite_le", date=date_affichee(e["satisfaite_le"]))
                    if e["satisfaite_le"] else (tr("envie.deja", n=e["en_cave"]) if e.get("en_cave") else ""))
            if a:
                etat = " · ".join(x for x in (tr("envie.alerte", prix=argent(a["prix"])), etat) if x)
            for c, val in enumerate((tr(PRIORITES[e["priorite"]]) if e["priorite"] in PRIORITES
                                     else e["priorite"], e["producteur"], e["cuvee"], e["appellation"],
                                     e["millesime"], qp, releve, etat)):
                it = _cellule(val, e["id"] if c == 0 else None)
                if a:
                    it.setBackground(fond)
                self.table.setItem(r, c, it)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._etat()

    def _choisie(self) -> dict | None:
        rangs = self.table.selectionModel().selectedRows()
        if not rangs:
            return None
        eid = self.table.item(rangs[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        return next((e for e in self.lignes if e["id"] == eid), None)

    def _etat(self) -> None:
        e = self._choisie()
        for w in (self.b_modifier, self.b_supprimer):
            w.setEnabled(e is not None)
        self.b_achetee.setEnabled(bool(e and not e["satisfaite_le"]))
        self.b_prix.setEnabled(bool(e and not e["satisfaite_le"]))

    def ajouter(self, vin_id: int | None = None) -> None:
        if DialogueEnvie(self.cave, None, self, vin_id=vin_id or None).exec() == QDialog.DialogCode.Accepted:
            self.rafraichir()
            self.modifie.emit()

    def modifier(self) -> None:
        e = self._choisie()
        if e and DialogueEnvie(self.cave, e, self).exec() == QDialog.DialogCode.Accepted:
            self.rafraichir()

    def achetee(self) -> None:
        e = self._choisie()
        if e:
            self.cave.satisfaire_envie(e["id"])
            self.rafraichir()

    def prix_vu(self) -> None:
        e = self._choisie()
        if e:
            d = DialoguePrix(self.cave, e, self)
            d.exec()
            if d.modifie:
                self.rafraichir()
                self.modifie.emit()

    def importer_prix(self) -> None:
        chemin, _ = QFileDialog.getOpenFileName(self, tr("envie.importer_prix"), str(Path.home()),
                                                FILTRE_CSV)
        if not chemin:
            return
        r = achats.importer_prix_csv(self.cave, chemin)
        details = "\n".join((r.non_rapproches + r.erreurs)[:15])
        QMessageBox.information(self, tr("envie.importer_prix"),
                                tr("prix.import_bilan", n=r.importes, non=len(r.non_rapproches),
                                   err=len(r.erreurs)) + ("\n\n" + details if details else ""))
        if r.importes:
            self.rafraichir()
            self.modifie.emit()

    def supprimer(self) -> None:
        e = self._choisie()
        if e and QMessageBox.question(self, tr("onglet.envies"), tr("envie.supprimer_q")) \
                == QMessageBox.StandardButton.Yes:
            self.cave.supprimer_envie(e["id"])
            self.rafraichir()
