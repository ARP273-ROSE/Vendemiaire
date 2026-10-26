# -*- coding: utf-8 -*-
"""Bases de référence : copie locale de LWIN, registres d'appellations, accès
au réseau, moteur OCR — état, licences, mises à jour."""
from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QGroupBox, QHBoxLayout, QLabel,
                             QLineEdit, QMessageBox, QProgressDialog, QPushButton, QScrollArea,
                             QVBoxLayout, QWidget)

from .. import ocr, reseau
from ..i18n import date_affichee, tr
from ..mondial import appellations, lwin
from . import travail

FILTRE_LWIN = "LWIN (*.xlsx *.csv)"
PERIODE_LWIN_JOURS = 30
LICENCES_UI = {"inao": "ref.licence_inao", "eambrosia": "ref.licence_eambrosia"}


def importer_lwin(refs, chemin, progression=None) -> int:
    """Dans un fil de fond : sa connexion à references.db est fermée à la fin."""
    try:
        return refs.remplacer_lwin(lwin.lignes_fichier(chemin), source=Path(chemin).name,
                                   progression=progression)
    finally:
        refs.fermer()


def telecharger_lwin(refs, url: str) -> int:
    """Lien direct donné par Liv-ex : téléchargement (réseau) puis import."""
    corps = reseau.client().get(url).corps
    suffixe = ".csv" if url.lower().split("?")[0].endswith(".csv") else ".xlsx"
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / f"lwin{suffixe}"
        f.write_bytes(corps)
        try:
            n = refs.remplacer_lwin(lwin.lignes_fichier(f), source=url)
        finally:
            refs.fermer()
    return n


def mise_a_jour_lwin_due() -> str | None:
    """Lien direct à rafraîchir si l'utilisateur a demandé la mise à jour
    périodique et que la dernière a plus de 30 jours."""
    s = QSettings()
    url = s.value("lwin/url", "") or ""
    if not url or not s.value("lwin/periodique", False, type=bool) or not reseau.autorise():
        return None
    derniere = s.value("lwin/derniere_verif", "") or ""
    try:
        if derniere and datetime.fromisoformat(derniere) > datetime.now() - timedelta(days=PERIODE_LWIN_JOURS):
            return None
    except ValueError:
        pass
    return url


