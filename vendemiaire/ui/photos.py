# -*- coding: utf-8 -*-
"""Photos d'un vin : import (fichier, glisser-déposer, webcam), recadrage et
redressement automatiques avec réglage à la main, lecture du texte (OCR).

La photo d'origine est toujours gardée ; la version redressée est un autre
fichier, et ses réglages (coins, quarts de tour, déroulage) restent modifiables.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import (QColor, QDesktopServices, QIcon, QImage, QPainter, QPen, QPixmap,
                         QPolygonF)
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                             QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                             QMessageBox, QPlainTextEdit, QPushButton, QSlider, QSplitter,
                             QVBoxLayout, QWidget)

from .. import images, ocr
from ..i18n import lib, nombre, tr
from . import travail

MOTIF_IMAGES = "(*.jpg *.jpeg *.png *.webp *.tif *.tiff *.bmp)"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}


def fichiers_images(mime) -> list[str]:
    """Fichiers images d'un glisser-déposer."""
    if not mime.hasUrls():
        return []
    return [u.toLocalFile() for u in mime.urls()
            if u.isLocalFile() and Path(u.toLocalFile()).suffix.lower() in EXTENSIONS]


# ---------------------------------------------------------------- coins à la main
class VueCoins(QWidget):
    """La photo, et quatre poignées à déplacer pour cerner l'étiquette."""
    change = pyqtSignal()
    RAYON = 9

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image: QImage | None = None
        self.coins: list[tuple[float, float]] | None = None
        self._prise: int | None = None
        self.setMinimumSize(420, 420)
        self.setMouseTracking(True)

    def definir(self, image: QImage, coins) -> None:
        self.image = image
        self.coins = [tuple(c) for c in coins] if coins else None
        self.update()

    def _cadre(self) -> tuple[float, float, float]:
        if self.image is None or self.image.isNull():
            return 1.0, 0.0, 0.0
        e = min(self.width() / self.image.width(), self.height() / self.image.height())
        return e, (self.width() - self.image.width() * e) / 2, (self.height() - self.image.height() * e) / 2

    def _ecran(self, p) -> QPointF:
        e, dx, dy = self._cadre()
        return QPointF(dx + p[0] * e, dy + p[1] * e)

    def _image(self, pos) -> tuple[float, float]:
        e, dx, dy = self._cadre()
        x = min(max((pos.x() - dx) / e, 0), self.image.width())
        y = min(max((pos.y() - dy) / e, 0), self.image.height())
        return (x, y)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#1E1517"))
        if self.image is None or self.image.isNull():
            return
        e, dx, dy = self._cadre()
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawImage(QRectF(dx, dy, self.image.width() * e, self.image.height() * e), self.image)
        if not self.coins:
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        poly = QPolygonF([self._ecran(c) for c in self.coins])
        p.setPen(QPen(QColor("#F3D58A"), 2))
        p.drawPolygon(poly)
        for i, c in enumerate(self.coins):
            p.setBrush(QColor("#C99A3B") if i != self._prise else QColor("#FFFFFF"))
            p.drawEllipse(self._ecran(c), self.RAYON, self.RAYON)

    def mousePressEvent(self, ev):
        if not self.coins:
            return
        pos = ev.position()
        proches = [(abs(self._ecran(c).x() - pos.x()) + abs(self._ecran(c).y() - pos.y()), i)
                   for i, c in enumerate(self.coins)]
        d, i = min(proches)
        self._prise = i if d < 4 * self.RAYON else None

    def mouseMoveEvent(self, ev):
        if self._prise is not None and self.coins:
            self.coins[self._prise] = self._image(ev.position())
            self.update()

    def mouseReleaseEvent(self, _ev):
        if self._prise is not None:
            self._prise = None
            self.update()
            self.change.emit()


