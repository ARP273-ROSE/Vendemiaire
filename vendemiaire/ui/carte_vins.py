# -*- coding: utf-8 -*-
"""Carte des vins « de grand restaurant » : réglages, choix des vins, aperçu,
PDF (LaTeX, ou repli Qt) et HTML. Les cartes enregistrées se régénèrent d'un
clic : la cave a changé, la carte suit (une bouteille bue disparaît)."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QDate, QSettings, Qt
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDateEdit, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                             QPlainTextEdit, QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QTabWidget,
                             QTextBrowser, QVBoxLayout, QWidget)

from .. import i18n
from ..documents import carte as mod_carte
from ..documents import latex as mod_latex
from ..documents.qt_pdf import document
from ..i18n import tr
from . import travail

FILTRE_PDF = "PDF (*.pdf)"
FILTRE_HTML = "HTML (*.html)"
FILTRE_PROGRAMMES = "(*)"
MODELES = {"classique": "carte.m_classique", "moderne": "carte.m_moderne", "bistrot": "carte.m_bistrot"}
FORMATS = {"a4": "carte.f_a4", "a5": "carte.f_a5", "simple": "carte.f_simple"}
CASES = (("prix", "carte.o_prix"), ("france_dabord", "carte.o_france"), ("cartes", "carte.o_cartes"),
         ("index", "carte.o_index"), ("accords_auto", "carte.o_accords"), ("degre", "carte.o_degre"),
         ("cepages", "carte.o_cepages"))


def moteur_choisi():
    chemin = QSettings().value("documents/moteur", "") or None
    return mod_latex.trouver_moteur(chemin)


class DialogueCarteVins(QDialog):
    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        self.carte_id: int | None = None
        self._travail = None
        self.dernier_moteur = ""
        self.setWindowTitle(tr("carte.titre_dialogue"))
        self.resize(1320, 860)
        racine = QHBoxLayout(self)
        coupe = QSplitter()
        # --- cartes enregistrées
        gauche = QWidget()
        lg = QVBoxLayout(gauche)
        t = QLabel(tr("carte.enregistrees"))
        t.setObjectName("sous_titre")
        lg.addWidget(t)
        self.liste = QListWidget()
        lg.addWidget(self.liste, 1)
        self.b_nouvelle = QPushButton(tr("carte.nouvelle"))
        self.b_supprimer = QPushButton(tr("carte.supprimer"))
        self.b_regenerer = QPushButton(tr("carte.regenerer"))
        self.b_regenerer.setToolTip(tr("carte.regenerer_aide"))
        for b in (self.b_nouvelle, self.b_regenerer, self.b_supprimer):
            lg.addWidget(b)
        coupe.addWidget(gauche)
        # --- réglages / vins / aperçu
        self.onglets = QTabWidget()
        self.onglets.addTab(self._reglages(), tr("carte.onglet_reglages"))
        self.onglets.addTab(self._vins(), tr("carte.onglet_vins"))
        self.apercu = QTextBrowser()
        self.onglets.addTab(self.apercu, tr("carte.onglet_apercu"))
        droite = QWidget()
        ld = QVBoxLayout(droite)
        ld.addWidget(self.onglets, 1)
        self.etat = QLabel()
        self.etat.setObjectName("legende")
        self.etat.setWordWrap(True)
        ld.addWidget(self.etat)
        bas = QHBoxLayout()
        self.b_enregistrer = QPushButton(tr("carte.enregistrer"))
        self.b_bins = QPushButton(tr("carte.inscrire_bins"))
        self.b_bins.setToolTip(tr("carte.inscrire_bins_aide"))
        self.b_html = QPushButton(tr("carte.html"))
        self.b_pdf = QPushButton(tr("carte.pdf"))
        self.b_pdf.setObjectName("principal")
        self.b_moteur = QPushButton(tr("carte.moteur"))
        fermer = QPushButton(tr("regles.fermer"))
        for b in (self.b_enregistrer, self.b_bins, self.b_moteur):
            bas.addWidget(b)
        bas.addStretch(1)
        for b in (self.b_html, self.b_pdf, fermer):
            bas.addWidget(b)
        ld.addLayout(bas)
        coupe.addWidget(droite)
        coupe.setSizes([260, 1060])
        racine.addWidget(coupe)

        self.liste.currentItemChanged.connect(lambda it, _a: self.charger(it.data(Qt.ItemDataRole.UserRole))
                                              if it else None)
        self.b_nouvelle.clicked.connect(self.nouvelle)
        self.b_supprimer.clicked.connect(self.supprimer)
        self.b_regenerer.clicked.connect(lambda: self.pdf(self._dernier_chemin()))
        self.b_enregistrer.clicked.connect(self.enregistrer)
        self.b_bins.clicked.connect(self.inscrire_bins)
        self.b_html.clicked.connect(lambda: self.html())
        self.b_pdf.clicked.connect(lambda: self.pdf())
        self.b_moteur.clicked.connect(self.choisir_moteur)
        fermer.clicked.connect(self.accept)
        self.onglets.currentChanged.connect(lambda i: self.rafraichir_apercu() if i == 2 else None)
        self.remplir_liste()
        self.nouvelle()
        self._etat_moteur()

    # ------------------------------------------------------------------ construction
    def _reglages(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        self.nom = QLineEdit(tr("carte.nom_defaut"))
        self.modele = QComboBox()
        for code, cle in MODELES.items():
            self.modele.addItem(tr(cle), code)
        self.format = QComboBox()
        for code, cle in FORMATS.items():
            self.format.addItem(tr(cle), code)
        self.langue = QComboBox()
        for code, nom in i18n.LANGUES.items():
            self.langue.addItem(nom, code)
        self.langue.setCurrentIndex(max(0, self.langue.findData(i18n.langue())))
        self.titre = QLineEdit()
        self.titre.setPlaceholderText(tr("carte.titre_defaut"))
        self.lieu = QLineEdit()
        self.lieu.setPlaceholderText(tr("carte.lieu_aide"))
        self.date = QDateEdit(QDate.currentDate())
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("dd/MM/yyyy" if i18n.langue() == "fr" else "yyyy-MM-dd")
        self.mot = QPlainTextEdit()
        self.mot.setPlaceholderText(tr("carte.mot_aide"))
        self.mot.setMaximumHeight(90)
        self.menu = QPlainTextEdit()
        self.menu.setPlaceholderText(tr("carte.menu_aide"))
        self.menu.setMaximumHeight(110)
        self.cases = {}
        grille = QHBoxLayout()
        colonne = QVBoxLayout()
        for i, (cle, texte) in enumerate(CASES):
            c = QCheckBox(tr(texte))
            c.setChecked(bool(mod_carte.OPTIONS_DEFAUT[cle]))
            self.cases[cle] = c
            colonne.addWidget(c)
            if i == 3:
                grille.addLayout(colonne)
                colonne = QVBoxLayout()
        grille.addLayout(colonne)
        self.toute = QCheckBox(tr("carte.toute_la_cave"))
        self.toute.setChecked(True)
        self.toute.setToolTip(tr("carte.toute_la_cave_aide"))
        f.addRow(tr("carte.c_nom"), self.nom)
        f.addRow(tr("carte.c_modele"), self.modele)
        f.addRow(tr("carte.c_format"), self.format)
        f.addRow(tr("carte.c_langue"), self.langue)
        f.addRow(tr("carte.c_titre"), self.titre)
        f.addRow(tr("carte.c_lieu"), self.lieu)
        f.addRow(tr("carte.c_date"), self.date)
        f.addRow(tr("carte.c_mot"), self.mot)
        f.addRow(tr("carte.c_menu"), self.menu)
        f.addRow(tr("carte.c_options"), grille)
        f.addRow("", self.toute)
        aide = QLabel(tr("carte.aide_regles"))
        aide.setObjectName("legende")
        aide.setWordWrap(True)
        f.addRow(aide)
        return w

    def _vins(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        aide = QLabel(tr("carte.vins_aide"))
        aide.setObjectName("legende")
        aide.setWordWrap(True)
        l.addWidget(aide)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([tr("carte.v_inclure"), tr("carte.v_vin"), tr("carte.v_verre"),
                                              tr("carte.v_prix"), tr("carte.v_prix_verre"), tr("carte.v_accord")])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        l.addWidget(self.table, 1)
        r = self.cave.base.lire("SELECT vin_id, COUNT(*) n FROM bouteille WHERE statut='en_cave' GROUP BY vin_id")
        vins = sorted(((self.cave.nom_vin(x["vin_id"]), x["vin_id"], x["n"]) for x in r), key=lambda v: v[0].lower())
        self.table.setRowCount(len(vins))
        self.lignes_vins: list[int] = []
        for i, (nom, vid, n) in enumerate(vins):
            self.lignes_vins.append(vid)
            inc = QTableWidgetItem()
            inc.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            inc.setCheckState(Qt.CheckState.Checked)
            self.table.setItem(i, 0, inc)
            it = QTableWidgetItem(f"{nom}  ({n})")
            it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 1, it)
            verre = QTableWidgetItem()
            verre.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            verre.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(i, 2, verre)
            for j in (3, 4):
                s = QDoubleSpinBox()
                s.setRange(0, 100000)
                s.setDecimals(2)
                s.setSpecialValueText(" ")
                self.table.setCellWidget(i, j, s)
            self.table.setItem(i, 5, QTableWidgetItem(""))
        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(2, 70)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 100)
        return w

    # ------------------------------------------------------------------ options ⇄ écran
    def options(self) -> dict:
        o = {"modele": self.modele.currentData(), "format": self.format.currentData(),
             "langue": self.langue.currentData(), "titre": self.titre.text().strip(),
             "lieu": self.lieu.text().strip(), "date": self.date.date().toString("yyyy-MM-dd"),
             "mot": self.mot.toPlainText().strip(),
             "menu": [x.strip() for x in self.menu.toPlainText().splitlines() if x.strip()]}
        for cle, c in self.cases.items():
            o[cle] = c.isChecked()
        return o

    def reglages_vins(self) -> dict:
        """{vin_id: {inclus, au_verre, prix, prix_verre, accord}}."""
        sortie = {}
        for i, vid in enumerate(self.lignes_vins):
            sortie[vid] = {"inclus": self.table.item(i, 0).checkState() == Qt.CheckState.Checked,
                           "au_verre": self.table.item(i, 2).checkState() == Qt.CheckState.Checked,
                           "prix": self.table.cellWidget(i, 3).value() or None,
                           "prix_verre": self.table.cellWidget(i, 4).value() or None,
                           "accord": (self.table.item(i, 5).text() or "").strip()}
        return sortie

    def construire(self) -> mod_carte.Carte:
        r = self.reglages_vins()
        if self.toute.isChecked():
            return mod_carte.construire(self.cave, self.options(), None, r)
        choisis = [v for v, d in r.items() if d["inclus"]]
        return mod_carte.construire(self.cave, self.options(), choisis, r)

    def remplir(self, options: dict, vins: dict | None, reglages: dict) -> None:
        o = mod_carte.options_completes(options)
        self.modele.setCurrentIndex(max(0, self.modele.findData(o["modele"])))
        self.format.setCurrentIndex(max(0, self.format.findData(o["format"])))
        self.langue.setCurrentIndex(max(0, self.langue.findData(o["langue"])))
        self.titre.setText(o.get("titre") or "")
        self.lieu.setText(o.get("lieu") or "")
        self.date.setDate(QDate.fromString(o["date"][:10], "yyyy-MM-dd"))
        self.mot.setPlainText(o.get("mot") or "")
        self.menu.setPlainText("\n".join(o.get("menu") or []))
        for cle, c in self.cases.items():
            c.setChecked(bool(o.get(cle)))
        self.toute.setChecked(vins is None)
        for i, vid in enumerate(self.lignes_vins):
            d = reglages.get(vid) or {}
            self.table.item(i, 0).setCheckState(Qt.CheckState.Checked if (vins is None or vid in vins)
                                                else Qt.CheckState.Unchecked)
            self.table.item(i, 2).setCheckState(Qt.CheckState.Checked if d.get("au_verre") else Qt.CheckState.Unchecked)
            self.table.cellWidget(i, 3).setValue(float(d.get("prix") or 0))
            self.table.cellWidget(i, 4).setValue(float(d.get("prix_verre") or 0))
            self.table.item(i, 5).setText(d.get("accord") or "")

    # ------------------------------------------------------------------ cartes enregistrées
    def remplir_liste(self, choisir: int | None = None) -> None:
        self.liste.blockSignals(True)
        self.liste.clear()
        for c in mod_carte.cartes(self.cave):
            it = QListWidgetItem(c["nom"])
            it.setData(Qt.ItemDataRole.UserRole, c["id"])
            self.liste.addItem(it)
            if c["id"] == choisir:
                self.liste.setCurrentItem(it)
        self.liste.blockSignals(False)

    def nouvelle(self) -> None:
        self.carte_id = None
        self.liste.clearSelection()
        self.nom.setText(tr("carte.nom_defaut"))
        self.remplir(mod_carte.OPTIONS_DEFAUT | {"langue": i18n.langue()}, None, {})
        self._etat_moteur()

    def charger(self, carte_id: int) -> None:
        r, o, vins = mod_carte.lire(self.cave, carte_id)
        reglages = {x["vin_id"]: dict(x) for x in self.cave.base.lire(
            "SELECT * FROM carte_vin WHERE carte_id=?", (carte_id,))}
        self.carte_id = carte_id
        self.nom.setText(r["nom"])
        self.remplir(o, vins, reglages)
        if self.onglets.currentIndex() == 2:
            self.rafraichir_apercu()
        self._etat_moteur()

    def enregistrer(self) -> int:
        r = self.reglages_vins()
        if self.toute.isChecked():
            vins = {v: d for v, d in r.items() if d["au_verre"] or d["prix"] or d["prix_verre"] or d["accord"]}
            self.carte_id = mod_carte.enregistrer(self.cave, self.nom.text().strip() or tr("carte.nom_defaut"),
                                                  self.options(), None, self.carte_id)
            if vins:                                 # réglages par vin gardés même pour « toute la cave »
                with self.cave.base.ecriture() as c:
                    for vid, d in vins.items():
                        c.execute("INSERT OR REPLACE INTO carte_vin(carte_id, vin_id, au_verre, prix, prix_verre, accord) "
                                  "VALUES(?,?,?,?,?,?)", (self.carte_id, vid, 1 if d["au_verre"] else 0, d["prix"],
                                                          d["prix_verre"], d["accord"] or None))
        else:
            vins = {v: d for v, d in r.items() if d["inclus"]}
            self.carte_id = mod_carte.enregistrer(self.cave, self.nom.text().strip() or tr("carte.nom_defaut"),
                                                  self.options(), vins, self.carte_id)
        self.remplir_liste(self.carte_id)
        self.etat.setText(tr("carte.enregistree"))
        return self.carte_id

    def supprimer(self) -> None:
        if self.carte_id and QMessageBox.question(self, tr("carte.titre_dialogue"), tr("carte.confirmer_suppression")) \
                == QMessageBox.StandardButton.Yes:
            mod_carte.supprimer(self.cave, self.carte_id)
            self.remplir_liste()
            self.nouvelle()

    def _dernier_chemin(self) -> str | None:
        if self.carte_id:
            r = self.cave.base.un("SELECT dernier_pdf FROM carte WHERE id=?", (self.carte_id,))
            return r["dernier_pdf"] if r else None
        return None

    # ------------------------------------------------------------------ sorties
    def rafraichir_apercu(self) -> None:
        k = self.construire()
        images: dict = {}
        page = mod_carte.html(k, images)
        doc = document(page, images)
        self.apercu.setDocument(doc)
        self._doc_apercu = doc
        self.etat.setText(tr("carte.resume", n=len(k.toutes_les_lignes()), b=k.bouteilles))

    def html(self, chemin: str | None = None) -> str | None:
        if not chemin:
            chemin, _ = QFileDialog.getSaveFileName(self, tr("carte.html"), str(Path.home() / "carte-des-vins.html"),
                                                    FILTRE_HTML)
        if chemin:
            Path(chemin).write_text(mod_carte.html(self.construire()), encoding="utf-8")
            self.etat.setText(tr("carte.ecrit", chemin=chemin))
        return chemin or None

    def pdf(self, chemin: str | None = None, attendre: bool = False) -> str | None:
        if not chemin:
            chemin, _ = QFileDialog.getSaveFileName(self, tr("carte.pdf"), str(Path.home() / "carte-des-vins.pdf"),
                                                    FILTRE_PDF)
        if not chemin:
            return None
        k = self.construire()
        if k.vide():
            QMessageBox.information(self, tr("carte.titre_dialogue"), tr("carte.vide"))
            return None
        m = moteur_choisi()
        if self.carte_id:
            mod_carte.noter_pdf(self.cave, self.carte_id, chemin)
        if m is None:
            self.dernier_moteur = mod_carte.ecrire_pdf(k, chemin, forcer_qt=True)
            self.etat.setText(tr("carte.ecrit_qt", chemin=chemin))
            return chemin
        source, annexes = mod_carte.latex(k, m.unicode)
        self.b_pdf.setEnabled(False)
        self.etat.setText(tr("carte.compilation", moteur=m.nom))

        def fini(r):
            self.b_pdf.setEnabled(True)
            self.dernier_moteur = r.moteur
            self.etat.setText(tr("carte.ecrit_latex", chemin=chemin, moteur=r.moteur))

        def echec(e):
            self.b_pdf.setEnabled(True)
            # repli : le même contenu par Qt, et l'erreur dite
            self.dernier_moteur = mod_carte.ecrire_pdf(k, chemin, forcer_qt=True)
            self.etat.setText(tr("carte.echec_latex", erreur=str(e)[:300], chemin=chemin))

        self._travail = travail.lancer(mod_latex.compiler, source, chemin, annexes, moteur=m, fini=fini, echec=echec,
                                       parent=self)
        if attendre:
            travail.attendre(self._travail, 240000)
        return chemin

    def inscrire_bins(self) -> None:
        n = mod_carte.attribuer_bins(self.cave, self.construire())
        self.etat.setText(tr("carte.bins_inscrits", n=n))

    def choisir_moteur(self) -> None:
        chemin, _ = QFileDialog.getOpenFileName(self, tr("carte.moteur"), str(Path.home()), FILTRE_PROGRAMMES)
        QSettings().setValue("documents/moteur", chemin or "")
        self._etat_moteur()

    def _etat_moteur(self) -> None:
        m = moteur_choisi()
        self.etat.setText(tr("carte.moteur_trouve", moteur=m.nom) if m else tr("carte.moteur_absent"))
        self.etat.setToolTip(m.chemin if m else "")
