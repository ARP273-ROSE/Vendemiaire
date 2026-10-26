# -*- coding: utf-8 -*-
"""Servir un vin d'après le dossier (`service.json`) : température, sortie de
cave, carafe, verre.

* Température : la règle `temp.*` du style (une seule par style), puis les
  ajustements du dossier — vieux vin (+1 °C au-delà de 15 ans pour les rouges
  de garde), plafond 18 °C. On verse au BAS de la plage : le vin gagne environ
  2 °C en dix minutes dans le verre (`temp.ajust.servir_plus_frais`) ; c'est
  aussi la température que vise le tableau « sortie de cave » du dossier
  (rouge 16-18 °C : sortir 1 h 45 avant pour le boire à 16 °C).
* Sortie de cave : loi de Newton du dossier, calibrée sur les durées publiées
  par la Champagne (`service.sortie_de_cave`) :
      t = τ · ln((T_air − T_départ) / (T_air − T_cible))
  avec τ = 2,58 h dans l'air (pièce ou réfrigérateur) et 37,6 min dans un seau
  d'eau glacée ; hypothèses du dossier : pièce 20 °C, réfrigérateur 4 °C, eau
  glacée 0 °C. Marge ± 30 %. Ces paramètres redonnent les tableaux du dossier
  à la minute près (essai `test_sortie_de_cave_redonne_le_tableau`).
* Carafe et verre : toutes les règles du style qui s'appliquent à l'âge du vin,
  puis les règles générales (`*`).
"""
from __future__ import annotations

import html
import math
from dataclasses import dataclass, field

from . import Estimation
from .anglais import en
from .jeu import JeuRegles, jeu
from .styles import Classement, classer

#: hypothèses du dossier (explication de `service.sortie_de_cave`, chapitre « Servir »)
REFRIGERATEUR_C = 4.0
SEAU_C = 0.0


def _est(r: dict, valeur: dict | None = None, fr: str | None = None, en_: str | None = None) -> Estimation:
    return Estimation(valeur if valeur is not None else dict(r.get("valeur") or {}),
                      fr or r.get("explication_fr", ""), en_ or r.get("explication_en", ""),
                      list(r.get("sources") or []), r.get("id", ""), None, r.get("confiance"),
                      dict(r.get("marge") or {}))


def _concerne(r: dict, style_id: str) -> bool:
    return "*" in r["styles"] or style_id in r["styles"]


def newton_minutes(depart: float, air: float, cible: float, tau_min: float) -> float | None:
    """Minutes pour aller de `depart` à `cible` dans un milieu à `air` (loi de
    Newton) ; None si la cible n'est pas entre les deux."""
    if depart == cible:
        return 0.0
    if not (min(depart, air) < cible < max(depart, air)):
        return None
    return tau_min * math.log((air - depart) / (air - cible))


@dataclass
class Service:
    classement: Classement
    age: int | None
    temperature: Estimation              # plage {min_c, max_c} après ajustements
    a_verser_c: float
    sortie: Estimation                    # {action, minutes, frigo_min, seau_min, cave_c, piece_c}
    carafes: list[Estimation] = field(default_factory=list)
    verres: list[Estimation] = field(default_factory=list)
    ajustements: list[Estimation] = field(default_factory=list)


def temperature(style_id: str, age: int | None, regles: JeuRegles | None = None):
    """(règle, plage ajustée {min_c, max_c}, ajustements appliqués)."""
    regles = regles or jeu()
    s = regles.service
    r = next(x for x in s["temperature"] if style_id in x["styles"])
    tmin, tmax = float(r["valeur"]["min_c"]), float(r["valeur"]["max_c"])
    appliques = []
    for a in s["ajustements_temperature"]:
        v = a["valeur"]
        if a["id"] == "temp.ajust.vieux_vin" and _concerne(a, style_id) and age is not None \
                and age >= v.get("age_min_ans", 0):
            tmin, tmax = tmin + v["delta_c"], tmax + v["delta_c"]
            appliques.append(a)
    for a in s["ajustements_temperature"]:
        if "max_c" in a["valeur"] and _concerne(a, style_id):
            plafond = float(a["valeur"]["max_c"])
            if tmax > plafond or tmin > plafond:
                tmin, tmax = min(tmin, plafond), min(tmax, plafond)
                appliques.append(a)
    return r, {"min_c": tmin, "max_c": tmax}, appliques


