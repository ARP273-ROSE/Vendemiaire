# -*- coding: utf-8 -*-
"""Plan visuel des casiers : arbre cave › meuble › casier, grille rangées ×
colonnes, glisser-déposer d'une ou plusieurs bouteilles (échange si la case est
prise), déplacement en lot vers un autre casier. Chaque déplacement est
consigné (historique) ; un lot invalide est refusé en entier."""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout,
                             QGraphicsEllipseItem, QGraphicsItem, QGraphicsScene,
                             QGraphicsSimpleTextItem, QGraphicsView, QHBoxLayout, QInputDialog,
                             QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QSplitter,
                             QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import style
from ..i18n import lib, tr
from ..modele import CaseOccupee
from .saisie import casiers

CASE = 46          # pixels par case
MARGE = 30


class PastilleBouteille(QGraphicsEllipseItem):
    def __init__(self, ligne, parent=None):
        super().__init__(0, 0, CASE - 10, CASE - 10, parent)
        self.bid = ligne["id"]
        self.vin_id = ligne["vin_id"]
        self.rangee, self.colonne = ligne["rangee"], ligne["colonne"]
        teinte = QColor(style.TEINTES_VIN.get(ligne["couleur"], style.TEINTES_VIN[None]))
        self.setBrush(QBrush(teinte))
        self.setPen(QPen(QColor(style.OR) if ligne["format"] != "bouteille"
                         else QColor("#3A2A20"), 3 if ligne["format"] != "bouteille" else 1.2))
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable
                      | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        nom = " · ".join(str(x) for x in (ligne["producteur"], ligne["cuvee"],
                                          ligne["appellation"], ligne["millesime"]) if x)
        self.setToolTip(f"{nom}\n{lib('format', ligne['format'])}")
        if ligne["millesime"]:
            t = QGraphicsSimpleTextItem(str(ligne["millesime"])[2:], self)
            f = QFont(style.FAMILLE)
            f.setPixelSize(12)
            f.setBold(True)
            t.setFont(f)
            t.setBrush(QBrush(QColor("#FFFFFF") if ligne["couleur"] in ("rouge", None)
                              else QColor(style.ENCRE)))
            r = t.boundingRect()
            t.setPos((CASE - 10 - r.width()) / 2, (CASE - 10 - r.height()) / 2)
        self.replacer()

    def replacer(self) -> None:
        self.setPos(position_case(self.rangee, self.colonne))

    def paint(self, painter, option, widget=None):
        if self.isSelected():
            painter.setPen(QPen(QColor(style.OR), 4))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(self.rect().adjusted(-3, -3, 3, 3))
        super().paint(painter, option, widget)


def position_case(rangee: int, colonne: int) -> QPointF:
    return QPointF(MARGE + (colonne - 1) * CASE + 5, MARGE + (rangee - 1) * CASE + 5)


def case_sous(point: QPointF) -> tuple[int, int]:
    """Case (rangée, colonne) sous le centre d'une pastille."""
    return (int((point.y() - MARGE) // CASE) + 1, int((point.x() - MARGE) // CASE) + 1)


class SceneCasier(QGraphicsScene):
    relache = pyqtSignal()

    def mouseReleaseEvent(self, ev):
        super().mouseReleaseEvent(ev)
        self.relache.emit()


class DialogueDeplacement(QDialog):
    def __init__(self, cave, nombre: int, sauf: int | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("plan.deplacer_titre", n=nombre))
        f = QFormLayout(self)
        self.casier = QComboBox()
        for eid, chemin in casiers(cave):
            if eid != sauf:
                libres = len(cave.cases_libres(eid))
                self.casier.addItem(tr("plan.casier_libres", chemin=chemin, n=libres), eid)
        self.motif = QLineEdit()
        f.addRow(tr("plan.destination"), self.casier)
        f.addRow(tr("plan.motif"), self.motif)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        b.button(QDialogButtonBox.StandardButton.Ok).setText(tr("plan.deplacer"))
        b.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("bouton.annuler"))
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        f.addRow(b)


class DialogueCasier(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("plan.nouveau_casier"))
        f = QFormLayout(self)
        self.nom = QLineEdit()
        self.rangees = QSpinBox()
        self.rangees.setRange(1, 200)
        self.rangees.setValue(6)
        self.colonnes = QSpinBox()
        self.colonnes.setRange(1, 200)
        self.colonnes.setValue(8)
        f.addRow(tr("plan.nom"), self.nom)
        f.addRow(tr("plan.rangees"), self.rangees)
        f.addRow(tr("plan.colonnes"), self.colonnes)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        b.button(QDialogButtonBox.StandardButton.Ok).setText(tr("bouton.creer"))
        b.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("bouton.annuler"))
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        f.addRow(b)


