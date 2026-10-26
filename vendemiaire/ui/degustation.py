# -*- coding: utf-8 -*-
"""Fiche de dégustation (robe, nez, bouche, finale, roue des arômes du dossier)
et aide au diagnostic d'une bouteille (défauts du dossier)."""
from __future__ import annotations

from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox,
                             QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QSplitter,
                             QTextBrowser, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ..i18n import langue, lib, tr
from ..regles import degustation as r_deg
from . import regles_ui

#: libellés des cercles de la roue (codes du dossier -> clés de textes)
CERCLES = {"primaire": "deg.primaire", "secondaire": "deg.secondaire", "tertiaire": "deg.tertiaire",
           "défaut": "deg.defaut"}


class RoueAromes(QTreeWidget):
    """Roue des arômes du dossier : cercles › familles › descripteurs, à cocher."""

    def __init__(self, choix: str | None = None, parent=None):
        super().__init__(parent)
        lg = langue()
        self.setHeaderHidden(True)
        coches = set(r_deg.decoder(choix))
        cercles: dict[str, QTreeWidgetItem] = {}
        for f in r_deg.familles():
            c = cercles.get(f["cercle"])
            if c is None:
                c = QTreeWidgetItem([tr(CERCLES.get(f["cercle"], "deg.defaut"))])
                self.addTopLevelItem(c)
                cercles[f["cercle"]] = c
            fam = QTreeWidgetItem([f"{r_deg.nom_famille(f, lg)}  ({f['code']})"])
            fam.setData(0, Qt.ItemDataRole.UserRole, (f["code"], None))
            fam.setCheckState(0, Qt.CheckState.Checked if (f["code"], None) in coches
                              else Qt.CheckState.Unchecked)
            c.addChild(fam)
            for d in f["descripteurs"]:
                it = QTreeWidgetItem([r_deg.descripteur(d, lg)])
                it.setData(0, Qt.ItemDataRole.UserRole, (f["code"], d))
                it.setCheckState(0, Qt.CheckState.Checked if (f["code"], d) in coches else Qt.CheckState.Unchecked)
                fam.addChild(it)
                if (f["code"], d) in coches:
                    c.setExpanded(True)
                    fam.setExpanded(True)
        for c in cercles.values():
            if c.childCount() and not any(c.child(i).isExpanded() for i in range(c.childCount())):
                c.setExpanded(False)

    def choix(self) -> list[tuple[str, str | None]]:
        sortie = []
        for i in range(self.topLevelItemCount()):
            c = self.topLevelItem(i)
            for j in range(c.childCount()):
                fam = c.child(j)
                if fam.checkState(0) == Qt.CheckState.Checked:
                    sortie.append(fam.data(0, Qt.ItemDataRole.UserRole))
                for k in range(fam.childCount()):
                    it = fam.child(k)
                    if it.checkState(0) == Qt.CheckState.Checked:
                        sortie.append(it.data(0, Qt.ItemDataRole.UserRole))
        return [tuple(x) for x in sortie]


class DialogueDegustation(QDialog):
    def __init__(self, cave, vin_id: int, degustation: dict | None = None, bouteille_id: int | None = None,
                 parent=None):
        super().__init__(parent)
        self.cave, self.vin_id = cave, vin_id
        self.did = degustation["id"] if degustation else None
        d = dict(degustation) if degustation else {}
        self.bid = d.get("bouteille_id") or bouteille_id
        self.setWindowTitle(tr("deg.titre", vin=cave.nom_vin(vin_id)))
        self.resize(940, 680)
        racine = QVBoxLayout(self)
        coupe = QSplitter()
        gauche = QWidget()
        f = QFormLayout(gauche)
        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("dd/MM/yyyy" if langue() == "fr" else "yyyy-MM-dd")
        from PyQt6.QtCore import QDate
        self.date.setDate(QDate.fromString((d.get("date") or date.today().isoformat())[:10], "yyyy-MM-dd"))
        self.robe = QLineEdit(d.get("robe") or "")
        self.nez = QPlainTextEdit(d.get("nez") or "")
        self.bouche = QPlainTextEdit(d.get("bouche") or "")
        self.finale = QLineEdit(d.get("finale") or "")
        for w in (self.nez, self.bouche):
            w.setMaximumHeight(80)
        self.note = QDoubleSpinBox()
        self.note.setRange(0, 100)
        self.note.setDecimals(1)
        self.note.setSpecialValueText(" ")
        self.note.setValue(float(d.get("note") or 0))
        self.echelle = QComboBox()
        for code in ("20", "100", "5"):
            self.echelle.addItem(lib("echelle", code), code)
        self.echelle.setCurrentIndex(max(0, self.echelle.findData(d.get("echelle") or "20")))
        ligne = QHBoxLayout()
        ligne.addWidget(self.note)
        ligne.addWidget(self.echelle)
        self.aveugle = QCheckBox(tr("deg.aveugle"))
        self.aveugle.setChecked(bool(d.get("aveugle")))
        self.commentaire = QPlainTextEdit(d.get("commentaire") or "")
        for cle, w in (("deg.date", self.date), ("deg.robe", self.robe), ("deg.nez", self.nez),
                       ("deg.bouche", self.bouche), ("deg.finale", self.finale)):
            f.addRow(tr(cle), w)
        f.addRow(tr("deg.note"), ligne)
        f.addRow("", self.aveugle)
        f.addRow(tr("deg.commentaire"), self.commentaire)
        coupe.addWidget(gauche)
        droite = QWidget()
        ld = QVBoxLayout(droite)
        titre = QLabel(tr("deg.roue"))
        titre.setObjectName("sous_titre")
        ld.addWidget(titre)
        self.roue = RoueAromes(d.get("aromes"))
        ld.addWidget(self.roue, 1)
        aide = QLabel(tr("deg.roue_aide"))
        aide.setObjectName("legende")
        aide.setWordWrap(True)
        ld.addWidget(aide)
        coupe.addWidget(droite)
        coupe.setSizes([500, 420])
        racine.addWidget(coupe, 1)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        b.button(QDialogButtonBox.StandardButton.Save).setText(tr("bouton.enregistrer"))
        b.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("bouton.annuler"))
        b.accepted.connect(self.accepter)
        b.rejected.connect(self.reject)
        racine.addWidget(b)

    def donnees(self) -> dict:
        return {"vin_id": self.vin_id, "bouteille_id": self.bid,
                "date": self.date.date().toString("yyyy-MM-dd"),
                "robe": self.robe.text().strip() or None, "nez": self.nez.toPlainText().strip() or None,
                "bouche": self.bouche.toPlainText().strip() or None,
                "finale": self.finale.text().strip() or None,
                "aromes": r_deg.coder(self.roue.choix()) or None,
                "note": self.note.value() or None,
                "echelle": self.echelle.currentData() if self.note.value() else None,
                "commentaire": self.commentaire.toPlainText().strip() or None,
                "aveugle": 1 if self.aveugle.isChecked() else 0}

    def accepter(self) -> None:
        self.did = self.cave.enregistrer_degustation(self.donnees(), self.did)
        self.accept()


