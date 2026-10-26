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

RATTACHEMENT (donnée de l'application, pas du dossier) : le dossier nomme ses
régions (« Bordeaux rive gauche (Médoc, Graves) »…) sans dire quelles
appellations y entrent ; la table `RATTACHEMENT` fait ce lien géographique,
mot par mot, et l'explication affichée nomme toujours la région retenue.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .jeu import JeuRegles, jeu, normaliser

#: ordre de préférence des tableaux et échelle de chacun
ORDRE_SOURCES = ("WE", "WSO", "WSP", "BB")

#: région du dossier -> (couleurs, types, mots cherchés dans appellation, région,
#: sous-région, pays, cuvée). Ordre = priorité (le plus précis d'abord).
RATTACHEMENT: list[tuple[str, tuple, tuple, tuple]] = [
    ("sauternes", ("blanc",), ("doux",), ("sauternes", "barsac")),
    ("loire_doux", ("blanc",), ("doux",), ("loire", "layon", "vouvray", "bonnezeaux", "quarts de chaume",
                                          "montlouis", "anjou", "saumur")),
    ("porto", ("rouge",), ("mute",), ("porto", "port", "douro")),
    ("champagne", ("blanc", "rose"), ("effervescent",), ("champagne",)),
    ("bx_droite", ("rouge",), ("tranquille",), ("pomerol", "saint emilion", "fronsac", "lalande",
                                               "castillon")),
    ("bx_gauche", ("rouge",), ("tranquille",), ("medoc", "pauillac", "margaux", "saint julien",
                                               "saint estephe", "listrac", "moulis", "graves", "pessac")),
    ("bx_blanc", ("blanc",), ("tranquille",), ("pessac", "graves", "entre deux mers", "bordeaux")),
    ("chablis", ("blanc",), ("tranquille",), ("chablis",)),
    ("bourgogne_rouge", ("rouge",), ("tranquille",), ("bourgogne", "burgundy", "cote de nuits",
                                                      "cote de beaune")),
    ("bourgogne_blanc", ("blanc",), ("tranquille",), ("bourgogne", "burgundy", "meursault", "montrachet",
                                                      "corton charlemagne", "cote de beaune")),
    ("rhone_nord", ("rouge", "blanc"), ("tranquille",), ("cote rotie", "hermitage", "cornas", "saint joseph",
                                                         "crozes", "condrieu", "rhone nord",
                                                         "rhone septentrional")),
    ("rhone_sud", ("rouge", "blanc", "rose"), ("tranquille",), ("chateauneuf", "gigondas", "vacqueyras",
                                                                "rasteau", "cotes du rhone", "lirac",
                                                                "rhone sud", "rhone meridional")),
    ("loire", ("blanc", "rouge"), ("tranquille",), ("loire", "muscadet", "sancerre", "pouilly fume",
                                                    "chinon", "bourgueil", "saumur", "savennieres",
                                                    "vouvray", "anjou", "touraine")),
    ("alsace", ("blanc", "rouge"), ("tranquille", "doux"), ("alsace",)),
    ("piemont", ("rouge",), ("tranquille",), ("barolo", "barbaresco", "piemont", "piedmont", "langhe")),
    ("toscane", ("rouge",), ("tranquille",), ("brunello", "montalcino", "chianti", "toscane", "tuscany",
                                             "vino nobile")),
    ("rioja", ("rouge",), ("tranquille",), ("rioja",)),
    ("ribera", ("rouge",), ("tranquille",), ("ribera del duero",)),
    ("allemagne", ("blanc",), ("tranquille", "doux"), ("allemagne", "germany", "deutschland", "mosel",
                                                       "rheingau", "pfalz", "nahe", "rheinhessen")),
    ("napa", ("rouge",), ("tranquille",), ("napa",)),
    ("oregon", ("rouge",), ("tranquille",), ("oregon", "willamette")),
    ("barossa", ("rouge",), ("tranquille",), ("barossa", "mclaren")),
    ("marlborough", ("blanc",), ("tranquille",), ("marlborough",)),
    ("otago", ("rouge",), ("tranquille",), ("otago",)),
    ("mendoza", ("rouge",), ("tranquille",), ("mendoza",)),
    ("chili", ("rouge",), ("tranquille",), ("chili", "chile", "maipo", "colchagua")),
    ("afrique_sud", ("rouge",), ("tranquille",), ("afrique du sud", "south africa", "stellenbosch", "paarl",
                                                 "swartland")),
]


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


def region_du_vin(vin: dict) -> str | None:
    texte = " | ".join(normaliser(vin.get(k)) for k in
                       ("appellation", "region", "sous_region", "pays", "cuvee"))
    for rid, couleurs, types, mots in RATTACHEMENT:
        if vin.get("couleur") not in couleurs or (vin.get("type") or "tranquille") not in types:
            continue
        if any(re.search(r"\b" + re.escape(m) + r"\b", texte) for m in mots):
            return rid
    return None


def note(vin: dict, regles: JeuRegles | None = None) -> NoteMillesime | None:
    """Note du millésime du vin, ou None (pas de millésime, région non couverte,
    année absente des tableaux)."""
    regles = regles or jeu()
    mil = vin.get("millesime")
    if not mil:
        return None
    rid = region_du_vin(vin)
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
