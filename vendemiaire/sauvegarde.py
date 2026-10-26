# -*- coding: utf-8 -*-
"""Sauvegardes automatiques de la base.

* Copie par l'API de sauvegarde de SQLite (cohérente même base ouverte), écrite
  dans un fichier temporaire puis renommée : jamais de copie à moitié écrite.
* Seulement si la base a changé depuis la dernière copie (une base qui n'a pas
  bougé n'est pas recopiée toutes les trente minutes).
* Rotation : les 10 dernières copies « auto », plus une par semaine sur
  8 semaines ; les copies « manuel » et « avant-import » ne sont jamais
  supprimées automatiquement au-delà de 20.
* Le dossier des sauvegardes vit avec les données, hors du dossier
  d'installation (la mise à jour le remplace).
"""
from __future__ import annotations

import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

GARDER_AUTO = 10
GARDER_SEMAINES = 8
GARDER_AUTRES = 20


def _copies(dossier: Path, etiquette: str) -> list[Path]:
    return sorted(dossier.glob(f"vendemiaire_{etiquette}_*.db"))


def sauvegarder(chemin_base: str | Path, dossier: str | Path, etiquette: str = "auto",
                seulement_si_modifiee: bool = False) -> Path | None:
    chemin_base, dossier = Path(chemin_base), Path(dossier)
    if not chemin_base.exists():
        return None
    dossier.mkdir(parents=True, exist_ok=True)
    if seulement_si_modifiee:
        copies = _copies(dossier, etiquette)
        if copies and chemin_base.stat().st_mtime <= copies[-1].stat().st_mtime:
            return None
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    cible = dossier / f"vendemiaire_{etiquette}_{horodatage}.db"
    n = 1
    while cible.exists():
        n += 1
        cible = dossier / f"vendemiaire_{etiquette}_{horodatage}_{n}.db"
    tmp = cible.with_name("." + cible.name + ".tmp")
    source = sqlite3.connect(str(chemin_base), timeout=10)
    try:
        dest = sqlite3.connect(str(tmp))
        try:
            source.backup(dest)
        finally:
            dest.close()
    finally:
        source.close()
    os.replace(tmp, cible)
    tourner(dossier)
    log.info("Sauvegarde %s", cible.name)
    return cible


def tourner(dossier: str | Path) -> list[Path]:
    """Applique la rotation ; renvoie les fichiers supprimés."""
    dossier = Path(dossier)
    supprimes = []
    auto = _copies(dossier, "auto")
    garder = set(auto[-GARDER_AUTO:])
    semaines = {}
    for p in auto:
        try:
            jour = datetime.strptime(p.stem.split("_")[2], "%Y%m%d")
        except (IndexError, ValueError):
            garder.add(p)
            continue
        semaines.setdefault(jour.isocalendar()[:2], p)
    for cle in sorted(semaines)[-GARDER_SEMAINES:]:
        garder.add(semaines[cle])
    for p in auto:
        if p not in garder:
            p.unlink(missing_ok=True)
            supprimes.append(p)
    for etiquette in ("manuel", "avant-import", "avant-migration"):
        for p in _copies(dossier, etiquette)[:-GARDER_AUTRES]:
            p.unlink(missing_ok=True)
            supprimes.append(p)
    return supprimes


def restaurer(copie: str | Path, chemin_base: str | Path) -> None:
    """Remplace la base par une copie (la base actuelle est d'abord mise de côté).
    La base doit être FERMÉE par l'application avant l'appel."""
    copie, chemin_base = Path(copie), Path(chemin_base)
    if chemin_base.exists():
        sauvegarder(chemin_base, copie.parent, "avant-restauration")
    tmp = chemin_base.with_name(chemin_base.name + ".restauration")
    src = sqlite3.connect(str(copie))
    try:
        dest = sqlite3.connect(str(tmp))
        try:
            src.backup(dest)
        finally:
            dest.close()
    finally:
        src.close()
    os.replace(tmp, chemin_base)


def liste(dossier: str | Path) -> list[tuple[Path, float]]:
    dossier = Path(dossier)
    if not dossier.is_dir():
        return []
    return sorted(((p, p.stat().st_mtime) for p in dossier.glob("vendemiaire_*.db")),
                  key=lambda x: x[1], reverse=True)


def age_derniere(dossier: str | Path) -> float | None:
    l = liste(dossier)
    return time.time() - l[0][1] if l else None