class VuePlan(QWidget):
    modifie = pyqtSignal()
    vin_choisi = pyqtSignal(int)

    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        self.casier_id: int | None = None
        self.pastilles: dict[int, PastilleBouteille] = {}
        racine = QHBoxLayout(self)
        separation = QSplitter(Qt.Orientation.Horizontal)
        racine.addWidget(separation)

        gauche = QWidget()
        lg = QVBoxLayout(gauche)
        self.arbre = QTreeWidget()
        self.arbre.setHeaderLabels([tr("plan.emplacements"), tr("plan.bouteilles")])
        self.arbre.setColumnWidth(0, 220)
        lg.addWidget(self.arbre)
        ligne1 = QHBoxLayout()
        self.b_cave = QPushButton(tr("plan.nouvelle_cave"))
        self.b_meuble = QPushButton(tr("plan.nouveau_meuble"))
        ligne1.addWidget(self.b_cave)
        ligne1.addWidget(self.b_meuble)
        lg.addLayout(ligne1)
        ligne2 = QHBoxLayout()
        self.b_casier = QPushButton(tr("plan.nouveau_casier"))
        self.b_renommer = QPushButton(tr("plan.renommer"))
        ligne2.addWidget(self.b_casier)
        ligne2.addWidget(self.b_renommer)
        lg.addLayout(ligne2)
        separation.addWidget(gauche)

        droite = QWidget()
        ld = QVBoxLayout(droite)
        self.titre = QLabel()
        self.titre.setObjectName("titre")
        self.aide = QLabel(tr("plan.aide"))
        self.aide.setObjectName("legende")
        self.aide.setWordWrap(True)
        ld.addWidget(self.titre)
        ld.addWidget(self.aide)
        self.legende = QLabel(" &nbsp; ".join(
            f'<span style="color:{style.TEINTES_VIN[c]}; font-size:16pt;">●</span> {lib("couleur", c)}'
            for c in ("rouge", "blanc", "rose", "orange")))
        ld.addWidget(self.legende)
        self.scene = SceneCasier(self)
        self.vue = QGraphicsView(self.scene)
        self.vue.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.vue.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.vue.setBackgroundBrush(QBrush(QColor(style.CREME)))
        ld.addWidget(self.vue, 1)
        actions = QHBoxLayout()
        self.b_deplacer = QPushButton(tr("plan.deplacer_selection"))
        self.b_ranger = QPushButton(tr("plan.ranger_sans_case"))
        self.b_tout = QPushButton(tr("plan.tout_selectionner"))
        self.etat = QLabel()
        self.etat.setObjectName("legende")
        for w in (self.b_tout, self.b_deplacer, self.b_ranger):
            actions.addWidget(w)
        actions.addStretch(1)
        actions.addWidget(self.etat)
        ld.addLayout(actions)
        separation.addWidget(droite)
        separation.setSizes([300, 900])

        self.arbre.currentItemChanged.connect(self._noeud_change)
        self.scene.relache.connect(self._fin_glisser)
        self.scene.selectionChanged.connect(self._selection)
        self.b_cave.clicked.connect(lambda: self._creer("cave"))
        self.b_meuble.clicked.connect(lambda: self._creer("meuble"))
        self.b_casier.clicked.connect(lambda: self._creer("casier"))
        self.b_renommer.clicked.connect(self._renommer)
        self.b_deplacer.clicked.connect(self.deplacer_selection)
        self.b_ranger.clicked.connect(self.ranger_sans_case)
        self.b_tout.clicked.connect(self._tout)
        self.rafraichir()

    # -- arbre ---------------------------------------------------------------
    def rafraichir(self) -> None:
        courant = self.casier_id
        self.arbre.blockSignals(True)
        self.arbre.clear()
        comptes = {r[0]: r[1] for r in self.cave.base.lire(
            "SELECT emplacement_id, COUNT(*) FROM bouteille WHERE statut='en_cave' "
            "GROUP BY emplacement_id")}
        noeuds: dict[int, QTreeWidgetItem] = {}
        enfants: dict = {}
        for e in self.cave.emplacements():
            enfants.setdefault(e["parent_id"], []).append(e)
        premier_casier = None

        def poser(parent_id, parent_item, profondeur=0):
            nonlocal premier_casier
            if profondeur > 20:                      # garde-fou contre un cycle
                return
            for e in sorted(enfants.get(parent_id, []), key=lambda x: (x["ordre"], x["id"])):
                nom = e["nom"]
                if e["niveau"] == "casier" and e["rangees"]:
                    nom += f"  ({e['rangees']}×{e['colonnes']})"
                it = QTreeWidgetItem(parent_item, [nom, str(comptes.get(e["id"], "")) or ""])
                it.setData(0, Qt.ItemDataRole.UserRole, e["id"])
                it.setData(1, Qt.ItemDataRole.UserRole, e["niveau"])
                it.setToolTip(0, lib("niveau_emplacement", e["niveau"]))
                f = it.font(0)
                f.setBold(e["niveau"] == "cave")
                it.setFont(0, f)
                noeuds[e["id"]] = it
                if e["niveau"] == "casier" and premier_casier is None:
                    premier_casier = it
                poser(e["id"], it, profondeur + 1)

        poser(None, self.arbre)
        self.arbre.expandAll()
        self.arbre.blockSignals(False)
        cible = noeuds.get(courant) or premier_casier
        if cible is not None:
            self.arbre.setCurrentItem(cible)
        self.afficher_casier(cible.data(0, Qt.ItemDataRole.UserRole) if cible else None)

    def _noeud_change(self, courant, _avant) -> None:
        if courant is None:
            return
        if courant.data(1, Qt.ItemDataRole.UserRole) == "casier":
            self.afficher_casier(courant.data(0, Qt.ItemDataRole.UserRole))

    def _noeud_courant(self):
        it = self.arbre.currentItem()
        if it is None:
            return None, None
        return it.data(0, Qt.ItemDataRole.UserRole), it.data(1, Qt.ItemDataRole.UserRole)

    def _parent_pour(self, niveau: str) -> int | None:
        """Parent d'un nouvel emplacement d'après le nœud courant : la cave
        pour un meuble ; le meuble (ou la cave) pour un casier."""
        eid, _n = self._noeud_courant()
        while eid is not None:
            e = self.cave.emplacement(eid)
            if e is None:
                return None
            if (niveau == "meuble" and e["niveau"] == "cave") or \
                    (niveau == "casier" and e["niveau"] in ("cave", "meuble")):
                return eid
            eid = e["parent_id"]
        return None

    def _creer(self, niveau: str) -> None:
        parent = None
        if niveau != "cave":
            parent = self._parent_pour(niveau)
            if parent is None:
                QMessageBox.information(self, tr("plan.titre"), tr("plan.choisir_parent"))
                return
        if niveau == "casier":
            d = DialogueCasier(self)
            if d.exec() != QDialog.DialogCode.Accepted or not d.nom.text().strip():
                return
            nouveau = self.cave.creer_emplacement(d.nom.text().strip(), "casier", parent,
                                                  d.rangees.value(), d.colonnes.value())
            self.casier_id = nouveau
        else:
            titre = tr("plan.nouveau_meuble") if niveau == "meuble" else tr("plan.nouvelle_cave")
            nom, ok = QInputDialog.getText(self, titre, tr("plan.nom"))
            if not ok or not nom.strip():
                return
            self.cave.creer_emplacement(nom.strip(), niveau, parent)
        self.rafraichir()
        self.modifie.emit()

    def _renommer(self) -> None:
        eid, _n = self._noeud_courant()
        if eid is None:
            return
        e = self.cave.emplacement(eid)
        nom, ok = QInputDialog.getText(self, tr("plan.renommer"), tr("plan.nom"), text=e["nom"])
        if ok and nom.strip():
            self.cave.renommer_emplacement(eid, nom.strip())
            self.rafraichir()
            self.modifie.emit()

    # -- grille ----------------------------------------------------------------
    def afficher_casier(self, casier_id: int | None) -> None:
        self.casier_id = casier_id
        self.scene.clear()
        self.pastilles.clear()
        e = self.cave.emplacement(casier_id) if casier_id else None
        if e is None:
            self.titre.setText(tr("plan.aucun_casier"))
            self.etat.clear()
            return
        self.titre.setText(" › ".join(self.cave.chemin_emplacement(casier_id)))
        rangees, colonnes = e["rangees"] or 1, e["colonnes"] or 1
        crayon = QPen(QColor(style.BORD), 1)
        fond = QBrush(QColor(style.CARTE))
        police = QFont(style.FAMILLE)
        police.setPixelSize(11)
        for r in range(1, rangees + 1):
            t = self.scene.addSimpleText(str(r), police)
            t.setBrush(QBrush(QColor(style.GRIS)))
            t.setPos(8, MARGE + (r - 1) * CASE + CASE / 2 - 7)
            for c in range(1, colonnes + 1):
                self.scene.addRect(QRectF(MARGE + (c - 1) * CASE, MARGE + (r - 1) * CASE,
                                          CASE, CASE), crayon, fond).setZValue(-1)
        for c in range(1, colonnes + 1):
            t = self.scene.addSimpleText(str(c), police)
            t.setBrush(QBrush(QColor(style.GRIS)))
            t.setPos(MARGE + (c - 1) * CASE + CASE / 2 - 4, 8)
        sans_case = 0
        for ligne in self.cave.contenu_casier(casier_id):
            if not ligne["rangee"] or not ligne["colonne"]:
                sans_case += 1
                continue
            p = PastilleBouteille(ligne)
            self.scene.addItem(p)
            self.pastilles[p.bid] = p
        self.scene.setSceneRect(QRectF(0, 0, MARGE * 2 + colonnes * CASE, MARGE * 2 + rangees * CASE))
        sans_emplacement = self.cave.base.valeur(
            "SELECT COUNT(*) FROM bouteille WHERE statut='en_cave' AND emplacement_id IS NULL") or 0
        self.b_ranger.setEnabled(bool(sans_emplacement + sans_case))
        self.b_ranger.setToolTip(tr("plan.ranger_aide", n=sans_emplacement, m=sans_case))
        self._selection()

    def _selection(self) -> None:
        try:
            choisies = [i for i in self.scene.selectedItems() if isinstance(i, PastilleBouteille)]
        except RuntimeError:                      # scène en cours de destruction
            return
        e = self.cave.emplacement(self.casier_id) if self.casier_id else None
        libres = len(self.cave.cases_libres(self.casier_id)) if e else 0
        self.etat.setText(tr("plan.etat", n=len(self.pastilles), libres=libres, choisies=len(choisies)))
        self.b_deplacer.setEnabled(bool(choisies))
        if len(choisies) == 1:
            self.vin_choisi.emit(choisies[0].vin_id)

    def _tout(self) -> None:
        for p in self.pastilles.values():
            p.setSelected(True)

    def selectionner_bouteille(self, bid: int) -> None:
        b = self.cave.bouteille(bid)
        if b is None or not b["emplacement_id"]:
            return
        self.casier_id = b["emplacement_id"]
        self.rafraichir()
        p = self.pastilles.get(bid)
        if p is not None:
            self.scene.clearSelection()
            p.setSelected(True)
            self.vue.centerOn(p)

    # -- glisser-déposer -----------------------------------------------------------
    def _fin_glisser(self) -> None:
        deplacees = [p for p in self.pastilles.values()
                     if (p.pos() - position_case(p.rangee, p.colonne)).manhattanLength() > 2]
        if not deplacees:
            return
        e = self.cave.emplacement(self.casier_id)
        occupants = {(p.rangee, p.colonne): p for p in self.pastilles.values()}
        mouvements, liberees = [], set()
        for p in deplacees:
            centre = p.pos() + QPointF((CASE - 10) / 2, (CASE - 10) / 2)
            r, c = case_sous(centre)
            if not (1 <= r <= e["rangees"] and 1 <= c <= e["colonnes"]):
                return self._annuler(deplacees)
            mouvements.append((p, r, c))
            liberees.add((p.rangee, p.colonne))
        destinations = {(r, c) for _p, r, c in mouvements}
        if len(destinations) != len(mouvements):
            return self._annuler(deplacees)
        lot = [(p.bid, self.casier_id, r, c) for p, r, c in mouvements]
        # une case prise par une bouteille qui ne bouge pas : échange (une
        # seule bouteille glissée) ou refus (plusieurs)
        bloquees = [occupants[d] for d in destinations
                    if d in occupants and occupants[d] not in deplacees]
        if bloquees:
            if len(mouvements) != 1:
                return self._annuler(deplacees)
            autre, p = bloquees[0], mouvements[0][0]
            lot.append((autre.bid, self.casier_id, p.rangee, p.colonne))
        try:
            self.cave.deplacer(lot, motif=tr("plan.motif_glisser"))
        except (CaseOccupee, ValueError):
            return self._annuler(deplacees)
        self.afficher_casier(self.casier_id)
        self.modifie.emit()

    def _annuler(self, pastilles) -> None:
        for p in pastilles:
            p.replacer()

    def deplacer_selection(self) -> None:
        choisies = [i for i in self.scene.selectedItems() if isinstance(i, PastilleBouteille)]
        if not choisies:
            return
        d = DialogueDeplacement(self.cave, len(choisies), self.casier_id, self)
        if d.exec() != QDialog.DialogCode.Accepted or d.casier.currentData() is None:
            return
        self.deplacer_vers([p.bid for p in sorted(choisies, key=lambda p: (p.rangee, p.colonne))],
                           d.casier.currentData(), d.motif.text().strip())

    def deplacer_vers(self, bouteilles: list[int], casier: int, motif: str = "") -> bool:
        """Déplacement en lot : remplit les cases libres du casier dans l'ordre."""
        libres = self.cave.cases_libres(casier)
        if len(libres) < len(bouteilles):
            QMessageBox.warning(self, tr("plan.titre"),
                                tr("plan.pas_assez", n=len(bouteilles), libres=len(libres)))
            return False
        lot = [(bid, casier, r, c) for bid, (r, c) in zip(bouteilles, libres)]
        self.cave.deplacer(lot, motif=motif or tr("plan.motif_lot"))
        self.rafraichir()
        self.modifie.emit()
        return True

    def ranger_sans_case(self) -> None:
        """Pose dans les cases libres de ce casier les bouteilles en cave sans case
        (celles du casier d'abord, puis celles qui n'ont aucun emplacement)."""
        if self.casier_id is None:
            return
        ids = [r[0] for r in self.cave.base.lire(
            "SELECT id FROM bouteille WHERE statut='en_cave' AND ((emplacement_id=? AND "
            "(rangee IS NULL OR colonne IS NULL)) OR emplacement_id IS NULL) "
            "ORDER BY emplacement_id IS NULL, vin_id, id", (self.casier_id,))]
        libres = self.cave.cases_libres(self.casier_id)
        n = min(len(ids), len(libres))
        if not n:
            QMessageBox.information(self, tr("plan.titre"), tr("plan.rien_a_ranger"))
            return
        self.cave.deplacer([(bid, self.casier_id, r, c) for bid, (r, c) in zip(ids, libres)],
                           motif=tr("plan.motif_ranger"))
        self.rafraichir()
        self.modifie.emit()
