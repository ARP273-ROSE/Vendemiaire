# -*- coding: utf-8 -*-
"""Inventaire de contrôle : compter un casier (ou un meuble, une cave), voir
les écarts, et décider quoi faire des bouteilles introuvables.

On coche ce qu'on trouve, ou on lit le code de la bouteille (code de casier
`V…`, saisi au clavier ou par un lecteur de codes qui « tape » le code). Rien
ne change dans la cave tant que l'utilisateur ne le demande pas."""
from __future__ import annotations

import json

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout)

from ..i18n import lib, tr


class DialogueInventaire(QDialog):
    def __init__(self, cave, emplacement_id: int | None = None, parent=None):
        super().__init__(parent)
        self.cave = cave
        self.ecarts: dict | None = None
        self.setWindowTitle(tr("inv.titre"))
        self.resize(760, 680)
        racine = QVBoxLayout(self)
        haut = QHBoxLayout()
        haut.addWidget(QLabel(tr("inv.lieu")))
        self.lieu = QComboBox()
        for e in cave.emplacements():
            self.lieu.addItem(" › ".join(cave.chemin_emplacement(e["id"])), e["id"])
        if emplacement_id is not None:
            self.lieu.setCurrentIndex(max(0, self.lieu.findData(emplacement_id)))
        haut.addWidget(self.lieu, 1)
        racine.addLayout(haut)
        aide = QLabel(tr("inv.aide"))
        aide.setWordWrap(True)
        aide.setObjectName("legende")
        racine.addWidget(aide)
        lecture = QHBoxLayout()
        self.code = QLineEdit()
        self.code.setPlaceholderText(tr("inv.code_aide"))
        lecture.addWidget(self.code, 1)
        self.b_tout = QPushButton(tr("inv.tout_cocher"))
        lecture.addWidget(self.b_tout)
        racine.addLayout(lecture)
        self.liste = QListWidget()
        racine.addWidget(self.liste, 1)
        racine.addWidget(QLabel(tr("inv.en_trop")))
        self.en_trop = QPlainTextEdit()
        self.en_trop.setPlaceholderText(tr("inv.en_trop_aide"))
        self.en_trop.setMaximumHeight(70)
        racine.addWidget(self.en_trop)
        self.resultat = QLabel()
        self.resultat.setWordWrap(True)
        racine.addWidget(self.resultat)
        bas = QHBoxLayout()
        self.b_enregistrer = QPushButton(tr("inv.enregistrer"))
        self.b_enregistrer.setObjectName("principal")
        self.b_manquantes = QPushButton(tr("inv.sortir_manquantes"))
        self.b_manquantes.setEnabled(False)
        self.b_fermer = QPushButton(tr("bouton.fermer"))
        bas.addWidget(self.b_enregistrer)
        bas.addWidget(self.b_manquantes)
        bas.addStretch(1)
        bas.addWidget(self.b_fermer)
        racine.addLayout(bas)
        self.lieu.currentIndexChanged.connect(lambda _i: self.charger())
        self.code.returnPressed.connect(self.lire_code)
        self.b_tout.clicked.connect(self.tout_cocher)
        self.b_enregistrer.clicked.connect(self.enregistrer)
        self.b_manquantes.clicked.connect(self.sortir_manquantes)
        self.b_fermer.clicked.connect(self.accept)
        self.charger()

    def charger(self) -> None:
        self.liste.clear()
        self.ecarts = None
        self.b_manquantes.setEnabled(False)
        self.resultat.clear()
        eid = self.lieu.currentData()
        if eid is None:
            return
        for b in self.cave.attendues(eid):
            place = " › ".join(self.cave.chemin_emplacement(b["emplacement_id"]))
            if b["rangee"] and b["colonne"]:
                place += " " + tr("plan.case", r=b["rangee"], c=b["colonne"])
            texte = f"{self.cave.nom_vin(b['vin_id'])} — {lib('format', b['format'])} — {place} " \
                    f"[{b['code_interne']}]"
            it = QListWidgetItem(texte)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Unchecked)
            it.setData(Qt.ItemDataRole.UserRole, b["id"])
            it.setData(Qt.ItemDataRole.UserRole + 1, b["code_interne"])
            self.liste.addItem(it)
        self.resultat.setText(tr("inv.attendues", n=self.liste.count()))

    def lire_code(self) -> None:
        code = self.code.text().strip()
        self.code.clear()
        if not code:
            return
        for i in range(self.liste.count()):
            it = self.liste.item(i)
            if it.data(Qt.ItemDataRole.UserRole + 1) == code:
                it.setCheckState(Qt.CheckState.Checked)
                self.liste.scrollToItem(it)
                return
        b = self.cave.bouteille_par_code(code)
        ligne = f"{code} — {self.cave.nom_vin(b['vin_id'])}" if b else code
        self.en_trop.appendPlainText(ligne)

    def tout_cocher(self) -> None:
        for i in range(self.liste.count()):
            self.liste.item(i).setCheckState(Qt.CheckState.Checked)

    def trouvees(self) -> list[int]:
        return [self.liste.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.liste.count())
                if self.liste.item(i).checkState() == Qt.CheckState.Checked]

    def enregistrer(self) -> None:
        eid = self.lieu.currentData()
        if eid is None:
            return
        en_trop = [l.strip() for l in self.en_trop.toPlainText().splitlines() if l.strip()]
        self.ecarts = self.cave.enregistrer_inventaire(eid, self.trouvees(), en_trop)
        n_manq = len(self.ecarts["manquantes"])
        self.resultat.setText(tr("inv.resultat", attendues=self.liste.count(), trouvees=len(self.trouvees()),
                                 manquantes=n_manq, en_trop=len(self.ecarts["en_trop"])))
        self.b_manquantes.setEnabled(n_manq > 0)

    def sortir_manquantes(self) -> None:
        if not self.ecarts or not self.ecarts["manquantes"]:
            return
        n = len(self.ecarts["manquantes"])
        if QMessageBox.question(self, self.windowTitle(), tr("inv.sortir_q", n=n)) \
                != QMessageBox.StandardButton.Yes:
            return
        self.cave.marquer_manquantes(self.ecarts["manquantes"])
        self.charger()


def resume_inventaire(ligne) -> str:
    try:
        e = json.loads(ligne["ecarts"] or "{}")
    except ValueError:
        e = {}
    return tr("inv.resume", attendu=ligne["attendu"] or 0, compte=ligne["compte"] or 0,
              manquantes=len(e.get("manquantes", [])), en_trop=len(e.get("en_trop", [])))
