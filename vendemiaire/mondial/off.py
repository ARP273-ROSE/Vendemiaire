# -*- coding: utf-8 -*-
"""Open Food Facts : lecture du code-barres EAN d'une bouteille.

API ouverte (lecture sans compte) ; base sous ODbL, contenus sous DbCL, photos
sous CC BY-SA — crédit « contributeurs d'Open Food Facts ». La recherche par
texte du service est limitée (et souvent indisponible) : seule la lecture par
code-barres est utilisée, une requête par seconde au plus.

Contribuer (option documentée, jamais automatique) : une bouteille absente
peut être ajoutée par l'utilisateur sur le site ou l'application mobile
d'Open Food Facts ; `url_contribuer(ean)` ouvre la bonne page.
"""
from __future__ import annotations

import re

from .appariement import Candidat, Raison

API_PRODUIT = "https://world.openfoodfacts.org/api/v2/product/{ean}.json"
PAGE_PRODUIT = "https://world.openfoodfacts.org/product/{ean}"
LICENCE_BASE = "ODbL 1.0"
LICENCE_IMAGES = "CC BY-SA 3.0"
CREDIT = "Open Food Facts contributors"
CHAMPS = ("code,product_name,product_name_fr,product_name_en,generic_name,brands,quantity,"
          "nutriments,alcohol_value,image_front_url,image_url,origins,countries,categories_tags,"
          "labels,manufacturing_places")


def ean_valide(code: str | None) -> bool:
    """Clé de contrôle d'un EAN-13 / EAN-8 / UPC-A."""
    c = re.sub(r"\D", "", code or "")
    if len(c) not in (8, 12, 13):
        return False
    chiffres = [int(x) for x in c]
    corps, cle = chiffres[:-1], chiffres[-1]
    # règle GTIN : en partant de la droite, poids 3, 1, 3, 1…
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(corps)))
    return (10 - total % 10) % 10 == cle


def eans_dans(texte: str | None) -> list[str]:
    """Codes-barres valides trouvés dans un texte (texte lu sur une contre-étiquette)."""
    vus = []
    for m in re.finditer(r"(?<!\d)(\d[\d ]{6,16}\d)(?!\d)", texte or ""):
        c = m.group(1).replace(" ", "")
        if len(c) in (8, 12, 13) and ean_valide(c) and c not in vus:
            vus.append(c)
    return vus


def produit(client, ean: str) -> dict | None:
    """Fiche du produit, ou None s'il n'est pas dans la base."""
    ean = re.sub(r"\D", "", ean or "")
    d = client.json(API_PRODUIT.format(ean=ean), {"fields": CHAMPS})
    if not d or d.get("status") in (0, "failure") or not d.get("product"):
        return None
    return d["product"]


def degre(p: dict) -> float | None:
    n = p.get("nutriments") or {}
    for cle in ("alcohol_100g", "alcohol_value", "alcohol"):
        v = n.get(cle, p.get(cle))
        try:
            x = float(str(v).replace(",", "."))
        except (TypeError, ValueError):
            continue
        if 0 < x <= 30:
            return x
    return None


def nom(p: dict, langue: str = "fr") -> str:
    return (p.get(f"product_name_{langue}") or p.get("product_name") or p.get("generic_name")
            or "").strip()


def donnees_pour_vin(p: dict) -> dict:
    d = {"ean": p.get("code"), "degre": degre(p)}
    return {k: v for k, v in d.items() if v not in (None, "")}


def candidat(p: dict, langue: str = "fr") -> Candidat:
    """Un code-barres désigne une bouteille sans ambiguïté : le score dit
    seulement que l'identifiant est sûr ; le NOM reste à confirmer à l'œil."""
    libelle = " · ".join(x for x in (p.get("brands"), nom(p, langue), p.get("quantity")) if x)
    raisons = [Raison("appariement.r_ean", {"ean": p.get("code", "")}, 1)]
    if degre(p):
        raisons.append(Raison("appariement.r_degre", {"degre": degre(p)}, 0))
    if p.get("image_front_url"):
        raisons.append(Raison("appariement.r_photo_off", {}, 0))
    return Candidat("off", p.get("code", ""), libelle or p.get("code", ""), 1.0, raisons,
                    donnees_pour_vin(p), brut=p, url=PAGE_PRODUIT.format(ean=p.get("code", "")))


def url_contribuer(ean: str) -> str:
    """Page où l'utilisateur peut ajouter ou compléter le produit lui-même."""
    return PAGE_PRODUIT.format(ean=re.sub(r"\D", "", ean or ""))
