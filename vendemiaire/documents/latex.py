# -*- coding: utf-8 -*-
"""Compiler un document LaTeX (carte des vins, rapport d'assurance).

Choix du moteur, dans cet ordre :

1. celui que l'utilisateur a désigné (réglage « documents/moteur », ou la
   variable VENDEMIAIRE_LATEX) ;
2. Tectonic posé à côté de l'application (`tectonic/tectonic[.exe]`, prévu pour
   le paquet de la phase 5) ou trouvé dans le PATH ;
3. une distribution installée : XeLaTeX, LuaLaTeX, puis pdfLaTeX (PATH, puis les
   dossiers usuels de MiKTeX, TeX Live et MacTeX).

Sans moteur, l'application ne se bloque pas : chaque document a un repli
HTML → PDF par Qt (`QTextDocument`), même contenu, typographie plus simple.
Pourquoi Tectonic pour l'embarquer : un seul exécutable (licence MIT, ≈ 30 Mo,
Windows/macOS/Linux) fondé sur XeTeX, qui ne télécharge que les paquets dont un
document a besoin (une fois, puis cache) — contre 100 Mo à plusieurs Go pour une
distribution complète. Voir docs/documents.md.

La compilation se fait dans un dossier temporaire supprimé ensuite : seuls le
`.tex` (si demandé) et le `.pdf` sont rendus. Deux passes (références de pages
de l'index) ; Tectonic relance lui-même ce qu'il faut.
"""
from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ORDRE = ("tectonic", "xelatex", "lualatex", "pdflatex")
DELAI_S = 240


class LatexIndisponible(RuntimeError):
    """Aucun moteur LaTeX : utiliser le repli HTML → PDF."""


class ErreurLatex(RuntimeError):
    def __init__(self, message: str, journal: str = ""):
        super().__init__(message)
        self.journal = journal


@dataclass
class Moteur:
    nom: str            # tectonic, xelatex, lualatex, pdflatex
    chemin: str

    @property
    def unicode(self) -> bool:
        """Polices OpenType (fontspec) disponibles ?"""
        return self.nom != "pdflatex"


def _dossiers_usuels() -> list[str]:
    d: list[str] = []
    racine_app = Path(__file__).resolve().parent.parent.parent
    d.append(str(racine_app / "tectonic"))
    if sys.platform == "win32":
        for base in (os.environ.get("LOCALAPPDATA", ""), os.environ.get("ProgramFiles", r"C:\Program Files")):
            if base:
                d += [os.path.join(base, "Programs", "MiKTeX", "miktex", "bin", "x64"),
                      os.path.join(base, "MiKTeX", "miktex", "bin", "x64")]
        d += sorted(glob.glob(r"C:\texlive\20*\bin\windows"), reverse=True)
        d += sorted(glob.glob(r"C:\texlive\20*\bin\win64"), reverse=True)
    elif sys.platform == "darwin":
        d += ["/Library/TeX/texbin", "/opt/homebrew/bin", "/usr/local/bin"]
        d += sorted(glob.glob("/usr/local/texlive/20*/bin/universal-darwin"), reverse=True)
    else:
        d += sorted(glob.glob("/usr/local/texlive/20*/bin/x86_64-linux"), reverse=True)
        d += sorted(glob.glob("/usr/local/texlive/20*/bin/aarch64-linux"), reverse=True)
    return d


def _nom_moteur(chemin: str) -> str | None:
    base = Path(chemin).name.lower().replace(".exe", "")
    return base if base in ORDRE else None


def trouver_moteur(prefere: str | None = None, interdits: tuple = ()) -> Moteur | None:
    """Le moteur à utiliser, ou None. `prefere` : chemin d'un exécutable ou nom
    (« xelatex »…) ; `interdits` : noms à écarter (essais)."""
    voulu = prefere or os.environ.get("VENDEMIAIRE_LATEX")
    if voulu:
        nom = _nom_moteur(voulu)
        if nom and Path(voulu).is_file():
            return Moteur(nom, voulu)
        if voulu in ORDRE:
            trouve = shutil.which(voulu)
            if trouve:
                return Moteur(voulu, trouve)
    dossiers = _dossiers_usuels()
    for nom in ORDRE:
        if nom in interdits:
            continue
        exe = nom + (".exe" if sys.platform == "win32" else "")
        trouve = shutil.which(nom)
        if not trouve:
            for d in dossiers:
                p = Path(d) / exe
                if p.is_file():
                    trouve = str(p)
                    break
        if trouve:
            return Moteur(nom, trouve)
    return None


