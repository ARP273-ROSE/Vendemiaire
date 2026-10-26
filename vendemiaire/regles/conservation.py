# -*- coding: utf-8 -*-
"""Conserver : conseils de cave, alertes de conditions, bouchons fatigués,
bouteille ouverte (`conservation.json`, `bouteille_ouverte.json`).

* Conditions : une mesure est « hors plage » si la température sort de
  10-15 °C ou l'hygrométrie de 55-75 % (`cave.temperature`, `cave.hygrometrie`) ;
  la marge du dossier (± 2 °C, ± 10 %) est affichée, pas ajoutée en silence.
* Bouchons fatigués : bouteilles de plus de 15 ans (`cave.bouchon_fatigue`,
  marge ± 5 ans) — vérifier niveau et bouchon.
* Bouteille ouverte : jours de garde selon le style et le mode (bouchon seul ;
  pompe à vide ou gaz ; Coravin : « semaines à mois », dires du fabricant).
"""
from __future__ import annotations

from datetime import date, timedelta

from . import Estimation
from .anglais import en
from .jeu import JeuRegles, jeu
from .styles import classer

TEMPERATURE = "cave.temperature"
HYGROMETRIE = "cave.hygrometrie"
#: modes de Vendémiaire (referentiels « conservation_ouverte ») -> clés du dossier
MODES = {"bouchon": "jours_bouchon", "vide": "jours_bouchon_et_vide_ou_gaz",
         "gaz": "jours_bouchon_et_vide_ou_gaz", "coravin": "coravin"}


def _est(r: dict, valeur=None) -> Estimation:
    return Estimation(dict(r.get("valeur") or {}) if valeur is None else valeur,
                      r.get("explication_fr", ""), r.get("explication_en", ""),
                      list(r.get("sources") or []), r.get("id", ""), None, r.get("confiance"),
                      dict(r.get("marge") or {}))


def conseils(regles: JeuRegles | None = None) -> list[Estimation]:
    """Les règles de la cave idéale, dans l'ordre du dossier."""
    regles = regles or jeu()
    return [_est(r) for r in regles.conservation["cave"]]


def regle(rid: str, regles: JeuRegles | None = None) -> dict:
    regles = regles or jeu()
    return next(r for r in regles.conservation["cave"] if r["id"] == rid)


def hors_plage(temperature: float | None, hygrometrie: float | None,
               regles: JeuRegles | None = None) -> list[tuple[str, str]]:
    """[(règle, sens)] : (« cave.temperature », « haut » / « bas »)…"""
    regles = regles or jeu()
    t, h = regle("cave.temperature", regles)["valeur"], regle("cave.hygrometrie", regles)["valeur"]
    alertes = []
    if temperature is not None:
        if temperature > t["max_c"]:
            alertes.append(("cave.temperature", "haut"))
        elif temperature < t["min_c"]:
            alertes.append(("cave.temperature", "bas"))
    if hygrometrie is not None:
        if hygrometrie > h["max_pct"]:
            alertes.append(("cave.hygrometrie", "haut"))
        elif hygrometrie < h["min_pct"]:
            alertes.append(("cave.hygrometrie", "bas"))
    return alertes


def age_controle_bouchon(regles: JeuRegles | None = None) -> int:
    return int(regle("cave.bouchon_fatigue", regles)["valeur"]["age_controle_ans"])


def texte_valeur(rid: str, valeur: dict, langue: str) -> str:
    """Valeur d'une règle de cave, lisible (sans changer les chiffres)."""
    t = (lambda s: s) if langue == "fr" else en  # noqa: E731
    if rid == "cave.temperature":
        a, b = valeur["ideal_c"]
        return (f"{valeur['min_c']}–{valeur['max_c']} °C (idéal {a}–{b} °C)" if langue == "fr" else
                f"{valeur['min_c']}–{valeur['max_c']} °C (ideal {a}–{b} °C)")
    if rid == "cave.hygrometrie":
        return f"{valeur['min_pct']}–{valeur['max_pct']} %"
    if rid == "cave.bouchon_fatigue":
        return (f"contrôle au-delà de {valeur['age_controle_ans']} ans" if langue == "fr" else
                f"check beyond {valeur['age_controle_ans']} years")
    if rid == "cave.position":
        if langue == "fr":
            return (f"liège : {valeur['liege']} ; capsule à vis ou synthétique : "
                    f"{valeur['capsule_a_vis_ou_synthetique']} ; effervescent : {valeur['effervescent']}")
        return (f"natural cork: {t(valeur['liege'])}; screw cap or synthetic: "
                f"{t(valeur['capsule_a_vis_ou_synthetique'])}; sparkling: {t(valeur['effervescent'])}")
    if rid == "cave.variations":
        return "non chiffré" if langue == "fr" else "not quantified"
    morceaux = [t(str(v)) for v in valeur.values() if v is not None]
    return ", ".join(morceaux)


# ---------------------------------------------------------------------------- bouteille ouverte
def bouteille_ouverte(vin: dict, mode: str = "bouchon", ouverte_le: date | None = None,
                      regles: JeuRegles | None = None) -> Estimation | None:
    """Combien de jours la garder une fois ouverte. valeur = {jours: [a, b] ou
    None, texte (Coravin), lieu, a_finir_entre: [date, date]}."""
    regles = regles or jeu()
    cl = classer(vin, regles)
    if cl is None:
        return None
    r = next((x for x in regles.ouverte["regles"] if cl.id in x["styles"]), None)
    if r is None:
        return None
    cle = MODES.get(mode, "jours_bouchon")
    v = r["valeur"]
    valeur = {"mode": mode, "lieu": v.get("lieu"), "jours": None, "texte": None, "a_finir_entre": None,
              "style": cl.id}
    if cle == "coravin":
        valeur["texte"] = v.get("coravin")
    else:
        a, b = v[cle]
        valeur["jours"] = [a, b]
        if ouverte_le:
            valeur["a_finir_entre"] = [(ouverte_le + timedelta(days=a)).isoformat(),
                                       (ouverte_le + timedelta(days=b)).isoformat()]
    e = _est(r, valeur)
    modes = regles.ouverte.get("modes")
    if modes and mode != "bouchon":
        e.details_fr.append(modes["explication_fr"])
        e.details_en.append(modes.get("explication_en") or modes["explication_fr"])
        e.sources += [s for s in modes["sources"] if s not in e.sources]
    return e