class DialogueRetouche(QDialog):
    """Recadrer, redresser, dérouler une photo ; lire son texte. Résultat :
    `resultat` (QImage), `retouche` (images.Retouche), `type_image`, `texte_ocr`."""

    def __init__(self, image: QImage, retouche: images.Retouche | None = None,
                 type_image: str = "etiquette", parent=None, detecter: bool = True):
        super().__init__(parent)
        self.setWindowTitle(tr("retouche.titre"))
        self.resize(1180, 760)
        self.originale = image
        self.retouche = retouche or images.Retouche()
        self.resultat: QImage | None = None
        self.texte_ocr: str | None = None
        self.lignes_principales: list[str] = []
        self._travail = None
        racine = QVBoxLayout(self)
        haut = QSplitter()
        gauche = QWidget()
        lg = QVBoxLayout(gauche)
        self.vue = VueCoins()
        lg.addWidget(self.vue, 1)
        self.aide = QLabel(tr("retouche.aide"))
        self.aide.setWordWrap(True)
        self.aide.setObjectName("legende")
        lg.addWidget(self.aide)
        haut.addWidget(gauche)
        droite = QWidget()
        ld = QVBoxLayout(droite)
        self.apercu = QLabel()
        self.apercu.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.apercu.setMinimumSize(300, 380)
        ld.addWidget(self.apercu, 1)
        haut.addWidget(droite)
        haut.setSizes([700, 460])
        racine.addWidget(haut, 1)

        outils = QHBoxLayout()
        self.b_detecter = QPushButton(tr("retouche.detecter"))
        self.b_tout = QPushButton(tr("retouche.tout"))
        self.b_gauche = QPushButton(tr("retouche.gauche"))
        self.b_droite = QPushButton(tr("retouche.droite"))
        for b in (self.b_detecter, self.b_tout, self.b_gauche, self.b_droite):
            outils.addWidget(b)
        outils.addWidget(QLabel(tr("retouche.deroulage")))
        self.courbure = QSlider(Qt.Orientation.Horizontal)
        self.courbure.setRange(0, 100)
        self.courbure.setValue(int(self.retouche.courbure * 100))
        self.courbure.setMaximumWidth(180)
        outils.addWidget(self.courbure)
        outils.addWidget(QLabel(tr("retouche.type")))
        self.type = QComboBox()
        for code in ("etiquette", "contre_etiquette", "capsule", "caisse", "bouteille", "autre"):
            self.type.addItem(lib("image", code), code)
        self.type.setCurrentIndex(max(0, self.type.findData(type_image)))
        outils.addWidget(self.type)
        outils.addStretch(1)
        racine.addLayout(outils)

        ocr_ligne = QHBoxLayout()
        self.b_ocr = QPushButton(tr("retouche.lire"))
        self.etat = QLabel()
        self.etat.setObjectName("legende")
        self.etat.setWordWrap(True)
        ocr_ligne.addWidget(self.b_ocr)
        ocr_ligne.addWidget(self.etat, 1)
        racine.addLayout(ocr_ligne)
        self.texte = QPlainTextEdit()
        self.texte.setPlaceholderText(tr("retouche.texte_aide"))
        self.texte.setMaximumHeight(90)
        racine.addWidget(self.texte)

        boutons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        boutons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("bouton.enregistrer"))
        boutons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("bouton.annuler"))
        boutons.accepted.connect(self.accepter)
        boutons.rejected.connect(self.reject)
        racine.addWidget(boutons)

        self.b_detecter.clicked.connect(self.detecter)
        self.b_tout.clicked.connect(self.tout)
        self.b_gauche.clicked.connect(lambda: self.tourner(-1))
        self.b_droite.clicked.connect(lambda: self.tourner(1))
        self.courbure.valueChanged.connect(lambda _v: self._minuteur.start())
        self.vue.change.connect(self.rafraichir_apercu)
        self.b_ocr.clicked.connect(self.lire_texte)
        self._minuteur = QTimer(self)
        self._minuteur.setSingleShot(True)
        self._minuteur.setInterval(150)
        self._minuteur.timeout.connect(self.rafraichir_apercu)
        if not ocr.moteur():
            self.b_ocr.setEnabled(False)
            self.etat.setText(tr("ocr.absent", installer=ocr.installation()))

        self._tournee = images.pivoter(self.originale, self.retouche.quarts)
        if self.retouche.coins:
            self.vue.definir(self._tournee, self.retouche.coins)
            self.rafraichir_apercu()
        elif detecter:
            self.detecter()
        else:
            self.tout()

    # -- réglages ------------------------------------------------------------
    def tout(self) -> None:
        w, h = self._tournee.width(), self._tournee.height()
        self.vue.definir(self._tournee, [(0, 0), (w, 0), (w, h), (0, h)])
        self.retouche.auto = False
        self.rafraichir_apercu()

    def detecter(self) -> None:
        d = images.detecter_etiquette(self._tournee)
        if d is None:
            self.etat.setText(tr("retouche.rien_trouve"))
            self.tout()
            return
        self.vue.definir(self._tournee, d.coins)
        self.retouche.auto = True
        self.etat.setText(tr("retouche.trouve", pct=int(d.confiance * 100), methode=d.methode))
        self.rafraichir_apercu()

    def tourner(self, sens: int) -> None:
        self.retouche.quarts = (self.retouche.quarts + sens) % 4
        self._tournee = images.pivoter(self.originale, self.retouche.quarts)
        self.detecter()

    def _retouche_courante(self) -> images.Retouche:
        r = self.retouche
        coins = self.vue.coins
        w, h = self._tournee.width(), self._tournee.height()
        if coins and [tuple(map(round, c)) for c in coins] == [(0, 0), (w, 0), (w, h), (0, h)]:
            coins = None                                  # toute la photo : pas de perspective
        return images.Retouche(coins=coins, quarts=r.quarts,
                               courbure=self.courbure.value() / 100, auto=r.auto, extra=r.extra)

    def rafraichir_apercu(self) -> None:
        try:
            self.resultat = images.appliquer(self.originale, self._retouche_courante())
        except ValueError:
            return
        pm = QPixmap.fromImage(self.resultat).scaled(
            self.apercu.size() - QSize(8, 8), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        self.apercu.setPixmap(pm)

    # -- OCR ------------------------------------------------------------------
    def lire_texte(self) -> None:
        if self.resultat is None:
            self.rafraichir_apercu()
        self.b_ocr.setEnabled(False)
        self.etat.setText(tr("ocr.en_cours"))
        self._travail = travail.lancer(ocr.lire, self.resultat.copy(), fini=self._texte_lu,
                                       echec=self._ocr_rate, parent=self)

    def _texte_lu(self, r) -> None:
        self.b_ocr.setEnabled(True)
        self.texte_ocr = r.texte
        self.lignes_principales = r.lignes_principales()
        self.texte.setPlainText(r.texte)
        self.etat.setText(tr("ocr.fini", n=len(r.mots), duree=nombre(r.duree, 1), moteur=r.moteur))

    def _ocr_rate(self, e) -> None:
        self.b_ocr.setEnabled(True)
        self.etat.setText(tr("ocr.echec", erreur=str(e)[:200]))

    def accepter(self) -> None:
        self.rafraichir_apercu()
        self.retouche = self._retouche_courante()
        self.type_image = self.type.currentData()
        if self.texte.toPlainText().strip():
            self.texte_ocr = self.texte.toPlainText()
        if self.resultat is None:
            return
        self.accept()


# ---------------------------------------------------------------- webcam
class DialogueWebcam(QDialog):
    """Prendre une photo avec la webcam (si l'ordinateur en a une)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("webcam.titre"))
        self.resize(820, 640)
        self.image: QImage | None = None
        racine = QVBoxLayout(self)
        self.vue = QLabel(tr("webcam.attente"))
        self.vue.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vue.setMinimumSize(640, 480)
        racine.addWidget(self.vue, 1)
        boutons = QHBoxLayout()
        self.b_prendre = QPushButton(tr("webcam.prendre"))
        self.b_prendre.setObjectName("principal")
        self.b_annuler = QPushButton(tr("bouton.annuler"))
        boutons.addStretch(1)
        boutons.addWidget(self.b_prendre)
        boutons.addWidget(self.b_annuler)
        racine.addLayout(boutons)
        self.b_annuler.clicked.connect(self.reject)
        self.b_prendre.clicked.connect(self.prendre)
        self._derniere: QImage | None = None
        self.camera = None
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
            self.puits.videoFrameChanged.connect(self._image_recue)
            self.camera.start()
        except Exception:
            self.vue.setText(tr("webcam.aucune"))
            self.b_prendre.setEnabled(False)

    @staticmethod
    def disponible() -> bool:
        try:
            from PyQt6.QtMultimedia import QMediaDevices
            return bool(QMediaDevices.videoInputs())
        except Exception:
            return False

    def _image_recue(self, trame) -> None:
        img = trame.toImage()
        if img.isNull():
            return
        self._derniere = img
        self.vue.setPixmap(QPixmap.fromImage(img).scaled(
            self.vue.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))

    def prendre(self) -> None:
        if self._derniere is not None:
            self.image = self._derniere.copy()
            self.accept()

    def done(self, r):
        if self.camera is not None:
            self.camera.stop()
        super().done(r)


# ---------------------------------------------------------------- photos d'un vin
def enregistrer_retouche(cave, d: DialogueRetouche, original: str | Path | None, vin_id: int,
                         image_id: int | None = None) -> int:
    """Écrit la version redressée (fichier temporaire, puis copie par la cave) et
    l'inscrit ; l'original est gardé tel quel."""
    with tempfile.TemporaryDirectory() as tmp:
        traite = images.enregistrer(d.resultat, Path(tmp) / "etiquette.jpg")
        if original is None:
            original = images.enregistrer(d.originale, Path(tmp) / "original.jpg")
        if image_id is not None:
            cave.retoucher_image(image_id, traite, d.retouche.json(), d.texte_ocr)
            if d.type_image != cave.image(image_id)["type"]:
                cave.changer_type_image(image_id, d.type_image)
            return image_id
        deja = cave.base.valeur("SELECT COUNT(*) FROM image WHERE vin_id=? AND type=?",
                                (vin_id, d.type_image))
        return cave.ajouter_image(traite, vin_id=vin_id, type_image=d.type_image, origine="perso",
                                  principale=not deja or d.type_image == "etiquette",
                                  original=original, retouche=d.retouche.json(),
                                  texte_ocr=d.texte_ocr)


class DialoguePhotos(QDialog):
    """Toutes les images d'un vin : étiquette, contre-étiquette, capsule, caisse…"""
    identifier_demande = pyqtSignal(object)            # (vin_id, texte lu)

    def __init__(self, cave, vin_id: int, parent=None):
        super().__init__(parent)
        self.cave = cave
        self.vin_id = vin_id
        self.modifie = False
        self.setWindowTitle(tr("photos.titre", vin=cave.nom_vin(vin_id)))
        self.resize(900, 620)
        self.setAcceptDrops(True)
        racine = QVBoxLayout(self)
        aide = QLabel(tr("photos.aide"))
        aide.setObjectName("legende")
        aide.setWordWrap(True)
        racine.addWidget(aide)
        self.liste = QListWidget()
        self.liste.setViewMode(QListWidget.ViewMode.IconMode)
        self.liste.setIconSize(QSize(150, 200))
        self.liste.setGridSize(QSize(190, 270))
        self.liste.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.liste.setMovement(QListWidget.Movement.Static)
        self.liste.setWordWrap(True)
        self.liste.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        racine.addWidget(self.liste, 1)
        self.credit = QLabel()
        self.credit.setWordWrap(True)
        self.credit.setObjectName("legende")
        self.credit.setOpenExternalLinks(True)
        racine.addWidget(self.credit)
        b = QHBoxLayout()
        self.b_fichier = QPushButton(tr("photos.fichier"))
        self.b_webcam = QPushButton(tr("photos.webcam"))
        self.b_retoucher = QPushButton(tr("photos.retoucher"))
        self.b_principale = QPushButton(tr("photos.principale"))
        self.b_identifier = QPushButton(tr("photos.identifier"))
        self.b_supprimer = QPushButton(tr("photos.supprimer"))
        self.b_fermer = QPushButton(tr("bouton.fermer"))
        for w in (self.b_fichier, self.b_webcam, self.b_retoucher, self.b_principale,
                  self.b_identifier, self.b_supprimer):
            b.addWidget(w)
        b.addStretch(1)
        b.addWidget(self.b_fermer)
        racine.addLayout(b)
        self.b_webcam.setEnabled(DialogueWebcam.disponible())
        if not self.b_webcam.isEnabled():
            self.b_webcam.setToolTip(tr("webcam.aucune"))
        self.b_fichier.clicked.connect(self.depuis_fichier)
        self.b_webcam.clicked.connect(self.depuis_webcam)
        self.b_retoucher.clicked.connect(self.retoucher)
        self.b_principale.clicked.connect(self.principale)
        self.b_supprimer.clicked.connect(self.supprimer)
        self.b_identifier.clicked.connect(self.identifier)
        self.b_fermer.clicked.connect(self.accept)
        self.liste.itemSelectionChanged.connect(self._etat)
        self.liste.itemDoubleClicked.connect(lambda _i: self.retoucher())
        self.rafraichir()

    def rafraichir(self) -> None:
        choisi = self.image_choisie()
        self.liste.clear()
        for im in self.cave.images(self.vin_id):
            chemin = self.cave.chemin_image(im["fichier"])
            v = images.vignette(chemin, 300, 400, self.cave.dossier_vignettes) if chemin else None
            texte = lib("image", im["type"])
            if im["principale"]:
                texte += " ★"
            if im["origine"] != "perso":
                texte += f"\n{im['origine']}"
            it = QListWidgetItem(QIcon(QPixmap(str(v))) if v else QIcon(), texte)
            it.setData(Qt.ItemDataRole.UserRole, im["id"])
            it.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.liste.addItem(it)
            if im["id"] == choisi:
                it.setSelected(True)
        if not self.liste.selectedItems() and self.liste.count():
            self.liste.item(0).setSelected(True)
        self._etat()

    def image_choisie(self) -> int | None:
        it = self.liste.selectedItems() if hasattr(self, "liste") else []
        return it[0].data(Qt.ItemDataRole.UserRole) if it else None

    def _etat(self) -> None:
        iid = self.image_choisie()
        im = self.cave.image(iid) if iid else None
        for w in (self.b_retoucher, self.b_principale, self.b_supprimer, self.b_identifier):
            w.setEnabled(im is not None)
        if im is None:
            self.credit.clear()
            return
        morceaux = []
        if im["credit"] or im["licence"]:
            morceaux.append(tr("photos.credit", credit=im["credit"] or "?", licence=im["licence"] or "?"))
        if im["url_source"]:
            morceaux.append(f'<a href="{im["url_source"]}">{tr("photos.source")}</a>')
        if im["fichier_original"]:
            morceaux.append(tr("photos.original_garde"))
        if im["texte_ocr"]:
            morceaux.append(tr("photos.texte_lu", texte=" ".join(im["texte_ocr"].split())[:160]))
        self.credit.setText(" · ".join(morceaux))

    # -- ajouts ---------------------------------------------------------------
    def depuis_fichier(self) -> None:
        chemin, _ = QFileDialog.getOpenFileName(self, tr("dialogue.photo"), str(Path.home()),
                                                tr("filtre.images") + " " + MOTIF_IMAGES)
        if chemin:
            self.ajouter_fichier(chemin)

    def ajouter_fichier(self, chemin: str, type_image: str = "etiquette") -> int | None:
        try:
            img = images.charger(chemin)
        except ValueError as e:
            QMessageBox.warning(self, self.windowTitle(), str(e))
            return None
        d = DialogueRetouche(img, type_image=type_image, parent=self)
        if d.exec() != QDialog.DialogCode.Accepted:
            return None
        iid = enregistrer_retouche(self.cave, d, chemin, self.vin_id)
        self._apres_modif()
        return iid

    def depuis_webcam(self) -> None:
        w = DialogueWebcam(self)
        if w.exec() != QDialog.DialogCode.Accepted or w.image is None:
            return
        d = DialogueRetouche(w.image, parent=self)
        if d.exec() == QDialog.DialogCode.Accepted:
            enregistrer_retouche(self.cave, d, None, self.vin_id)
            self._apres_modif()

    def retoucher(self) -> None:
        iid = self.image_choisie()
        im = self.cave.image(iid) if iid else None
        if im is None:
            return
        source = self.cave.chemin_image(im["fichier_original"]) or self.cave.chemin_image(im["fichier"])
        if source is None:
            return
        d = DialogueRetouche(images.charger(source), images.Retouche.depuis_json(im["retouche"]),
                             im["type"], self, detecter=not im["fichier_original"])
        if im["texte_ocr"]:
            d.texte.setPlainText(im["texte_ocr"])
        if d.exec() == QDialog.DialogCode.Accepted:
            enregistrer_retouche(self.cave, d, None, self.vin_id, image_id=iid)
            self._apres_modif()

    def principale(self) -> None:
        iid = self.image_choisie()
        if iid:
            self.cave.definir_principale(iid)
            self._apres_modif()

    def supprimer(self) -> None:
        iid = self.image_choisie()
        if iid and QMessageBox.question(self, self.windowTitle(), tr("photos.supprimer_q")) \
                == QMessageBox.StandardButton.Yes:
            self.cave.supprimer_image(iid)
            self._apres_modif()

    def identifier(self) -> None:
        iid = self.image_choisie()
        im = self.cave.image(iid) if iid else None
        if im is not None:
            self.identifier_demande.emit((self.vin_id, im["texte_ocr"] or ""))

    def _apres_modif(self) -> None:
        from .pochette import vider_cache
        vider_cache()
        self.modifie = True
        self.rafraichir()

    # -- glisser-déposer -------------------------------------------------------
    def dragEnterEvent(self, ev):
        if fichiers_images(ev.mimeData()):
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        for f in fichiers_images(ev.mimeData()):
            self.ajouter_fichier(f)
        ev.acceptProposedAction()


def ouvrir_url(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))
