# -*- coding: utf-8 -*-
"""Fabrique `vendemiaire/donnees/cartes_simplifiees.json` : contours SIMPLIFIÉS
des pays du vin et positions approchées de leurs régions, pour les petites
cartes de la carte des vins.

Pourquoi pas les cartes du dossier « Le vin » ? Elles pèsent 136 Mo (relief,
aires parcellaires INAO, rivières OpenStreetMap sous licence ODbL) : trop
lourdes pour l'application et soumises à des obligations d'attribution par
couche. On garde ici l'essentiel, libre et léger (≈ 150 Ko) :

* contours : Natural Earth 1:10 m, « Admin 0 – Countries » (domaine public),
  recadrés sur la partie viticole (métropole, États contigus…) puis simplifiés
  (Douglas-Peucker, 0,03°) et arrondis au centième de degré ;
* régions : positions des étiquettes des cartes du dossier « Le vin »
  (`data/regions_europe.json`, `regions_monde.json`) et centres des cadres de
  ses cartes régionales (`regions_france.json`, `regions_pays.json`).

    python outils/cartes_simplifiees.py <ne_10m_admin_0_countries.shp> <dossier Le vin>

Dépendance de l'outil seulement (pas de l'application) : `pyshp`.
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "vendemiaire" / "donnees" / "cartes_simplifiees.json"
TOLERANCE = 0.03

#: nom usuel (français, comme dans la cave) -> (code ISO 3, nom anglais, cadre [o, s, e, n] ou None)
PAYS = {
    "France": ("FRA", "France", (-5.3, 41.3, 9.7, 51.2)),
    "Italie": ("ITA", "Italy", None),
    "Espagne": ("ESP", "Spain", (-9.6, 35.8, 4.4, 43.9)),
    "Portugal": ("PRT", "Portugal", (-9.6, 36.9, -6.1, 42.2)),
    "Allemagne": ("DEU", "Germany", None),
    "Autriche": ("AUT", "Austria", None),
    "Suisse": ("CHE", "Switzerland", None),
    "Hongrie": ("HUN", "Hungary", None),
    "Grèce": ("GRC", "Greece", None),
    "Géorgie": ("GEO", "Georgia", None),
    "Arménie": ("ARM", "Armenia", None),
    "Liban": ("LBN", "Lebanon", None),
    "Israël": ("ISR", "Israel", None),
    "Slovénie": ("SVN", "Slovenia", None),
    "Croatie": ("HRV", "Croatia", None),
    "Roumanie": ("ROU", "Romania", None),
    "Moldavie": ("MDA", "Moldova", None),
    "Bulgarie": ("BGR", "Bulgaria", None),
    "Chypre": ("CYP", "Cyprus", None),
    "Royaume-Uni": ("GBR", "United Kingdom", (-8.7, 49.8, 2.0, 59.0)),
    "États-Unis": ("USA", "United States", (-125.0, 24.0, -66.0, 49.6)),
    "Canada": ("CAN", "Canada", (-128.0, 41.5, -60.0, 53.0)),
    "Mexique": ("MEX", "Mexico", None),
    "Argentine": ("ARG", "Argentina", (-74.0, -55.5, -53.0, -21.7)),
    "Chili": ("CHL", "Chile", (-76.0, -56.0, -66.0, -17.4)),
    "Uruguay": ("URY", "Uruguay", None),
    "Brésil": ("BRA", "Brazil", None),
    "Australie": ("AUS", "Australia", (112.0, -44.0, 154.0, -10.0)),
    "Nouvelle-Zélande": ("NZL", "New Zealand", (166.0, -47.5, 179.0, -34.0)),
    "Afrique du Sud": ("ZAF", "South Africa", (16.0, -35.0, 33.0, -22.0)),
    "Chine": ("CHN", "China", None),
    "Japon": ("JPN", "Japan", (128.0, 30.0, 146.0, 46.0)),
    "Inde": ("IND", "India", None),
}
#: cartes régionales du dossier : identifiant -> nom affiché (centre du cadre)
NOMS_CADRES = {
    "medoc": "Médoc", "libournais": "Libournais", "graves_sauternes": "Graves et Sauternes",
    "bourgogne": "Bourgogne", "cote_nuits": "Côte de Nuits", "cote_beaune": "Côte de Beaune",
    "chablis": "Chablis", "beaujolais": "Beaujolais", "muscadet": "Muscadet", "jura": "Jura",
    "savoie": "Savoie", "rhone_nord": "Rhône nord", "rhone_sud": "Rhône sud", "corse": "Corse",
    "sud_ouest": "Sud-Ouest", "piemont": "Piémont", "toscane": "Toscane", "venetie": "Vénétie",
    "etna": "Etna", "santorin": "Santorin", "rioja": "Rioja", "douro": "Douro", "moselle": "Moselle",
    "tokaj": "Tokaj", "californie": "Californie", "napa": "Napa", "sonoma": "Sonoma",
    "central_coast": "Central Coast", "willamette": "Willamette", "new_york": "Finger Lakes",
    "mendoza": "Mendoza", "salta": "Salta", "chili_centre": "Chili central",
    "australie_sud": "Australie-Méridionale", "victoria": "Victoria", "margaret_river": "Margaret River",
    "tasmanie": "Tasmanie", "hunter": "Hunter", "marlborough": "Marlborough", "otago": "Central Otago",
    "hawkes_bay": "Hawke's Bay", "wairarapa": "Wairarapa", "cap": "Le Cap", "niagara": "Niagara",
    "okanagan": "Okanagan", "kakhetie": "Kakhétie",
}


#: régions au ras d'une frontière : pays donné (la péninsule du Niagara est en Ontario)
PAYS_IMPOSE = {"Niagara": "Canada"}


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t)
    return "".join(c for c in t if not unicodedata.combining(c)).lower().replace("-", " ").replace("'", " ")


def dp(points, tol):
    """Douglas-Peucker."""
    if len(points) < 3:
        return points
    (x1, y1), (x2, y2) = points[0], points[-1]
    dx, dy = x2 - x1, y2 - y1
    l2 = dx * dx + dy * dy
    imax, dmax = 0, -1.0
    for i in range(1, len(points) - 1):
        x, y = points[i]
        if l2 == 0:
            d = ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
        else:
            t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / l2))
            d = ((x - x1 - t * dx) ** 2 + (y - y1 - t * dy) ** 2) ** 0.5
        if d > dmax:
            imax, dmax = i, d
    if dmax <= tol:
        return [points[0], points[-1]]
    return dp(points[:imax + 1], tol)[:-1] + dp(points[imax:], tol)


def aire(anneau) -> float:
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(anneau, anneau[1:] + anneau[:1]))) / 2


def dedans(x, y, anneau) -> bool:
    c = False
    for (x1, y1), (x2, y2) in zip(anneau, anneau[1:] + anneau[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def main(shp: str, dossier: str) -> int:
    import shapefile
    lecteur = shapefile.Reader(shp, encoding="utf-8")
    champs = [f[0] for f in lecteur.fields[1:]]
    par_iso = {}
    for enr in lecteur.iterShapeRecords():
        rec = dict(zip(champs, enr.record))
        iso = rec.get("ADM0_A3") or rec.get("ISO_A3")
        par_iso.setdefault(iso, []).append(enr.shape)
    pays_sortie = {}
    for nom, (iso, nom_en, cadre) in PAYS.items():
        anneaux = []
        for forme in par_iso.get(iso, []):
            parts = list(forme.parts) + [len(forme.points)]
            for a, b in zip(parts, parts[1:]):
                anneau = [tuple(p) for p in forme.points[a:b]]
                if cadre:
                    o, s, e, n = cadre
                    cx = sum(p[0] for p in anneau) / len(anneau)
                    cy = sum(p[1] for p in anneau) / len(anneau)
                    if not (o <= cx <= e and s <= cy <= n):
                        continue
                anneaux.append(anneau)
        if not anneaux:
            print("pays absent :", nom, iso)
            continue
        plus_grande = max(aire(a) for a in anneaux)
        garde = []
        for a in anneaux:
            if aire(a) < plus_grande * 0.004:          # îlots invisibles à cette échelle
                continue
            s = dp(a, TOLERANCE)
            if len(s) >= 4:
                garde.append([[round(x, 2), round(y, 2)] for x, y in s])
        xs = [p[0] for a in garde for p in a]
        ys = [p[1] for a in garde for p in a]
        pays_sortie[nom] = {"iso": iso, "en": nom_en, "cadre": [min(xs), min(ys), max(xs), max(ys)],
                            "anneaux": garde}
    d = Path(dossier) / "data"
    regions = []
    vus = set()

    def ajouter(nom, lon, lat):
        cle = norm(nom)
        if cle in vus:
            return
        if nom in PAYS_IMPOSE:                          # frontière trop proche pour le contour simplifié
            regions.append({"nom": nom, "pays": PAYS_IMPOSE[nom], "lon": round(lon, 2), "lat": round(lat, 2)})
            vus.add(cle)
            return
        for p, info in pays_sortie.items():
            if any(dedans(lon, lat, a) for a in info["anneaux"]):
                regions.append({"nom": nom, "pays": p, "lon": round(lon, 2), "lat": round(lat, 2)})
                vus.add(cle)
                return
        # tout près de la côte (contour simplifié) : le pays dont le cadre le contient
        for p, info in pays_sortie.items():
            o, s, e, n = info["cadre"]
            if o <= lon <= e and s <= lat <= n:
                regions.append({"nom": nom, "pays": p, "lon": round(lon, 2), "lat": round(lat, 2)})
                vus.add(cle)
                return

    for fichier in ("regions_europe.json", "regions_monde.json"):
        for r in json.loads((d / fichier).read_text(encoding="utf-8")):
            nom = r["nom"].split(" (")[0]
            ajouter(nom, r["lon"], r["lat"])
    for fichier in ("regions_france.json", "regions_pays.json"):
        for cle, r in json.loads((d / fichier).read_text(encoding="utf-8")).items():
            if cle in NOMS_CADRES and isinstance(r, dict) and r.get("bbox"):
                o, s, e, n = r["bbox"]
                ajouter(NOMS_CADRES[cle], (o + e) / 2, (s + n) / 2)
    sortie = {
        "version": 1,
        "explication": "Contours simplifiés (Natural Earth 1:10 m, domaine public) et positions approchées des régions "
                       "(d'après les cartes du dossier « Le vin »), pour les petites cartes de la carte des vins.",
        "sources": ["Natural Earth, Admin 0 – Countries 1:10m (domaine public, naturalearthdata.com)",
                    "Dossier « Le vin » : positions des étiquettes et cadres de ses cartes régionales"],
        "pays": pays_sortie,
        "regions": regions,
    }
    SORTIE.write_text(json.dumps(sortie, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(SORTIE, f"{SORTIE.stat().st_size // 1024} Ko", len(pays_sortie), "pays", len(regions), "régions")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
