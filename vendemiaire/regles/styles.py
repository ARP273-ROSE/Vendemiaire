# -*- coding: utf-8 -*-
"""Rattacher un vin à un « style » du dossier (`styles.json`).

Règle du dossier (LISEZMOI, « Classer un vin dans un style ») : prendre les
styles par priorité croissante ; un style convient si (1) la couleur du vin est
dans `criteres.couleur` et son type dans `criteres.type` ; (2) si au moins une
des listes `appellations`, `regions`, `mots`, `cepages` est non vide, au moins
une expression de ces listes est trouvée (insensible à la casse et aux
accents) dans l'appellation, la cuvée, la région ou les cépages du vin. Les
expressions sont des motifs (l'une d'elles est `\\bpx\\b`) : on les cherche
comme des expressions régulières dans le texte normalisé.

Critères facultatifs (dossier, 26/10/2026) : `millesime` = « avec » (le vin
doit porter un millésime) ou « sans » ; `exclure` = expressions qui, trouvées
comme ci-dessus, écartent le style (banyuls « rimage » : pas oxydatif).

L'utilisateur peut imposer un style (`vin.style`) : il passe alors avant le
classement automatique, qui reste affiché pour mémoire.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .jeu import JeuRegles, jeu, normaliser

#: champs du vin où chercher les expressions, dans l'ordre de l'explication
CHAMPS = (("appellation", "l'appellation", "the appellation"), ("cuvee", "la cuvée", "the cuvée"),
          ("region", "la région", "the region"), ("cepages", "les cépages", "the grapes"))
LISTES = ("appellations", "regions", "mots", "cepages")


@dataclass
class Classement:
    style: dict
    impose: bool = False                       # choisi par l'utilisateur
    raisons_fr: list[str] = field(default_factory=list)
    raisons_en: list[str] = field(default_factory=list)
    automatique: dict | None = None            # style qu'aurait donné le classement

    @property
    def id(self) -> str:
        return self.style["id"]

    def nom(self, langue: str = "fr") -> str:
        return self.style["nom_fr"] if langue == "fr" else self.style["nom_en"]

    def raisons(self, langue: str = "fr") -> list[str]:
        return self.raisons_fr if langue == "fr" else self.raisons_en


def _textes(vin: dict) -> dict[str, str]:
    cep = vin.get("cepages") or []
    cep = " ; ".join(c if isinstance(c, str) else (c[0] or "") for c in cep)
    return {"appellation": normaliser(vin.get("appellation")), "cuvee": normaliser(vin.get("cuvee")),
            "region": normaliser(vin.get("region")), "cepages": normaliser(cep)}


def _cherche(motif: str, textes: dict[str, str]):
    rx = re.compile(normaliser(motif))            # « \bpx\b » traverse normaliser() intact
    for champ, _fr, _en in CHAMPS:
        if textes[champ] and rx.search(textes[champ]):
            return champ
    return None


def convient(style: dict, vin: dict, textes: dict | None = None):
    """(True, raisons) si le style convient au vin ; (False, None) sinon."""
    c = style["criteres"]
    if vin.get("couleur") not in c["couleur"] or (vin.get("type") or "tranquille") not in c["type"]:
        return False, None
    fr = [f"couleur « {vin.get('couleur')} » et type « {vin.get('type') or 'tranquille'} » prévus par le style"]
    en = [f"colour \"{vin.get('couleur')}\" and type \"{vin.get('type') or 'tranquille'}\" match the style"]
    exige = c.get("millesime")
    if exige:
        a_un = bool(vin.get("millesime"))
        if a_un != (exige == "avec"):
            return False, None
        fr.append("millésime présent, exigé par le style" if a_un else "sans millésime, comme l'exige le style")
        en.append("vintage present, required by the style" if a_un else "non-vintage, as the style requires")
    textes = textes or _textes(vin)
    for motif in c.get("exclure") or []:
        if _cherche(motif, textes):
            return False, None
    listes = [m for cle in LISTES for m in c.get(cle) or []]
    if not listes:
        fr.append("style par défaut de cette couleur et de ce type (aucune autre liste)")
        en.append("default style for this colour and type (no other list)")
        return True, (fr, en)
    for cle in LISTES:
        for motif in c.get(cle) or []:
            champ = _cherche(motif, textes)
            if champ:
                ou_fr, ou_en = next((f, e) for k, f, e in CHAMPS if k == champ)
                fr.append(f"« {motif} » trouvé dans {ou_fr} (liste « {cle} » du style)")
                en.append(f"\"{motif}\" found in {ou_en} (style list \"{cle}\")")
                return True, (fr, en)
    return False, None


def classer(vin: dict, regles: JeuRegles | None = None) -> Classement | None:
    """Style du vin ; None si la couleur ou le type manquent (rien à deviner)."""
    regles = regles or jeu()
    textes = _textes(vin)
    auto = None
    for st in regles.styles:
        ok, raisons = convient(st, vin, textes)
        if ok:
            auto = Classement(st, raisons_fr=raisons[0], raisons_en=raisons[1])
            break
    impose = vin.get("style")
    if impose and impose in regles.styles_par_id:
        c = Classement(regles.styles_par_id[impose], impose=True,
                       raisons_fr=["style choisi par vous (le classement automatique reste affiché)"],
                       raisons_en=["style chosen by you (the automatic classification is still shown)"],
                       automatique=auto.style if auto else None)
        return c
    return auto
