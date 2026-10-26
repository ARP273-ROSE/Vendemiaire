# -*- coding: utf-8 -*-
"""Lecture locale du texte d'une étiquette (OCR), puis indices pour la recherche.

Moteur retenu : **Tesseract** (licence Apache 2.0), appelé comme programme
externe. Pourquoi (mesures du 26/10/2026, détail dans docs/photos_et_ocr.md) :

* même appel sur Windows, macOS et Linux, sans module compilé à embarquer ;
* léger : bibliothèque ≈ 2,3 Mo + Leptonica ≈ 1,8 Mo, modèles « fast » du
  français et de l'anglais ≈ 5 Mo ; hors ligne, rien n'est envoyé nulle part ;
* l'autre candidat sérieux, RapidOCR (modèles PaddleOCR en ONNX), pèse
  ≈ 120 Mo de roues (onnxruntime + OpenCV + numpy + modèles) et tire une
  OpenCV « avec interface » qui entre en conflit avec le Qt de PyQt6.

Tesseract est cherché : réglage de l'utilisateur (`definir_chemin`), variable
TESSERACT_CMD, dossier `ocr/` de l'application installée (si un paquet
l'embarque), PATH, puis emplacements usuels (Windows : Program Files ;
macOS : Homebrew). Absent : l'interface le dit, explique comment l'installer,
et la recherche par texte saisi à la main reste possible.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

_chemin_utilisateur: str | None = None

EMPLACEMENTS = {
    "win32": [r"C:\Program Files\Tesseract-OCR\tesseract.exe",
              r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"],
    "darwin": ["/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract"],
    "linux": ["/usr/bin/tesseract", "/usr/local/bin/tesseract"],
}
INSTALLER = {
    "win32": "https://github.com/UB-Mannheim/tesseract/wiki",
    "darwin": "brew install tesseract tesseract-lang",
    "linux": "sudo apt install tesseract-ocr tesseract-ocr-fra",
}


@dataclass
class Mot:
    texte: str
    confiance: float
    boite: tuple[int, int, int, int]      # x, y, largeur, hauteur
    ligne: tuple[int, int, int]           # bloc, paragraphe, ligne


@dataclass
class ResultatOCR:
    texte: str
    mots: list[Mot] = field(default_factory=list)
    moteur: str = ""
    duree: float = 0.0

    def lignes_principales(self, n: int = 6) -> list[str]:
        """Les lignes écrites le plus gros (nom du domaine, cuvée…), dans l'ordre
        de lecture : sur une étiquette, la taille dit l'importance."""
        par_ligne: dict[tuple, list[Mot]] = {}
        for m in self.mots:
            par_ligne.setdefault(m.ligne, []).append(m)
        lignes = []
        for cle, mots in par_ligne.items():
            texte = " ".join(m.texte for m in mots).strip()
            if len(re.sub(r"[^\w]", "", texte)) < 3:
                continue
            hauteur = sorted(m.boite[3] for m in mots)[len(mots) // 2]
            lignes.append((hauteur, min(m.boite[1] for m in mots), texte))
        grandes = sorted(lignes, key=lambda l: -l[0])[:n]
        return [t for _, _, t in sorted(grandes, key=lambda l: l[1])]


def definir_chemin(chemin: str | None) -> None:
    global _chemin_utilisateur
    _chemin_utilisateur = chemin or None


def _systeme() -> str:
    return "win32" if sys.platform == "win32" else ("darwin" if sys.platform == "darwin" else "linux")


def installation() -> str:
    """Comment installer Tesseract sur ce système (texte court ou adresse)."""
    return INSTALLER[_systeme()]


def moteur() -> str | None:
    """Chemin de l'exécutable Tesseract, ou None."""
    candidats = [_chemin_utilisateur, os.environ.get("TESSERACT_CMD")]
    racine = Path(__file__).resolve().parent.parent
    for d in (racine / "ocr", racine.parent / "ocr"):
        candidats.append(str(d / ("tesseract.exe" if _systeme() == "win32" else "tesseract")))
    candidats.append(shutil.which("tesseract"))
    candidats += EMPLACEMENTS[_systeme()]
    for c in candidats:
        if c and Path(c).is_file() and os.access(c, os.X_OK):
            return c
    return None


def _executer(args: list[str], delai: float = 60) -> subprocess.CompletedProcess:
    options = {}
    if sys.platform == "win32":
        options["creationflags"] = 0x08000000          # CREATE_NO_WINDOW : pas de console qui clignote
    return subprocess.run(args, capture_output=True, timeout=delai, **options)


def version() -> str | None:
    m = moteur()
    if not m:
        return None
    try:
        r = _executer([m, "--version"], 15)
    except (OSError, subprocess.SubprocessError):
        return None
    sortie = (r.stdout or r.stderr).decode("utf-8", "replace").splitlines()
    return sortie[0].strip() if sortie else None


def langues() -> list[str]:
    m = moteur()
    if not m:
        return []
    try:
        r = _executer([m, "--list-langs"], 15)
    except (OSError, subprocess.SubprocessError):
        return []
    texte = (r.stdout or b"").decode("utf-8", "replace")
    return [l.strip() for l in texte.splitlines()[1:] if l.strip() and " " not in l.strip()]


def langues_etiquette() -> str:
    """Langues usuelles des étiquettes, parmi celles installées."""
    voulues = ["fra", "eng", "ita", "spa", "deu", "por"]
    dispo = langues()
    choix = [l for l in voulues if l in dispo] or (["eng"] if "eng" in dispo else dispo[:1])
    return "+".join(choix) or "eng"


def lire(image, langue: str | None = None, delai: float = 90) -> ResultatOCR:
    """Lit le texte d'une image (chemin ou QImage). Lent (une à quelques
    secondes) : à appeler hors du fil de l'interface."""
    m = moteur()
    if not m:
        raise FileNotFoundError("Tesseract introuvable")
    debut = time.monotonic()
    with tempfile.TemporaryDirectory() as tmp:
        if isinstance(image, (str, Path)):
            source = str(image)
        else:
            source = str(Path(tmp) / "etiquette.png")
            image.save(source, "PNG")
        args = [m, source, "stdout", "-l", langue or langues_etiquette(), "--psm", "3", "tsv"]
        r = _executer(args, delai)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or b"").decode("utf-8", "replace")[-400:])
    mots = analyser_tsv(r.stdout.decode("utf-8", "replace"))
    texte = texte_depuis_mots(mots)
    return ResultatOCR(texte, mots, "Tesseract", time.monotonic() - debut)


