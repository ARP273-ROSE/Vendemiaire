# -*- coding: utf-8 -*-
"""Fenêtre principale : tableau de bord, cave, mur d'étiquettes, plan des
casiers, livre de cave, « que boire ce soir ? », liste d'envies, conditions de
cave."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from PyQt6.QtCore import QLocale, QSettings, QTimer, QUrl
from PyQt6.QtGui import QAction, QActionGroup, QDesktopServices, QKeySequence
from PyQt6.QtWidgets import (QApplication, QDialog, QFileDialog, QMainWindow, QMessageBox,
                             QTabWidget)

from .. import __version__, chemins, echanges, i18n, logo, ocr, regles, reseau, sauvegarde
from ..i18n import tr
from . import pochette, travail
from .conditions import VueConditions
from .envies import DialogueEnvie, VueEnvies
from .liste import VueCave
from .livre import VueLivre
from .mur import VueMur
from .plan import VuePlan
from .saisie import DialogueAjoutBouteilles, DialogueBouteille, DialogueSortie, DialogueVin
from .tableau import TableauDeBord

log = logging.getLogger(__name__)
FILTRE_CSV = "CSV (*.csv *.txt *.tsv)"
FILTRE_JSON = "JSON (*.json)"
FILTRE_TABLEURS = "Excel / CSV (*.xlsx *.xlsm *.csv *.txt *.tsv)"
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
        self._travaux = []
        reglages = QSettings()
        reseau.autoriser(reglages.value("reseau/autorise", False, type=bool))
        ocr.definir_chemin(reglages.value("ocr/tesseract", "") or None)
        regles.charger_livres()
        self.recalculer_fenetres()
        self.construire()
        etat = QSettings().value("fenetre/geometrie")
        if etat:
            self.restoreGeometry(etat)
        self.minuteur = QTimer(self)
        self.minuteur.timeout.connect(self.sauvegarde_auto)
        self.minuteur.start(PERIODE_SAUVEGARDE_MS)
        QTimer.singleShot(8000, self._mise_a_jour_lwin_periodique)

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
        self.mur = VueMur(self.cave)
        self.plan = VuePlan(self.cave)
        self.livre = VueLivre(self.cave, charger=False)
        self.envies = VueEnvies(self.cave)
        self.conditions = VueConditions(self.cave)
        from .ce_soir import VueCeSoir
        from .seances import VueSeances
        from .statistiques import VueStatistiques
        self.ce_soir = VueCeSoir(self.cave, charger=False)
        self.statistiques = VueStatistiques(self.cave, charger=False)
        # chargés à leur première ouverture (grande cave : démarrage plus court)
        self._a_rafraichir = {self.livre, self.ce_soir}
        self.seances = VueSeances(self.cave)
        self.onglets.addTab(self.tableau, tr("onglet.tableau"))
        self.onglets.addTab(self.vue_cave, tr("onglet.cave"))
        self.onglets.addTab(self.mur, tr("onglet.mur"))
        self.onglets.addTab(self.plan, tr("onglet.plan"))
        self.onglets.addTab(self.livre, tr("onglet.livre"))
        self.onglets.addTab(self.ce_soir, tr("onglet.ce_soir"))
        self.onglets.addTab(self.statistiques, tr("onglet.statistiques"))
        self.onglets.addTab(self.seances, tr("onglet.seances"))
        self.onglets.addTab(self.envies, tr("onglet.envies"))
        self.onglets.addTab(self.conditions, tr("onglet.conditions"))
        ancien = self.centralWidget()
        self.setCentralWidget(self.onglets)
        if ancien is not None:
            ancien.deleteLater()
        self.onglets.setCurrentIndex(onglet)
        self.onglets.currentChanged.connect(self._onglet_change)
        if onglet:
            self._onglet_change(onglet)

        f = self.vue_cave.fiche
        self.vue_cave.bouton_nouveau.clicked.connect(self.nouveau_vin)
        self.vue_cave.bouton_identifier.clicked.connect(self.identifier_toute_la_cave)
        self.vue_cave.modifier_demande.connect(self.modifier_vin)
        f.modifier.connect(self.modifier_vin)
        f.ajouter_bouteilles.connect(self.ajouter_bouteilles)
        f.choisir_photo.connect(self.choisir_photo)
        f.sortir.connect(self.sortir_bouteille)
        f.modifier_bouteille.connect(self.modifier_bouteille)
        f.recevoir.connect(self.recevoir_bouteille)
        f.voir_plan.connect(self.voir_au_plan)
        f.identifier.connect(self.identifier_vin)
        f.photos.connect(self.photos_vin)
        f.envie.connect(self.envie_depuis_vin)
        f.photo_deposee.connect(self.photo_deposee)
        f.modifie.connect(self.tout_rafraichir)
        f.ce_soir.connect(self.fiche_ce_soir)
        f.entamer.connect(self.entamer_bouteille)
        f.diagnostic.connect(self.diagnostic_bouteille)
        self.ce_soir.vin_choisi.connect(self.montrer_vin)
        self.mur.vin_choisi.connect(self.montrer_vin)
        self.mur.photo_deposee.connect(self.photo_deposee)
        self.plan.modifie.connect(self.tout_rafraichir)
        self.plan.vin_choisi.connect(lambda vid: self.vue_cave.fiche.afficher(vid))
        self.livre.modifie.connect(self.tout_rafraichir)
        self._menus()
        self._raccourcis_onglets()
        self.statusBar().showMessage(tr("etat.base", chemin=str(self.cave.base.chemin)))

    def _menus(self) -> None:
        m = self.menuBar().addMenu(tr("menu.fichier"))
        self._action(m, "menu.importer_csv", self.importer_csv)
        self._action(m, "menu.importer_ct", self.importer_cellartracker)
        self._action(m, "menu.importer_tableur", lambda: self.importer_tableur("generique"))
        self._action(m, "menu.importer_vivino", lambda: self.importer_tableur("vivino"))
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
        self._action(m, "menu.modifier_vin", lambda: self._vin_courant(self.modifier_vin), "Ctrl+E")
        self._action(m, "menu.ajouter_bouteilles", lambda: self._vin_courant(self.ajouter_bouteilles),
                     "Ctrl+Shift+B")
        self._action(m, "menu.sortir", self._sortir_courante, "Ctrl+Shift+D")
        m.addSeparator()
        self._action(m, "menu.inventaire", self.inventaire)
        self._action(m, "menu.scanner", self.scanner)
        m.addSeparator()
        self._action(m, "menu.ce_soir", lambda: self.onglets.setCurrentWidget(self.ce_soir))
        self._action(m, "menu.fiche_ce_soir", lambda: self._vin_courant(self.fiche_ce_soir))
        self._action(m, "menu.diagnostic", lambda: self.diagnostic_bouteille(
            self.vue_cave.fiche.bouteille_choisie()))
        m.addSeparator()
        self._action(m, "menu.supprimer_vin", lambda: self._vin_courant(self.supprimer_vin))

        m = self.menuBar().addMenu(tr("menu.documents"))
        self._action(m, "menu.carte_vins", self.carte_vins)
        self._action(m, "menu.assurance", self.rapport_assurance)
        self._action(m, "menu.partage", self.partager)
        self._action(m, "menu.etiquettes", self.etiquettes_qr)
        m.addSeparator()
        self._action(m, "menu.liste_achats", self.liste_achats, QKeySequence("Ctrl+Shift+L"))

        m = self.menuBar().addMenu(tr("menu.references"))
        self._action(m, "menu.identifier_vin", lambda: self._vin_courant(self.identifier_vin))
        self._action(m, "menu.identifier_photo", self.identifier_par_photo)
        self._action(m, "menu.code_barres", self.identifier_par_code)
        self._action(m, "menu.identifier_cave", self.identifier_toute_la_cave)
        m.addSeparator()
        self._action(m, "menu.bases_reference", self.bases_reference)
        self._action(m, "menu.regles", self.voir_regles)

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
                if getattr(self.aide, "act_manuel", None) is not None:
                    self.aide.act_manuel.setShortcut(QKeySequence(QKeySequence.StandardKey.HelpContents))
                m.addSeparator()
            except Exception:
                log.exception("menu Aide du kit")
                self.aide = None
        self._action(m, "menu.demonstration", self.ouvrir_demonstration)
        self._action(m, "menu.apropos", self.a_propos)

    def _raccourcis_onglets(self) -> None:
        """Accessibilité au clavier : Ctrl+1 … Ctrl+9 et Ctrl+0 ouvrent les dix
        onglets (Ctrl+Tab / Ctrl+Maj+Tab les parcourent, comme partout dans Qt) ;
        les infobulles des onglets rappellent leur raccourci."""
        from PyQt6.QtGui import QShortcut
        for anciens in getattr(self, "_raccourcis", []):
            anciens.setParent(None)
        self._raccourcis = []
        for i in range(min(10, self.onglets.count())):
            touche = QKeySequence(f"Ctrl+{(i + 1) % 10}")
            r = QShortcut(touche, self)
            r.activated.connect(lambda i=i: self.onglets.setCurrentIndex(i))
            self._raccourcis.append(r)
            self.onglets.setTabToolTip(i, touche.toString(QKeySequence.SequenceFormat.NativeText))

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
        elif w is self.mur:
            self.mur.rafraichir()
        elif w is self.statistiques:
            self.statistiques.rafraichir()
        elif w in getattr(self, "_a_rafraichir", set()):
            w.rafraichir()
        getattr(self, "_a_rafraichir", set()).discard(w)

    def changer_langue(self, code: str) -> None:
        i18n.definir_langue(code)
        QSettings().setValue("langue", code)
        pochette.vider_cache()
        vin = self.vue_cave.vin_courant()
        self.construire()
        if vin:
            self.vue_cave.selectionner(vin)

    def recalculer_fenetres(self, vin_ids=None) -> None:
        """Fenêtres calculées d'après le dossier « Le vin », rangées dans la base
        (source « calcul »). Un jeu de règles invalide est signalé, jamais masqué."""
        try:
            self.cave.enregistrer_fenetres_calculees(vin_ids)
        except Exception:
            log.exception("fenêtres calculées")

    def tout_rafraichir(self, vin: int | None = None) -> None:
        self.recalculer_fenetres([vin] if vin else None)
        self.vue_cave.recharger_filtres()
        if vin:
            self.vue_cave.selectionner(vin)
        self.vue_cave.fiche.afficher(vin or self.vue_cave.vin_courant())
        # seul l'onglet visible se recalcule tout de suite ; les autres à leur
        # prochaine ouverture (une grande cave ne gèle plus à chaque saisie)
        courant = self.onglets.currentWidget()
        vues = (self.plan, self.livre, self.envies, self.ce_soir, self.conditions, self.seances)
        self._a_rafraichir = set(vues)
        for v in (self.tableau, self.statistiques, self.mur) + vues:
            if v is courant:
                v.rafraichir()
                self._a_rafraichir.discard(v)

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
        """Photo de l'étiquette depuis un fichier : recadrée et redressée
        (réglable), la photo d'origine est gardée."""
        chemin, _ = QFileDialog.getOpenFileName(self, tr("dialogue.photo"), str(Path.home()),
                                                tr("filtre.images") + " " + MOTIF_IMAGES)
        if not chemin:
            return
        self.photo_deposee((vin_id, chemin))

    def photo_deposee(self, quoi) -> None:
        """(vin, fichier) : photo choisie, glissée sur la fiche ou sur le mur."""
        from .photos import DialoguePhotos
        vin_id, chemin = quoi
        d = DialoguePhotos(self.cave, vin_id, self)
        d.identifier_demande.connect(self._identifier_depuis_photo)
        if d.ajouter_fichier(chemin) is not None:
            pochette.vider_cache()
            self.tout_rafraichir(vin_id)
        d.deleteLater()

    def photos_vin(self, vin_id: int) -> None:
        from .photos import DialoguePhotos
        d = DialoguePhotos(self.cave, vin_id, self)
        d.identifier_demande.connect(self._identifier_depuis_photo)
        d.exec()
        if d.modifie:
            pochette.vider_cache()
            self.tout_rafraichir(vin_id)

    def _identifier_depuis_photo(self, quoi) -> None:
        vin_id, texte = quoi
        self.identifier_vin(vin_id, texte)

    def identifier_vin(self, vin_id: int, texte: str = "") -> None:
        from .identifier import DialogueIdentifier
        d = DialogueIdentifier(self.cave, vin_id, texte_etiquette=texte, parent=self)
        if d.exec() == QDialog.DialogCode.Accepted:
            pochette.vider_cache()
            self.tout_rafraichir(vin_id)

    def identifier_toute_la_cave(self) -> None:
        """Références › Identifier toute la cave… : calcul en fond, récapitulatif,
        rien n'est écrit sans « Valider la sélection »."""
        from .identifier_lot import DialogueIdentifierLot
        d = DialogueIdentifierLot(self.cave, parent=self)
        d.exec()
        if d.modifie:
            pochette.vider_cache()
            self.tout_rafraichir()

    def identifier_par_photo(self) -> None:
        """Une bouteille inconnue : sa photo → texte lu (OCR) → candidats → vin créé."""
        from . import photos
        from .identifier import DialogueIdentifier
        from .. import images
        chemin, _ = QFileDialog.getOpenFileName(self, tr("dialogue.photo"), str(Path.home()),
                                                tr("filtre.images") + " " + MOTIF_IMAGES)
        if not chemin:
            return
        r = photos.DialogueRetouche(images.charger(chemin), parent=self)
        if r.exec() != QDialog.DialogCode.Accepted:
            return
        from ..ocr import indices, requete_depuis_indices
        ind = indices(r.texte_ocr or "", r.lignes_principales, self.cave.references)
        requete = requete_depuis_indices(ind)
        if ind.eans:
            requete["ean"] = ind.eans[0]
        d = DialogueIdentifier(self.cave, None, requete, texte_etiquette="\n".join(ind.lignes) or
                               (r.texte_ocr or ""), parent=self)
        if self.cave.references.nb_lwin():
            d.chercher_lwin()
        if d.exec() == QDialog.DialogCode.Accepted and d.vin_id:
            photos.enregistrer_retouche(self.cave, r, chemin, d.vin_id)
            pochette.vider_cache()
            self.onglets.setCurrentWidget(self.vue_cave)
            self.vue_cave.statut.setCurrentIndex(1)
            self.tout_rafraichir(d.vin_id)

    def identifier_par_code(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        from .identifier import DialogueIdentifier
        code, ok = QInputDialog.getText(self, tr("menu.code_barres"), tr("ident.ean_saisie"))
        if not ok or not code.strip():
            return
        vin_id = self.vue_cave.vin_courant()
        d = DialogueIdentifier(self.cave, None, {"ean": code.strip()}, parent=self)
        d.chercher_off()
        if d.exec() == QDialog.DialogCode.Accepted and d.vin_id:
            self.onglets.setCurrentWidget(self.vue_cave)
            self.vue_cave.statut.setCurrentIndex(1)
            self.tout_rafraichir(d.vin_id)
        elif vin_id:
            self.tout_rafraichir(vin_id)

    def bases_reference(self) -> None:
        from .references import DialogueReferences
        DialogueReferences(self.cave, self).exec()

    def _mise_a_jour_lwin_periodique(self) -> None:
        """Mise à jour périodique de LWIN (si l'utilisateur l'a demandée), en fond."""
        from .references import mise_a_jour_lwin_due, telecharger_lwin
        url = mise_a_jour_lwin_due()
        if not url:
            return

        def fini(n):
            from datetime import datetime
            QSettings().setValue("lwin/derniere_verif", datetime.now().isoformat(timespec="seconds"))
            self.statusBar().showMessage(tr("ref.lwin_fini", n=n), 8000)
        self._travaux.append(travail.lancer(telecharger_lwin, self.cave.references, url, fini=fini,
                                            echec=lambda e: log.info("MAJ LWIN : %s", e), parent=self))

    def envie_depuis_vin(self, vin_id: int) -> None:
        if DialogueEnvie(self.cave, None, self, vin_id=vin_id).exec() == QDialog.DialogCode.Accepted:
            self.envies.rafraichir()
            self.onglets.setCurrentWidget(self.envies)

    def montrer_vin(self, vin_id: int) -> None:
        self.onglets.setCurrentWidget(self.vue_cave)
        if not self.vue_cave.selectionner(vin_id):
            self.vue_cave.statut.setCurrentIndex(1)
            self.vue_cave.selectionner(vin_id)

    def fiche_ce_soir(self, vin_id: int) -> None:
        from .ce_soir import DialogueFicheCeSoir
        DialogueFicheCeSoir(self.cave, [vin_id], parent=self).exec()

    def entamer_bouteille(self, bid: int) -> None:
        from .ce_soir import DialogueEntamer
        b = self.cave.bouteille(bid)
        if b is None or b["statut"] != "en_cave":
            return
        if DialogueEntamer(self.cave, bid, self).exec() == QDialog.DialogCode.Accepted:
            self.tout_rafraichir(b["vin_id"])

    def diagnostic_bouteille(self, bid: int | None = None) -> None:
        from .degustation import DialogueDiagnostic
        d = DialogueDiagnostic(self.cave, bid, self)
        d.exec()
        if d.sortie and bid:
            self.tout_rafraichir(self.cave.bouteille(bid)["vin_id"])

    def voir_regles(self) -> None:
        from .regles_ui import DialogueRegles
        DialogueRegles(self).exec()

    def inventaire(self) -> None:
        from .inventaire import DialogueInventaire
        DialogueInventaire(self.cave, None, self).exec()
        self.tout_rafraichir()

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

    def importer_tableur(self, profil: str = "generique") -> None:
        from .import_tableur import DialogueImportTableur
        cle = "menu.importer_vivino" if profil == "vivino" else "menu.importer_tableur"
        chemin, _ = QFileDialog.getOpenFileName(self, tr(cle), str(Path.home()), FILTRE_TABLEURS)
        if not chemin:
            return
        try:
            d = DialogueImportTableur(self.cave, chemin, profil, self)
        except (OSError, ValueError) as ex:
            QMessageBox.warning(self, tr(cle), tr("imp.illisible", erreur=str(ex)))
            return
        if d.exec() == QDialog.DialogCode.Accepted:
            self._avant_import()
            self._rapport(d.importer())

    # ------------------------------------------------------------------ documents (phase 4)
    def carte_vins(self) -> None:
        from .carte_vins import DialogueCarteVins
        DialogueCarteVins(self.cave, self).exec()
        self.tout_rafraichir()

    def rapport_assurance(self) -> None:
        from .documents import DialogueAssurance
        DialogueAssurance(self.cave, self).exec()

    def liste_achats(self) -> None:
        from .achats import DialogueAchats
        DialogueAchats(self.cave, self).exec()

    def partager(self) -> None:
        from .documents import DialoguePartage
        DialoguePartage(self.cave, self).exec()

    def etiquettes_qr(self) -> None:
        from .documents import DialogueEtiquettes
        DialogueEtiquettes(self.cave, self.vue_cave.vin_courant(), self).exec()

    def scanner(self) -> None:
        from .scanner import DialogueScanner
        d = DialogueScanner(self.cave, self)
        d.sortir.connect(self.sortir_bouteille)
        d.voir_vin.connect(self.montrer_vin)
        d.exec()

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
    def commande_demonstration(self) -> tuple[str, list[str]]:
        """Programme et arguments qui ouvrent la cave de démonstration dans une
        AUTRE fenêtre (son propre dossier de données, son propre verrou : la
        vraie cave n'est jamais touchée)."""
        import sys
        racine = chemins.RACINE_APP
        py = racine.parent / "python" / "pythonw.exe"
        exe = str(py) if py.exists() else sys.executable
        return exe, [str(racine / "run.py"), "--demo", "--lang", i18n.langue()]

    def ouvrir_demonstration(self) -> None:
        from PyQt6.QtCore import QProcess
        exe, args = self.commande_demonstration()
        if not QProcess.startDetached(exe, args)[0]:
            QMessageBox.warning(self, tr("menu.demonstration"), tr("demonstration.echec"))

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
            self.cave.fermer_references()
        except Exception:
            log.exception("fermeture")
        for w in QApplication.topLevelWidgets():
            if w is not self and w.isVisible():
                w.close()
        super().closeEvent(ev)
