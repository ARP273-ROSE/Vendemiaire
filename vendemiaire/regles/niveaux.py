# -*- coding: utf-8 -*-
"""Ce que veut dire le niveau d'une vieille bouteille selon son âge
(`niveaux.json` : échelle bordelaise des ventes aux enchères, bourguignonne en
centimètres sous le bouchon).

Lecture des champs du dossier :
* `normal_si_age_min_ans` : à partir de cet âge, le niveau est normal ; plus
  jeune, il est BAS pour son âge (signal : bouchon ou conservation) ;
  `null` = risqué à tout âge ;
* `excellent_si_age_min_ans` : à partir de cet âge, c'est excellent pour l'âge ;
* bourgogne : la première ligne dont `cm_max` couvre la mesure ; au-delà de
  7 cm, l'échelle du dossier s'arrête (on le dit).
"""
from __future__ import annotations

from . import Estimation
from .anglais import en
from .jeu import JeuRegles, jeu

#: verdicts (codes) ; libellés FR/EN dans textes.py (« niveau.verdict_* »)
VERDICTS = ("excellent", "normal", "bas_pour_age", "risque", "inconnu", "hors_echelle")


def bordelais(code: str, age: int | None, regles: JeuRegles | None = None) -> Estimation | None:
    regles = regles or jeu()
    n = next((x for x in regles.niveaux["bordelaise"] if x["code"] == code), None)
    if n is None:
        return None
    normal, excellent = n.get("normal_si_age_min_ans"), n.get("excellent_si_age_min_ans")
    if normal is None:
        verdict = "risque"
    elif age is None:
        verdict = "inconnu"
    elif excellent is not None and age >= excellent:
        verdict = "excellent"
    elif age >= normal:
        verdict = "normal"
    else:
        verdict = "bas_pour_age"
    valeur = {"code": code, "verdict": verdict, "risque": n.get("risque"), "normal_des": normal,
              "excellent_des": excellent, "nom_fr": n["nom_fr"], "nom_en": n["nom_en"]}
    return Estimation(valeur, n["explication_fr"], en(n["explication_fr"]), list(n["sources"]),
                      f"niveau.{code}", None, None, {})


def bourguignon(cm: float, age: int | None, regles: JeuRegles | None = None) -> Estimation | None:
    regles = regles or jeu()
    lignes = sorted(regles.niveaux["bourguignonne_cm"], key=lambda x: x["cm_max"])
    n = next((x for x in lignes if cm <= x["cm_max"]), None)
    if n is None:
        dernier = lignes[-1]
        return Estimation({"cm": cm, "verdict": "hors_echelle", "cm_max_echelle": dernier["cm_max"]},
                          dernier["explication_fr"], en(dernier["explication_fr"]),
                          list(dernier["sources"]), "niveau.bourgogne", None, None, {})
    normal = n.get("normal_si_age_min_ans")
    if age is None:
        verdict = "inconnu"
    elif normal is not None and age >= normal:
        verdict = "excellent" if normal == 0 else "normal"
    else:
        verdict = "bas_pour_age"
    return Estimation({"cm": cm, "verdict": verdict, "cm_max": n["cm_max"], "normal_des": normal},
                      n["explication_fr"], en(n["explication_fr"]), list(n["sources"]),
                      f"niveau.bourgogne.{n['cm_max']}", None, None, {})


def sens_niveau(code: str | None, age: int | None, cm: float | None = None,
                regles: JeuRegles | None = None) -> Estimation | None:
    if code:
        return bordelais(code, age, regles)
    if cm:
        return bourguignon(cm, age, regles)
    return None
