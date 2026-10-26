# -*- coding: utf-8 -*-
"""Liste d'achats : générée par les seuils de réassort, complétée au choix par
les envies (avec leurs alertes de prix). Aperçu, PDF imprimable, CSV."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel,
                             QMessageBox, QPushButton, QTextBrowser, QVBoxLayout)

from .. import achats
from ..i18n import argent, date_affichee, tr

FILTRE_PDF = "PDF (*.pdf)"
FILTRE_CSV = "CSV (*.csv)"


def textes() -> dict:
    return {"date": tr("achats.date", date=date_affichee(date.today().isoformat())),
            "reassort": tr("achats.reassort"), "envies": tr("achats.envies"), "vin": tr("livre.vin"),
            "quantite": tr("achats.quantite"), "detail": tr("achats.detail"),
            "detail_reassort": tr("achats.detail_reassort"), "dernier_prix": tr("achats.dernier_prix"),
            "prix_max": tr("achats.prix_max"), "alerte": tr("achats.alerte"), "vide": tr("achats.vide")}


class DialogueAchats(QDialog):
    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        self.setWindowTitle(tr("achats.titre"))
        self.resize(820, 680)
        v = QVBoxLayout(self)
        aide = QLabel(tr("achats.aide"))
        aide.setObjectName("legende")
        aide.setWordWrap(True)
        v.addWidget(aide)
        h = QHBoxLayout()
        self.avec_envies = QCheckBox(tr("achats.avec_envies"))
        self.avec_envies.setChecked(True)
        self.priorite = QComboBox()
        for p, cle in ((1, "achats.priorite_1"), (2, "achats.priorite_2"), (3, "achats.priorite_3")):
            self.priorite.addItem(tr(cle), p)
        self.priorite.setCurrentIndex(2)
        self.priorite.setAccessibleName(tr("envie.priorite"))
        h.addWidget(self.avec_envies)
        h.addWidget(self.priorite)
        h.addStretch(1)
        v.addLayout(h)
        self.apercu = QTextBrowser()
        self.apercu.setAccessibleName(tr("achats.titre"))
        v.addWidget(self.apercu, 1)
        self.bilan = QLabel()
        self.bilan.setObjectName("legende")
        v.addWidget(self.bilan)
        b = QHBoxLayout()
        self.b_pdf = QPushButton(tr("achats.pdf"))
        self.b_pdf.setObjectName("principal")
        self.b_csv = QPushButton(tr("achats.csv"))
        fermer = QPushButton(tr("bouton.fermer"))
        b.addWidget(self.b_pdf)
        b.addWidget(self.b_csv)
        b.addStretch(1)
        b.addWidget(fermer)
        v.addLayout(b)
        self.avec_envies.toggled.connect(self.rafraichir)
        self.priorite.currentIndexChanged.connect(self.rafraichir)
        self.b_pdf.clicked.connect(self.pdf)
        self.b_csv.clicked.connect(self.csv)
        fermer.clicked.connect(self.accept)
        self.rafraichir()

    def rafraichir(self, *_a) -> None:
        self.lignes = achats.liste_achats(self.cave, self.avec_envies.isChecked(), self.priorite.currentData())
        self.apercu.setHtml(achats.html_liste(self.lignes, tr("achats.titre"), textes(), argent))
        n_r = sum(1 for l in self.lignes if l.origine == "reassort")
        bouteilles = sum(l.a_acheter or 0 for l in self.lignes)
        self.bilan.setText(tr("achats.bilan", r=n_r, e=len(self.lignes) - n_r, n=bouteilles))
        self.b_pdf.setEnabled(bool(self.lignes))
        self.b_csv.setEnabled(bool(self.lignes))

    def pdf(self) -> None:
        chemin, _ = QFileDialog.getSaveFileName(self, tr("achats.pdf"),
                                                str(Path.home() / tr("achats.fichier")), FILTRE_PDF)
        if not chemin:
            return
        if not chemin.lower().endswith(".pdf"):
            chemin += ".pdf"
        from ..documents.qt_pdf import html_vers_pdf
        html_vers_pdf(achats.html_liste(self.lignes, tr("achats.titre"), textes(), argent), chemin)
        QMessageBox.information(self, tr("achats.titre"), tr("achats.ecrit", chemin=chemin))

    def csv(self) -> None:
        chemin, _ = QFileDialog.getSaveFileName(self, tr("achats.csv"),
                                                str(Path.home() / (Path(tr("achats.fichier")).stem + ".csv")),
                                                FILTRE_CSV)
        if not chemin:
            return
        if not chemin.lower().endswith(".csv"):
            chemin += ".csv"
        achats.exporter_csv(self.lignes, chemin)
        QMessageBox.information(self, tr("achats.titre"), tr("achats.ecrit", chemin=chemin))
