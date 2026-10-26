# -*- coding: utf-8 -*-
"""Import d'un tableau quelconque (Excel .xlsx, CSV) avec correspondance des
colonnes, et import de l'export utilisateur de Vivino.

Excel : lu directement (lecteur XLSX en flux de `mondial.lwin`, sans
dépendance) ; la première ligne non vide donne les en-têtes. Les dates
Excel (nombres de jours depuis 1899-12-30) sont converties.

Vivino : pas d'API ni de format d'export documenté publiquement. L'utilisateur
peut demander ses données à Vivino et obtient des fichiers CSV ; leurs en-têtes
n'ont PAS été vérifiés sur un vrai fichier. Le profil « vivino » ne fait donc
que PROPOSER une correspondance à partir d'en-têtes plausibles (« Winery »,
« Wine name », « Vintage »…) ; l'utilisateur la voit et la corrige avant
d'importer. Une note Vivino (1 à 5 étoiles) devient une dégustation notée sur
5 ; une ligne sans quantité crée le vin seul (pas de bouteille inventée).

Comme tous les imports : jamais d'écrasement d'une saisie manuelle
(`Cave.completer_vin`), vin retrouvé s'il existe déjà, rapport détaillé."""
from __future__ import annotations

import csv
import io
import re
from datetime import date, timedelta
from pathlib import Path

from .echanges import (Rapport, _ajouter, _entier, _reel, _vin_pour_import, format_le_plus_proche,
                       lire_texte, texte_vers_cepages, _litres)
from .regles.jeu import normaliser

#: champs que l'on peut remplir, dans l'ordre de la boîte de correspondance
CHAMPS = ("producteur", "cuvee", "appellation", "region", "pays", "couleur", "type", "millesime",
          "cepages", "degre", "quantite", "format", "prix_achat", "date_achat", "lieu_achat", "note",
          "commentaire", "date_degustation", "notes", "ean")
#: en-têtes reconnus (normalisés : minuscules, sans accents) — FR, EN et en-têtes plausibles de Vivino
SYNONYMES = {
    "producteur": ("producteur", "domaine", "chateau", "producer", "winery", "maison", "estate"),
    "cuvee": ("cuvee", "vin", "nom", "wine", "wine name", "designation", "name"),
    "appellation": ("appellation", "aoc", "aop", "denomination", "sub region", "subregion"),
    "region": ("region", "region viticole", "wine region"),
    "pays": ("pays", "country"),
    "couleur": ("couleur", "color", "colour", "wine type", "type de vin"),
    "type": ("type", "categorie", "category", "regional wine style"),
    "millesime": ("millesime", "annee", "vintage", "year"),
    "cepages": ("cepages", "cepage", "grapes", "grape", "varietal", "variety", "grape variety"),
    "degre": ("degre", "alcool", "abv", "alcohol"),
    "quantite": ("quantite", "nombre", "qte", "bouteilles", "quantity", "qty", "bottles", "count",
                 "user cellar count", "cellar count"),
    "format": ("format", "contenance", "taille", "size", "bottle size"),
    "prix_achat": ("prix", "prix d achat", "prix achat", "price", "purchase price", "cost"),
    "date_achat": ("date d achat", "date achat", "achat", "purchase date", "purchased", "date"),
    "lieu_achat": ("lieu d achat", "fournisseur", "caviste", "store", "purchased from", "vendor"),
    "note": ("note", "ma note", "score", "rating", "your rating", "my rating"),
    "commentaire": ("commentaire", "avis", "review", "your review", "tasting note"),
    "date_degustation": ("date de degustation", "scan date", "tasting date", "drunk"),
    "notes": ("notes", "remarques", "personal note", "note personnelle", "comment"),
    "ean": ("ean", "code barre", "code barres", "barcode", "gtin"),
}
PROFILS = ("generique", "vivino")


def lire_tableau(chemin: str | Path) -> tuple[list[str], list[list[str]]]:
    """(en-têtes, lignes) d'un XLSX ou d'un CSV ; lignes vides retirées."""
    chemin = Path(chemin)
    if chemin.suffix.lower() in (".xlsx", ".xlsm"):
        from .mondial.lwin import lire_xlsx
        brutes = list(lire_xlsx(chemin))
    else:
        texte = lire_texte(chemin)
        ech = texte[:8192]
        sep = max((";", ",", "\t"), key=ech.count)
        brutes = list(csv.reader(io.StringIO(texte), delimiter=sep))
    brutes = [[(x or "").strip() for x in r] for r in brutes if any((x or "").strip() for x in r)]
    if not brutes:
        return [], []
    entetes = brutes[0]
    n = len(entetes)
    return entetes, [r + [""] * (n - len(r)) for r in brutes[1:]]


