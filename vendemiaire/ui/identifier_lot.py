# -*- coding: utf-8 -*-
"""Références › Identifier toute la cave… (1.0.2).

Les candidats de chaque vin sont calculés en tâche de fond (lectures seules,
barre de progression, annulation) ; un récapitulatif unique montre une ligne
par vin, les décisions sûres cochées d'avance, les douteuses signalées et non
cochées, les vins sans candidat à part. Rien n'est écrit avant « Valider la
sélection » ; la validation confirme chaque vin coché dans sa propre
transaction courte, par la règle habituelle (champs vides et non saisis à la
main seulement), puis affiche le journal de ce qui a été rempli et d'où.
"""
from __future__ import annotations

import threading

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QHBoxLayout, QHeaderView,
                             QLabel, QListWidget, QListWidgetItem, QPlainTextEdit, QProgressBar,
                             QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout,
                             QWidget)

from .. import reseau
from ..i18n import langue, tr
from ..mondial import appariement, lot
from . import travail

COL_VIN, COL_CANDIDAT, COL_SCORE, COL_RAISON, COL_SECOND, COL_ETAT = range(6)

CATEGORIES = (lot.SURE, lot.DOUTEUSE, lot.DEJA, lot.AUCUN)
MOTIFS = {"ambigu": "lot.motif_ambigu", "faible": "lot.motif_faible", "sur": "lot.motif_sur",
          "aucun": "lot.motif_aucun"}
COURTS = {"appariement.r_producteur": "lot.court_domaine", "appariement.r_cuvee": "lot.court_cuvee",
          "appariement.r_appellation": "lot.court_appellation",
          "appariement.r_nom_wikidata": "lot.court_nom"}
CHAMPS = {"producteur": "vin.producteur", "cuvee": "vin.cuvee", "appellation": "vin.appellation",
          "region": "vin.region_seule", "sous_region": "vin.sous_region", "pays": "vin.pays",
          "classement": "vin.classement", "couleur": "vin.couleur", "type": "vin.type",
          "lwin": "vin.lwin", "site_web": "ident.site_web", "adresse": "ident.adresse",
          "cepages": "vin.cepages"}
SURE_FOND = QColor("#e6f0dc")
DOUTE_FOND = QColor("#fbefd5")


def pct(score: float) -> str:
    return f"{int(round(score * 100))} %"


def raison_courte(c: appariement.Candidat) -> str:
    """Une ligne : les ressemblances qui comptent, puis la première objection."""
    morceaux = []
    objection = None
    for r in c.raisons:
        if r.cle in COURTS and "pct" in r.valeurs:
            morceaux.append(tr(COURTS[r.cle], pct=r.valeurs["pct"]))
        elif r.cle == "appariement.r_grand_vin":
            morceaux.append(tr("lot.court_grand_vin"))
        if r.signe < 0 and objection is None and r.cle not in COURTS:
            objection = appariement.explication_texte([r], tr)[2:]
    texte = " · ".join(morceaux)
    return f"{texte} — {objection}" if objection else texte


def libelle_source(c: appariement.Candidat) -> str:
    if c.source == "wikidata":
        return tr("lot.source_wikidata", nom=c.libelle)
    return f"LWIN {c.identifiant} — {c.libelle}"


class _Signaux(QObject):
    avance = pyqtSignal(int, int)


