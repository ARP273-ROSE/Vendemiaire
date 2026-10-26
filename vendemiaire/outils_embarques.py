# -*- coding: utf-8 -*-
"""Outils tiers livrés avec le paquet (clé « outils » de kit.json).

Le kit commun les pose dans `outils/<nom>/`, À CÔTÉ de `python/` et `app/` :

* `outils/tesseract/` : Tesseract (conda-forge) + modèles `fra` et `eng`
  (`tessdata/`, dépôt officiel tessdata_fast) — lecture des étiquettes ;
* `outils/tectonic/` : Tectonic (licence MIT) et un CACHE de paquets LaTeX
  rempli à la construction (cartes des vins, rapport d'assurance, étiquettes,
  manuel) : les documents se compilent hors ligne.

Comme l'interpréteur, ces outils arrivent avec le paquet complet ; la mise à
jour automatique (qui ne remplace que `app/`) n'y touche pas. Depuis les
sources, ou dans une installation qui ne les a pas, l'application se replie
sur ceux du système (PATH, emplacements usuels).

Le cache de Tectonic livré est un MODÈLE : il est recopié une fois dans le
profil de l'utilisateur (rien n'écrit jamais dans le dossier d'installation).
"""
from __future__ import annotations

import os
import shutil
import sys
import threading
from pathlib import Path

from . import chemins

RACINE_PAQUET = chemins.RACINE_APP.parent
_verrou = threading.Lock()


def racine_outils() -> Path:
    return Path(os.environ.get("VENDEMIAIRE_OUTILS") or RACINE_PAQUET / "outils")


def dossier(nom: str) -> Path | None:
    d = racine_outils() / nom
    return d if d.is_dir() else None


def executable(nom: str) -> str | None:
    """Exécutable d'un outil embarqué (`outils/<nom>/bin/<nom>[.exe]`), ou None."""
    d = dossier(nom)
    if d is None:
        return None
    exe = nom + (".exe" if sys.platform == "win32" else "")
    for p in (d / "bin" / exe, d / exe):
        if p.is_file() and (sys.platform == "win32" or os.access(p, os.X_OK)):
            return str(p)
    return None


def est_embarque(chemin: str | None) -> bool:
    """Vrai si `chemin` désigne un exécutable de outils/."""
    if not chemin:
        return False
    try:
        Path(chemin).resolve().relative_to(racine_outils().resolve())
        return True
    except (ValueError, OSError):
        return False


def tessdata() -> str | None:
    d = dossier("tesseract")
    if d is not None and (d / "tessdata").is_dir():
        return str(d / "tessdata")
    return None


def _empreinte_modele(modele: Path) -> str:
    n = taille = 0
    for f in modele.rglob("*"):
        if f.is_file():
            n += 1
            taille += f.stat().st_size
    return f"{modele.resolve()}|{n}|{taille}"


def cache_tectonic() -> Path | None:
    """Copie de travail du cache de Tectonic dans le profil (recopiée depuis le
    modèle du paquet quand il change) ; None sans cache embarqué."""
    d = dossier("tectonic")
    modele = d / "cache" if d is not None else None
    if modele is None or not modele.is_dir():
        return None
    cible = chemins.dossier_profil() / "cache" / "tectonic"
    marque = cible / ".modele"
    attendu = _empreinte_modele(modele)
    with _verrou:
        try:
            if marque.read_text(encoding="utf-8") == attendu:
                return cible
        except OSError:
            pass
        tmp = cible.with_name("tectonic.nouveau")
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.copytree(modele, tmp)
        (tmp / ".modele").write_text(attendu, encoding="utf-8")
        shutil.rmtree(cible, ignore_errors=True)
        os.replace(tmp, cible)
    return cible


def etat() -> dict:
    """Ce qui est embarqué (fenêtre « À propos », rapports, essais)."""
    return {"tesseract": executable("tesseract"), "tessdata": tessdata(),
            "tectonic": executable("tectonic"),
            "cache_tectonic": str(dossier("tectonic") / "cache") if dossier("tectonic") else None}


def essai() -> str:
    """Essai réel des outils et bibliothèques embarqués, lancé par la
    vérification du paquet (kit.json « essai_embarquees ») : code QR écrit
    (segno) puis relu (zxing-cpp), étiquette lue par Tesseract, document
    compilé par Tectonic SANS réseau. Lève une erreur si un outil présent
    échoue ; dans un paquet, l'absence d'un outil est aussi une erreur."""
    from PyQt6.QtGui import QGuiApplication
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])  # noqa: F841
    from . import codes, ocr
    from .documents import latex
    resultats = []
    # codes QR : écrire puis relire
    texte_qr = "VDM-ESSAI-42"
    lus = [c.texte for c in codes.lire_qimage(_image_qr(codes.matrice_qr(texte_qr)))]
    if texte_qr not in lus:
        raise RuntimeError(f"zxing-cpp n'a pas relu le code QR ({lus})")
    resultats.append("QR ok")
    dans_paquet = chemins.empaquete()
    # Tesseract
    if executable("tesseract") or dans_paquet:
        if not executable("tesseract"):
            raise RuntimeError("Tesseract absent du paquet")
        langues = ocr.langues()
        if not {"fra", "eng"} <= set(langues):
            raise RuntimeError(f"modèles fra/eng absents : {langues}")
        lu = ocr.lire(_image_texte("CHATEAU EXEMPLE 2015"), "eng").texte.upper()
        if "2015" not in lu or "EXEMPLE" not in lu:
            raise RuntimeError(f"Tesseract a lu « {lu.strip()} »")
        resultats.append("Tesseract ok")
    # Tectonic, hors ligne
    if executable("tectonic") or dans_paquet:
        if not executable("tectonic"):
            raise RuntimeError("Tectonic absent du paquet")
        import tempfile
        m = latex.trouver_moteur()
        if m is None or not est_embarque(m.chemin):
            raise RuntimeError(f"moteur choisi : {m}")
        with tempfile.TemporaryDirectory() as tmp:
            source = (r"\documentclass{article}\usepackage{fontspec}\usepackage[french]{babel}"
                      r"\begin{document}Vendémiaire : essai hors ligne.\end{document}")
            r = latex.compiler(source, Path(tmp) / "essai.pdf", moteur=m, reseau=False)
            if not r.pdf.is_file():
                raise RuntimeError("Tectonic n'a pas produit de PDF")
        resultats.append("Tectonic hors ligne ok")
    return ", ".join(resultats)


def _image_qr(matrice, module: int = 8):
    from PyQt6.QtGui import QColor, QImage, QPainter
    n = len(matrice)
    img = QImage((n + 8) * module, (n + 8) * module, QImage.Format.Format_RGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    for y, rangee in enumerate(matrice):
        for x, noir in enumerate(rangee):
            if noir:
                p.fillRect((x + 4) * module, (y + 4) * module, module, module, QColor("black"))
    p.end()
    return img


def _image_texte(texte: str):
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter
    from .style import FAMILLE, POLICES
    for police in POLICES.glob("*.[ot]tf"):
        QFontDatabase.addApplicationFont(str(police))
    img = QImage(900, 160, QImage.Format.Format_RGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    f = QFont(FAMILLE)
    f.setPixelSize(64)
    p.setFont(f)
    p.setPen(QColor("black"))
    p.drawText(img.rect(), int(Qt.AlignmentFlag.AlignCenter), texte)
    p.end()
    return img