def sortie_de_cave(cible: float, cave_c: float | None = None, piece_c: float | None = None,
                   regles: JeuRegles | None = None) -> Estimation:
    """Quand sortir (ou rafraîchir) la bouteille pour qu'elle soit à `cible`."""
    regles = regles or jeu()
    r = regles.service["sortie_de_cave"]
    v = r["valeur"]
    cave = float(v["cave_c"] if cave_c is None else cave_c)
    piece = float(v["piece_c"] if piece_c is None else piece_c)
    tau_air, tau_seau = float(v["tau_air_h"]) * 60, float(v["tau_seau_min"])
    valeur = {"cible_c": cible, "cave_c": cave, "piece_c": piece, "action": "rien", "minutes": 0,
              "frigo_min": None, "seau_min": None}
    if abs(cave - cible) < 0.25:
        pass
    elif cave < cible:
        m = newton_minutes(cave, piece, cible, tau_air)
        valeur.update(action="sortir" if m is not None else "piece_trop_froide",
                      minutes=None if m is None else round(m))
    else:
        f = newton_minutes(cave, REFRIGERATEUR_C, cible, tau_air)
        s = newton_minutes(cave, SEAU_C, cible, tau_seau)
        valeur.update(action="rafraichir", minutes=None, frigo_min=None if f is None else round(f),
                      seau_min=None if s is None else round(s))
    return _est(r, valeur)


def service(vin: dict, annee: int, cave_c: float | None = None, piece_c: float | None = None,
            regles: JeuRegles | None = None) -> Service | None:
    regles = regles or jeu()
    cl = classer(vin, regles)
    if cl is None:
        return None
    age = annee - int(vin["millesime"]) if vin.get("millesime") else None
    r, plage, appliques = temperature(cl.id, age, regles)
    est_t = _est(r, dict(plage))
    a_verser = plage["min_c"]
    sortie = sortie_de_cave(a_verser, cave_c, piece_c, regles)
    carafes = []
    for c in regles.service["carafe"]:
        if not _concerne(c, cl.id) or "*" in c["styles"]:
            continue
        v = c["valeur"]
        if "age_max_ans" in v and (age is None or age >= v["age_max_ans"]):
            continue
        if "age_min_ans" in v and (age is None or age < v["age_min_ans"]):
            continue
        carafes.append(_est(c))
    carafes += [_est(c) for c in regles.service["carafe"] if "*" in c["styles"]]
    verres = [_est(v) for v in regles.service["verre"] if cl.id in v["styles"]]
    verres += [_est(v) for v in regles.service["verre"] if "*" in v["styles"]]
    ajust = [_est(a) for a in appliques]
    plus_frais = next((a for a in regles.service["ajustements_temperature"]
                       if a["id"] == "temp.ajust.servir_plus_frais"), None)
    if plus_frais:
        ajust.insert(0, _est(plus_frais))
    return Service(cl, age, est_t, a_verser, sortie, carafes, verres, ajust)


# ---------------------------------------------------------------------------- libellés
ACTIONS_CARAFE = {
    "carafer": ("Carafer", "Decant to aerate"),
    "decanter": ("Décanter (séparer le dépôt)", "Decant off the sediment"),
    "facultatif": ("Carafe facultative", "Decanting optional"),
    "non": ("Pas de carafe", "No decanting"),
    "aerer_si_odeur": ("Aérer si odeur de réduction", "Aerate if it smells reduced"),
    "ouvrir_a_l_avance": ("Ouvrir à l'avance", "Open in advance"),
}


