# -*- coding: utf-8 -*-
"""Livre de cave : toutes les entrées et sorties, avec occasion, convives,
plat, note et commentaire de dégustation — et les photos du moment (le plat,
la tablée, la bouteille ouverte), rangées avec la ligne du livre."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QIcon, QKeySequence, QPixmap, QShortcut
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                             QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from .. import images
from ..i18n import date_affichee, lib, nombre, tr
from .photos import EXTENSIONS, MOTIF_IMAGES, fichiers_images

COLONNES = ["livre.date", "livre.type", "livre.vin", "livre.millesime", "livre.photos", "livre.occasion",
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


class PanneauPhotos(QWidget):
    """Les photos de la ligne choisie du livre : ajouter (fichier ou
    glisser-déposer), ouvrir, retirer."""
    modifie = pyqtSignal()

    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        self.mouvement: dict | None = None
        self.setAcceptDrops(True)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.titre = QLabel(tr("livre.photos_titre"))
        self.titre.setObjectName("sous")
        self.titre.setWordWrap(True)
        v.addWidget(self.titre)
        self.liste = QListWidget()
        self.liste.setViewMode(QListWidget.ViewMode.IconMode)
        self.liste.setIconSize(QSize(150, 150))
        self.liste.setGridSize(QSize(170, 175))
        self.liste.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.liste.setMovement(QListWidget.Movement.Static)
        self.liste.setAccessibleName(tr("livre.photos_titre"))
        v.addWidget(self.liste, 1)
        self.aide = QLabel(tr("livre.photos_aide"))
        self.aide.setObjectName("legende")
        self.aide.setWordWrap(True)
        v.addWidget(self.aide)
        b = QHBoxLayout()
        self.b_ajouter = QPushButton(tr("livre.photos_ajouter"))
        self.b_ouvrir = QPushButton(tr("livre.photos_ouvrir"))
        self.b_retirer = QPushButton(tr("livre.photos_retirer"))
        for w in (self.b_ajouter, self.b_ouvrir, self.b_retirer):
            b.addWidget(w)
        v.addLayout(b)
        self.b_ajouter.clicked.connect(self.ajouter)
        self.b_ouvrir.clicked.connect(self.ouvrir)
        self.b_retirer.clicked.connect(self.retirer)
        self.liste.itemActivated.connect(lambda _i: self.ouvrir())
        self.liste.itemSelectionChanged.connect(self._etat)
        self.afficher(None)

    def afficher(self, m: dict | None) -> None:
        self.mouvement = m
        self.liste.clear()
        if m is not None:
            dossier_cache = self.cave.dossier_vignettes
            for im in self.cave.photos_mouvement(m["id"]):
                chemin = self.cave.chemin_image(im["fichier"])
                if chemin is None:
                    continue
                v = images.vignette(chemin, 150, 150, dossier_cache) or chemin
                it = QListWidgetItem(QIcon(QPixmap(str(v))), "")
                it.setData(Qt.ItemDataRole.UserRole, im["id"])
                it.setToolTip(Path(chemin).name)
                self.liste.addItem(it)
            self.titre.setText(tr("livre.photos_de", vin=" · ".join(
                str(x) for x in (m.get("producteur"), m.get("cuvee"), m.get("millesime")) if x)
                or date_affichee(m["date"]), date=date_affichee(m["date"])))
        else:
            self.titre.setText(tr("livre.photos_titre"))
        self._etat()

    def _etat(self) -> None:
        self.b_ajouter.setEnabled(self.mouvement is not None)
        choisie = bool(self.liste.selectedItems())
        self.b_ouvrir.setEnabled(choisie)
        self.b_retirer.setEnabled(choisie)

    def ajouter_fichiers(self, fichiers) -> int:
        if self.mouvement is None:
            return 0
        n = 0
        for f in fichiers:
            if Path(f).suffix.lower() in EXTENSIONS:
                self.cave.ajouter_photo_mouvement(self.mouvement["id"], f)
                n += 1
        if n:
            self.afficher(self.mouvement)
            self.modifie.emit()
        return n

    def ajouter(self) -> None:
        fichiers, _ = QFileDialog.getOpenFileNames(self, tr("livre.photos_ajouter"), str(Path.home()),
                                                   f"{tr('filtre.images')} {MOTIF_IMAGES}")
        self.ajouter_fichiers(fichiers)

    def _choisie(self) -> int | None:
        items = self.liste.selectedItems()
        return items[0].data(Qt.ItemDataRole.UserRole) if items else None

    def ouvrir(self) -> None:
        iid = self._choisie()
        im = self.cave.image(iid) if iid else None
        chemin = self.cave.chemin_image(im["fichier"]) if im else None
        if chemin:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(chemin)))

    def retirer(self) -> None:
        iid = self._choisie()
        if iid and QMessageBox.question(self, tr("livre.photos_retirer"), tr("livre.photos_retirer_q")) \
                == QMessageBox.StandardButton.Yes:
            self.cave.supprimer_image(iid)
            self.afficher(self.mouvement)
            self.modifie.emit()

    def dragEnterEvent(self, ev):
        if self.mouvement is not None and fichiers_images(ev.mimeData()):
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        self.ajouter_fichiers(fichiers_images(ev.mimeData()))
        ev.acceptProposedAction()


class VueLivre(QWidget):
    vin_choisi = pyqtSignal(int)
    modifie = pyqtSignal()

    def __init__(self, cave, parent=None, charger: bool = True):
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
        self.photos = PanneauPhotos(cave)
        coupe = QSplitter(Qt.Orientation.Horizontal)
        coupe.addWidget(self.table)
        coupe.addWidget(self.photos)
        coupe.setStretchFactor(0, 4)
        coupe.setStretchFactor(1, 1)
        coupe.setSizes([900, 260])
        racine.addWidget(coupe, 1)
        self.photos.modifie.connect(self._photos_modifiees)
        self.recherche.setAccessibleName(tr("livre.recherche"))
        self.filtre.setAccessibleName(tr("livre.tout"))
        self.table.setAccessibleName(tr("onglet.livre"))
        QShortcut(QKeySequence(QKeySequence.StandardKey.Find), self, self.recherche.setFocus)
        aide = QLabel(tr("livre.aide"))
        aide.setObjectName("legende")
        racine.addWidget(aide)
        self.recherche.textChanged.connect(self.rafraichir)
        self.filtre.currentIndexChanged.connect(self.rafraichir)
        self.table.cellDoubleClicked.connect(self._modifier)
        self.table.currentCellChanged.connect(self._ligne)
        self.lignes: list[dict] = []
        if charger:                      # la fenêtre le charge à la première ouverture
            self.rafraichir()

    def rafraichir(self, *_a) -> None:
        self.lignes = self.cave.mouvements(type_prefixe=self.filtre.currentData() or "",
                                           texte=self.recherche.text())
        self.table.setRowCount(len(self.lignes))
        photos = self.cave.nombre_photos_mouvements()
        for r, m in enumerate(self.lignes):
            vin = " · ".join(x for x in (m["producteur"], m["cuvee"], m["appellation"]) if x)
            note = ""
            if m["note"] is not None:
                note = f"{nombre(m['note'])} {lib('echelle', m['echelle'])}".strip()
            n = photos.get(m["id"], 0)
            cellules = (date_affichee(m["date"]), lib("mouvement", m["type"]), vin,
                        m["millesime"] or "", tr("livre.n_photos", n=n) if n else "", m["occasion"],
                        m["convives"], m["plat"], note, m["commentaire"])
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
        self.photos.afficher(self.lignes[r] if 0 <= r < len(self.lignes) else None)
        if 0 <= r < len(self.lignes) and self.lignes[r]["vin_id"]:
            self.vin_choisi.emit(self.lignes[r]["vin_id"])

    def _photos_modifiees(self) -> None:
        r = self.table.currentRow()
        self.rafraichir()
        if 0 <= r < self.table.rowCount():
            self.table.setCurrentCell(r, 0)
        self.modifie.emit()

    def _modifier(self, r, _c) -> None:
        if 0 <= r < len(self.lignes):
            if DialogueMouvement(self.cave, self.lignes[r], self).exec() == QDialog.DialogCode.Accepted:
                self.rafraichir()
                self.modifie.emit()
