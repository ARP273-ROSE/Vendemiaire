# -*- coding: utf-8 -*-
"""Liste d'envies (et « cave idéale ») : ce qu'on aimerait avoir, avec un prix
maximal et une priorité ; marquée « achetée » quand l'envie est satisfaite."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QFormLayout, QHBoxLayout, QHeaderView, QLabel,
                             QMessageBox, QPlainTextEdit, QPushButton, QSpinBox, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from ..i18n import argent, date_affichee, tr
from .saisie import _ligne, _reel

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
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([tr("envie.c_priorite"), tr("vin.producteur"),
                                              tr("vin.cuvee"), tr("vin.appellation"),
                                              tr("vin.millesime"), tr("envie.c_quantite_prix"),
                                              tr("envie.c_etat")])
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
        self.toutes = QCheckBox(tr("envie.montrer_satisfaites"))
        for w in (self.b_ajouter, self.b_modifier, self.b_achetee, self.b_supprimer):
            b.addWidget(w)
        b.addStretch(1)
        b.addWidget(self.toutes)
        racine.addLayout(b)
        self.b_ajouter.clicked.connect(self.ajouter)
        self.b_modifier.clicked.connect(self.modifier)
        self.b_achetee.clicked.connect(self.achetee)
        self.b_supprimer.clicked.connect(self.supprimer)
        self.toutes.toggled.connect(lambda _b: self.rafraichir())
        self.table.itemSelectionChanged.connect(self._etat)
        self.table.itemDoubleClicked.connect(lambda _i: self.modifier())
        self.rafraichir()

    def rafraichir(self) -> None:
        self.lignes = self.cave.envies(self.toutes.isChecked())
        self.table.setRowCount(len(self.lignes))
        for r, e in enumerate(self.lignes):
            qp = " · ".join(x for x in (str(e["quantite"]) if e["quantite"] else None,
                                         tr("envie.max", prix=argent(e["prix_max"])) if e["prix_max"]
                                         else None) if x)
            etat = (tr("envie.satisfaite_le", date=date_affichee(e["satisfaite_le"]))
                    if e["satisfaite_le"] else (tr("envie.deja", n=e["en_cave"]) if e.get("en_cave") else ""))
            for c, val in enumerate((tr(PRIORITES[e["priorite"]]) if e["priorite"] in PRIORITES
                                     else e["priorite"], e["producteur"], e["cuvee"], e["appellation"],
                                     e["millesime"], qp, etat)):
                self.table.setItem(r, c, _cellule(val, e["id"] if c == 0 else None))
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

    def supprimer(self) -> None:
        e = self._choisie()
        if e and QMessageBox.question(self, tr("onglet.envies"), tr("envie.supprimer_q")) \
                == QMessageBox.StandardButton.Yes:
            self.cave.supprimer_envie(e["id"])
            self.rafraichir()
