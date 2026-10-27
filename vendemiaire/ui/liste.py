# -*- coding: utf-8 -*-
"""Liste de la cave : filtres, recherche, colonnes au choix, pochettes."""
from __future__ import annotations

from PyQt6.QtCore import (QAbstractTableModel, QModelIndex, QSettings, QSize,
                          QSortFilterProxyModel, Qt, pyqtSignal)
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QLabel,
                             QLineEdit, QMenu, QPushButton, QSplitter, QTableView,
                             QVBoxLayout, QWidget)

from .. import referentiels
from ..i18n import argent, lib, nombre, tr
from .fiche import FicheVin
from .pochette import pochette

#: (clé de donnée, clé de texte de l'en-tête, visible par défaut)
COLONNES = [
    ("pochette", "col.pochette", True),
    ("producteur", "col.producteur", True),
    ("cuvee", "col.cuvee", True),
    ("appellation", "col.appellation", True),
    ("millesime", "col.millesime", True),
    ("couleur", "col.couleur", True),
    ("type", "col.type", False),
    ("region", "col.region", True),
    ("pays", "col.pays", False),
    ("cepages", "col.cepages", False),
    ("degre", "col.degre", False),
    ("formats", "col.formats", False),
    ("en_cave", "col.en_cave", True),
    ("a_venir", "col.a_venir", True),
    ("prix_moyen", "col.prix_moyen", True),
    ("valeur_unitaire", "col.valeur", False),
    ("classement", "col.classement", False),
    ("lwin", "col.lwin", False),
]
NUMERIQUES = {"millesime", "en_cave", "a_venir", "prix_moyen", "valeur_unitaire", "degre"}
TAILLE_POCHETTE = QSize(30, 40)


class ModeleVins(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lignes: list[dict] = []

    def charger(self, lignes: list[dict]) -> None:
        self.beginResetModel()
        self.lignes = lignes
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.lignes)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(COLONNES)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return "" if COLONNES[section][0] == "pochette" else tr(COLONNES[section][1])
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.ToolTipRole:
            return tr(COLONNES[section][1])
        return None

    def _texte(self, l: dict, cle: str) -> str:
        v = l.get(cle)
        if cle == "millesime":
            return str(v) if v else (tr("vin.nm") if l.get("non_millesime") else "")
        if cle in ("couleur", "type"):
            return lib(cle, v)
        if cle == "formats":
            return ", ".join(lib("format", f) for f in (v or "").split(",") if f)
        if cle in ("prix_moyen", "valeur_unitaire"):
            return argent(v)
        if cle == "degre":
            return f"{nombre(v)} %" if v else ""
        if cle in ("en_cave", "a_venir"):
            return str(v or 0) if (v or cle == "en_cave") else ""
        return "" if v is None else str(v)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        l = self.lignes[index.row()]
        cle = COLONNES[index.column()][0]
        if role == Qt.ItemDataRole.DisplayRole:
            return "" if cle == "pochette" else self._texte(l, cle)
        if role == Qt.ItemDataRole.DecorationRole and cle == "pochette":
            return pochette(l, TAILLE_POCHETTE.width(), TAILLE_POCHETTE.height(),
                            l.get("_image"), l.get("_cache"))
        if role == Qt.ItemDataRole.UserRole:              # tri
            v = l.get(cle)
            if cle in NUMERIQUES:
                return float(v or 0)
            return (self._texte(l, cle) or "").lower()
        if role == Qt.ItemDataRole.TextAlignmentRole and cle in NUMERIQUES:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ForegroundRole and cle == "en_cave" and not l.get("en_cave"):
            return QColor("#7D7064")
        if role == Qt.ItemDataRole.ToolTipRole and cle == "producteur" and l.get("coup_de_coeur"):
            return tr("vin.coup_de_coeur")
        return None


