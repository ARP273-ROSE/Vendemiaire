# -*- coding: utf-8 -*-
"""Livre de cave : toutes les entrées et sorties, avec occasion, convives,
plat, note et commentaire de dégustation."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox,
                             QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
                             QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..i18n import date_affichee, lib, nombre, tr

COLONNES = ["livre.date", "livre.type", "livre.vin", "livre.millesime", "livre.occasion",
            "livre.convives", "livre.plat", "livre.note", "livre.commentaire"]


class DialogueMouvement(QDialog):
    def __init__(self, cave, m: dict, parent=None):
        super().__init__(parent)
        self.cave, self.m = cave, m
        self.setWindowTitle(tr("livre.modifier_titre"))
        self.resize(480, 380)
        f = QFormLayout(self)
        self.occasion = QLineEdit(m.get("occasion") or "")
        self.convives = QLineEdit(m.get("convives") or "")
        self.plat = QLineEdit(m.get("plat") or "")
        self.note = QLineEdit(nombre(m.get("note")) if m.get("note") is not None else "")
        self.commentaire = QPlainTextEdit(m.get("commentaire") or "")
        f.addRow(tr("sortie.occasion"), self.occasion)
        f.addRow(tr("sortie.convives"), self.convives)
        f.addRow(tr("sortie.plat"), self.plat)
        f.addRow(tr("sortie.note"), self.note)
        f.addRow(tr("sortie.commentaire"), self.commentaire)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        b.button(QDialogButtonBox.StandardButton.Save).setText(tr("bouton.enregistrer"))
        b.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("bouton.annuler"))
        b.accepted.connect(self.accepter)
        b.rejected.connect(self.reject)
        f.addRow(b)

    def accepter(self) -> None:
        try:
            note = float(self.note.text().replace(",", ".")) if self.note.text().strip() else None
        except ValueError:
            note = self.m.get("note")
        self.cave.modifier_mouvement(self.m["id"], {
            "occasion": self.occasion.text().strip() or None,
            "convives": self.convives.text().strip() or None,
            "plat": self.plat.text().strip() or None, "note": note,
            "echelle": self.m.get("echelle") or ("20" if note is not None else None),
            "commentaire": self.commentaire.toPlainText().strip() or None})
        self.accept()


class VueLivre(QWidget):
    vin_choisi = pyqtSignal(int)
    modifie = pyqtSignal()

    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        racine = QVBoxLayout(self)
        haut = QHBoxLayout()
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText(tr("livre.recherche"))
        self.recherche.setClearButtonEnabled(True)
        self.filtre = QComboBox()
        self.filtre.addItem(tr("livre.tout"), "")
        self.filtre.addItem(tr("livre.entrees"), "entree")
        self.filtre.addItem(tr("livre.sorties"), "sortie")
        self.compte = QLabel()
        self.compte.setObjectName("legende")
        haut.addWidget(self.recherche, 3)
        haut.addWidget(self.filtre, 1)
        haut.addWidget(self.compte)
        racine.addLayout(haut)
        self.table = QTableWidget(0, len(COLONNES))
        self.table.setHorizontalHeaderLabels([tr(c) for c in COLONNES])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        racine.addWidget(self.table, 1)
        aide = QLabel(tr("livre.aide"))
        aide.setObjectName("legende")
        racine.addWidget(aide)
        self.recherche.textChanged.connect(self.rafraichir)
        self.filtre.currentIndexChanged.connect(self.rafraichir)
        self.table.cellDoubleClicked.connect(self._modifier)
        self.table.currentCellChanged.connect(self._ligne)
        self.lignes: list[dict] = []
        self.rafraichir()

    def rafraichir(self, *_a) -> None:
        self.lignes = self.cave.mouvements(type_prefixe=self.filtre.currentData() or "",
                                           texte=self.recherche.text())
        self.table.setRowCount(len(self.lignes))
        for r, m in enumerate(self.lignes):
            vin = " · ".join(x for x in (m["producteur"], m["cuvee"], m["appellation"]) if x)
            note = ""
            if m["note"] is not None:
                note = f"{nombre(m['note'])} {lib('echelle', m['echelle'])}".strip()
            cellules = (date_affichee(m["date"]), lib("mouvement", m["type"]), vin,
                        m["millesime"] or "", m["occasion"], m["convives"], m["plat"], note,
                        m["commentaire"])
            for c, v in enumerate(cellules):
                it = QTableWidgetItem("" if v is None else str(v))
                if c == 1 and m["type"].startswith("sortie"):
                    it.setForeground(Qt.GlobalColor.darkRed)
                self.table.setItem(r, c, it)
        self.table.resizeColumnsToContents()
        entrees = sum(1 for m in self.lignes if m["type"].startswith("entree"))
        self.compte.setText(tr("livre.compte", n=len(self.lignes), e=entrees,
                               s=len(self.lignes) - entrees))

    def _ligne(self, r, *_a) -> None:
        if 0 <= r < len(self.lignes) and self.lignes[r]["vin_id"]:
            self.vin_choisi.emit(self.lignes[r]["vin_id"])

    def _modifier(self, r, _c) -> None:
        if 0 <= r < len(self.lignes):
            if DialogueMouvement(self.cave, self.lignes[r], self).exec() == QDialog.DialogCode.Accepted:
                self.rafraichir()
                self.modifie.emit()
