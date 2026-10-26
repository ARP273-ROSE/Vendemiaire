# -*- coding: utf-8 -*-
"""Accords mets-vins dans les deux sens (`accords.json`).

* « J'ouvre ce vin » : les plats qui citent le style du vin (le dossier dit :
  « dériver de plats : pour un style, les plats qui le citent, même source, même
  pourquoi »), avec les phrases attestées du corpus (`preuves_corpus`).
* « J'ai ce plat » : recherche TOLÉRANTE du plat (sans accents, pluriels,
  fautes de frappe légères, français ou anglais), puis les bouteilles de la
  cave dont le style est cité, prêtes à boire d'abord.
* Les accords difficiles (artichaut, vinaigrette…) sont signalés quand la
  recherche les touche.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from . import Estimation
from .anglais import en
from .jeu import JeuRegles, jeu, normaliser

MOTS_VIDES = {"de", "du", "des", "la", "le", "les", "au", "aux", "a", "et", "en", "un", "une", "with",
              "and", "the", "of", "in", "sauce", "plat", "plats", "dish"}


def _mots(texte: str) -> list[str]:
    t = re.sub(r"[^a-z0-9 ]", " ", normaliser(texte))
    sortie = []
    for m in t.split():
        if m in MOTS_VIDES or len(m) < 3:
            continue
        sortie.append(m[:-1] if len(m) > 4 and m.endswith(("s", "x")) else m)
    return sortie


@dataclass
class Plat:
    regle: dict
    score: float = 1.0

    @property
    def id(self) -> str:
        return self.regle["id"]

    def nom(self, langue: str = "fr") -> str:
        return self.regle["plat_fr"] if langue == "fr" else en(self.regle["plat_fr"])

    def pourquoi(self, langue: str = "fr") -> str:
        return self.regle["pourquoi_fr"] if langue == "fr" else en(self.regle["pourquoi_fr"])

    def exemples(self, langue: str = "fr") -> str:
        return self.regle.get("exemples_fr", "") if langue == "fr" else en(self.regle.get("exemples_fr", ""))

    @property
    def styles(self) -> list[str]:
        return self.regle["styles"]

    def estimation(self) -> Estimation:
        r = self.regle
        return Estimation({"plat": r["id"], "styles": list(r["styles"]),
                           "preuves": list(r.get("preuves_corpus") or [])},
                          r["pourquoi_fr"], en(r["pourquoi_fr"]), list(r["sources"]), f"accord.{r['id']}",
                          None, r.get("confiance"), {})


@dataclass
class Difficile:
    regle: dict
    score: float = 1.0

    def nom(self, langue: str = "fr") -> str:
        return self.regle["fr"] if langue == "fr" else en(self.regle["fr"])

    def pourquoi(self, langue: str = "fr") -> str:
        return self.regle["pourquoi_fr"] if langue == "fr" else en(self.regle["pourquoi_fr"])


def plats(regles: JeuRegles | None = None) -> list[Plat]:
    regles = regles or jeu()
    return [Plat(p) for p in regles.accords["plats"]]


def _score(requete: list[str], cible: str) -> float:
    """Moyenne, sur les mots de la requête, de la meilleure ressemblance avec un
    mot de la cible ; 0 si aucun mot de la requête n'est vraiment retrouvé
    (ressemblance ≥ 0,85 : « huitre » = « huîtres », « choclat » = « chocolat »)."""
    mots = _mots(cible)
    if not requete or not mots:
        return 0.0
    total, fort = 0.0, False
    for q in requete:
        meilleur = 0.0
        for m in mots:
            if q == m or (len(q) >= 4 and (m.startswith(q) or q.startswith(m))):
                meilleur = 1.0
                break
            meilleur = max(meilleur, difflib.SequenceMatcher(None, q, m).ratio())
        fort = fort or meilleur >= 0.85
        total += meilleur
    return total / len(requete) if fort else 0.0


def chercher_plats(texte: str, regles: JeuRegles | None = None, seuil: float = 0.5) -> list[Plat]:
    """Plats du dossier qui ressemblent à `texte` (meilleurs d'abord), cherchés
    dans le nom français et le nom anglais du plat."""
    regles = regles or jeu()
    q = _mots(texte)
    if not q:
        return []
    trouves = []
    for p in regles.accords["plats"]:
        s = max(_score(q, p["plat_fr"]), _score(q, en(p["plat_fr"])), _score(q, p["id"].replace("_", " ")))
        if normaliser(texte) and normaliser(texte) in normaliser(p["plat_fr"]):
            s = max(s, 1.0)
        if s >= seuil:
            trouves.append(Plat(p, s))
    return sorted(trouves, key=lambda x: -x.score)


def difficiles(texte: str, regles: JeuRegles | None = None, seuil: float = 0.5) -> list[Difficile]:
    regles = regles or jeu()
    q = _mots(texte)
    sortie = []
    for d in regles.accords["accords_difficiles"]:
        s = max(_score(q, d["fr"]), _score(q, en(d["fr"])))
        if s >= seuil:
            sortie.append(Difficile(d, s))
    return sorted(sortie, key=lambda x: -x.score)


def plats_pour_style(style_id: str, regles: JeuRegles | None = None) -> list[Plat]:
    """« J'ouvre ce vin » : les plats qui citent ce style, dans l'ordre du dossier."""
    return [p for p in plats(regles) if style_id in p.styles]


def principes(regles: JeuRegles | None = None) -> list[Estimation]:
    regles = regles or jeu()
    return [Estimation(dict(r["valeur"]), r["explication_fr"], r.get("explication_en", ""),
                       list(r["sources"]), r["id"], None, r.get("confiance"), {})
            for r in regles.accords["principes"]]


#: ordre de priorité des bouteilles proposées (phases de garde.phase / alertes)
PRIORITE_PHASE = {"declin": 0, "passe": 0, "a_boire": 1, "apogee": 2, "apogee_passee": 2, "buvable": 3,
                  None: 4, "trop_jeune": 9}


@dataclass
class Proposition:
    bouteille: dict                  # au moins vin_id, style, phase, alerte (+ ce que l'appelant veut)
    plats: list[Plat] = field(default_factory=list)

    @property
    def rang(self) -> int:
        b = self.bouteille
        cle = "a_boire" if b.get("alerte") == "a_boire" else b.get("phase")
        return PRIORITE_PHASE.get(cle, 4)


def vins_pour_plat(plat: Plat, bouteilles: list[dict], avec_trop_jeunes: bool = False) -> list[Proposition]:
    """Les bouteilles de la cave dont le style est cité pour ce plat. Les trop
    jeunes sont écartées (sauf demande) ; les plus urgentes d'abord (déclin,
    à boire cette année, apogée, buvable)."""
    sortie = []
    for b in bouteilles:
        if b.get("style") not in plat.styles:
            continue
        if b.get("phase") == "trop_jeune" and not avec_trop_jeunes:
            continue
        sortie.append(Proposition(b, [plat]))
    return sorted(sortie, key=lambda p: (p.rang, p.bouteille.get("apogee_fin") or 9999))