class DialogueDiagnostic(QDialog):
    """« Ma bouteille a un problème ? » : on décrit ce qu'on sent, le dossier
    propose les défauts compatibles, leur cause et que faire. Une bouteille
    bouchonnée peut être sortie du livre de cave d'ici."""

    def __init__(self, cave, bouteille_id: int | None = None, parent=None):
        super().__init__(parent)
        self.cave, self.bid = cave, bouteille_id
        self.setWindowTitle(tr("diag.titre"))
        self.resize(860, 620)
        racine = QVBoxLayout(self)
        haut = QHBoxLayout()
        haut.addWidget(QLabel(tr("diag.je_sens")))
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText(tr("diag.aide"))
        haut.addWidget(self.recherche, 1)
        racine.addLayout(haut)
        coupe = QSplitter()
        self.liste = QListWidget()
        self.detail = QTextBrowser()
        coupe.addWidget(self.liste)
        coupe.addWidget(self.detail)
        coupe.setSizes([320, 520])
        racine.addWidget(coupe, 1)
        bas = QHBoxLayout()
        self.b_bouchonnee = QPushButton(tr("diag.bouchonnee"))
        self.b_bouchonnee.setVisible(bool(bouteille_id) and
                                     (cave.bouteille(bouteille_id) or {"statut": ""})["statut"] == "en_cave")
        fermer = QPushButton(tr("regles.fermer"))
        bas.addWidget(self.b_bouchonnee)
        bas.addStretch(1)
        bas.addWidget(fermer)
        racine.addLayout(bas)
        self.recherche.textChanged.connect(lambda _t: self.rafraichir())
        self.liste.currentItemChanged.connect(lambda *_: self.montrer())
        self.b_bouchonnee.clicked.connect(self.bouchonnee)
        fermer.clicked.connect(self.accept)
        self.sortie = False
        self.rafraichir()

    def rafraichir(self) -> None:
        lg = langue()
        self.liste.clear()
        for d, n in r_deg.diagnostic(self.recherche.text()):
            it = QListWidgetItem(r_deg.texte_defaut(d, "nom", lg))
            it.setData(Qt.ItemDataRole.UserRole, d)
            it.setToolTip(r_deg.texte_defaut(d, "perception", lg))
            self.liste.addItem(it)
        if self.liste.count():
            self.liste.setCurrentRow(0)
        else:
            self.detail.setHtml(f"<p>{regles_ui.e(tr('diag.rien'))}</p>")

    def montrer(self) -> None:
        it = self.liste.currentItem()
        if it is None:
            return
        d = it.data(Qt.ItemDataRole.UserRole)
        lg = langue()
        e = regles_ui.e
        lignes = [("diag.ce_qu_on_sent", "perception"), ("diag.molecule", "molecule"), ("diag.seuil", "seuil"),
                  ("diag.cause", "cause"), ("diag.que_faire", "que_faire")]
        corps = "".join(f"<tr><td style='padding:3px 8px 3px 0'><b>{e(tr(c))}</b></td>"
                        f"<td>{e(r_deg.texte_defaut(d, champ, lg))}</td></tr>" for c, champ in lignes)
        html = (f"<h3>{e(r_deg.texte_defaut(d, 'nom', lg))}</h3><table>{corps}</table>"
                f"<p style='color:gray'>{e(lib('confiance', d.get('confiance')))}</p>"
                + regles_ui.sources_html(d.get("sources")))
        self.detail.setHtml(html)
        self.b_bouchonnee.setEnabled(d["id"] == "tca")

    def bouchonnee(self) -> None:
        if QMessageBox.question(self, self.windowTitle(), tr("diag.confirmer")) != QMessageBox.StandardButton.Yes:
            return
        self.cave.sortir(self.bid, "sortie_bouchonnee", commentaire=tr("diag.commentaire"))
        self.sortie = True
        self.accept()


