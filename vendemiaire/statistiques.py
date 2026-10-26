# -*- coding: utf-8 -*-
"""Statistiques de la cave (phase 4) : répartitions, valeur dans le temps,
consommation contre achats, courbe d'apogée par couleur.

Tout se compte en BOUTEILLES en cave (ou en valeur retenue : dernière valeur
datée du vin dans ce format, sinon prix d'achat — la même règle que le tableau
de bord et le rapport d'assurance)."""
from __future__ import annotations

from datetime import date

from .regles import garde as r_garde

AXES = ("pays", "region", "couleur", "cepage", "millesime", "prix", "format", "emplacement")
#: tranches de prix (prix retenu d'une bouteille), en unités de la devise
TRANCHES = (10, 20, 40, 80, 150)


def _valeurs_courantes(cave) -> dict:
    return {(r["vin_id"], r["format"]): r["montant"] for r in cave.base.lire(
        "SELECT vin_id, format, montant FROM valeur va WHERE id = (SELECT id FROM valeur v2 WHERE "
        "v2.vin_id=va.vin_id AND v2.format=va.format ORDER BY date DESC, id DESC LIMIT 1)")}


def tranche(prix: float | None) -> str:
    """Code de tranche : « <10 », « 10-20 »…, « >150 », ou « ? »."""
    if prix is None:
        return "?"
    bas = 0
    for haut in TRANCHES:
        if prix < haut:
            return f"<{haut}" if bas == 0 else f"{bas}-{haut}"
        bas = haut
    return f">{TRANCHES[-1]}"


def repartition(cave, axe: str, mesure: str = "bouteilles") -> list[tuple[object, float]]:
    """[(clé, total)] trié du plus grand au plus petit (millésime et prix : dans
    l'ordre naturel). Cépages : une bouteille compte pour chaque cépage au
    prorata de son pourcentage (à parts égales si les pourcentages manquent)."""
    if axe not in AXES:
        raise ValueError(axe)
    valeurs = _valeurs_courantes(cave)
    bouteilles = cave.base.lire(
        "SELECT b.id, b.vin_id, b.format, b.prix_achat, b.emplacement_id, v.pays, v.region, v.couleur, v.millesime "
        "FROM bouteille b JOIN vin v ON v.id=b.vin_id WHERE b.statut='en_cave'")
    cepages: dict[int, list] = {}
    if axe == "cepage":
        for r in cave.base.lire("SELECT vin_id, cepage, pourcentage FROM vin_cepage ORDER BY vin_id, rang"):
            cepages.setdefault(r["vin_id"], []).append((r["cepage"], r["pourcentage"]))
    racines = {}
    if axe == "emplacement":
        racines = cave._racines()
        noms = {e["id"]: e["nom"] for e in cave.emplacements()}
    totaux: dict = {}
    for b in bouteilles:
        prix = valeurs.get((b["vin_id"], b["format"]), b["prix_achat"])
        poids = 1.0 if mesure == "bouteilles" else (prix or 0.0)
        if axe == "cepage":
            liste = cepages.get(b["vin_id"]) or [(None, None)]
            somme = sum(p or 0 for _c, p in liste)
            for c, p in liste:
                part = (p / somme) if somme and p else 1 / len(liste)
                totaux[c] = totaux.get(c, 0) + poids * part
            continue
        if axe == "prix":
            cle = tranche(prix)
        elif axe == "emplacement":
            r = racines.get(b["emplacement_id"])
            cle = noms.get(r) if r else None
        else:
            cle = b[axe]
        totaux[cle] = totaux.get(cle, 0) + poids
    paires = list(totaux.items())
    if axe == "millesime":
        return sorted(paires, key=lambda kv: (kv[0] is None, kv[0] or 0))
    if axe == "prix":
        ordre = ["<10"] + [f"{a}-{b}" for a, b in zip(TRANCHES, TRANCHES[1:])] + [f">{TRANCHES[-1]}", "?"]
        return sorted(paires, key=lambda kv: ordre.index(kv[0]))
    return sorted(paires, key=lambda kv: (-kv[1], str(kv[0])))


def _fins_de_mois(debut: date, fin: date) -> list[date]:
    sortie = []
    a, m = debut.year, debut.month
    while (a, m) <= (fin.year, fin.month):
        suivant = date(a + (m == 12), m % 12 + 1, 1)
        sortie.append(min(fin, date.fromordinal(suivant.toordinal() - 1)))
        a, m = suivant.year, suivant.month
    return sortie


