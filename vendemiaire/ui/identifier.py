# -*- coding: utf-8 -*-
"""Identifier un vin dans les bases mondiales : candidats classés, score
expliqué, champs proposés, confirmation.

Rien n'est écrit sans le bouton « Confirmer » ; seuls les champs cochés sont
remplis, et seulement s'ils sont vides et n'ont pas été saisis à la main
(`Cave.completer_vin`) ; tout remplissage est noté au journal avec sa source.
"""
from __future__ import annotations

import hashlib
import tempfile
import urllib.parse
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QFormLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu,
                             QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTableWidget,
                             QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from .. import reseau
from ..i18n import langue, lib, nombre, tr
from ..mondial import appariement, lwin as m_lwin, off, wikidata
from . import travail


# ---------------------------------------------------------------- accord réseau
def demander_accord(parent) -> bool:
    """Accord de l'utilisateur pour interroger les services en ligne (retenu)."""
    if reseau.autorise():
        return True
    reponse = QMessageBox.question(parent, tr("reseau.titre"), tr("reseau.question"))
    oui = reponse == QMessageBox.StandardButton.Yes
    reseau.autoriser(oui)
    QSettings().setValue("reseau/autorise", oui)
    return oui


def _cellule(texte, donnee=None) -> QTableWidgetItem:
    it = QTableWidgetItem("" if texte is None else str(texte))
    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
    if donnee is not None:
        it.setData(Qt.ItemDataRole.UserRole, donnee)
    return it


CHAMPS_LIBELLES = {
    "producteur": "vin.producteur", "cuvee": "vin.cuvee", "appellation": "vin.appellation",
    "region": "vin.region_seule", "sous_region": "vin.sous_region", "pays": "vin.pays",
    "classement": "vin.classement", "couleur": "vin.couleur", "type": "vin.type",
    "degre": "vin.degre", "lwin": "vin.lwin", "ean": "vin.ean", "millesime": "vin.millesime",
    "site_web": "ident.site_web", "adresse": "ident.adresse",
}


DECISIONS = {"sur": "ident.decision_sur", "ambigu": "ident.decision_ambigu",
             "faible": "ident.decision_faible", "aucun": "ident.decision_aucun",
             "ean": "ident.decision_ean"}
ETATS = {"remplira": "ident.etat_remplira", "deja": "ident.etat_deja", "manuel": "ident.etat_manuel",
         "identique": "ident.etat_identique"}


def _valeur_affichee(champ, v) -> str:
    if v in (None, ""):
        return ""
    if champ == "couleur":
        return lib("couleur", v)
    if champ == "type":
        return lib("type", v)
    if champ == "degre":
        return f"{nombre(v)} %"
    return str(v)


