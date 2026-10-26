# -*- coding: utf-8 -*-
"""Où vivent les données : TOUJOURS hors du dossier d'installation.

La mise à jour automatique remplace le dossier de l'application en entier :
une base posée à côté du programme disparaîtrait à la première mise à jour.

* Windows : %LOCALAPPDATA%\\Vendemiaire
* macOS   : ~/Library/Application Support/Vendemiaire
* Linux   : $XDG_DATA_HOME/Vendemiaire (~/.local/share/Vendemiaire)

Ce dossier par défaut s'appelle le PROFIL. Les données peuvent vivre ailleurs,
par exemple sur un partage réseau (lecteur réseau d'un NAS) pour que d'autres
programmes les lisent : le profil garde alors un petit fichier
`emplacement.json` qui pointe vers ce dossier (menu Fichier › Dossier des
données…). La variable d'environnement VENDEMIAIRE_DONNEES l'emporte sur tout
(essais, démonstration).

Un seul écrivain : le verrou d'instance (`vendemiaire.verrou`) est posé DANS le
dossier des données, donc sur le partage lui-même — deux postes ne peuvent pas
écrire ensemble. Les lecteurs extérieurs ouvrent la base en lecture seule
(`Base.lecture_seule`, `python -m vendemiaire.export_dossier`).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

NOM = "Vendemiaire"
RACINE_APP = Path(__file__).resolve().parent.parent


def empaquete() -> bool:
    """Vrai dans le paquet autonome du kit : python/ à côté de app/."""
    py = RACINE_APP.parent / "python"
    return (py / "python.exe").exists() or (py / "bin" / "python3").exists()


def dossier_profil() -> Path:
    """Dossier par défaut, propre à l'utilisateur et à la machine."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / NOM
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / NOM
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / NOM
    base.mkdir(parents=True, exist_ok=True)
    return base


def emplacement_choisi() -> Path | None:
    """Dossier des données choisi par l'utilisateur (emplacement.json du profil)."""
    try:
        d = json.loads((dossier_profil() / "emplacement.json").read_text(encoding="utf-8"))
        return Path(d["donnees"]) if d.get("donnees") else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def choisir_emplacement(dossier: str | Path | None) -> None:
    """Retient un autre dossier des données (None : revenir au profil)."""
    fichier = dossier_profil() / "emplacement.json"
    if dossier is None:
        fichier.unlink(missing_ok=True)
        return
    fichier.write_text(json.dumps({"donnees": str(dossier)}, ensure_ascii=False, indent=1),
                       encoding="utf-8")


def dossier_donnees() -> Path:
    force = os.environ.get("VENDEMIAIRE_DONNEES")
    if force:
        base = Path(force)
    else:
        base = emplacement_choisi() or dossier_profil()
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        base = Path.home() / f".{NOM.lower()}"
        base.mkdir(parents=True, exist_ok=True)
    return base


def chemin_base() -> Path:
    return dossier_donnees() / "cave.db"


def dossier_sauvegardes() -> Path:
    return dossier_donnees() / "sauvegardes"


def dossier_images() -> Path:
    return dossier_donnees() / "images"


def dossier_docs() -> Path:
    return RACINE_APP / "docs"
