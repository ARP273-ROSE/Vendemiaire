# -*- coding: utf-8 -*-
"""Fenêtre principale : tableau de bord, cave, plan des casiers, livre de cave."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from PyQt6.QtCore import QLocale, QSettings, QTimer, QUrl
from PyQt6.QtGui import QAction, QActionGroup, QDesktopServices, QKeySequence
from PyQt6.QtWidgets import (QApplication, QDialog, QFileDialog, QMainWindow, QMessageBox,
                             QTabWidget)

from .. import __version__, chemins, echanges, i18n, logo, sauvegarde
from ..i18n import tr
from . import pochette
from .liste import VueCave
from .livre import VueLivre
from .plan import VuePlan
from .saisie import DialogueAjoutBouteilles, DialogueBouteille, DialogueSortie, DialogueVin
from .tableau import TableauDeBord

log = logging.getLogger(__name__)
FILTRE_CSV = "CSV (*.csv *.txt *.tsv)"
FILTRE_JSON = "JSON (*.json)"
MOTIF_IMAGES = "(*.jpg *.jpeg *.png *.webp *.tif *.tiff)"
FILTRE_BASE = "SQLite (*.db)"
#: sauvegarde automatique : toutes les 30 minutes si la base a changé
PERIODE_SAUVEGARDE_MS = 30 * 60 * 1000


class FenetrePrincipale(QMainWindow):
    def __init__(self, cave, aide_kit: bool = True):
        super().__init__()
        self.cave = cave
        self.setWindowIcon(logo.icone())
        self.resize(1360, 860)
        self.aide = None
        self._avec_aide = aide_kit
        self.construire()
        etat = QSettings().value("fenetre/geometrie")
        if etat:
            self.restoreGeometry(etat)
        self.minuteur = QTimer(self)
        self.minuteur.timeout.connect(self.sauvegarde_auto)
        self.minuteur.start(PERIODE_SAUVEGARDE_MS)

    # ------------------------------------------------------------------ interface
    def construire(self) -> None:
        """(Re)construit menus et onglets dans la langue courante."""
        onglet = self.onglets.currentIndex() if hasattr(self, "onglets") else 0
        # nombres et dates des champs de saisie dans la langue de l'interface
        QLocale.setDefault(QLocale(QLocale.Language.French, QLocale.Country.France)
                           if i18n.langue() == "fr" else
                           QLocale(QLocale.Language.English, QLocale.Country.UnitedKingdom))
        self.setWindowTitle(f"{tr('app.nom')} {__version__}")
        for action in self.menuBar().actions():       # anciens menus : détruits, pas seulement retirés
            if action.menu() is not None:
                action.menu().deleteLater()
        self.menuBar().clear()
        self.onglets = QTabWidget()
        self.tableau = TableauDeBord(self.cave)
        self.vue_cave = VueCave(self.cave)
        self.plan = VuePlan(self.cave)
        self.livre = VueLivre(self.cave)
        self.onglets.addTab(self.tableau, tr("onglet.tableau"))
        self.onglets.addTab(self.vue_cave, tr("onglet.cave"))
        self.onglets.addTab(self.plan, tr("onglet.plan"))
        self.onglets.addTab(self.livre, tr("onglet.livre"))
        ancien = self.centralWidget()
        self.setCentralWidget(self.onglets)
        if ancien is not None:
            ancien.deleteLater()
        self.onglets.setCurrentIndex(onglet)
        self.onglets.currentChanged.connect(self._onglet_change)

        f = self.vue_cave.fiche
        self.vue_cave.bouton_nouveau.clicked.connect(self.nouveau_vin)
        self.vue_cave.modifier_demande.connect(self.modifier_vin)
        f.modifier.connect(self.modifier_vin)
        f.ajouter_bouteilles.connect(self.ajouter_bouteilles)
        f.choisir_photo.connect(self.choisir_photo)
        f.sortir.connect(self.sortir_bouteille)
        f.modifier_bouteille.connect(self.modifier_bouteille)
        f.recevoir.connect(self.recevoir_bouteille)
        f.voir_plan.connect(self.voir_au_plan)
        self.plan.modifie.connect(self.tout_rafraichir)
        self.plan.vin_choisi.connect(lambda vid: self.vue_cave.fiche.afficher(vid))
        self.livre.modifie.connect(self.tout_rafraichir)
        self._menus()
        self.statusBar().showMessage(tr("etat.base", chemin=str(self.cave.base.chemin)))

    def _menus(self) -> None:
        m = self.menuBar().addMenu(tr("menu.fichier"))
        self._action(m, "menu.importer_csv", self.importer_csv)
        self._action(m, "menu.importer_ct", self.importer_cellartracker)
        m.addSeparator()
        self._action(m, "menu.exporter_csv", self.exporter_csv)
        self._action(m, "menu.exporter_json", self.exporter_json)
        m.addSeparator()
        self._action(m, "menu.sauvegarder", self.sauvegarde_manuelle)
        self._action(m, "menu.restaurer", self.restaurer)
        self._action(m, "menu.dossier_sauvegardes",
                     lambda: self._ouvrir_dossier(self.dossier_sauvegardes()))
        self._action(m, "menu.dossier_donnees", self.choisir_dossier_donnees)
        m.addSeparator()
        self._action(m, "menu.quitter", self.close, QKeySequence.StandardKey.Quit)

        m = self.menuBar().addMenu(tr("menu.cave"))
        self._action(m, "action.nouveau_vin", self.nouveau_vin, QKeySequence.StandardKey.New)
        self._action(m, "menu.modifier_vin", lambda: self._vin_courant(self.modifier_vin))
        self._action(m, "menu.ajouter_bouteilles", lambda: self._vin_courant(self.ajouter_bouteilles))
        self._action(m, "menu.sortir", self._sortir_courante)
        m.addSeparator()
        self._action(m, "menu.supprimer_vin", lambda: self._vin_courant(self.supprimer_vin))

        m = self.menuBar().addMenu(tr("menu.langue"))
        groupe = QActionGroup(self)
        for code, nom in i18n.LANGUES.items():
            a = QAction(nom, self, checkable=True)
            a.setChecked(code == i18n.langue())
            a.triggered.connect(lambda _c=False, code=code: self.changer_langue(code))
            groupe.addAction(a)
            m.addAction(a)

        m = self.menuBar().addMenu(tr("menu.aide"))
        if self._avec_aide:
            try:
                import kit_aide
                self.aide = kit_aide.AideKit(self, __version__, i18n.langue,
                                             [chemins.dossier_docs()], nom_fil="vendemiaire",
                                             etat=self._etat_rapport)
                self.aide.remplir_menu(m)
                m.addSeparator()
            except Exception:
                log.exception("menu Aide du kit")
                self.aide = None
        self._action(m, "menu.apropos", self.a_propos)

    def _action(self, menu, cle: str, fonction, raccourci=None) -> QAction:
        a = QAction(tr(cle), self)
        if raccourci is not None:
            a.setShortcut(QKeySequence(raccourci))
        a.triggered.connect(lambda *_: fonction())
        menu.addAction(a)
        return a

    def _etat_rapport(self) -> dict:
        try:
            s = self.cave.statistiques()
            return {"bouteilles": s["bouteilles"], "vins": s["vins"],
                    "schema": self.cave.base.version(), "langue": i18n.langue()}
        except Exception:
            return {}

    def _onglet_change(self, i: int) -> None:
        w = self.onglets.widget(i)
        if w is self.tableau:
            self.tableau.rafraichir()

    def changer_langue(self, code: str) -> None:
        i18n.definir_langue(code)
        QSettings().setValue("langue", code)
        pochette.vider_cache()
        vin = self.vue_cave.vin_courant()
        self.construire()
        if vin:
            self.vue_cave.selectionner(vin)

    def tout_rafraichir(self, vin: int | None = None) -> None:
        self.vue_cave.recharger_filtres()
        if vin:
            self.vue_cave.selectionner(vin)
        self.vue_cave.fiche.afficher(vin or self.vue_cave.vin_courant())
        self.plan.rafraichir()
        self.livre.rafraichir()
        self.tableau.rafraichir()

    # ------------------------------------------------------------------ vins
    def _vin_courant(self, fonction) -> None:
        vid = self.vue_cave.vin_courant()
        if vid is None:
            QMessageBox.information(self, tr("app.nom"), tr("message.choisir_vin"))
            return
        fonction(vid)

    def nouveau_vin(self) -> None:
        d = DialogueVin(self.cave, None, self)
        if d.exec() == QDialog.DialogCode.Accepted:
            self.onglets.setCurrentWidget(self.vue_cave)
            self.vue_cave.statut.setCurrentIndex(1)       # « tous » : un vin sans bouteille reste visible
            self.tout_rafraichir(d.vin_id)

    def modifier_vin(self, vin_id: int) -> None:
        d = DialogueVin(self.cave, vin_id, self)
        if d.exec() == QDialog.DialogCode.Accepted:
            pochette.vider_cache()
            self.tout_rafraichir(vin_id)

    def supprimer_vin(self, vin_id: int) -> None:
        n = len(self.cave.bouteilles(vin_id))
        if QMessageBox.question(self, tr("app.nom"),
                                tr("message.supprimer_vin", vin=self.cave.nom_vin(vin_id), n=n)) \
                != QMessageBox.StandardButton.Yes:
            return
        sauvegarde.sauvegarder(self.cave.base.chemin, self.dossier_sauvegardes(), "manuel")
        self.cave.supprimer_vin(vin_id)
        self.tout_rafraichir()

    def ajouter_bouteilles(self, vin_id: int) -> None:
        d = DialogueAjoutBouteilles(self.cave, vin_id, self)
        if d.exec() == QDialog.DialogCode.Accepted:
            self.tout_rafraichir(vin_id)

    def choisir_photo(self, vin_id: int) -> None:
        chemin, _ = QFileDialog.getOpenFileName(self, tr("dialogue.photo"), str(Path.home()),
                                                tr("filtre.images") + " " + MOTIF_IMAGES)
        if not chemin:
            return
        self.cave.ajouter_image(chemin, vin_id=vin_id, type_image="etiquette", origine="perso")
        pochette.vider_cache()
        self.tout_rafraichir(vin_id)

    # ------------------------------------------------------------------ bouteilles
    def _sortir_courante(self) -> None:
        bid = self.vue_cave.fiche.bouteille_choisie()
        if bid is None:
            QMessageBox.information(self, tr("app.nom"), tr("message.choisir_bouteille"))
            return
        self.sortir_bouteille(bid)

    def sortir_bouteille(self, bid: int) -> None:
        b = self.cave.bouteille(bid)
        if b is None or b["statut"] != "en_cave":
            return
        d = DialogueSortie(self.cave, bid, self)
        if d.exec() == QDialog.DialogCode.Accepted:
            self.tout_rafraichir(b["vin_id"])
            self.statusBar().showMessage(tr("etat.sortie"), 6000)

    def modifier_bouteille(self, bid: int) -> None:
        b = self.cave.bouteille(bid)
        if DialogueBouteille(self.cave, bid, self).exec() == QDialog.DialogCode.Accepted:
            self.tout_rafraichir(b["vin_id"])

    def recevoir_bouteille(self, bid: int) -> None:
        b = self.cave.bouteille(bid)
        self.cave.recevoir(bid)
        self.tout_rafraichir(b["vin_id"])

    def voir_au_plan(self, bid: int) -> None:
        self.onglets.setCurrentWidget(self.plan)
        self.plan.selectionner_bouteille(bid)

    # ------------------------------------------------------------------ échanges
    def _avant_import(self) -> None:
        sauvegarde.sauvegarder(self.cave.base.chemin, self.dossier_sauvegardes(), "avant-import")

    def _rapport(self, r: echanges.Rapport) -> None:
        texte = tr("import.rapport", lignes=r.lignes, crees=r.vins_crees, completes=r.vins_completes,
                   bouteilles=r.bouteilles, deja=r.deja_presentes)
        if r.avertissements:
            texte += "\n\n" + "\n".join(r.avertissements[:15])
            if len(r.avertissements) > 15:
                texte += "\n…"
        QMessageBox.information(self, tr("import.titre"), texte)
        self.tout_rafraichir()

    def importer_csv(self) -> None:
        chemin, _ = QFileDialog.getOpenFileName(self, tr("menu.importer_csv"), str(Path.home()),
                                                FILTRE_CSV)
        if chemin:
            self._avant_import()
            self._rapport(echanges.importer_csv(self.cave, chemin))

    def importer_cellartracker(self) -> None:
        chemin, _ = QFileDialog.getOpenFileName(self, tr("menu.importer_ct"), str(Path.home()),
                                                FILTRE_CSV)
        if chemin:
            self._avant_import()
            self._rapport(echanges.importer_cellartracker(self.cave, chemin))

    def exporter_csv(self) -> None:
        chemin, _ = QFileDialog.getSaveFileName(self, tr("menu.exporter_csv"),
                                                str(Path.home() / "vendemiaire.csv"), FILTRE_CSV)
        if chemin:
            n = echanges.exporter_csv(self.cave, chemin)
            self.statusBar().showMessage(tr("etat.exporte", n=n, chemin=chemin), 8000)

    def exporter_json(self) -> None:
        chemin, _ = QFileDialog.getSaveFileName(self, tr("menu.exporter_json"),
                                                str(Path.home() / "vendemiaire.json"), FILTRE_JSON)
        if chemin:
            n = sum(echanges.exporter_json(self.cave, chemin).values())
            self.statusBar().showMessage(tr("etat.exporte", n=n, chemin=chemin), 8000)

    # ------------------------------------------------------------------ sauvegardes
    def dossier_sauvegardes(self) -> Path:
        """À côté de la base ouverte (dossier des données), jamais ailleurs."""
        return self.cave.base.chemin.parent / "sauvegardes"

    def sauvegarde_auto(self) -> None:
        try:
            sauvegarde.sauvegarder(self.cave.base.chemin, self.dossier_sauvegardes(), "auto",
                                   seulement_si_modifiee=True)
        except Exception:
            log.exception("sauvegarde automatique")

    def sauvegarde_manuelle(self) -> None:
        p = sauvegarde.sauvegarder(self.cave.base.chemin, self.dossier_sauvegardes(), "manuel")
        if p:
            self.statusBar().showMessage(tr("etat.sauvegarde", nom=p.name), 8000)

    def restaurer(self) -> None:
        chemin, _ = QFileDialog.getOpenFileName(self, tr("menu.restaurer"),
                                                str(self.dossier_sauvegardes()), FILTRE_BASE)
        if not chemin:
            return
        if QMessageBox.question(self, tr("menu.restaurer"), tr("message.restaurer",
                                                               nom=os.path.basename(chemin))) \
                != QMessageBox.StandardButton.Yes:
            return
        base = self.cave.base
        base.fermer()
        sauvegarde.restaurer(chemin, base.chemin)
        base.migrer()
        pochette.vider_cache()
        self.tout_rafraichir()

    def choisir_dossier_donnees(self) -> None:
        actuel = chemins.dossier_donnees()
        dossier = QFileDialog.getExistingDirectory(self, tr("menu.dossier_donnees"), str(actuel))
        if not dossier or Path(dossier) == actuel:
            return
        cible = Path(dossier)
        if (cible / "cave.db").exists():
            texte = tr("message.donnees_existantes", dossier=dossier)
        else:
            texte = tr("message.donnees_copier", dossier=dossier)
        if QMessageBox.question(self, tr("menu.dossier_donnees"), texte) != QMessageBox.StandardButton.Yes:
            return
        if not (cible / "cave.db").exists():
            sauvegarde.restaurer(self.cave.base.chemin, cible / "cave.db")
        chemins.choisir_emplacement(cible)
        QMessageBox.information(self, tr("menu.dossier_donnees"), tr("message.redemarrer"))

    def _ouvrir_dossier(self, dossier: Path) -> None:
        dossier.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(dossier)))

    # ------------------------------------------------------------------ aide
    def a_propos(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(tr("menu.apropos"))
        box.setIconPixmap(logo.pixmap(128))
        box.setText(f"<h3>{tr('app.nom')} {__version__}</h3>")
        box.setInformativeText(tr("apropos.texte", base=str(self.cave.base.chemin)))
        box.exec()

    # ------------------------------------------------------------------ sortie
    def closeEvent(self, ev):
        """Tout ce qui doit être écrit l'est ICI : la sortie normale de PyQt
        tue ensuite le processus (os._exit dans run.py)."""
        try:
            QSettings().setValue("fenetre/geometrie", self.saveGeometry())
            QSettings().sync()
            self.sauvegarde_auto()
            self.cave.base.fermer()
        except Exception:
            log.exception("fermeture")
        for w in QApplication.topLevelWidgets():
            if w is not self and w.isVisible():
                w.close()
        super().closeEvent(ev)