def deviner(entetes: list[str], profil: str = "generique") -> dict[str, int]:
    """{champ: index de colonne} proposé d'après les en-têtes (chaque colonne sert une fois)."""
    norm = [re.sub(r"[^a-z0-9 ]", " ", normaliser(e)).strip() for e in entetes]
    norm = [re.sub(r"\s+", " ", e) for e in norm]
    pris: set[int] = set()
    sortie: dict[str, int] = {}
    for champ in CHAMPS:
        for syn in SYNONYMES.get(champ, ()):
            for i, e in enumerate(norm):
                if i not in pris and e == syn:
                    sortie[champ] = i
                    pris.add(i)
                    break
            if champ in sortie:
                break
    if profil == "vivino" and "couleur" not in sortie and "type" in sortie:
        sortie["couleur"] = sortie["type"]
    return sortie


def date_iso(v) -> str | None:
    t = (v or "").strip()
    if not t:
        return None
    if re.fullmatch(r"\d{5}(\.\d+)?", t):                     # date Excel
        jours = float(t)
        if 20000 < jours < 80000:
            return (date(1899, 12, 30) + timedelta(days=int(jours))).isoformat()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.match(r"^(\d{1,2})[/.](\d{1,2})[/.](\d{4})", t)
    if m:                                                     # jour/mois/année (usage français)
        return f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return None


def couleur_type(texte_couleur: str, texte_type: str = "") -> tuple[str | None, str]:
    t = normaliser(f"{texte_couleur} {texte_type}")
    couleur = None
    if re.search(r"\bros", t):
        couleur = "rose"
    elif re.search(r"\b(white|blanc)", t):
        couleur = "blanc"
    elif re.search(r"\b(red|rouge)", t):
        couleur = "rouge"
    elif re.search(r"\b(orange|amber)", t):
        couleur = "orange"
    if re.search(r"sparkling|effervescent|champagne|petillant|cremant|prosecco|cava", t):
        typ = "effervescent"
        couleur = couleur or "blanc"
    elif re.search(r"fortified|porto|port\b|sherry|xeres|mute|madeira|madere", t):
        typ = "mute"
    elif re.search(r"dessert|sweet|liquoreux|moelleux|doux", t):
        typ = "doux"
        couleur = couleur or "blanc"
    else:
        typ = "tranquille"
    return couleur, typ


def _format(texte: str) -> str:
    t = normaliser(texte)
    if not t:
        return "bouteille"
    for code in ("magnum", "demi", "jeroboam", "mathusalem", "clavelin", "piccolo"):
        if code in t:
            return {"jeroboam": "double_magnum"}.get(code, code)
    if "half" in t:
        return "demi"
    litres = _litres(texte)
    if litres is None:
        r = _reel(texte)
        litres = (r / 100 if r > 10 else r) if r else None      # « 75 » = 75 cl, « 1.5 » = 1,5 L
    return format_le_plus_proche(litres)


def importer(cave, entetes: list[str], lignes: list[list[str]], correspondance: dict[str, int],
             source: str = "tableur", echelle_note: str = "5", quantite_defaut: int = 0) -> Rapport:
    """Importe les lignes. `quantite_defaut` : bouteilles par ligne si la
    colonne « quantité » manque ou est vide (0 = le vin seul)."""
    rapport = Rapport()

    def val(ligne, champ):
        i = correspondance.get(champ)
        return ligne[i].strip() if i is not None and i < len(ligne) else ""

    for n, l in enumerate(lignes, 2):
        rapport.lignes += 1
        if not any(val(l, c) for c in ("producteur", "cuvee", "appellation")):
            rapport.avertissements.append(f"ligne {n} : ni producteur, ni cuvée, ni appellation — ignorée")
            continue
        couleur, typ = couleur_type(val(l, "couleur"), val(l, "type"))
        vin = {"producteur": val(l, "producteur"), "cuvee": val(l, "cuvee"), "appellation": val(l, "appellation"),
               "region": val(l, "region"), "pays": val(l, "pays"), "couleur": couleur, "type": typ,
               "millesime": _entier(val(l, "millesime")), "degre": _reel(val(l, "degre")),
               "cepages": texte_vers_cepages(val(l, "cepages").replace(",", ";")), "notes": val(l, "notes"),
               "ean": re.sub(r"\D", "", val(l, "ean")) or None}
        if vin["millesime"] is not None and not 1700 <= vin["millesime"] <= 2200:
            vin["millesime"] = None                          # « N.V. », 0…
        vin_id = _vin_pour_import(cave, vin, source, rapport, f"ligne {n}")
        q = _entier(val(l, "quantite"))
        q = quantite_defaut if q is None else q
        if q and q > 0:
            b = {"format": _format(val(l, "format")), "prix_achat": _reel(val(l, "prix_achat")),
                 "date_achat": date_iso(val(l, "date_achat")), "lieu_achat": val(l, "lieu_achat") or None}
            b = {k: v for k, v in b.items() if v not in (None, "")}
            for _ in range(min(q, 500)):
                _ajouter(cave, vin_id, b, None)
                rapport.bouteilles += 1
        note = _reel(val(l, "note"))
        if note is not None or val(l, "commentaire"):
            cave.enregistrer_degustation({
                "vin_id": vin_id, "date": date_iso(val(l, "date_degustation")) or date.today().isoformat(),
                "note": note, "echelle": echelle_note if note is not None else None,
                "commentaire": val(l, "commentaire") or None, "privee": 1})
    return rapport