class DialogueReferences(QDialog):
    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        self.refs = cave.references
        self._travail = None
        self.setWindowTitle(tr("ref.titre"))
        self.resize(820, 760)
        defil = QScrollArea()
        defil.setWidgetResizable(True)
        corps = QWidget()
        defil.setWidget(corps)
        racine = QVBoxLayout(self)
        racine.addWidget(defil)
        lc = QVBoxLayout(corps)

        # -- LWIN -----------------------------------------------------------------
        g = QGroupBox(tr("ref.lwin"))
        l = QVBoxLayout(g)
        self.etat_lwin = QLabel()
        self.etat_lwin.setWordWrap(True)
        l.addWidget(self.etat_lwin)
        explication = QLabel(tr("ref.lwin_aide"))
        explication.setWordWrap(True)
        explication.setObjectName("legende")
        l.addWidget(explication)
        b = QHBoxLayout()
        self.b_page = QPushButton(tr("ref.lwin_page"))
        self.b_importer = QPushButton(tr("ref.lwin_importer"))
        self.b_importer.setObjectName("principal")
        b.addWidget(self.b_page)
        b.addWidget(self.b_importer)
        b.addStretch(1)
        l.addLayout(b)
        u = QHBoxLayout()
        u.addWidget(QLabel(tr("ref.lwin_url")))
        self.url = QLineEdit(QSettings().value("lwin/url", "") or "")
        self.url.setPlaceholderText(tr("ref.lwin_url_aide"))
        u.addWidget(self.url, 1)
        self.b_maj = QPushButton(tr("ref.lwin_maj"))
        u.addWidget(self.b_maj)
        l.addLayout(u)
        self.periodique = QCheckBox(tr("ref.lwin_periodique", jours=PERIODE_LWIN_JOURS))
        self.periodique.setChecked(QSettings().value("lwin/periodique", False, type=bool))
        l.addWidget(self.periodique)
        licence = QLabel(tr("ref.lwin_licence", credit=lwin.CREDIT, licence=lwin.LICENCE,
                            url=lwin.PAGE_LICENCE))
        licence.setOpenExternalLinks(True)
        licence.setWordWrap(True)
        l.addWidget(licence)
        lc.addWidget(g)

        # -- registres ---------------------------------------------------------------
        g = QGroupBox(tr("ref.registres"))
        l = QVBoxLayout(g)
        self.etat_registres = QLabel()
        self.etat_registres.setWordWrap(True)
        self.etat_registres.setOpenExternalLinks(True)
        l.addWidget(self.etat_registres)
        b = QHBoxLayout()
        self.b_registres = QPushButton(tr("ref.registres_maj"))
        b.addWidget(self.b_registres)
        b.addStretch(1)
        l.addLayout(b)
        lc.addWidget(g)

        # -- réseau ------------------------------------------------------------------
        g = QGroupBox(tr("ref.reseau"))
        l = QVBoxLayout(g)
        self.autorise = QCheckBox(tr("ref.reseau_autorise"))
        self.autorise.setChecked(reseau.autorise())
        l.addWidget(self.autorise)
        aide = QLabel(tr("ref.reseau_aide", ua=reseau.USER_AGENT))
        aide.setWordWrap(True)
        aide.setObjectName("legende")
        l.addWidget(aide)
        lc.addWidget(g)

        # -- OCR et images --------------------------------------------------------------
        g = QGroupBox(tr("ref.ocr"))
        l = QVBoxLayout(g)
        self.etat_ocr = QLabel()
        self.etat_ocr.setWordWrap(True)
        self.etat_ocr.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        l.addWidget(self.etat_ocr)
        b = QHBoxLayout()
        self.b_tesseract = QPushButton(tr("ref.ocr_choisir"))
        b.addWidget(self.b_tesseract)
        b.addStretch(1)
        l.addLayout(b)
        lc.addWidget(g)
        lc.addStretch(1)

        fermer = QPushButton(tr("bouton.fermer"))
        fermer.clicked.connect(self.accept)
        bas = QHBoxLayout()
        bas.addStretch(1)
        bas.addWidget(fermer)
        racine.addLayout(bas)

        self.b_page.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(lwin.PAGE_TELECHARGEMENT)))
        self.b_importer.clicked.connect(self.importer)
        self.b_maj.clicked.connect(self.mettre_a_jour)
        self.periodique.toggled.connect(lambda v: QSettings().setValue("lwin/periodique", v))
        self.url.editingFinished.connect(lambda: QSettings().setValue("lwin/url", self.url.text().strip()))
        self.b_registres.clicked.connect(self.registres_en_ligne)
        self.autorise.toggled.connect(self._autoriser)
        self.b_tesseract.clicked.connect(self.choisir_tesseract)
        self.rafraichir()

    # ------------------------------------------------------------------ état
    def rafraichir(self) -> None:
        n = self.refs.nb_lwin()
        if n:
            self.etat_lwin.setText(tr("ref.lwin_etat", n=n, date=date_affichee(self.refs.meta("lwin_date")),
                                      source=self.refs.meta("lwin_source") or ""))
        else:
            self.etat_lwin.setText(tr("ref.lwin_vide"))
        lignes = []
        for registre, titre in (("inao", "INAO"), ("eambrosia", "eAmbrosia")):
            lignes.append(tr("ref.registre_etat", registre=titre, n=self.refs.nb_appellations(registre),
                             date=date_affichee(self.refs.meta(f"appellations_{registre}_extraction")),
                             licence=tr(LICENCES_UI[registre])))
        self.etat_registres.setText("<br>".join(lignes))
        m = ocr.moteur()
        if m:
            texte = tr("ref.ocr_ok", version=ocr.version() or "?", chemin=m,
                       langues=", ".join(ocr.langues()) or "?")
        else:
            texte = tr("ocr.absent", installer=ocr.installation())
        try:
            import cv2  # noqa: F401
            texte += "\n" + tr("ref.opencv_oui")
        except ImportError:
            texte += "\n" + tr("ref.opencv_non")
        self.etat_ocr.setText(texte)

    def _autoriser(self, oui: bool) -> None:
        reseau.autoriser(oui)
        QSettings().setValue("reseau/autorise", oui)

    # ------------------------------------------------------------------ LWIN
    def _progression(self, titre: str) -> QProgressDialog:
        p = QProgressDialog(titre, "", 0, 0, self)
        p.setCancelButton(None)
        p.setWindowModality(Qt.WindowModality.WindowModal)
        p.setMinimumDuration(0)
        p.show()
        return p

    def importer(self) -> None:
        chemin, _ = QFileDialog.getOpenFileName(self, tr("ref.lwin_importer"), str(Path.home()),
                                                FILTRE_LWIN)
        if not chemin:
            return
        self._lancer(importer_lwin, self.refs, chemin)

    def mettre_a_jour(self) -> None:
        url = self.url.text().strip()
        QSettings().setValue("lwin/url", url)
        if not url:
            QMessageBox.information(self, self.windowTitle(), tr("ref.lwin_url_vide"))
            return
        from .identifier import demander_accord
        if not demander_accord(self):
            return
        self.autorise.setChecked(True)
        self._lancer(telecharger_lwin, self.refs, url, verif=True)

    def _lancer(self, fonction, *args, verif: bool = False) -> None:
        attente = self._progression(tr("ref.lwin_en_cours"))

        def fini(n):
            attente.close()
            if verif:
                QSettings().setValue("lwin/derniere_verif", datetime.now().isoformat(timespec="seconds"))
            self.rafraichir()
            QMessageBox.information(self, self.windowTitle(), tr("ref.lwin_fini", n=n))

        def rate(e):
            attente.close()
            QMessageBox.warning(self, self.windowTitle(), tr("ref.echec", erreur=str(e)[:300]))
        self._travail = travail.lancer(fonction, *args, fini=fini, echec=rate, parent=self)

    # ------------------------------------------------------------------ registres
    def registres_en_ligne(self) -> None:
        from .identifier import demander_accord
        if not demander_accord(self):
            return
        self.autorise.setChecked(True)
        attente = self._progression(tr("ref.registres_en_cours"))

        def fini(faits):
            attente.close()
            self.rafraichir()
            QMessageBox.information(self, self.windowTitle(),
                                    tr("ref.registres_fini", inao=faits.get("inao", 0),
                                       eambrosia=faits.get("eambrosia", 0)))

        def rate(e):
            attente.close()
            QMessageBox.warning(self, self.windowTitle(), tr("ref.echec", erreur=str(e)[:300]))
        self._travail = travail.lancer(appellations.mettre_a_jour_en_ligne, self.refs, reseau.client(),
                                       fini=fini, echec=rate, parent=self)

    # ------------------------------------------------------------------ OCR
    def choisir_tesseract(self) -> None:
        chemin, _ = QFileDialog.getOpenFileName(self, tr("ref.ocr_choisir"), str(Path.home()))
        if chemin:
            QSettings().setValue("ocr/tesseract", chemin)
            ocr.definir_chemin(chemin)
            self.rafraichir()