class DialogueIdentifier(QDialog):
    """`vin_id` None : identification d'une bouteille nouvelle (depuis sa
    photo) ; la confirmation CRÉE le vin, dont l'id est ensuite dans `vin_id`."""

    def __init__(self, cave, vin_id: int | None = None, requete: dict | None = None,
                 texte_etiquette: str = "", parent=None):
        super().__init__(parent)
        self.cave = cave
        self.refs = cave.references
        self.vin_id = vin_id
        self.cree = False
        self.candidats: list[appariement.Candidat] = []
        self._travail = None
        self.setWindowTitle(tr("ident.titre", vin=cave.nom_vin(vin_id)) if vin_id
                            else tr("ident.titre_nouveau"))
        self.resize(1180, 820)
        r = dict(appariement.requete_depuis_vin(cave, vin_id) if vin_id else {})
        r.update({k: v for k, v in (requete or {}).items() if v})
        racine = QVBoxLayout(self)

        # -- requête --------------------------------------------------------------
        g = QGroupBox(tr("ident.requete"))
        f = QFormLayout(g)
        self.producteur = QLineEdit(r.get("producteur") or "")
        self.cuvee = QLineEdit(r.get("cuvee") or "")
        self.appellation = QLineEdit(r.get("appellation") or "")
        self.millesime = QLineEdit(str(r.get("millesime") or ""))
        self.millesime.setMaximumWidth(90)
        self.couleur = QComboBox()
        self.couleur.addItem("", None)
        for code in ("rouge", "blanc", "rose", "orange"):
            self.couleur.addItem(lib("couleur", code), code)
        self.couleur.setCurrentIndex(max(0, self.couleur.findData(r.get("couleur"))))
        self.ean = QLineEdit(r.get("ean") or (cave.vin(vin_id)["ean"] if vin_id else "") or "")
        self.ean.setMaximumWidth(180)
        ligne = QHBoxLayout()
        ligne.addWidget(self.millesime)
        ligne.addWidget(QLabel(tr("vin.couleur")))
        ligne.addWidget(self.couleur)
        ligne.addWidget(QLabel(tr("vin.ean")))
        ligne.addWidget(self.ean)
        ligne.addStretch(1)
        self.texte = QPlainTextEdit(texte_etiquette or r.get("texte") or "")
        self.texte.setPlaceholderText(tr("ident.texte_aide"))
        self.texte.setMaximumHeight(64)
        f.addRow(tr("vin.producteur"), self.producteur)
        f.addRow(tr("vin.cuvee"), self.cuvee)
        f.addRow(tr("vin.appellation"), self.appellation)
        f.addRow(tr("vin.millesime"), ligne)
        f.addRow(tr("ident.texte"), self.texte)
        racine.addWidget(g)

        boutons = QHBoxLayout()
        self.b_lwin = QPushButton(tr("ident.chercher_lwin"))
        self.b_lwin.setObjectName("principal")
        self.b_wd_prod = QPushButton(tr("ident.chercher_wd_producteur"))
        self.b_wd_app = QPushButton(tr("ident.chercher_wd_appellation"))
        self.b_off = QPushButton(tr("ident.chercher_off"))
        self.b_web = QToolButton()
        self.b_web.setText(tr("ident.web"))
        self.b_web.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.b_web)
        menu.addAction(tr("ident.web_vivino"), lambda: self._web("vivino"))
        menu.addAction(tr("ident.web_ws"), lambda: self._web("winesearcher"))
        self.b_web.setMenu(menu)
        for b in (self.b_lwin, self.b_wd_prod, self.b_wd_app, self.b_off, self.b_web):
            boutons.addWidget(b)
        boutons.addStretch(1)
        racine.addLayout(boutons)
        self.etat = QLabel()
        self.etat.setWordWrap(True)
        racine.addWidget(self.etat)

        # -- candidats et explication ----------------------------------------------
        milieu = QSplitter()
        self.t_candidats = QTableWidget(0, 3)
        self.t_candidats.setHorizontalHeaderLabels([tr("ident.c_source"), tr("ident.c_candidat"),
                                                    tr("ident.c_score")])
        self.t_candidats.verticalHeader().setVisible(False)
        self.t_candidats.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.t_candidats.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.t_candidats.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        milieu.addWidget(self.t_candidats)
        droite = QWidget()
        ld = QVBoxLayout(droite)
        ld.setContentsMargins(0, 0, 0, 0)
        ld.addWidget(QLabel(tr("ident.pourquoi")))
        self.explication = QPlainTextEdit()
        self.explication.setReadOnly(True)
        ld.addWidget(self.explication, 1)
        self.fiche = QLabel()
        self.fiche.setWordWrap(True)
        self.fiche.setOpenExternalLinks(True)
        self.fiche.setObjectName("legende")
        ld.addWidget(self.fiche)
        milieu.addWidget(droite)
        milieu.setSizes([640, 520])
        racine.addWidget(milieu, 1)

        # -- champs proposés ---------------------------------------------------------
        self.g_champs = QGroupBox(tr("ident.champs"))
        lc = QVBoxLayout(self.g_champs)
        self.t_champs = QTableWidget(0, 4)
        self.t_champs.setHorizontalHeaderLabels([tr("ident.f_champ"), tr("ident.f_propose"),
                                                 tr("ident.f_actuel"), tr("ident.f_etat")])
        self.t_champs.verticalHeader().setVisible(False)
        self.t_champs.horizontalHeader().setStretchLastSection(True)
        lc.addWidget(self.t_champs)
        self.photo_off = QCheckBox(tr("ident.photo_off"))
        self.photo_off.setVisible(False)
        lc.addWidget(self.photo_off)
        racine.addWidget(self.g_champs)

        bas = QHBoxLayout()
        self.b_page = QPushButton(tr("ident.page_source"))
        self.b_confirmer = QPushButton(tr("ident.confirmer"))
        self.b_confirmer.setObjectName("principal")
        self.b_fermer = QPushButton(tr("bouton.fermer"))
        bas.addWidget(self.b_page)
        bas.addStretch(1)
        bas.addWidget(self.b_confirmer)
        bas.addWidget(self.b_fermer)
        racine.addLayout(bas)

        self.b_lwin.clicked.connect(self.chercher_lwin)
        self.b_wd_prod.clicked.connect(lambda: self.chercher_wikidata("producteur"))
        self.b_wd_app.clicked.connect(lambda: self.chercher_wikidata("appellation"))
        self.b_off.clicked.connect(self.chercher_off)
        self.b_confirmer.clicked.connect(self.confirmer)
        self.b_fermer.clicked.connect(self.reject)
        self.b_page.clicked.connect(self._page)
        self.t_candidats.itemSelectionChanged.connect(self._candidat_change)
        self._etat_lwin()
        self._candidat_change()

    # ------------------------------------------------------------------ requête
    def requete(self) -> dict:
        try:
            mil = int(self.millesime.text().strip()) if self.millesime.text().strip() else None
        except ValueError:
            mil = None
        texte = self.texte.toPlainText().strip()
        if not mil and texte:
            mil = appariement.jeton_millesime(texte)
        return {"producteur": self.producteur.text().strip() or None,
                "cuvee": self.cuvee.text().strip() or None,
                "appellation": self.appellation.text().strip() or None,
                "millesime": mil, "couleur": self.couleur.currentData(),
                "pays": (self.cave.vin(self.vin_id)["pays"] if self.vin_id else None),
                "texte": texte or None}

    def _etat_lwin(self) -> None:
        n = self.refs.nb_lwin()
        self.b_lwin.setEnabled(bool(n))
        if not n:
            self.etat.setText(tr("ident.lwin_absent"))
            self.b_lwin.setToolTip(tr("ident.lwin_absent"))

    def _occupe(self, oui: bool, message: str = "") -> None:
        for b in (self.b_lwin, self.b_wd_prod, self.b_wd_app, self.b_off, self.b_confirmer):
            b.setEnabled(not oui)
        if message:
            self.etat.setText(message)
        if not oui:
            self._etat_lwin()
            self._candidat_change()

    # ------------------------------------------------------------------ recherches
    def chercher_lwin(self) -> None:
        r = self.requete()
        self.candidats = appariement.candidats_lwin(self.refs, r,
                                                    appellation_officielle=self.refs.appellation_officielle)
        self._montrer(appariement.decider(self.candidats))

    def chercher_wikidata(self, objet: str) -> None:
        r = self.requete()
        nom = r["producteur"] if objet == "producteur" else r["appellation"]
        if not nom:
            self.etat.setText(tr("ident.nom_manquant"))
            return
        if not demander_accord(self):
            return
        self._objet_wd = objet
        self._occupe(True, tr("ident.recherche_en_ligne", service="Wikidata"))
        self._travail = travail.lancer(wikidata.candidats, reseau.client(), objet, nom, r.get("pays"),
                                       langue(), fini=self._resultats, echec=self._echec, parent=self)

    def chercher_off(self) -> None:
        code = "".join(ch for ch in self.ean.text() if ch.isdigit())
        if not code:
            trouves = off.eans_dans(self.texte.toPlainText())
            code = trouves[0] if trouves else ""
            self.ean.setText(code)
        if not off.ean_valide(code):
            self.etat.setText(tr("ident.ean_invalide"))
            return
        if not demander_accord(self):
            return
        self._occupe(True, tr("ident.recherche_en_ligne", service="Open Food Facts"))

        def chercher():
            p = off.produit(reseau.client(), code)
            return [off.candidat(p, langue())] if p else []
        self._travail = travail.lancer(chercher, fini=self._resultats, echec=self._echec, parent=self)

    def _resultats(self, candidats) -> None:
        self.candidats = list(candidats)
        self._occupe(False)
        if self.candidats and self.candidats[0].source == "off":
            # un code-barres désigne la bouteille : pas de concurrence, mais le nom reste à vérifier
            self._montrer(appariement.Decision(self.candidats, self.candidats[0], "ean"))
        else:
            self._montrer(appariement.decider(self.candidats))

    def _echec(self, e) -> None:
        self._occupe(False)
        cle = "ident.hors_ligne" if isinstance(e, reseau.HorsLigne) else "ident.erreur_reseau"
        self.etat.setText(tr(cle, erreur=str(e)[:200]))

    def _montrer(self, d: appariement.Decision) -> None:
        self.decision = d
        self.t_candidats.setRowCount(len(d.candidats))
        for i, c in enumerate(d.candidats):
            self.t_candidats.setItem(i, 0, _cellule(c.source.upper() if c.source != "wikidata"
                                                    else "Wikidata", i))
            self.t_candidats.setItem(i, 1, _cellule(c.libelle))
            s = _cellule(f"{int(round(c.score * 100))} %")
            s.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
            self.t_candidats.setItem(i, 2, s)
        self.t_candidats.resizeColumnToContents(0)
        self.t_candidats.resizeColumnToContents(2)
        self.etat.setText(tr(DECISIONS[d.motif], n=len(d.candidats)))
        self.t_candidats.clearSelection()
        if d.choisi is not None:
            self.t_candidats.selectRow(d.candidats.index(d.choisi))
        self._candidat_change()

    # ------------------------------------------------------------------ candidat choisi
    def candidat(self) -> appariement.Candidat | None:
        lignes = self.t_candidats.selectionModel().selectedRows()
        if not lignes:
            return None
        i = self.t_candidats.item(lignes[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        return self.candidats[i] if i is not None and i < len(self.candidats) else None

    def _candidat_change(self) -> None:
        c = self.candidat()
        self.b_confirmer.setEnabled(c is not None)
        self.b_page.setEnabled(bool(c and c.url))
        self.photo_off.setVisible(bool(c and c.source == "off" and c.brut.get("image_front_url")))
        self.photo_off.setChecked(self.photo_off.isVisible() and self.vin_id is not None
                                  and self.cave.image_principale(self.vin_id) is None)
        if c is None:
            self.explication.clear()
            self.fiche.clear()
            self.t_champs.setRowCount(0)
            return
        self.explication.setPlainText(appariement.explication_texte(c.raisons, tr))
        self.fiche.setText(self._resume_fiche(c))
        self._champs(c)

    def _resume_fiche(self, c) -> str:
        if c.source == "lwin":
            return tr("ident.credit_lwin", credit=m_lwin.CREDIT, licence=m_lwin.LICENCE)
        if c.source == "off":
            return tr("ident.credit_off", base=off.LICENCE_BASE, images=off.LICENCE_IMAGES)
        f = c.brut
        morceaux = []
        if f.get("fondation"):
            morceaux.append(tr("ident.fondation", annee=f["fondation"]))
        if f.get("coordonnees"):
            lat, lon = f["coordonnees"]
            morceaux.append(tr("ident.coordonnees", lat=f"{lat:.4f}", lon=f"{lon:.4f}"))
        if f.get("proprietaires"):
            morceaux.append(tr("ident.proprietaires", noms=", ".join(f["proprietaires"][:4])))
        wp = f.get("wikipedia_fr" if langue() == "fr" else "wikipedia_en") or f.get("wikipedia_en")
        if wp:
            morceaux.append(f'<a href="{wp}">Wikipedia</a>')
        if f.get("image"):
            morceaux.append(tr("ident.image_commons", fichier=f["image"]))
        morceaux.append(tr("ident.credit_wikidata", licence=wikidata.LICENCE))
        return " · ".join(morceaux)

    def _champs(self, c) -> None:
        if c.source == "wikidata" and c.donnees:
            lignes = self._apercu_producteur(c.donnees)
        elif self.vin_id is not None:
            lignes = appariement.apercu(self.cave, self.vin_id, c.donnees)
        else:
            lignes = [(k, v, None, "remplira") for k, v in c.donnees.items()]
        self.t_champs.setRowCount(len(lignes))
        for i, (champ, propose, actuel, etat) in enumerate(lignes):
            it = _cellule(tr(CHAMPS_LIBELLES.get(champ, "ident.f_champ")), champ)
            if etat == "remplira":
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(Qt.CheckState.Checked)
            self.t_champs.setItem(i, 0, it)
            self.t_champs.setItem(i, 1, _cellule(_valeur_affichee(champ, propose)))
            self.t_champs.setItem(i, 2, _cellule(_valeur_affichee(champ, actuel)))
            self.t_champs.setItem(i, 3, _cellule(tr(ETATS[etat])))
        self.t_champs.resizeColumnsToContents()

    def _apercu_producteur(self, donnees: dict) -> list:
        pid = self.cave.vin(self.vin_id)["producteur_id"] if self.vin_id else None
        p = self.cave.producteur(pid) if pid else None
        sortie = []
        for champ, propose in donnees.items():
            actuel = p[champ] if p is not None else None
            etat = "remplira" if actuel in (None, "") else (
                "identique" if str(actuel) == str(propose) else "deja")
            sortie.append((champ, propose, actuel, etat if p is not None else "deja"))
        return sortie

    def champs_coches(self) -> list[str]:
        sortie = []
        for i in range(self.t_champs.rowCount()):
            it = self.t_champs.item(i, 0)
            if it.flags() & Qt.ItemFlag.ItemIsUserCheckable and it.checkState() == Qt.CheckState.Checked:
                sortie.append(it.data(Qt.ItemDataRole.UserRole))
        return sortie

    # ------------------------------------------------------------------ confirmation
    def confirmer(self) -> None:
        c = self.candidat()
        if c is None:
            return
        champs = self.champs_coches()
        explication = appariement.explication_texte(c.raisons, tr)
        if self.vin_id is None:
            r = self.requete()
            debut = {"millesime": r["millesime"]} if r.get("millesime") else {"cuvee": None}
            self.vin_id = self.cave.enregistrer_vin(debut, None, origine="etiquette")
            self.cree = True
        if c.source == "wikidata":
            self._confirmer_wikidata(c, champs, explication)
            return
        remplis = appariement.confirmer(self.cave, self.vin_id, c, champs, explication)
        self.etat.setText(tr("ident.confirme", n=len(remplis)))
        if c.source == "off" and self.photo_off.isChecked() and c.brut.get("image_front_url"):
            self._photo_off(c)
        else:
            self.accept()

    def _confirmer_wikidata(self, c, champs, explication) -> None:
        objet = getattr(self, "_objet_wd", "producteur")
        pid = self.cave.vin(self.vin_id)["producteur_id"]
        if not demander_accord(self):
            return
        self._occupe(True, tr("ident.telechargement"))
        dossier = self.cave.dossier_images

        def preparer():
            """Lent : crédit et vignette de l'image de Commons (hors transaction)."""
            f = dict(c.brut)
            if f.get("image"):
                credit = wikidata.credit_commons(reseau.client(), f["image"], 800)
                if credit and credit.get("vignette"):
                    corps = reseau.client().get(credit["vignette"]).corps
                    h = hashlib.sha256(corps).hexdigest()
                    rel = f"commons/{h[:16]}{Path(urllib.parse.urlsplit(credit['vignette']).path).suffix.lower() or '.jpg'}"
                    (dossier / rel).parent.mkdir(parents=True, exist_ok=True)
                    (dossier / rel).write_bytes(corps)
                    credit["image_fichier"] = rel
                f["image_credit"] = credit
            return f

        def fini(f):
            self._occupe(False)
            if objet == "producteur" and pid:
                self.cave.enregistrer_fiche("wikidata", c.identifiant, "producteur", f, nom=f.get("nom"),
                                            producteur_id=pid, licence=wikidata.LICENCE, url=c.url)
                self.cave.completer_producteur(pid, {k: v for k, v in c.donnees.items() if k in champs},
                                               "wikidata", f"wikidata:{c.identifiant}")
            else:
                self.cave.enregistrer_fiche("wikidata", c.identifiant, objet, f, nom=f.get("nom"),
                                            vin_id=self.vin_id, licence=wikidata.LICENCE, url=c.url)
            self.cave.retenir_identifiant(self.vin_id, f"wikidata_{objet}", c.identifiant, c.score,
                                          explication)
            self.accept()
        self._travail = travail.lancer(preparer, fini=fini, echec=self._echec, parent=self)

    def _photo_off(self, c) -> None:
        """Photo du produit d'Open Food Facts (CC BY-SA, crédit enregistré) :
        téléchargée dans un fil, inscrite ensuite."""
        url = c.brut.get("image_front_url")
        self._occupe(True, tr("ident.telechargement"))

        def fini(corps):
            with tempfile.TemporaryDirectory() as tmp:
                chemin = Path(tmp) / ("off" + (Path(urllib.parse.urlsplit(url).path).suffix or ".jpg"))
                chemin.write_bytes(corps)
                self.cave.ajouter_image(chemin, vin_id=self.vin_id, type_image="bouteille",
                                        origine="off", credit=off.CREDIT, licence=off.LICENCE_IMAGES,
                                        url_source=c.url, principale=True)
            self._occupe(False)
            self.accept()

        def rate(_e):
            self._occupe(False)
            self.accept()
        self._travail = travail.lancer(lambda: reseau.client().get(url).corps, fini=fini, echec=rate,
                                       parent=self)

    # ------------------------------------------------------------------ navigateur
    def _page(self) -> None:
        c = self.candidat()
        if c and c.url:
            QDesktopServices.openUrl(QUrl(c.url))

    def _web(self, site: str) -> None:
        """Ouvre seulement une recherche dans le navigateur : ni Vivino ni
        Wine-Searcher n'ont d'API publique, et on ne les aspire pas."""
        r = self.requete()
        q = " ".join(str(x) for x in (r["producteur"], r["cuvee"], r["appellation"], r["millesime"]) if x)
        if not q:
            return
        if site == "vivino":
            url = "https://www.vivino.com/search/wines?q=" + urllib.parse.quote(q)
        else:
            url = "https://www.wine-searcher.com/find/" + urllib.parse.quote(q.replace(" ", "+"), safe="+")
        QDesktopServices.openUrl(QUrl(url))