def texte_carafe(e: Estimation, langue: str) -> str:
    v = e.valeur
    fr, en_ = ACTIONS_CARAFE.get(v.get("action"), (v.get("action"), v.get("action")))
    t = fr if langue == "fr" else en_
    if v.get("minutes_max"):
        t += f" : {v.get('minutes_min', 0)}–{v['minutes_max']} min" if langue == "fr" else \
            f": {v.get('minutes_min', 0)}–{v['minutes_max']} min"
    if v.get("heures_max"):
        t += f" : {v.get('heures_min', 0)}–{v['heures_max']} h" if langue == "fr" else \
            f": {v.get('heures_min', 0)}–{v['heures_max']} h"
    if v.get("debout_heures_avant"):
        t += (f" ; bouteille debout {v['debout_heures_avant']} h avant" if langue == "fr" else
              f"; stand the bottle upright {v['debout_heures_avant']} h before")
    return t


def texte_verre(e: Estimation, langue: str) -> str:
    v = e.valeur
    forme = v.get("forme", "")
    t = forme if langue == "fr" else en(forme)
    if v.get("remplissage"):
        t += f", {v['remplissage'] if langue == 'fr' else en(v['remplissage'])}"
    if v.get("dose_cl"):
        a, b = v["dose_cl"]
        t += f", {a}–{b} cl"
    return t


def duree(minutes: float | None, langue: str) -> str:
    if minutes is None:
        return "—"
    m = int(round(minutes))
    if m < 60:
        return f"{m} min"
    h, r = divmod(m, 60)
    return f"{h} h {r:02d}" if r else f"{h} h"


# ---------------------------------------------------------------------------- fiche « ce soir »
def fiche_ce_soir_html(entrees: list[dict], langue: str, titre: str, sous_titre: str = "",
                       pied: str = "") -> str:
    """Page HTML imprimable (et convertible en PDF) : une section par bouteille.

    `entrees` : dicts déjà mis en forme {nom, details, lignes: [(libellé, texte)],
    accords, pourquoi: [texte], sources: [texte]}."""
    e = html.escape
    morceaux = [
        "<!doctype html><html lang='%s'><head><meta charset='utf-8'><title>%s</title>" % (langue, e(titre)),
        "<style>body{font-family:'Source Serif 4','Georgia',serif;color:#2b1d1a;margin:18mm;}"
        "h1{color:#6d1a2a;font-size:22pt;margin:0 0 2pt 0;border-bottom:1.5pt solid #b08d3c;}"
        ".sous{color:#7a6a60;font-size:10pt;margin-bottom:12pt;}"
        "h2{color:#6d1a2a;font-size:15pt;margin:14pt 0 2pt 0;}"
        ".det{color:#7a6a60;font-size:10pt;margin:0 0 6pt 0;}"
        "table{border-collapse:collapse;width:100%;font-size:11pt;}"
        "td{padding:3pt 6pt;vertical-align:top;border-bottom:0.5pt solid #e3d6bf;}"
        "td.l{width:28%;color:#6d1a2a;font-weight:bold;}"
        ".pq{font-size:9pt;color:#4a3b35;margin:4pt 0 0 0;}"
        ".src{font-size:8pt;color:#8a7a70;margin:2pt 0 0 0;}"
        ".pied{font-size:8pt;color:#8a7a70;margin-top:16pt;border-top:0.5pt solid #b08d3c;padding-top:4pt;}"
        "</style></head><body>",
        f"<h1>{e(titre)}</h1>",
        f"<div class='sous'>{e(sous_titre)}</div>" if sous_titre else "",
    ]
    for x in entrees:
        morceaux.append(f"<h2>{e(x['nom'])}</h2>")
        if x.get("details"):
            morceaux.append(f"<div class='det'>{e(x['details'])}</div>")
        morceaux.append("<table>")
        for lib_, txt in x.get("lignes", []):
            morceaux.append(f"<tr><td class='l'>{e(lib_)}</td><td>{e(txt)}</td></tr>")
        morceaux.append("</table>")
        for p in x.get("pourquoi", []):
            morceaux.append(f"<p class='pq'>{e(p)}</p>")
        if x.get("sources"):
            morceaux.append(f"<p class='src'>{e(' ; '.join(x['sources']))}</p>")
    if pied:
        morceaux.append(f"<div class='pied'>{e(pied)}</div>")
    morceaux.append("</body></html>")
    return "".join(morceaux)