class VueCave(QWidget):
    vin_choisi = pyqtSignal(object)          # id du vin ou None
    modifier_demande = pyqtSignal(int)

    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        racine = QVBoxLayout(self)
        filtres = QHBoxLayout()
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText(tr("cave.recherche"))
        self.recherche.setClearButtonEnabled(True)
        self.couleur = QComboBox()
        self.pays = QComboBox()
        self.statut = QComboBox()
        self.compte = QLabel()
        self.compte.setObjectName("legende")
        self.bouton_nouveau = QPushButton(tr("action.nouveau_vin"))
        self.bouton_nouveau.setObjectName("principal")
        self.bouton_identifier = QPushButton(tr("cave.identifier_tout"))
        self.bouton_identifier.setToolTip(tr("lot.intro"))
        filtres.addWidget(self.recherche, 3)
        filtres.addWidget(QLabel(tr("cave.filtre_couleur")))
        filtres.addWidget(self.couleur, 1)
        filtres.addWidget(QLabel(tr("cave.filtre_pays")))
        filtres.addWidget(self.pays, 1)
        filtres.addWidget(QLabel(tr("cave.filtre_statut")))
        filtres.addWidget(self.statut, 1)
        filtres.addWidget(self.compte)
        filtres.addWidget(self.bouton_identifier)
        filtres.addWidget(self.bouton_nouveau)
        racine.addLayout(filtres)

        self.modele = ModeleVins(self)
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.modele)
        self.proxy.setSortRole(Qt.ItemDataRole.UserRole)
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setIconSize(TAILLE_POCHETTE)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(TAILLE_POCHETTE.height() + 6)
        self.table.setWordWrap(False)
        self.fiche = FicheVin(cave)
        separation = QSplitter(Qt.Orientation.Horizontal)
        separation.addWidget(self.table)
        separation.addWidget(self.fiche)
        separation.setStretchFactor(0, 3)
        separation.setStretchFactor(1, 2)
        separation.setSizes([820, 480])
        racine.addWidget(separation, 1)
        self._entete()

        self._remplir_filtres()
        self.recherche.textChanged.connect(self.rafraichir)
        for combo in (self.couleur, self.pays, self.statut):
            combo.currentIndexChanged.connect(self.rafraichir)
        self.table.selectionModel().currentRowChanged.connect(self._ligne_changee)
        self.table.doubleClicked.connect(self._double_clic)
        self.rafraichir()

    # -- en-tête : colonnes choisies, retenues ----------------------------
    def _entete(self) -> None:
        h = self.table.horizontalHeader()
        etat = QSettings().value("cave/entete")
        restaure = bool(etat) and h.restoreState(etat)
        # restoreState() remet aussi les DRAPEAUX : tout réglage d'en-tête se
        # pose APRÈS (piège payé dans MusicOthèque)
        h.setSectionsMovable(True)
        h.setStretchLastSection(False)
        h.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        h.customContextMenuRequested.connect(self._menu_colonnes)
        h.sectionMoved.connect(lambda *_: self._retenir())
        h.sectionResized.connect(lambda *_: self._retenir())
        if not restaure:
            for i, (_cle, _t, visible) in enumerate(COLONNES):
                self.table.setColumnHidden(i, not visible)
            h.resizeSection(0, TAILLE_POCHETTE.width() + 12)
            for i, cle in enumerate(c[0] for c in COLONNES):
                if cle in ("producteur", "cuvee", "appellation"):
                    h.resizeSection(i, 180)
                elif cle in ("millesime", "en_cave", "a_venir"):
                    h.resizeSection(i, 72)
            self.table.sortByColumn(1, Qt.SortOrder.AscendingOrder)

    def _retenir(self) -> None:
        QSettings().setValue("cave/entete", self.table.horizontalHeader().saveState())

    def _menu_colonnes(self, pos) -> None:
        menu = QMenu(self)
        for i, (cle, t, _v) in enumerate(COLONNES):
            if cle == "pochette":
                texte = tr("col.pochette")
            else:
                texte = tr(t)
            act = QAction(texte, menu)
            act.setCheckable(True)
            act.setChecked(not self.table.isColumnHidden(i))
            act.toggled.connect(lambda oui, i=i: (self.table.setColumnHidden(i, not oui),
                                                   self._retenir()))
            menu.addAction(act)
        menu.exec(self.table.horizontalHeader().mapToGlobal(pos))

    # -- filtres ------------------------------------------------------------
    def _remplir_filtres(self) -> None:
        avant = [c.currentData() for c in (self.couleur, self.pays, self.statut)]
        for combo in (self.couleur, self.pays, self.statut):
            combo.blockSignals(True)
            combo.clear()
        self.couleur.addItem(tr("cave.toutes"), "")
        for code in referentiels.codes("couleur"):
            self.couleur.addItem(lib("couleur", code), code)
        self.pays.addItem(tr("cave.tous"), "")
        for p in self.cave.valeurs_distinctes("pays"):
            self.pays.addItem(p, p)
        self.statut.addItem(tr("cave.statut_presents"), "presents")
        self.statut.addItem(tr("cave.statut_tous"), "tous")
        for code in referentiels.codes("statut"):
            self.statut.addItem(lib("statut", code), code)
        for combo, valeur in zip((self.couleur, self.pays, self.statut), avant):
            i = combo.findData(valeur) if valeur is not None else -1
            combo.setCurrentIndex(max(0, i))
            combo.blockSignals(False)

    def rafraichir(self, *_args, garder: int | None = None) -> None:
        actuel = garder if garder is not None else self.vin_courant()
        lignes = self.cave.liste_vins(self.recherche.text(), self.couleur.currentData() or "",
                                      self.pays.currentData() or "",
                                      self.statut.currentData() or "presents")
        for l in lignes:
            l["_image"] = self.cave.image_principale(l["id"])
            l["_cache"] = self.cave.dossier_vignettes
        self.modele.charger(lignes)
        bouteilles = sum(l["en_cave"] or 0 for l in lignes)
        self.compte.setText(tr("cave.compte", vins=len(lignes), bouteilles=bouteilles))
        if actuel is not None:
            self.selectionner(actuel)
        elif not lignes:
            self.fiche.afficher(None)

    def recharger_filtres(self) -> None:
        self._remplir_filtres()
        self.rafraichir()

    def selectionner(self, vin_id: int) -> bool:
        for r, l in enumerate(self.modele.lignes):
            if l["id"] == vin_id:
                idx = self.proxy.mapFromSource(self.modele.index(r, 1))
                self.table.setCurrentIndex(idx)
                self.table.scrollTo(idx)
                return True
        return False

    def vin_courant(self) -> int | None:
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        return self.modele.lignes[self.proxy.mapToSource(idx).row()]["id"]

    def _ligne_changee(self, courant, _avant) -> None:
        vid = None
        if courant.isValid():
            vid = self.modele.lignes[self.proxy.mapToSource(courant).row()]["id"]
        self.fiche.afficher(vid)
        self.vin_choisi.emit(vid)

    def _double_clic(self, idx) -> None:
        if idx.isValid():
            self.modifier_demande.emit(self.modele.lignes[self.proxy.mapToSource(idx).row()]["id"])
