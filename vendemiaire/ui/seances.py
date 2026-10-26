# -*- coding: utf-8 -*-
"""Onglet « Dégustations » : séances verticales, horizontales, à l'aveugle.

À l'aveugle, la liste ne montre que des lettres (A, B, C… dans un ordre tiré
au hasard) jusqu'à « Révéler » ; les notes prises avant restent figées."""
from __future__ import annotations

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
                             QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                             QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from .. import seances
from ..i18n import date_affichee, langue, nombre, tr

AIDES = {"verticale": "seance.aide_verticale", "horizontale": "seance.aide_horizontale",
         "libre": "seance.aide_libre", "aveugle": "seance.aide_aveugle"}
TYPES = {"verticale": "seance.t_verticale", "horizontale": "seance.t_horizontale",
         "aveugle": "seance.t_aveugle", "libre": "seance.t_libre"}


def _cellule(texte) -> QTableWidgetItem:
    it = QTableWidgetItem("" if texte is None else str(texte))
    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return it


class DialogueNouvelleSeance(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("seance.nouvelle"))
        f = QFormLayout(self)
        self.type = QComboBox()
        for code, cle in TYPES.items():
            self.type.addItem(tr(cle), code)
        self.titre = QLineEdit()
        self.date = QDateEdit(QDate.currentDate())
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("dd/MM/yyyy" if langue() == "fr" else "yyyy-MM-dd")
        f.addRow(tr("seance.type"), self.type)
        f.addRow(tr("seance.titre_champ"), self.titre)
        f.addRow(tr("seance.date"), self.date)
        aide = QLabel(tr("seance.aide_types"))
        aide.setObjectName("legende")
        aide.setWordWrap(True)
        f.addRow(aide)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        b.button(QDialogButtonBox.StandardButton.Ok).setText(tr("bouton.creer"))
        b.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("bouton.annuler"))
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        f.addRow(b)