# ---------------------------------------------------------------------------- texte
_ECHAPPE = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
            "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
            "<": r"\textless{}", ">": r"\textgreater{}", "|": r"\textbar{}"}
_RX = re.compile("|".join(re.escape(k) for k in _ECHAPPE))
#: caractères que pdfLaTeX ne sait pas composer sans paquet : remplacés
_REMPLACE = {"\u2009": " ", "\u202f": "~", "\u00a0": "~", "–": "--", "—": "---", "…": r"\dots{}",
             "’": "'", "‘": "`", "œ": r"\oe{}", "Œ": r"\OE{}", "€": r"\euro{}", "№": "No",
             "★": r"$\star$", "×": r"$\times$", "≈": r"$\approx$", "±": r"$\pm$", "°": r"\textdegree{}"}


def echapper(texte) -> str:
    """Texte quelconque -> LaTeX sûr (aucun « $ » laissé ouvert, aucun caractère
    actif). Les espaces fines et insécables deviennent des espaces LaTeX."""
    if texte is None:
        return ""
    t = _RX.sub(lambda m: _ECHAPPE[m.group(0)], str(texte))
    for a, b in _REMPLACE.items():
        t = t.replace(a, b)
    return t


# ---------------------------------------------------------------------------- compilation
@dataclass
class Resultat:
    pdf: Path
    moteur: str
    passes: int


def compiler(tex: str, sortie_pdf: str | Path, annexes: dict[str, bytes | str | Path] | None = None,
             moteur: Moteur | None = None, passes: int = 2, garder_tex: bool = False) -> Resultat:
    """Compile `tex` vers `sortie_pdf`. `annexes` : fichiers posés à côté
    ({nom: octets | chemin}). Lève LatexIndisponible ou ErreurLatex (avec la fin
    du journal). Les fichiers temporaires disparaissent dans tous les cas."""
    moteur = moteur or trouver_moteur()
    if moteur is None:
        raise LatexIndisponible("aucun moteur LaTeX")
    sortie_pdf = Path(sortie_pdf)
    with tempfile.TemporaryDirectory(prefix="vendemiaire-tex-") as tmp:
        t = Path(tmp)
        (t / "document.tex").write_text(tex, encoding="utf-8")
        for nom, contenu in (annexes or {}).items():
            cible = t / nom
            cible.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(contenu, bytes):
                cible.write_bytes(contenu)
            else:
                shutil.copyfile(contenu, cible)
        env = dict(os.environ)
        env.setdefault("TEXMFOUTPUT", tmp)
        if moteur.nom == "tectonic":
            commandes = [[moteur.chemin, "-X", "compile", "--keep-logs", "document.tex"]]
        else:
            commandes = [[moteur.chemin, "-interaction=nonstopmode", "-halt-on-error", "document.tex"]] * passes
        for i, cmd in enumerate(commandes):
            try:
                r = subprocess.run(cmd, cwd=tmp, capture_output=True, timeout=DELAI_S, env=env,
                                   **({"creationflags": 0x08000000} if sys.platform == "win32" else {}))
            except subprocess.TimeoutExpired as e:
                raise ErreurLatex(f"{moteur.nom} : délai dépassé ({DELAI_S} s)") from e
            if r.returncode != 0 or not (t / "document.pdf").exists():
                journal = ""
                if (t / "document.log").exists():
                    journal = (t / "document.log").read_text(encoding="utf-8", errors="replace")
                journal = journal or (r.stdout + r.stderr).decode("utf-8", "replace")
                lignes = journal.splitlines()
                erreurs = [l for l in lignes if l.startswith("!")] or [l for l in lignes if "error" in l.lower()]
                raise ErreurLatex(f"{moteur.nom} : échec de la compilation ({(erreurs or ['?'])[0][:200]})",
                                  journal[-6000:])
        sortie_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(t / "document.pdf", sortie_pdf)
        if garder_tex:
            sortie_pdf.with_suffix(".tex").write_text(tex, encoding="utf-8")
        return Resultat(sortie_pdf, moteur.nom, len(commandes))
