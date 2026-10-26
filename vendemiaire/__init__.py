# -*- coding: utf-8 -*-
"""Vendémiaire — gestion de cave à vin / wine cellar manager.

Le numéro de version n'existe qu'à un seul endroit : le fichier VERSION à la
racine du dépôt (copié à côté du paquet dans l'application installée).
"""
from pathlib import Path


def _lire_version() -> str:
    for dossier in (Path(__file__).resolve().parent.parent, Path(__file__).resolve().parent):
        try:
            return (dossier / "VERSION").read_text(encoding="utf-8").strip()
        except OSError:
            continue
    return "0.0.0"


__version__ = _lire_version()
NOM = "Vendemiaire"
