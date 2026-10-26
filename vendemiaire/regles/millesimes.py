# -*- coding: utf-8 -*-
"""Note d'un millésime d'après les tableaux du dossier (`millesimes.json`).

Le dossier croise quatre tableaux publiés (Wine Enthusiast 2018, The Wine
Society 2026, Wine Spectator 2026, Berry Bros. & Rudd 2026) pour 27 régions.
Pour décaler une fenêtre de garde (`garde.millesime`), il faut la note du
millésime ET la moyenne de la région dans le MÊME tableau (« chaque point au-
dessus de la moyenne de la région ») : on la calcule sur toutes les années de
la région présentes dans ce tableau.

Choix du tableau, dans cet ordre : Wine Enthusiast (celui sur lequel le
dossier a mesuré 0,44 an par point sur 100), The Wine Society (1,76 an par
point sur 10), Wine Spectator (sur 100), Berry Bros. (sur 10).

RATTACHEMENT (donnée du dossier, `rattachement_millesimes.json`) : le dossier
nomme ses régions (« Bordeaux rive gauche (Médoc, Graves) »…) et dit, dans ce
fichier, quelles appellations y entrent, mot par mot ; l'explication affichée
nomme toujours la région retenue. Une seule source : plus aucune table ici.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .jeu import JeuRegles, jeu, normaliser

#: ordre de préférence des tableaux et échelle de chacun
ORDRE_SOURCES = ("WE", "WSO", "WSP", "BB")

@dataclass
class NoteMillesime:
    region: str            # identifiant de la région du dossier
    region_nom: str
    source: str            # WE, WSO, WSP, BB
    source_nom: str
    echelle: int           # 100 ou 10
    note: float
    moyenne: float         # moyenne de la région dans ce tableau
    n_annees: int
    conseil: str | None
    autres: dict           # autres tableaux : {source: note}


def region_du_vin(vin: dict, regles: JeuRegles | None = None) -> str | None:
    regles = regles or jeu()
    texte = " | ".join(normaliser(vin.get(k)) for k in
                       ("appellation", "region", "sous_region", "pays", "cuvee"))
    for r in regles.rattachement:
        if vin.get("couleur") not in r["couleurs"] or (vin.get("type") or "tranquille") not in r["types"]:
            continue
        if any(re.search(r"\b" + re.escape(m) + r"\b", texte) for m in r["mots"]):
            return r["region"]
    return None


def note(vin: dict, regles: JeuRegles | None = None) -> NoteMillesime | None:
    """Note du millésime du vin, ou None (pas de millésime, région non couverte,
    année absente des tableaux)."""
    regles = regles or jeu()
    mil = vin.get("millesime")
    if not mil:
        return None
    rid = region_du_vin(vin, regles)
    if rid is None:
        return None
    region = next((r for r in regles.millesimes["regions"] if r["id"] == rid), None)
    if region is None:
        return None
    annee = next((a for a in region["annees"] if a["millesime"] == int(mil)), None)
    if annee is None:
        return None
    sources = regles.millesimes["sources"]
    for s in ORDRE_SOURCES:
        n = (annee["sources"].get(s) or {}).get("note")
        if n is None:
            continue
        toutes = [a["sources"][s]["note"] for a in region["annees"]
                  if (a["sources"].get(s) or {}).get("note") is not None]
        autres = {k: v["note"] for k, v in annee["sources"].items() if k != s and v.get("note") is not None}
        return NoteMillesime(rid, region["nom"], s, sources[s]["nom"], int(sources[s]["echelle"]), float(n),
                             sum(toutes) / len(toutes), len(toutes),
                             (annee["sources"][s] or {}).get("conseil"), autres)
    return None
