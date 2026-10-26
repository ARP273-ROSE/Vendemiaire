# -*- coding: utf-8 -*-
"""Import d'un tableau Excel/CSV (ou de l'export Vivino) : on choisit, pour
chaque champ de Vendémiaire, la colonne du fichier ; la correspondance est
proposée d'après les en-têtes, l'aperçu montre les premières lignes."""
from __future__ import annotations

from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGridLayout, QGroupBox, QLabel,
                             QScrollArea, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout)

from .. import imports_tableur
from ..i18n import lib, tr

#: libellé de chaque champ (table explicite : les clés restent vérifiables)
TEXTES_CHAMPS = {
    "producteur": "imp.ch_producteur",
    "cuvee": "imp.ch_cuvee",
    "appellation": "imp.ch_appellation",
    "region": "imp.ch_region",
    "pays": "imp.ch_pays",
    "couleur": "imp.ch_couleur",
    "type": "imp.ch_type",
    "millesime": "imp.ch_millesime",
    "cepages": "imp.ch_cepages",
    "degre": "imp.ch_degre",
    "quantite": "imp.ch_quantite",
    "format": "imp.ch_format",
    "prix_achat": "imp.ch_prix_achat",
    "date_achat": "imp.ch_date_achat",
    "lieu_achat": "imp.ch_lieu_achat",
    "note": "imp.ch_note",
    "commentaire": "imp.ch_commentaire",
    "date_degustation": "imp.ch_date_degustation",
    "notes": "imp.ch_notes",
    "ean": "imp.ch_ean",
}


class DialogueImportTableur(QDialog):
    def __init__(self, cave, chemin: str, profil: str = "generique", parent=None):
        super().__init__(parent)
        self.cave, self.chemin, self.profil = cave, chemin, profil
        self.setWindowTitle(tr("imp.titre_vivino" if profil == "vivino" else "imp.titre"))
        self.resize(1100, 820)
        self.entetes, self.lignes = imports_tableur.lire_tableau(chemin)
        devine = imports_tableur.deviner(self.entetes, profil)
        racine = QVBoxLayout(self)
        aide = QLabel(tr("imp.aide_vivino" if profil == "vivino" else "imp.aide", n=len(self.lignes)))
        aide.setWordWrap(True)
        aide.setObjectName("legende")
        racine.addWidget(aide)
        g = QGroupBox(tr("imp.correspondance"))
        grille = QGridLayout(g)
        self.choix: dict[str, QComboBox] = {}
        for i, champ in enumerate(imports_tableur.CHAMPS):
            c = QComboBox()
            c.addItem(tr("imp.aucune"), None)
            for j, e in enumerate(self.entetes):
                c.addItem(e or f"#{j + 1}", j)
            if champ in devine:
                c.setCurrentIndex(devine[champ] + 1)
            self.choix[champ] = c
            grille.addWidget(QLabel(tr(TEXTES_CHAMPS[champ])), i // 2, (i % 2) * 2)
            grille.addWidget(c, i // 2, (i % 2) * 2 + 1)
        zone = QScrollArea()
        zone.setWidgetResizable(True)
        zone.setWidget(g)
        racine.addWidget(zone, 2)
        f = QFormLayout()
        self.quantite = QSpinBox()
        self.quantite.setRange(0, 120)
        self.quantite.setValue(0 if profil == "vivino" else 1)
        self.echelle = QComboBox()
        for code in ("5", "20", "100"):
            self.echelle.addItem(lib("echelle", code), code)
        f.addRow(tr("imp.quantite_defaut"), self.quantite)
        f.addRow(tr("imp.echelle"), self.echelle)
        racine.addLayout(f)
        t = QLabel(tr("imp.apercu"))
        t.setObjectName("sous_titre")
        racine.addWidget(t)
        self.apercu = QTableWidget(min(8, len(self.lignes)), len(self.entetes))
        self.apercu.setHorizontalHeaderLabels(self.entetes)
        for i, l in enumerate(self.lignes[:8]):
            for j, v in enumerate(l[:len(self.entetes)]):
                self.apercu.setItem(i, j, QTableWidgetItem(v))
        racine.addWidget(self.apercu, 1)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        b.button(QDialogButtonBox.StandardButton.Ok).setText(tr("imp.importer"))
        b.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("bouton.annuler"))
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        racine.addWidget(b)
        self.rapport = None

    def correspondance(self) -> dict[str, int]:
        return {k: c.currentData() for k, c in self.choix.items() if c.currentData() is not None}

    def importer(self):
        self.rapport = imports_tableur.importer(self.cave, self.entetes, self.lignes, self.correspondance(),
                                                "vivino" if self.profil == "vivino" else "tableur",
                                                self.echelle.currentData(), self.quantite.value())
        return self.rapport

