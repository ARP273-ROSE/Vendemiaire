# -*- coding: utf-8 -*-
"""Photos d'étiquette : recadrage et redressement automatiques, déroulage,
vignettes en cache disque.

Tout se fait avec Qt (QImage, QTransform) et du Python pur : aucune
bibliothèque de plus à embarquer sur les trois systèmes. Si OpenCV est
installé (facultatif, `opencv-python-headless`), la détection des bords
l'utilise ; sinon elle suit la méthode ci-dessous, suffisante pour une
étiquette claire sur une bouteille ou un fond plus sombres (cas courant) — et
le réglage à la main reste toujours possible.

Détection sans OpenCV, sur une copie réduite à 320 pixels :
1. niveaux de gris, flou 3×3, seuil d'Otsu ;
2. pour chaque polarité (étiquette claire ou sombre), plus grande zone d'un
   seul tenant qui ne longe pas le bord de la photo ;
3. enveloppe convexe de la zone, simplifiée à 4 sommets (on retire tour à tour
   le sommet qui porte le plus petit triangle : les vrais coins restent) ;
4. confiance = surface de la zone / surface du quadrilatère.

La photo d'origine n'est JAMAIS modifiée : la version redressée est un autre
fichier, et les réglages (coins, quarts de tour, déroulage) sont gardés pour
pouvoir tout reprendre.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QImage, QImageReader, QPainter, QPolygonF, QTransform

TAILLE_ANALYSE = 320
COTE_MAX = 2400               # côté le plus long de la version redressée (poids maîtrisé)
QUALITE_JPEG = 90


@dataclass
class Detection:
    coins: list[tuple[float, float]]      # haut-gauche, haut-droit, bas-droit, bas-gauche (pixels)
    confiance: float
    methode: str                          # « qt » ou « opencv »


@dataclass
class Retouche:
    """Réglages appliqués à une photo (gardés en JSON avec l'image)."""
    coins: list[tuple[float, float]] | None = None
    quarts: int = 0                       # quarts de tour, sens horaire, appliqués EN PREMIER
    courbure: float = 0.0                 # 0 = plat ; 1 = étiquette très enroulée
    auto: bool = False                    # coins trouvés par la détection
    extra: dict = field(default_factory=dict)

    def json(self) -> str:
        return json.dumps({"coins": self.coins, "quarts": self.quarts, "courbure": self.courbure,
                           "auto": self.auto, **self.extra}, ensure_ascii=False)

    @classmethod
    def depuis_json(cls, texte: str | None) -> "Retouche":
        try:
            d = json.loads(texte or "{}")
        except ValueError:
            d = {}
        coins = d.pop("coins", None)
        return cls(coins=[tuple(c) for c in coins] if coins else None, quarts=int(d.pop("quarts", 0)),
                   courbure=float(d.pop("courbure", 0.0)), auto=bool(d.pop("auto", False)), extra=d)


# ---------------------------------------------------------------- chargement
def charger(chemin: str | Path) -> QImage:
    """Lit une image en respectant l'orientation EXIF des téléphones."""
    r = QImageReader(str(chemin))
    r.setAutoTransform(True)
    img = r.read()
    if img.isNull():
        raise ValueError(f"image illisible : {chemin} ({r.errorString()})")
    return img


def pivoter(img: QImage, quarts: int) -> QImage:
    q = quarts % 4
    if not q:
        return img
    return img.transformed(QTransform().rotate(90 * q), Qt.TransformationMode.SmoothTransformation)


# ---------------------------------------------------------------- détection
def _gris(img: QImage, cote: int) -> tuple[bytearray, int, int, float]:
    echelle = cote / max(img.width(), img.height())
    petit = img.scaled(max(1, round(img.width() * echelle)), max(1, round(img.height() * echelle)),
                       Qt.AspectRatioMode.IgnoreAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    g = petit.convertToFormat(QImage.Format.Format_Grayscale8)
    w, h, pas = g.width(), g.height(), g.bytesPerLine()
    brut = g.constBits()
    brut.setsize(pas * h)
    octets = bytes(brut)
    data = bytearray(w * h)
    for y in range(h):
        data[y * w:(y + 1) * w] = octets[y * pas:y * pas + w]
    return data, w, h, echelle


def _flou(data: bytearray, w: int, h: int) -> bytearray:
    """Flou 3×3 (moyenne), séparable."""
    tmp = bytearray(w * h)
    for y in range(h):
        ligne = data[y * w:(y + 1) * w]
        for x in range(w):
            a = ligne[x - 1] if x else ligne[x]
            b = ligne[x + 1] if x < w - 1 else ligne[x]
            tmp[y * w + x] = (a + ligne[x] + b) // 3
    sortie = bytearray(w * h)
    for y in range(h):
        haut = (y - 1 if y else y) * w
        bas = (y + 1 if y < h - 1 else y) * w
        for x in range(w):
            sortie[y * w + x] = (tmp[haut + x] + tmp[y * w + x] + tmp[bas + x]) // 3
    return sortie


def otsu(data: bytearray) -> int:
    hist = [0] * 256
    for v in data:
        hist[v] += 1
    total = len(data)
    somme = sum(i * n for i, n in enumerate(hist))
    sb = wb = 0
    meilleur, seuil = -1.0, 128
    for t in range(256):
        wb += hist[t]
        if wb == 0:
            continue
        wf = total - wb
        if wf == 0:
            break
        sb += t * hist[t]
        mb, mf = sb / wb, (somme - sb) / wf
        var = wb * wf * (mb - mf) ** 2
        if var > meilleur:
            meilleur, seuil = var, t
    return seuil


def _composantes(masque: bytearray, w: int, h: int) -> list[tuple[int, list[int], int]]:
    """Zones d'un seul tenant (4-voisinage) : (taille, pixels, pixels au bord)."""
    vu = bytearray(w * h)
    zones = []
    for depart in range(w * h):
        if not masque[depart] or vu[depart]:
            continue
        file = deque([depart])
        vu[depart] = 1
        pixels = []
        bord = 0
        while file:
            p = file.popleft()
            pixels.append(p)
            x, y = p % w, p // w
            if x == 0 or y == 0 or x == w - 1 or y == h - 1:
                bord += 1
            for q in ((p - 1) if x else -1, (p + 1) if x < w - 1 else -1,
                      (p - w) if y else -1, (p + w) if y < h - 1 else -1):
                if q >= 0 and masque[q] and not vu[q]:
                    vu[q] = 1
                    file.append(q)
        zones.append((len(pixels), pixels, bord))
    zones.sort(key=lambda z: z[0], reverse=True)
    return zones


def _enveloppe(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Enveloppe convexe (chaîne monotone d'Andrew)."""
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def croix(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    bas, haut = [], []
    for p in pts:
        while len(bas) >= 2 and croix(bas[-2], bas[-1], p) <= 0:
            bas.pop()
        bas.append(p)
    for p in reversed(pts):
        while len(haut) >= 2 and croix(haut[-2], haut[-1], p) <= 0:
            haut.pop()
        haut.append(p)
    return bas[:-1] + haut[:-1]


def _aire(poly) -> float:
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                   for i in range(len(poly)))) / 2


def _quadrilatere(enveloppe: list[tuple[float, float]]) -> list[tuple[float, float]] | None:
    """Simplifie une enveloppe convexe en 4 sommets (Visvalingam)."""
    poly = list(enveloppe)
    if len(poly) < 4:
        return None
    while len(poly) > 4:
        n = len(poly)
        aires = [_aire([poly[i - 1], poly[i], poly[(i + 1) % n]]) for i in range(n)]
        poly.pop(aires.index(min(aires)))
    return ordonner(poly)


def ordonner(coins) -> list[tuple[float, float]]:
    """Ordre haut-gauche, haut-droit, bas-droit, bas-gauche."""
    cx = sum(p[0] for p in coins) / len(coins)
    cy = sum(p[1] for p in coins) / len(coins)
    tries = sorted(coins, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))   # sens horaire (y vers le bas)
    depart = min(range(4), key=lambda i: tries[i][0] + tries[i][1])
    return [tuple(tries[(depart + i) % 4]) for i in range(4)]


def detecter_etiquette(img: QImage) -> Detection | None:
    """Les quatre coins de l'étiquette dans la photo, ou None si rien de net."""
    try:
        return _detecter_opencv(img)
    except ImportError:
        pass
    data, w, h, echelle = _gris(img, TAILLE_ANALYSE)
    data = _flou(data, w, h)
    seuil = otsu(data)
    meilleur: Detection | None = None
    for clair in (True, False):
        masque = bytearray(1 if ((v > seuil) == clair) else 0 for v in data)
        for taille, pixels, bord in _composantes(masque, w, h)[:3]:
            part = taille / (w * h)
            if part < 0.04 or part > 0.97 or bord > 0.25 * (2 * (w + h)):
                continue
            enveloppe = _enveloppe([(p % w, p // w) for p in pixels])
            quad = _quadrilatere(enveloppe)
            if quad is None:
                continue
            aire_quad = _aire(quad)
            if aire_quad <= 0:
                continue
            confiance = min(1.0, taille / aire_quad) * min(1.0, part / 0.08)
            if meilleur is None or confiance > meilleur.confiance:
                coins = [((x + 0.5) / echelle, (y + 0.5) / echelle) for x, y in quad]
                meilleur = Detection(coins, round(confiance, 3), "qt")
    if meilleur is None or meilleur.confiance < 0.55:
        return None
    return meilleur


def _detecter_opencv(img: QImage) -> Detection | None:
    import cv2  # noqa: F401  (facultatif)
    import numpy as np
    data, w, h, echelle = _gris(img, 640)
    a = np.frombuffer(bytes(data), dtype=np.uint8).reshape(h, w)
    a = cv2.GaussianBlur(a, (5, 5), 0)
    bords = cv2.dilate(cv2.Canny(a, 40, 120), None, iterations=2)
    contours, _ = cv2.findContours(bords, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    meilleur = None
    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        part = cv2.contourArea(approx) / (w * h)
        if len(approx) == 4 and 0.04 < part < 0.97:
            quad = ordonner([(float(p[0][0]), float(p[0][1])) for p in approx])
            meilleur = Detection([((x + 0.5) / echelle, (y + 0.5) / echelle) for x, y in quad],
                                 round(min(1.0, part / 0.08), 3), "opencv")
            break
    return meilleur


# ---------------------------------------------------------------- redressement
def taille_redressee(coins) -> tuple[int, int]:
    (a, b, c, d) = coins
    dist = lambda p, q: math.hypot(p[0] - q[0], p[1] - q[1])  # noqa: E731
    largeur = max(dist(a, b), dist(d, c))
    hauteur = max(dist(a, d), dist(b, c))
    k = min(1.0, COTE_MAX / max(largeur, hauteur, 1))
    return max(8, round(largeur * k)), max(8, round(hauteur * k))


def redresser(img: QImage, coins) -> QImage:
    """Correction de perspective : le quadrilatère `coins` devient un rectangle."""
    largeur, hauteur = taille_redressee(coins)
    source = QPolygonF([QPointF(x, y) for x, y in coins])
    cible = QPolygonF([QPointF(0, 0), QPointF(largeur, 0), QPointF(largeur, hauteur),
                       QPointF(0, hauteur)])
    t = QTransform()
    if not QTransform.quadToQuad(source, cible, t):
        raise ValueError("quadrilatère dégénéré")
    sortie = QImage(largeur, hauteur, QImage.Format.Format_RGB32)
    sortie.fill(Qt.GlobalColor.white)
    p = QPainter(sortie)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setTransform(t)
    p.drawImage(0, 0, img)
    p.end()
    return sortie


def derouler(img: QImage, courbure: float) -> QImage:
    """« Déroule » une étiquette collée sur une bouteille cylindrique vue de
    face : les bords, vus en fuite, sont étirés pour retrouver la largeur
    réelle. `courbure` 0..1 = demi-angle visible de 0 à 80°."""
    if courbure <= 0.01:
        return img
    alpha = math.radians(80 * min(1.0, courbure))
    w_in, h = img.width(), img.height()
    rayon = w_in / (2 * math.sin(alpha))
    w_out = max(1, round(2 * rayon * alpha))
    sortie = QImage(w_out, h, QImage.Format.Format_RGB32)
    sortie.fill(Qt.GlobalColor.white)
    p = QPainter(sortie)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    cx = w_in / 2
    for u in range(w_out):
        theta = (u + 0.5) / w_out * 2 * alpha - alpha
        x = cx + rayon * math.sin(theta)
        x2 = cx + rayon * math.sin(theta + 2 * alpha / w_out)
        p.drawImage(QRectF(u, 0, 1, h), img, QRectF(x, 0, max(0.5, x2 - x), h))
    p.end()
    return sortie


def appliquer(img: QImage, r: Retouche) -> QImage:
    """Quarts de tour, puis perspective, puis déroulage."""
    img = pivoter(img, r.quarts)
    if r.coins:
        img = redresser(img, r.coins)
    elif max(img.width(), img.height()) > COTE_MAX:
        img = img.scaled(COTE_MAX, COTE_MAX, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    return derouler(img, r.courbure)


def enregistrer(img: QImage, chemin: str | Path) -> Path:
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if not img.save(str(chemin), "JPG", QUALITE_JPEG):
        raise OSError(f"écriture impossible : {chemin}")
    return chemin


# ---------------------------------------------------------------- vignettes
def vignette(chemin: str | Path, largeur: int, hauteur: int, dossier_cache: str | Path) -> Path | None:
    """Vignette en cache disque (régénérée si la photo change). Lit la photo
    directement à la bonne taille (QImageReader.setScaledSize) : une photo de
    téléphone de 12 Mpx ne passe jamais entière en mémoire pour une vignette."""
    chemin = Path(chemin)
    try:
        st = chemin.stat()
    except OSError:
        return None
    cle = hashlib.sha1(f"{chemin.resolve()}|{st.st_mtime_ns}|{st.st_size}".encode()).hexdigest()[:20]
    cible = Path(dossier_cache) / cle[:2] / f"{cle}_{largeur}x{hauteur}.jpg"
    if cible.exists():
        return cible
    r = QImageReader(str(chemin))
    r.setAutoTransform(True)
    taille = r.size()
    if taille.isValid() and taille.width() > 0:
        echelle = min(largeur / taille.width(), hauteur / taille.height(), 1.0)
        r.setScaledSize(QSize(max(1, round(taille.width() * echelle)),
                              max(1, round(taille.height() * echelle))))
    img = r.read()
    if img.isNull():
        return None
    if img.width() > largeur or img.height() > hauteur:
        img = img.scaled(largeur, hauteur, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    cible.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(cible), "JPG", 85)
    return cible