class VueSeances(QWidget):
    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        racine = QHBoxLayout(self)
        coupe = QSplitter()
        gauche = QWidget()
        lg = QVBoxLayout(gauche)
        self.liste = QListWidget()
        lg.addWidget(self.liste, 1)
        bl = QHBoxLayout()
        self.b_nouvelle = QPushButton(tr("seance.nouvelle"))
        self.b_nouvelle.setObjectName("principal")
        self.b_supprimer = QPushButton(tr("seance.supprimer"))
        bl.addWidget(self.b_nouvelle)
        bl.addWidget(self.b_supprimer)
        lg.addLayout(bl)
        coupe.addWidget(gauche)

        droite = QWidget()
        ld = QVBoxLayout(droite)
        self.entete = QLabel()
        self.entete.setObjectName("titre_section")
        ld.addWidget(self.entete)
        self.etat = QLabel()
        self.etat.setObjectName("legende")
        self.etat.setWordWrap(True)
        ld.addWidget(self.etat)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([tr("seance.c_ordre"), tr("seance.c_vin"), tr("seance.c_note"),
                                              tr("seance.c_commentaire"), tr("seance.c_aromes")])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 360)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 300)
        ld.addWidget(self.table, 1)
        bd = QHBoxLayout()
        self.b_ajouter = QPushButton(tr("seance.ajouter_vin"))
        self.b_proposer = QPushButton(tr("seance.proposer"))
        self.b_retirer = QPushButton(tr("seance.retirer"))
        self.b_melanger = QPushButton(tr("seance.melanger"))
        self.b_noter = QPushButton(tr("seance.noter"))
        self.b_noter.setObjectName("principal")
        self.b_reveler = QPushButton(tr("seance.reveler"))
        for b in (self.b_ajouter, self.b_proposer, self.b_retirer, self.b_melanger):
            bd.addWidget(b)
        bd.addStretch(1)
        bd.addWidget(self.b_noter)
        bd.addWidget(self.b_reveler)
        ld.addLayout(bd)
        coupe.addWidget(droite)
        coupe.setSizes([320, 1000])
        racine.addWidget(coupe)

        self.liste.currentRowChanged.connect(lambda _i: self.afficher())
        self.b_nouvelle.clicked.connect(self.nouvelle)
        self.b_supprimer.clicked.connect(self.supprimer)
        self.b_ajouter.clicked.connect(self.ajouter_vin)
        self.b_proposer.clicked.connect(self.proposer)
        self.b_retirer.clicked.connect(self.retirer)
        self.b_melanger.clicked.connect(self.melanger)
        self.b_noter.clicked.connect(self.noter)
        self.table.cellDoubleClicked.connect(lambda _r, _c: self.noter())
        self.b_reveler.clicked.connect(self.reveler)
        self.rafraichir()

    # ------------------------------------------------------------------ état
    def seance_id(self) -> int | None:
        it = self.liste.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    def rafraichir(self, choisir: int | None = None) -> None:
        courant = choisir or self.seance_id()
        self.liste.blockSignals(True)
        self.liste.clear()
        for s in seances.seances(self.cave):
            texte = f"{date_affichee(s['date'])} — {tr(TYPES[s['type']])}"
            if s.get("titre"):
                texte += f" — {s['titre']}"
            texte += "  " + tr("seance.n_vins", n=s["n"])
            it = QListWidgetItem(texte)
            it.setData(Qt.ItemDataRole.UserRole, s["id"])
            self.liste.addItem(it)
            if s["id"] == courant:
                self.liste.setCurrentItem(it)
        if self.liste.currentRow() < 0 and self.liste.count():
            self.liste.setCurrentRow(0)
        self.liste.blockSignals(False)
        self.afficher()

    def afficher(self) -> None:
        sid = self.seance_id()
        s = seances.seance(self.cave, sid) if sid else None
        for b in (self.b_ajouter, self.b_proposer, self.b_retirer, self.b_melanger, self.b_noter, self.b_reveler,
                  self.b_supprimer):
            b.setEnabled(s is not None)
        self.table.setRowCount(0)
        if s is None:
            self.entete.setText(tr("seance.aucune"))
            self.etat.setText(tr("seance.aide_types"))
            return
        cache = seances.cachee(s)
        self.entete.setText(f"{tr(TYPES[s['type']])} — {s.get('titre') or ''} ({date_affichee(s['date'])})")
        if s["type"] == "aveugle":
            self.etat.setText(tr("seance.etat_cache") if cache else
                              tr("seance.etat_revele", date=date_affichee(s["revelee_le"])))
        else:
            self.etat.setText(tr(AIDES[s["type"]]))
        self.b_melanger.setVisible(s["type"] == "aveugle")
        self.b_reveler.setVisible(s["type"] == "aveugle")
        self.b_melanger.setEnabled(cache)
        self.b_reveler.setEnabled(cache)
        self.b_ajouter.setEnabled(not (s["type"] == "aveugle" and not cache))
        self.b_proposer.setVisible(s["type"] in ("verticale", "horizontale"))
        self.b_noter.setEnabled(not (s["type"] == "aveugle" and not cache))
        vs = seances.vins(self.cave, sid)
        self.table.setRowCount(len(vs))
        for i, v in enumerate(vs):
            nom = tr("seance.vin_cache", lettre=v.etiquette) if cache else (
                f"{v.etiquette} — {v.nom}" if s["type"] == "aveugle" else v.nom)
            d = v.degustation or {}
            note = f"{nombre(d['note'], 1)}/{d.get('echelle') or '20'}" if d.get("note") is not None else ""
            for j, x in enumerate((str(i + 1), nom, note, d.get("commentaire") or "", d.get("aromes") or "")):
                it = _cellule(x)
                if j == 0:
                    it.setData(Qt.ItemDataRole.UserRole, v.vin_id)
                    it.setData(Qt.ItemDataRole.UserRole + 1, v.id)
                    it.setData(Qt.ItemDataRole.UserRole + 2, nom)
                self.table.setItem(i, j, it)

    # ------------------------------------------------------------------ actions
    def nouvelle(self) -> None:
        d = DialogueNouvelleSeance(self)
        if d.exec():
            sid = seances.creer(self.cave, d.type.currentData(), d.titre.text().strip(),
                                d.date.date().toString("yyyy-MM-dd"))
            self.rafraichir(sid)

    def supprimer(self) -> None:
        sid = self.seance_id()
        if sid and QMessageBox.question(self, tr("seance.titre"), tr("seance.confirmer_suppression")) \
                == QMessageBox.StandardButton.Yes:
            seances.supprimer(self.cave, sid)
            self.rafraichir()

    def _vins_en_cave(self) -> list[tuple[str, int]]:
        r = self.cave.base.lire("SELECT DISTINCT vin_id FROM bouteille WHERE statut='en_cave'")
        noms = [(self.cave.nom_vin(x["vin_id"]), x["vin_id"]) for x in r]
        return sorted(noms, key=lambda x: x[0].lower())

    def ajouter_vin(self, vin_id: int | None = None) -> None:
        sid = self.seance_id()
        if sid is None:
            return
        if not vin_id:
            vins = self._vins_en_cave()
            nom, ok = QInputDialog.getItem(self, tr("seance.ajouter_vin"), tr("seance.choisir_vin"),
                                           [n for n, _v in vins], 0, False)
            if not ok:
                return
            vin_id = dict(vins)[nom]
        try:
            seances.ajouter_vin(self.cave, sid, vin_id)
        except seances.SeanceRevelee:
            QMessageBox.warning(self, tr("seance.titre"), tr("seance.figee"))
        self.rafraichir()

    def proposer(self) -> None:
        sid = self.seance_id()
        s = seances.seance(self.cave, sid) if sid else None
        vs = seances.vins(self.cave, sid) if sid else []
        if s is None or not vs:
            QMessageBox.information(self, tr("seance.titre"), tr("seance.proposer_aide"))
            return
        deja = {v.vin_id for v in vs}
        ajouts = [x for x in seances.suggestions(self.cave, s["type"], vs[0].vin_id) if x not in deja]
        if not ajouts:
            QMessageBox.information(self, tr("seance.titre"), tr("seance.rien_a_proposer"))
            return
        for vid in ajouts:
            seances.ajouter_vin(self.cave, sid, vid)
        self.rafraichir()

    def _ligne(self):
        r = self.table.currentRow()
        it = self.table.item(r, 0) if r >= 0 else None
        if it is None:
            return None
        return (it.data(Qt.ItemDataRole.UserRole), it.data(Qt.ItemDataRole.UserRole + 1),
                it.data(Qt.ItemDataRole.UserRole + 2))

    def retirer(self) -> None:
        l = self._ligne()
        if l:
            seances.retirer_vin(self.cave, l[1])
            self.rafraichir()

    def melanger(self) -> None:
        sid = self.seance_id()
        if sid:
            seances.melanger(self.cave, sid)
            self.rafraichir()

    def noter(self) -> None:
        sid, l = self.seance_id(), self._ligne()
        if not sid or not l:
            return
        s = seances.seance(self.cave, sid)
        if s["type"] == "aveugle" and not seances.cachee(s):
            QMessageBox.information(self, tr("seance.titre"), tr("seance.figee"))
            return
        from .degustation import DialogueDegustation
        ancien = self.cave.base.un("SELECT * FROM degustation WHERE seance_id=? AND vin_id=?", (sid, l[0]))
        d = DialogueDegustation(self.cave, l[0], dict(ancien) if ancien else None, parent=self, seance_id=sid,
                                titre=tr("seance.noter_titre", vin=l[2]))
        if s["type"] == "aveugle":
            d.aveugle.setChecked(True)
            d.aveugle.setEnabled(False)
        if d.exec():
            self.rafraichir()

    def reveler(self) -> None:
        sid = self.seance_id()
        if not sid:
            return
        vs = seances.vins(self.cave, sid)
        manque = sum(1 for v in vs if v.degustation is None)
        texte = tr("seance.confirmer_revelation") + (("\n\n" + tr("seance.manque_notes", n=manque)) if manque else "")
        if QMessageBox.question(self, tr("seance.titre"), texte) == QMessageBox.StandardButton.Yes:
            seances.reveler(self.cave, sid)
            self.rafraichir()

