# -*- coding: utf-8 -*-
"""Le mur d'étiquettes : la cave en « pochettes », comme une discothèque.

Une case par vin (sa photo d'étiquette, ou l'étiquette dessinée), vignettes
lues dans le cache disque. Double-clic : la fiche du vin. Une photo glissée
sur une case devient la photo de ce vin.
"""
from __future__ import annotations

from PyQt6.QtCore import QAbstractListModel, QModelIndex, QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit, QListView, QVBoxLayout,
                             QWidget)

from ..i18n import tr
from .photos import fichiers_images
from .pochette import pochette

TAILLE = QSize(150, 200)


class ModeleMur(QAbstractListModel):
    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        self.vins: list[dict] = []

    def charger(self, vins: list[dict]) -> None:
        self.beginResetModel()
        self.vins = vins
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.vins)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        v = self.vins[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            haut = " ".join(x for x in (v.get("producteur"), str(v["millesime"]) if v.get("millesime")
                                        else None) if x)
            bas = v.get("cuvee") or v.get("appellation") or ""
            n = v.get("en_cave") or 0
            return f"{haut}\n{bas}\n{tr('mur.bouteilles', n=n)}"
        if role == Qt.ItemDataRole.DecorationRole:
            return pochette(v, TAILLE.width(), TAILLE.height(), v.get("photo"),
                            self.cave.dossier_vignettes)
        if role == Qt.ItemDataRole.UserRole:
            return v["id"]
        if role == Qt.ItemDataRole.ToolTipRole:
            return " · ".join(str(x) for x in (v.get("producteur"), v.get("cuvee"), v.get("appellation"),
                                               v.get("millesime")) if x)
        return None


class Mur(QListView):
    photo_deposee = pyqtSignal(object)          # (vin_id, chemin)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setIconSize(TAILLE)
        self.setGridSize(QSize(TAILLE.width() + 40, TAILLE.height() + 70))
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setUniformItemSizes(True)
        self.setWordWrap(True)
        self.setSpacing(6)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, ev):
        if fichiers_images(ev.mimeData()):
            ev.acceptProposedAction()

    def dragMoveEvent(self, ev):
        if fichiers_images(ev.mimeData()) and self.indexAt(ev.position().toPoint()).isValid():
            ev.acceptProposedAction()
        else:
            ev.ignore()

    def dropEvent(self, ev):
        i = self.indexAt(ev.position().toPoint())
        fichiers = fichiers_images(ev.mimeData())
        if i.isValid() and fichiers:
            self.photo_deposee.emit((i.data(Qt.ItemDataRole.UserRole), fichiers[0]))
            ev.acceptProposedAction()


class VueMur(QWidget):
    vin_choisi = pyqtSignal(int)
    photo_deposee = pyqtSignal(object)

    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        racine = QVBoxLayout(self)
        haut = QHBoxLayout()
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText(tr("cave.recherche"))
        self.recherche.setClearButtonEnabled(True)
        self.statut = QComboBox()
        self.statut.addItem(tr("cave.statut_presents"), "presents")
        self.statut.addItem(tr("cave.statut_tous"), "tous")
        self.compte = QLabel()
        self.compte.setObjectName("legende")
        haut.addWidget(self.recherche, 3)
        haut.addWidget(self.statut, 1)
        haut.addWidget(self.compte)
        racine.addLayout(haut)
        aide = QLabel(tr("mur.aide"))
        aide.setObjectName("legende")
        racine.addWidget(aide)
        self.modele = ModeleMur(cave, self)
        self.vue = Mur()
        self.vue.setModel(self.modele)
        racine.addWidget(self.vue, 1)
        self.recherche.textChanged.connect(lambda _t: self.rafraichir())
        self.statut.currentIndexChanged.connect(lambda _i: self.rafraichir())
        self.vue.doubleClicked.connect(lambda i: self.vin_choisi.emit(i.data(Qt.ItemDataRole.UserRole)))
        self.vue.photo_deposee.connect(self.photo_deposee.emit)
        self.rafraichir()

    def rafraichir(self) -> None:
        vins = self.cave.mur(self.recherche.text(), self.statut.currentData() or "presents")
        self.modele.charger(vins)
        photos = sum(1 for v in vins if v.get("photo"))
        self.compte.setText(tr("mur.compte", vins=len(vins), photos=photos))
