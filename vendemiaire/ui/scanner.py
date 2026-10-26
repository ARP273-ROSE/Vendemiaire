# -*- coding: utf-8 -*-
"""Scanner une bouteille : code QR d'étiquette de casier ou code-barres EAN,
lu sur l'image de la webcam (décodage local zxing-cpp), sur une photo, ou tapé
(une douchette USB « tape » le code au clavier). Code interne -> la bouteille,
prête à sortir ; EAN -> les vins de la cave qui portent ce code."""
from __future__ import annotations

import time
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QPushButton, QVBoxLayout)

from .. import codes
from ..i18n import lib, tr

FILTRE_IMAGES = "(*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff)"
INTERVALLE_S = 0.3


class DialogueScanner(QDialog):
    sortir = pyqtSignal(int)          # bouteille
    voir_vin = pyqtSignal(int)
    ean_inconnu = pyqtSignal(str)

    def __init__(self, cave, parent=None, camera: bool = True):
        super().__init__(parent)
        self.cave = cave
        self.setWindowTitle(tr("scan.titre"))
        self.resize(880, 720)
        self._dernier = 0.0
        self._pause = False
        self.bouteille_id: int | None = None
        racine = QVBoxLayout(self)
        self.vue = QLabel(tr("webcam.attente"))
        self.vue.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vue.setMinimumSize(640, 360)
        racine.addWidget(self.vue, 1)
        ligne = QHBoxLayout()
        self.code = QLineEdit()
        self.code.setPlaceholderText(tr("scan.code_aide"))
        self.b_image = QPushButton(tr("scan.image"))
        ligne.addWidget(self.code, 1)
        ligne.addWidget(self.b_image)
        racine.addLayout(ligne)
        self.resultat = QLabel()
        self.resultat.setWordWrap(True)
        self.resultat.setObjectName("sous_titre")
        racine.addWidget(self.resultat)
        self.vins = QListWidget()
        self.vins.setMaximumHeight(120)
        self.vins.hide()
        racine.addWidget(self.vins)
        b = QHBoxLayout()
        self.b_sortir = QPushButton(tr("scan.sortir"))
        self.b_sortir.setObjectName("principal")
        self.b_fiche = QPushButton(tr("scan.fiche"))
        self.b_continuer = QPushButton(tr("scan.continuer"))
        fermer = QPushButton(tr("regles.fermer"))
        for x in (self.b_sortir, self.b_fiche, self.b_continuer):
            x.setEnabled(False)
            b.addWidget(x)
        b.addStretch(1)
        b.addWidget(fermer)
        racine.addLayout(b)
        self.code.returnPressed.connect(lambda: self.traiter(self.code.text()))
        self.b_image.clicked.connect(self.depuis_image)
        self.b_sortir.clicked.connect(self._sortir)
        self.b_fiche.clicked.connect(self._fiche)
        self.b_continuer.clicked.connect(self.continuer)
        self.vins.itemDoubleClicked.connect(lambda it: self.voir_vin.emit(it.data(Qt.ItemDataRole.UserRole)))
        fermer.clicked.connect(self.reject)
        self.camera = None
        if not codes.lecture_disponible():
            self.vue.setText(tr("scan.zxing_absent"))
        elif camera:
            self._demarrer_camera()
        else:
            self.vue.setText(tr("webcam.aucune"))
        self.code.setFocus()

    def _demarrer_camera(self) -> None:
        try:
            from PyQt6.QtMultimedia import QCamera, QMediaCaptureSession, QMediaDevices, QVideoSink
            entrees = QMediaDevices.videoInputs()
            if not entrees:
                raise RuntimeError("aucune caméra")
            self.camera = QCamera(entrees[0])
            self.session = QMediaCaptureSession()
            self.session.setCamera(self.camera)
            self.puits = QVideoSink()
            self.session.setVideoSink(self.puits)
            self.puits.videoFrameChanged.connect(self._trame)
            self.camera.start()
        except Exception:
            self.camera = None
            self.vue.setText(tr("scan.sans_camera"))

    def _trame(self, trame) -> None:
        img = trame.toImage()
        if img.isNull():
            return
        self.vue.setPixmap(QPixmap.fromImage(img).scaled(self.vue.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                                         Qt.TransformationMode.FastTransformation))
        maintenant = time.monotonic()
        if self._pause or maintenant - self._dernier < INTERVALLE_S:
            return
        self._dernier = maintenant
        lus = codes.lire_qimage(img.scaledToWidth(min(img.width(), 1280)))
        if lus:
            self.traiter_codes(lus)

    def depuis_image(self) -> None:
        chemin, _ = QFileDialog.getOpenFileName(self, tr("scan.image"), str(Path.home()), FILTRE_IMAGES)
        if chemin:
            self.lire_fichier(chemin)

    def lire_fichier(self, chemin: str) -> None:
        lus = codes.lire_fichier(chemin) if codes.lecture_disponible() else []
        if not lus:
            self.resultat.setText(tr("scan.rien"))
            return
        self.traiter_codes(lus)

    def traiter_codes(self, lus: list) -> None:
        interne = next((c for c in lus if c.interne), None)
        self.traiter((interne or lus[0]).texte)

    def traiter(self, texte: str) -> None:
        texte = (texte or "").strip()
        if not texte:
            return
        self.code.setText(texte)
        self._pause = True
        self.b_continuer.setEnabled(True)
        self.vins.clear()
        self.vins.hide()
        b = self.cave.bouteille_par_code(texte)
        if b is not None:
            self.bouteille_id = b["id"]
            lieu = " › ".join(self.cave.chemin_emplacement(b["emplacement_id"]))
            if b["rangee"]:
                lieu += " · " + tr("scan.case", r=b["rangee"], c=b["colonne"] or "?")
            self.resultat.setText(tr("scan.trouvee", vin=self.cave.nom_vin(b["vin_id"]), statut=lib("statut", b["statut"]),
                                     lieu=lieu or "—"))
            self.b_sortir.setEnabled(b["statut"] == "en_cave")
            self.b_fiche.setEnabled(True)
            return
        self.bouteille_id = None
        self.b_sortir.setEnabled(False)
        chiffres = "".join(ch for ch in texte if ch.isdigit())
        if chiffres and len(chiffres) in (8, 12, 13, 14):
            vins = self.cave.base.lire("SELECT id FROM vin WHERE ean=? OR ean=?", (chiffres, chiffres.lstrip("0")))
            if vins:
                self.resultat.setText(tr("scan.ean_cave", ean=chiffres, n=len(vins)))
                for v in vins:
                    it = QListWidgetItem(self.cave.nom_vin(v["id"]))
                    it.setData(Qt.ItemDataRole.UserRole, v["id"])
                    self.vins.addItem(it)
                self.vins.show()
                self.vins.setCurrentRow(0)
                self.b_fiche.setEnabled(True)
            else:
                self.resultat.setText(tr("scan.ean_inconnu", ean=chiffres))
                self.b_fiche.setEnabled(False)
                self.ean_inconnu.emit(chiffres)
            return
        self.resultat.setText(tr("scan.inconnu", code=texte))
        self.b_fiche.setEnabled(False)

    def continuer(self) -> None:
        self._pause = False
        self.code.clear()
        self.resultat.clear()
        for x in (self.b_sortir, self.b_fiche, self.b_continuer):
            x.setEnabled(False)

    def _sortir(self) -> None:
        if self.bouteille_id:
            self.sortir.emit(self.bouteille_id)
            self.continuer()

    def _fiche(self) -> None:
        if self.bouteille_id:
            b = self.cave.bouteille(self.bouteille_id)
            self.voir_vin.emit(b["vin_id"])
        elif self.vins.currentItem():
            self.voir_vin.emit(self.vins.currentItem().data(Qt.ItemDataRole.UserRole))

    def done(self, r):
        if self.camera is not None:
            self.camera.stop()
        super().done(r)