class DialogueIdentifierLot(QDialog):
    """`vin_ids` : pour les essais (sinon : les vins sans LWIN, ou tous)."""

    def __init__(self, cave, parent=None, demarrer: bool = True):
        super().__init__(parent)
        self.cave = cave
        self.lignes: list[lot.LigneLot] = []
        self.bilan: lot.Bilan | None = None
        self.modifie = False
        self._travail = None
        self._arret = threading.Event()
        self._signaux = _Signaux(self)
        self._signaux.avance.connect(self._avance)
        self.setWindowTitle(tr("lot.titre"))
        self.resize(1320, 820)
        racine = QVBoxLayout(self)

        intro = QLabel(tr("lot.intro"))
        intro.setWordWrap(True)
        intro.setObjectName("legende")
        racine.addWidget(intro)
        options = QHBoxLayout()
        self.o_tous = QCheckBox(tr("lot.option_tous"))
        self.o_wikidata = QCheckBox(tr("lot.option_wikidata"))
        self.o_wikidata.setEnabled(reseau.autorise())
        self.o_wikidata.setToolTip(tr("lot.wikidata_aide") if reseau.autorise()
                                   else tr("lot.wikidata_refuse"))
        self.b_chercher = QPushButton(tr("lot.chercher"))
        for w in (self.o_tous, self.o_wikidata):
            options.addWidget(w)
        options.addStretch(1)
        options.addWidget(self.b_chercher)
        racine.addLayout(options)

        avance = QHBoxLayout()
        self.barre = QProgressBar()
        self.barre.setTextVisible(True)
        self.b_annuler = QPushButton(tr("bouton.annuler"))
        self.b_annuler.setEnabled(False)
        avance.addWidget(self.barre, 1)
        avance.addWidget(self.b_annuler)
        racine.addLayout(avance)
        self.etat = QLabel()
        self.etat.setWordWrap(True)
        racine.addWidget(self.etat)

        partage = QSplitter(Qt.Orientation.Vertical)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([tr("lot.c_vin"), tr("lot.c_candidat"), tr("lot.c_score"),
                                              tr("lot.c_raison"), tr("lot.c_second"), tr("lot.c_etat")])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(False)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(COL_CANDIDAT, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(COL_RAISON, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(COL_SECOND, QHeaderView.ResizeMode.Stretch)
        partage.addWidget(self.table)
        bas = QWidget()
        lb = QVBoxLayout(bas)
        lb.setContentsMargins(0, 0, 0, 0)
        self.titre_aucun = QLabel(tr("lot.sans_candidat", n=0))
        lb.addWidget(self.titre_aucun)
        self.aucun = QListWidget()
        lb.addWidget(self.aucun)
        self.journal = QPlainTextEdit()
        self.journal.setReadOnly(True)
        self.journal.setVisible(False)
        lb.addWidget(self.journal)
        partage.addWidget(bas)
        partage.setSizes([560, 160])
        racine.addWidget(partage, 1)

        boutons = QHBoxLayout()
        self.b_cocher = QPushButton(tr("lot.cocher_sures"))
        self.b_decocher = QPushButton(tr("lot.tout_decocher"))
        self.b_valider = QPushButton(tr("lot.valider", n=0))
        self.b_valider.setObjectName("principal")
        self.b_fermer = QPushButton(tr("bouton.fermer"))
        for b in (self.b_cocher, self.b_decocher):
            boutons.addWidget(b)
        boutons.addStretch(1)
        boutons.addWidget(self.b_valider)
        boutons.addWidget(self.b_fermer)
        racine.addLayout(boutons)

        # lambda : clicked passe « checked » (un booléen), qui serait pris pour la liste des vins
        self.b_chercher.clicked.connect(lambda: self.chercher())
        self.b_annuler.clicked.connect(self.annuler)
        self.b_cocher.clicked.connect(lambda: self._cocher(seulement_sures=True))
        self.b_decocher.clicked.connect(lambda: self._cocher(aucune=True))
        self.b_valider.clicked.connect(self.valider)
        self.b_fermer.clicked.connect(self.reject)
        self.table.itemChanged.connect(lambda _it: self._compter())
        self.table.cellDoubleClicked.connect(lambda r, _c: self._ouvrir(self._vin_de_ligne(r)))
        self.aucun.itemDoubleClicked.connect(
            lambda it: self._ouvrir(it.data(Qt.ItemDataRole.UserRole)))
        self._occupe(False)
        if not cave.references.nb_lwin():
            self.etat.setText(tr("lot.lwin_absent"))
        if demarrer:
            self.chercher()

    # ------------------------------------------------------------------ calcul (lectures)
    def chercher(self, vin_ids: list[int] | None = None) -> None:
        if self._travail is not None and not self._travail.termine:
            return
        if not isinstance(vin_ids, list):
            vin_ids = lot.vins_a_identifier(self.cave, self.o_tous.isChecked())
        self._arret.clear()
        self.barre.setRange(0, max(1, len(vin_ids)))
        self.barre.setValue(0)
        self._occupe(True, tr("lot.en_cours", n=len(vin_ids)))
        client = reseau.client() if (self.o_wikidata.isChecked() and reseau.autorise()) else None
        signaux = self._signaux
        self._travail = travail.lancer(
            lot.preparer, self.cave, vin_ids, wikidata_client=client, langue=langue(),
            progression=lambda i, n: signaux.avance.emit(i, n), annule=self._arret.is_set,
            fini=self._resultats, echec=self._echec, parent=self)

    def annuler(self) -> None:
        self._arret.set()
        self.etat.setText(tr("lot.annulation"))

    def _avance(self, i: int, n: int) -> None:
        self.barre.setRange(0, max(1, n))
        self.barre.setValue(i)

    def _echec(self, e) -> None:
        self._occupe(False)
        if isinstance(e, lot.Annule):
            self.etat.setText(tr("lot.annule"))
        else:
            self.etat.setText(tr("lot.erreur", erreur=str(e)[:300]))

    def _occupe(self, oui: bool, message: str = "") -> None:
        self.b_annuler.setEnabled(oui)
        for w in (self.b_chercher, self.o_tous, self.b_cocher, self.b_decocher, self.b_valider):
            w.setEnabled(not oui)
        self.o_wikidata.setEnabled(not oui and reseau.autorise())
        if message:
            self.etat.setText(message)
        if not oui:
            self._compter()

    # ------------------------------------------------------------------ récapitulatif
    def _resultats(self, lignes) -> None:
        self.lignes = list(lignes)
        self.journal.setVisible(False)
        self.aucun.setVisible(True)
        ordre = {lot.SURE: 0, lot.DOUTEUSE: 1, lot.DEJA: 2}
        visibles = sorted((l for l in self.lignes if l.categorie != lot.AUCUN),
                          key=lambda l: (ordre[l.categorie], l.nom.lower()))
        self.table.blockSignals(True)
        self.table.setRowCount(len(visibles))
        for i, l in enumerate(visibles):
            self._remplir(i, l)
        self.table.blockSignals(False)
        self.table.resizeColumnToContents(COL_VIN)
        self.table.setColumnWidth(COL_VIN, min(self.table.columnWidth(COL_VIN), 360))
        for col in (COL_SCORE, COL_ETAT):
            self.table.resizeColumnToContents(col)
        self.aucun.clear()
        for l in self.lignes:
            if l.categorie == lot.AUCUN:
                it = QListWidgetItem(l.nom)
                it.setData(Qt.ItemDataRole.UserRole, l.vin_id)
                self.aucun.addItem(it)
        self.titre_aucun.setText(tr("lot.sans_candidat", n=self.aucun.count()))
        n = {k: sum(1 for l in self.lignes if l.categorie == k) for k in CATEGORIES}
        self.etat.setText(tr("lot.resume", total=len(self.lignes), sures=n[lot.SURE],
                             douteuses=n[lot.DOUTEUSE], deja=n[lot.DEJA], aucun=n[lot.AUCUN]))
        self._occupe(False)

    def _remplir(self, i: int, l: lot.LigneLot) -> None:
        c, second = l.meilleur, l.second
        cat = l.categorie
        vin = QTableWidgetItem(l.nom)
        vin.setData(Qt.ItemDataRole.UserRole, l.vin_id)
        if cat in (lot.SURE, lot.DOUTEUSE):
            vin.setFlags(vin.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            vin.setCheckState(Qt.CheckState.Checked if l.coche_d_avance else Qt.CheckState.Unchecked)
        self.table.setItem(i, COL_VIN, vin)
        cand = QTableWidgetItem(libelle_source(c))
        cand.setToolTip(appariement.explication_texte(c.raisons, tr))
        self.table.setItem(i, COL_CANDIDAT, cand)
        score = QTableWidgetItem(pct(c.score))
        score.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
        self.table.setItem(i, COL_SCORE, score)
        raison = QTableWidgetItem(raison_courte(c))
        raison.setToolTip(appariement.explication_texte(c.raisons, tr))
        self.table.setItem(i, COL_RAISON, raison)
        self.table.setItem(i, COL_SECOND, QTableWidgetItem(
            f"{libelle_source(second)} ({pct(second.score)})" if second else ""))
        if cat == lot.DEJA:
            etat = tr("lot.etat_deja", lwin=l.lwin_actuel)
        elif l.lwin_actuel:
            etat = tr("lot.etat_autre_lwin", lwin=l.lwin_actuel)
        elif cat == lot.DOUTEUSE:
            etat = tr("lot.etat_douteuse") + " — " + tr(MOTIFS[l.active.motif])
        else:
            etat = tr("lot.etat_sure")
        e = QTableWidgetItem(etat)
        self.table.setItem(i, COL_ETAT, e)
        fond = SURE_FOND if cat == lot.SURE else (DOUTE_FOND if cat == lot.DOUTEUSE else None)
        if fond is not None:
            for col in range(self.table.columnCount()):
                self.table.item(i, col).setBackground(QBrush(fond))

    def _vin_de_ligne(self, r: int) -> int | None:
        it = self.table.item(r, COL_VIN)
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    def _ligne(self, vin_id: int) -> lot.LigneLot | None:
        return next((l for l in self.lignes if l.vin_id == vin_id), None)

    def _cocher(self, seulement_sures: bool = False, aucune: bool = False) -> None:
        for r in range(self.table.rowCount()):
            it = self.table.item(r, COL_VIN)
            if not it.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                continue
            l = self._ligne(it.data(Qt.ItemDataRole.UserRole))
            oui = not aucune and l is not None and (l.coche_d_avance or not seulement_sures)
            it.setCheckState(Qt.CheckState.Checked if oui else Qt.CheckState.Unchecked)
        self._compter()

    def choix(self) -> list[tuple[int, appariement.Candidat]]:
        """Les (vin, candidat) cochés, dans l'ordre du tableau."""
        sortie = []
        for r in range(self.table.rowCount()):
            it = self.table.item(r, COL_VIN)
            if it.flags() & Qt.ItemFlag.ItemIsUserCheckable and it.flags() & Qt.ItemFlag.ItemIsEnabled \
                    and it.checkState() == Qt.CheckState.Checked:
                l = self._ligne(it.data(Qt.ItemDataRole.UserRole))
                if l is not None and l.meilleur is not None:
                    sortie.append((l.vin_id, l.meilleur))
        return sortie

    def _compter(self) -> None:
        n = len(self.choix()) if self.table.rowCount() else 0
        self.b_valider.setText(tr("lot.valider", n=n))
        occupe = self._travail is not None and not self._travail.termine
        self.b_valider.setEnabled(bool(n) and not occupe)

    # ------------------------------------------------------------------ écran habituel
    def _ouvrir(self, vin_id: int | None) -> None:
        if vin_id is None:
            return
        from .identifier import DialogueIdentifier
        d = DialogueIdentifier(self.cave, vin_id, parent=self)
        if self.cave.references.nb_lwin():
            d.chercher_lwin()
        if d.exec() == QDialog.DialogCode.Accepted:
            self.modifie = True
            self._fait_a_la_main(vin_id)

    def _fait_a_la_main(self, vin_id: int) -> None:
        """Identifié dans l'écran habituel : la ligne n'est plus à valider ici."""
        for r in range(self.table.rowCount()):
            it = self.table.item(r, COL_VIN)
            if it.data(Qt.ItemDataRole.UserRole) == vin_id:
                it.setCheckState(Qt.CheckState.Unchecked)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                self.table.item(r, COL_ETAT).setText(tr("lot.etat_main"))
        for i in range(self.aucun.count()):
            it = self.aucun.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == vin_id:
                it.setText(f"{it.text()} — {tr('lot.etat_main')}")
        self._compter()

    # ------------------------------------------------------------------ validation (écritures)
    def valider(self) -> None:
        choix = self.choix()
        if not choix:
            return
        self._arret.clear()
        self.barre.setRange(0, 0)
        self._occupe(True, tr("lot.application", n=len(choix)))

        def explication(c):
            return appariement.explication_texte(c.raisons, tr)
        self._travail = travail.lancer(lot.appliquer, self.cave, choix, explication,
                                       nom=self.cave.nom_vin, annule=self._arret.is_set,
                                       fini=self._applique, echec=self._echec, parent=self)

    def _applique(self, bilan: lot.Bilan) -> None:
        self.bilan = bilan
        self.modifie = self.modifie or bool(bilan.vins)
        self.barre.setRange(0, 1)
        self.barre.setValue(1)
        faits = {vin_id for vin_id, *_ in bilan.lignes}
        for r in range(self.table.rowCount()):
            it = self.table.item(r, COL_VIN)
            if it.data(Qt.ItemDataRole.UserRole) in faits:
                it.setCheckState(Qt.CheckState.Unchecked)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                self.table.item(r, COL_ETAT).setText(tr("lot.etat_fait"))
        self.journal.setPlainText(self.texte_journal(bilan))
        self.journal.setVisible(True)
        self.aucun.setVisible(False)
        self.titre_aucun.setText(tr("lot.journal"))
        self._occupe(False, tr("lot.fini", vins=bilan.vins, champs=bilan.champs,
                               echecs=len(bilan.echecs)))

    @staticmethod
    def texte_journal(bilan: lot.Bilan) -> str:
        lignes = []
        for _vin_id, nom, c, remplis in bilan.lignes:
            champs = ", ".join(tr(CHAMPS.get(x, "ident.f_champ")) for x in remplis) or tr("lot.rien")
            lignes.append(tr("lot.journal_ligne", vin=nom, source=libelle_source(c),
                             score=pct(c.score), champs=champs))
        for _vin_id, nom, erreur in bilan.echecs:
            lignes.append(tr("lot.journal_echec", vin=nom, erreur=erreur))
        return "\n".join(lignes)

    # ------------------------------------------------------------------ fermeture
    def done(self, r) -> None:
        """Fermeture (bouton, Échap, croix) : un calcul en cours est annulé et
        attendu — jamais un fil détruit pendant qu'il tourne. Une validation en
        cours s'arrête entre deux vins (chaque vin est tout ou rien)."""
        if self._travail is not None and not self._travail.termine:
            self._arret.set()
            travail.attendre(self._travail, 15000)
        super().done(r)