def analyser_tsv(tsv: str) -> list[Mot]:
    mots = []
    for ligne in tsv.splitlines()[1:]:
        champs = ligne.split("\t")
        if len(champs) < 12 or champs[0] != "5":
            continue
        texte = champs[11].strip()
        try:
            conf = float(champs[10])
        except ValueError:
            continue
        if not texte or conf < 30:
            continue
        mots.append(Mot(texte, conf, tuple(int(x) for x in champs[6:10]),
                        (int(champs[2]), int(champs[3]), int(champs[4]))))
    return mots


def texte_depuis_mots(mots: list[Mot]) -> str:
    lignes: dict[tuple, list[str]] = {}
    for m in mots:
        lignes.setdefault(m.ligne, []).append(m.texte)
    return "\n".join(" ".join(v) for v in lignes.values())


# ---------------------------------------------------------------- indices
@dataclass
class Indices:
    """Ce qu'on peut tirer du texte d'une étiquette pour chercher le vin."""
    millesime: int | None = None
    degre: float | None = None
    contenance_cl: float | None = None
    eans: list[str] = field(default_factory=list)
    appellations: list[str] = field(default_factory=list)
    couleur: str | None = None
    lignes: list[str] = field(default_factory=list)
    texte: str = ""


def indices(texte: str, lignes_principales: list[str] | None = None, refs=None) -> Indices:
    from .mondial.appariement import jeton_millesime
    from .mondial.off import eans_dans
    i = Indices(texte=texte or "", lignes=list(lignes_principales or []))
    i.millesime = jeton_millesime(texte)
    m = re.search(r"(\d{1,2})\s*[,.]\s*(\d)\s*%|(\d{1,2})\s*%\s*(?:vol|alc)", texte or "", re.I)
    if m:
        v = float(f"{m.group(1)}.{m.group(2)}") if m.group(1) else float(m.group(3))
        if 5 <= v <= 23:
            i.degre = v
    m = re.search(r"(\d{2,3}(?:[,.]\d)?)\s*c\s*l\b", texte or "", re.I)
    if m:
        i.contenance_cl = float(m.group(1).replace(",", "."))
    else:
        m = re.search(r"\b(\d(?:[,.]\d{1,2})?)\s*l\b", texte or "", re.I)
        if m and 0.1 <= float(m.group(1).replace(",", ".")) <= 30:
            i.contenance_cl = float(m.group(1).replace(",", ".")) * 100
    i.eans = eans_dans(texte)
    t = (texte or "").lower()
    for mot, code in (("rosé", "rose"), ("vin rouge", "rouge"), ("red wine", "rouge"),
                      ("vin blanc", "blanc"), ("white wine", "blanc"), ("rouge", "rouge"),
                      ("blanc", "blanc")):
        if re.search(rf"(?<!\w){mot}(?!\w)", t):
            i.couleur = code
            break
    if refs is not None:
        i.appellations = [a["nom"] for a in refs.appellations_dans(texte)][:5]
    return i


def requete_depuis_indices(ind: Indices) -> dict:
    """Requête d'appariement : le texte de l'étiquette sert de producteur et de
    cuvée (on ne sait pas lequel est lequel), l'appellation du registre, le
    millésime et la couleur trouvés."""
    return {"texte": "\n".join(ind.lignes) or ind.texte,
            "appellation": ind.appellations[0] if ind.appellations else None,
            "millesime": ind.millesime, "couleur": ind.couleur}