def valeur_dans_le_temps(cave, mois: int = 36, aujourdhui: date | None = None) -> list[tuple[str, float, float, int]]:
    """Pour chaque fin de mois des `mois` derniers mois : (date ISO, coût d'achat
    des bouteilles présentes, valeur retenue À CETTE DATE — dernière valeur
    connue à la date, sinon prix d'achat —, nombre de bouteilles). Une bouteille
    est présente entre son entrée (ou son achat) et sa sortie."""
    aujourdhui = aujourdhui or date.today()
    debut = date(aujourdhui.year - (mois // 12), aujourdhui.month, 1)
    if mois % 12:
        m = aujourdhui.month - mois % 12
        debut = date(debut.year - (m <= 0), (m - 1) % 12 + 1, 1)
    hist: dict = {}
    for r in cave.base.lire("SELECT vin_id, format, montant, date FROM valeur ORDER BY date, id"):
        hist.setdefault((r["vin_id"], r["format"]), []).append((r["date"][:10], r["montant"]))
    bs = cave.base.lire("SELECT vin_id, format, prix_achat, COALESCE(date_entree, date_achat) AS entree, "
                        "date_sortie, statut FROM bouteille WHERE statut NOT IN ('primeur', 'en_attente')")
    points = []
    for fin in _fins_de_mois(debut, aujourdhui):
        f = fin.isoformat()
        cout = valeur = 0.0
        n = 0
        for b in bs:
            if not b["entree"] or b["entree"][:10] > f:
                continue
            if b["date_sortie"] and b["date_sortie"][:10] <= f:
                continue
            if b["statut"] != "en_cave" and not b["date_sortie"]:
                continue
            n += 1
            cout += b["prix_achat"] or 0
            v = None
            for d, montant in hist.get((b["vin_id"], b["format"]), []):
                if d <= f:
                    v = montant
            valeur += v if v is not None else (b["prix_achat"] or 0)
        points.append((f, round(cout, 2), round(valeur, 2), n))
    return points


def consommation_achats(cave) -> list[tuple[int, int, int]]:
    """Par année du livre de cave : (année, bouteilles entrées, bouteilles sorties)."""
    par_an: dict[int, list[int]] = {}
    for r in cave.base.lire("SELECT substr(date,1,4) AS a, type, SUM(quantite) AS n FROM mouvement "
                            "GROUP BY a, type"):
        try:
            a = int(r["a"])
        except (TypeError, ValueError):
            continue
        ligne = par_an.setdefault(a, [0, 0])
        if (r["type"] or "").startswith("entree"):
            ligne[0] += r["n"] or 0
        elif (r["type"] or "").startswith("sortie"):
            ligne[1] += r["n"] or 0
    return [(a, e, s) for a, (e, s) in sorted(par_an.items())]


def rythme(cave, annee: int | None = None) -> dict:
    """Rythme de consommation (moyenne des sorties des 3 dernières années
    pleines) comparé à ce que la courbe d'apogée demande de boire par an."""
    annee = annee or date.today().year
    lignes = {a: (e, s) for a, e, s in consommation_achats(cave)}
    passees = [lignes.get(a, (0, 0)) for a in range(annee - 3, annee)]
    sorties = sum(s for _e, s in passees) / 3
    entrees = sum(e for e, _s in passees) / 3
    courbe = cave.courbe_apogee(annee, 20)
    besoin = sum(b for _a, b, _n in courbe[:5]) / 5 if courbe else 0.0
    return {"sorties_par_an": sorties, "entrees_par_an": entrees, "a_boire_par_an": besoin}


def apogee_par_couleur(cave, annee: int | None = None, annees: int = 20) -> dict[str, list]:
    """{couleur: [(année, à boire, à l'apogée)]} — même calcul que la courbe du
    tableau de bord, couleur par couleur."""
    annee = annee or date.today().year
    etat = [b for b in cave.etat_bouteilles(annee) if b.get("source_fenetre")]
    sortie = {}
    for c in ("rouge", "blanc", "rose", "orange"):
        sous = [b for b in etat if b.get("couleur") == c]
        if sous:
            sortie[c] = r_garde.courbe(sous, annee, annees)
    autres = [b for b in etat if b.get("couleur") not in ("rouge", "blanc", "rose", "orange")]
    if autres:
        sortie[None] = r_garde.courbe(autres, annee, annees)
    return sortie
