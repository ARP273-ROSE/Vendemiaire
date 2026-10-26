# -*- coding: utf-8 -*-
"""Documents de la cave : rapport d'assurance / d'inventaire (PDF format
maison), partage en lecture seule (HTML autonome ou PDF), planche d'étiquettes
de casier à code QR."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                             QLineEdit, QMessageBox, QPushButton, QSpinBox, QTextBrowser, QVBoxLayout)

from .. import codes, i18n
from ..documents import assurance, etiquettes, partage
from ..documents import latex as mod_latex
from ..documents.qt_pdf import document
from ..i18n import tr
from . import travail
from .carte_vins import FILTRE_HTML, FILTRE_PDF, moteur_choisi


GABARITS = {"3x8": "etiq.g_3_8", "3x7": "etiq.g_3_7"}


def _langues(combo: QComboBox) -> None:
    for code, nom in i18n.LANGUES.items():
        combo.addItem(nom, code)
    combo.setCurrentIndex(max(0, combo.findData(i18n.langue())))


class DialogueAssurance(QDialog):
    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        self._travail = None
        self.setWindowTitle(tr("assur.dialogue"))
        self.resize(1000, 780)
        l = QVBoxLayout(self)
        f = QFormLayout()
        self.langue = QComboBox()
        _langues(self.langue)
        self.titre = QLineEdit()
        self.titre.setPlaceholderText(tr("assur.titre"))
        self.primeurs = QCheckBox(tr("assur.avec_primeurs"))
        f.addRow(tr("carte.c_langue"), self.langue)
        f.addRow(tr("carte.c_titre"), self.titre)
        f.addRow("", self.primeurs)
        l.addLayout(f)
        aide = QLabel(tr("assur.aide"))
        aide.setObjectName("legende")
        aide.setWordWrap(True)
        l.addWidget(aide)
        self.apercu = QTextBrowser()
        l.addWidget(self.apercu, 1)
        self.etat = QLabel()
        self.etat.setObjectName("legende")
        self.etat.setWordWrap(True)
        l.addWidget(self.etat)
        b = QHBoxLayout()
        self.b_pdf = QPushButton(tr("carte.pdf"))
        self.b_pdf.setObjectName("principal")
        fermer = QPushButton(tr("regles.fermer"))
        b.addStretch(1)
        b.addWidget(self.b_pdf)
        b.addWidget(fermer)
        l.addLayout(b)
        self.langue.currentIndexChanged.connect(lambda _i: self.rafraichir())
        self.primeurs.toggled.connect(lambda _c: self.rafraichir())
        self.b_pdf.clicked.connect(lambda: self.pdf())
        fermer.clicked.connect(self.accept)
        self.rafraichir()

    def inventaire(self) -> assurance.Inventaire:
        statuts = ("en_cave", "primeur", "en_attente") if self.primeurs.isChecked() else ("en_cave",)
        return assurance.construire(self.cave, self.langue.currentData(), statuts)

    def rafraichir(self) -> None:
        images: dict = {}
        inv = self.inventaire()
        doc = document(assurance.html(inv, self.titre.text().strip(), images), images)
        self.apercu.setDocument(doc)
        self._doc = doc
        self.etat.setText(tr("assur.resume_etat", n=inv.bouteilles, v=i18n.argent(round(inv.total))))

    def pdf(self, chemin: str | None = None, attendre: bool = False) -> str | None:
        if not chemin:
            chemin, _ = QFileDialog.getSaveFileName(self, tr("carte.pdf"), str(Path.home() / "inventaire-cave.pdf"),
                                                    FILTRE_PDF)
        if not chemin:
            return None
        inv = self.inventaire()
        m = moteur_choisi()
        if m is None:
            assurance.ecrire_pdf(inv, chemin, self.titre.text().strip(), forcer_qt=True)
            self.etat.setText(tr("carte.ecrit_qt", chemin=chemin))
            return chemin
        source, annexes = assurance.latex(inv, self.titre.text().strip(), m.unicode)
        self.b_pdf.setEnabled(False)
        self.etat.setText(tr("carte.compilation", moteur=m.nom))

        def fini(r):
            self.b_pdf.setEnabled(True)
            self.etat.setText(tr("carte.ecrit_latex", chemin=chemin, moteur=r.moteur))

        def echec(e):
            self.b_pdf.setEnabled(True)
            assurance.ecrire_pdf(inv, chemin, self.titre.text().strip(), forcer_qt=True)
            self.etat.setText(tr("carte.echec_latex", erreur=str(e)[:300], chemin=chemin))

        self._travail = travail.lancer(mod_latex.compiler, source, chemin, annexes, moteur=m, fini=fini,
                                       echec=echec, parent=self)
        if attendre:
            travail.attendre(self._travail, 240000)
        return chemin


class DialoguePartage(QDialog):
    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        self.setWindowTitle(tr("partage.dialogue"))
        self.resize(980, 760)
        l = QVBoxLayout(self)
        f = QFormLayout()
        self.langue = QComboBox()
        _langues(self.langue)
        self.titre = QLineEdit()
        self.titre.setPlaceholderText(tr("partage.titre"))
        self.prix = QCheckBox(tr("partage.o_prix"))
        self.photos = QCheckBox(tr("partage.o_photos"))
        self.photos.setChecked(True)
        self.emplacements = QCheckBox(tr("partage.o_emplacements"))
        self.notes = QCheckBox(tr("partage.o_notes"))
        self.notes.setChecked(True)
        f.addRow(tr("carte.c_langue"), self.langue)
        f.addRow(tr("carte.c_titre"), self.titre)
        for c in (self.prix, self.photos, self.emplacements, self.notes):
            f.addRow("", c)
            c.toggled.connect(lambda _c: self.rafraichir())
        l.addLayout(f)
        aide = QLabel(tr("partage.aide"))
        aide.setObjectName("legende")
        aide.setWordWrap(True)
        l.addWidget(aide)
        self.apercu = QTextBrowser()
        l.addWidget(self.apercu, 1)
        self.etat = QLabel()
        self.etat.setObjectName("legende")
        l.addWidget(self.etat)
        b = QHBoxLayout()
        self.b_html = QPushButton(tr("carte.html"))
        self.b_pdf = QPushButton(tr("carte.pdf"))
        self.b_pdf.setObjectName("principal")
        fermer = QPushButton(tr("regles.fermer"))
        b.addStretch(1)
        for x in (self.b_html, self.b_pdf, fermer):
            b.addWidget(x)
        l.addLayout(b)
        self.langue.currentIndexChanged.connect(lambda _i: self.rafraichir())
        self.b_html.clicked.connect(lambda: self.html())
        self.b_pdf.clicked.connect(lambda: self.pdf())
        fermer.clicked.connect(self.accept)
        self.rafraichir()

    def options(self) -> dict:
        return {"langue": self.langue.currentData(), "titre": self.titre.text().strip(),
                "prix": self.prix.isChecked(), "photos": self.photos.isChecked(),
                "emplacements": self.emplacements.isChecked(), "notes": self.notes.isChecked()}

    def rafraichir(self) -> None:
        images: dict = {}
        doc = document(partage.html(self.cave, images=images, **self.options()), images)
        self.apercu.setDocument(doc)
        self._doc = doc

    def html(self, chemin: str | None = None) -> str | None:
        if not chemin:
            chemin, _ = QFileDialog.getSaveFileName(self, tr("carte.html"), str(Path.home() / "ma-cave.html"), FILTRE_HTML)
        if chemin:
            partage.ecrire_html(self.cave, chemin, **self.options())
            self.etat.setText(tr("carte.ecrit", chemin=chemin))
        return chemin or None

    def pdf(self, chemin: str | None = None) -> str | None:
        if not chemin:
            chemin, _ = QFileDialog.getSaveFileName(self, tr("carte.pdf"), str(Path.home() / "ma-cave.pdf"), FILTRE_PDF)
        if chemin:
            partage.ecrire_pdf(self.cave, chemin, **self.options())
            self.etat.setText(tr("carte.ecrit", chemin=chemin))
        return chemin or None


class DialogueEtiquettes(QDialog):
    """Planche d'étiquettes QR : toute la cave, le vin choisi ou un casier."""

    def __init__(self, cave, vin_id: int | None = None, parent=None):
        super().__init__(parent)
        self.cave, self.vin_id = cave, vin_id
        self.setWindowTitle(tr("etiq.dialogue"))
        self.resize(560, 300)
        f = QFormLayout(self)
        self.quoi = QComboBox()
        self.quoi.addItem(tr("etiq.toute_la_cave"), ("tout", None))
        if vin_id:
            self.quoi.addItem(tr("etiq.ce_vin", vin=cave.nom_vin(vin_id)), ("vin", vin_id))
            self.quoi.setCurrentIndex(1)
        for e in cave.emplacements():
            if e["niveau"] == "casier":
                self.quoi.addItem(tr("etiq.casier", casier=" › ".join(cave.chemin_emplacement(e["id"]))),
                                  ("casier", e["id"]))
        self.gabarit = QComboBox()
        for code in etiquettes.GABARITS:
            self.gabarit.addItem(tr(GABARITS[code]), code)
        self.depart = QSpinBox()
        self.depart.setRange(0, 23)
        f.addRow(tr("etiq.quoi"), self.quoi)
        f.addRow(tr("etiq.gabarit"), self.gabarit)
        f.addRow(tr("etiq.depart"), self.depart)
        aide = QLabel(tr("etiq.aide") if codes.ecriture_disponible() else tr("etiq.segno_absent"))
        aide.setObjectName("legende")
        aide.setWordWrap(True)
        f.addRow(aide)
        self.etat = QLabel()
        self.etat.setObjectName("legende")
        f.addRow(self.etat)
        b = QHBoxLayout()
        self.b_pdf = QPushButton(tr("carte.pdf"))
        self.b_pdf.setObjectName("principal")
        self.b_pdf.setEnabled(codes.ecriture_disponible())
        fermer = QPushButton(tr("regles.fermer"))
        b.addStretch(1)
        b.addWidget(self.b_pdf)
        b.addWidget(fermer)
        f.addRow(b)
        self.b_pdf.clicked.connect(lambda: self.pdf())
        fermer.clicked.connect(self.accept)

    def bouteilles(self) -> list[dict]:
        genre, ident = self.quoi.currentData()
        if genre == "vin":
            return etiquettes.bouteilles_pour_etiquettes(self.cave, vin_id=ident)
        if genre == "casier":
            return etiquettes.bouteilles_pour_etiquettes(self.cave, casier_id=ident)
        return etiquettes.bouteilles_pour_etiquettes(self.cave)

    def pdf(self, chemin: str | None = None) -> str | None:
        bs = self.bouteilles()
        if not bs:
            QMessageBox.information(self, tr("etiq.dialogue"), tr("etiq.aucune"))
            return None
        if not chemin:
            chemin, _ = QFileDialog.getSaveFileName(self, tr("carte.pdf"), str(Path.home() / "etiquettes-casiers.pdf"),
                                                    FILTRE_PDF)
        if chemin:
            pages = etiquettes.ecrire_planche(bs, chemin, self.gabarit.currentData(), i18n.langue(),
                                              self.depart.value())
            self.etat.setText(tr("etiq.ecrit", n=len(bs), pages=pages, chemin=chemin))
        return chemin or None
