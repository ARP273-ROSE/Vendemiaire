# -*- coding: utf-8 -*-
"""Petites cartes des régions (contours simplifiés de `donnees/cartes_simplifiees.json`,
fabriqué par `outils/cartes_simplifiees.py` : Natural Earth, domaine public ; positions
des régions d'après les cartes du dossier « Le vin »).

Deux rendus du même dessin : TikZ (carte des vins LaTeX) et SVG (aperçu HTML,
repli PDF par Qt). Projection équirectangulaire corrigée de cos(latitude) :
suffisante à cette échelle (quelques centimètres)."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..regles.jeu import normaliser

FICHIER = Path(__file__).resolve().parent.parent / "donnees" / "cartes_simplifiees.json"


@lru_cache(maxsize=1)
def donnees() -> dict:
    try:
        return json.loads(FICHIER.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"pays": {}, "regions": []}


def pays_geo(nom: str | None) -> tuple[str, dict] | None:
    """Entrée « pays » pour un nom de la cave (« France », « Italy »…)."""
    if not nom:
        return None
    n = normaliser(nom)
    for cle, info in donnees()["pays"].items():
        if normaliser(cle) == n or normaliser(info.get("en", "")) == n or info.get("iso", "").lower() == n:
            return cle, info
    return None


def nom_pays(nom: str | None, langue: str) -> str:
    """Nom du pays dans la langue du document (« Italie » -> « Italy »)."""
    if not nom:
        return ""
    trouve = pays_geo(nom)
    if trouve is None:
        return nom
    return trouve[1].get("en", nom) if langue == "en" else trouve[0]


def region_geo(pays: str | None, *textes) -> dict | None:
    """Point d'une région du pays qui apparaît dans les textes (région,
    sous-région, appellation du vin), le nom le plus long d'abord."""
    trouve = pays_geo(pays)
    if trouve is None:
        return None
    cle_pays = trouve[0]
    candidats = sorted((r for r in donnees()["regions"] if r["pays"] == cle_pays),
                       key=lambda r: -len(r["nom"]))
    for t in textes:
        n = f" {normaliser(t)} "
        if not n.strip():
            continue
        for r in candidats:
            if f" {normaliser(r['nom'])} " in n:
                return r
    return None


@dataclass
class Dessin:
    largeur: float              # unités du dessin (cm pour TikZ, px pour SVG)
    hauteur: float
    anneaux: list[list[tuple[float, float]]]
    points: list[tuple[float, float, str, str, float]]   # x, y, nom, côté de l'étiquette (« d »/« g »), décalage vertical


def projeter(pays: str, regions: list[dict], largeur: float, hauteur: float,
             taille_lettre: float) -> Dessin | None:
    trouve = pays_geo(pays)
    if trouve is None:
        return None
    info = trouve[1]
    o, s, e, n = info["cadre"]
    lat0 = math.radians((s + n) / 2)
    k = math.cos(lat0)
    w, h = (e - o) * k, (n - s)
    echelle = min(largeur / w, hauteur / h)
    W, H = w * echelle, h * echelle

    def xy(lon, lat):
        return ((lon - o) * k * echelle, (lat - s) * echelle)

    anneaux = [[xy(lon, lat) for lon, lat in a] for a in info["anneaux"]]
    points, boites = [], []
    # étiquettes : à droite, à gauche, puis décalées d'une demi-ligne vers le haut ou le bas, la première
    # place libre l'emporte (les régions voisines — Bourgogne, Jura, Beaujolais — ne se chevauchent plus)
    essais = [("d", 0.0), ("g", 0.0), ("d", 0.75), ("d", -0.75), ("g", 0.75), ("g", -0.75), ("d", 1.5), ("g", -1.5)]
    for r in sorted(regions, key=lambda r: -r["lat"]):
        x, y = xy(r["lon"], r["lat"])
        long_txt = taille_lettre * 0.55 * len(r["nom"])
        choix = ("d", 0.0)
        for cote, dy in essais:
            x0 = x + taille_lettre * 0.4 if cote == "d" else x - taille_lettre * 0.4 - long_txt
            yc = y + dy * taille_lettre
            b = (x0, yc - taille_lettre * 0.5, x0 + long_txt, yc + taille_lettre * 0.5)
            hors = b[0] < -W * 0.25 or b[2] > W * 1.25
            if not hors and not any(not (b[2] < c[0] or b[0] > c[2] or b[3] < c[1] or b[1] > c[3])
                                    for c in boites):
                choix = (cote, dy)
                boites.append(b)
                break
        points.append((x, y, r["nom"], choix[0], choix[1] * taille_lettre))
    return Dessin(W, H, anneaux, points)


def tikz(pays: str, regions: list[dict], largeur_cm: float = 5.0, hauteur_cm: float = 5.0,
         remplissage: str = "carte", trait: str = "carteTrait", point: str = "cartePoint",
         echapper=lambda t: t) -> str:
    d = projeter(pays, regions, largeur_cm, hauteur_cm, 0.22)
    if d is None:
        return ""
    lignes = [r"\begin{tikzpicture}[x=1cm,y=1cm]"]
    for a in d.anneaux:
        chemin = " -- ".join(f"({x:.2f},{y:.2f})" for x, y in a)
        lignes.append(rf"\filldraw[fill={remplissage},draw={trait},line width=0.3pt,line join=round] {chemin} -- cycle;")
    for x, y, nom, cote, dy in d.points:
        ancre = "west" if cote == "d" else "east"
        lignes.append(rf"\fill[{point}] ({x:.2f},{y:.2f}) circle (1.1pt);")
        lignes.append(rf"\node[anchor={ancre},inner sep=1.5pt,font=\scriptsize] at ({x:.2f},{y + dy:.2f}) {{{echapper(nom)}}};")
    lignes.append(r"\end{tikzpicture}")
    return "\n".join(lignes)


def svg(pays: str, regions: list[dict], largeur_px: int = 260, hauteur_px: int = 240,
        remplissage: str = "#EFE6D2", trait: str = "#8E2A3D", point: str = "#5E1427",
        police: str = "Georgia, serif") -> str:
    marge = 6
    d = projeter(pays, regions, largeur_px - 2 * marge, hauteur_px - 2 * marge, 11)
    if d is None:
        return ""
    W, H = d.largeur + 2 * marge, d.hauteur + 2 * marge

    def p(x, y):
        return f"{x + marge:.1f},{H - (y + marge):.1f}"

    from html import escape
    corps = []
    for a in d.anneaux:
        corps.append(f'<polygon points="{" ".join(p(x, y) for x, y in a)}" fill="{remplissage}" '
                     f'stroke="{trait}" stroke-width="0.8" stroke-linejoin="round"/>')
    for x, y, nom, cote, dy in d.points:
        px, py = (float(v) for v in p(x, y).split(","))
        corps.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.6" fill="{point}"/>')
        tx = px + 5 if cote == "d" else px - 5
        ancre = "start" if cote == "d" else "end"
        corps.append(f'<text x="{tx:.1f}" y="{py - dy + 3.5:.1f}" font-size="10.5" font-family="{police}" '
                     f'text-anchor="{ancre}" fill="#2A1A14">{escape(nom)}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
            f'viewBox="0 0 {W:.0f} {H:.0f}">' + "".join(corps) + "</svg>")
