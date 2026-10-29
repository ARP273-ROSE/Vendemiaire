# -*- coding: utf-8 -*-
"""Registres officiels des appellations viticoles : orthographe et complétion.

Deux sources publiques, embarquées dans l'application (dossier `donnees/`,
date d'extraction dans `donnees/sources.json`) et rafraîchissables en ligne :

* **INAO** — « Référentiel des produits sous signe officiel d'identification de
  la qualité et de l'origine (SIQO) », data.gouv.fr, Licence Ouverte 2.0 :
  appellations françaises ET leurs dénominations (premiers crus, dénominations
  géographiques complémentaires), en orthographe française officielle.
* **eAmbrosia** — registre des indications géographiques de l'Union européenne
  (Commission européenne, API publique) : AOP/IGP de tous les pays de l'UE et
  des pays tiers protégés dans l'UE. Réutilisation autorisée avec mention de la
  source (décision 2011/833/UE).

Les deux se lisent ici depuis leur format d'origine ; `outils/registres_appellations.py`
produit les copies embarquées avec ces mêmes fonctions.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Iterable, Iterator

DOSSIER_DONNEES = Path(__file__).resolve().parent.parent / "donnees"
FICHIERS = {"inao": "appellations_inao.csv", "eambrosia": "appellations_eambrosia.csv"}

URL_INAO_JEU = ("https://www.data.gouv.fr/api/1/datasets/69538fa5e19db626e660563d/")
PAGE_INAO = ("https://www.data.gouv.fr/datasets/referentiel-des-produits-sous-signe-officiel-"
             "didentification-de-la-qualite-et-de-lorigine-siqo")
URL_EAMBROSIA = ("https://webgate.ec.europa.eu/eambrosia-api/api/v1/geographical-indications"
                 "?productType=WINE")
PAGE_EAMBROSIA = "https://ec.europa.eu/agriculture/eambrosia/geographical-indications-register/"
LICENCES = {"inao": "Licence Ouverte 2.0 (Etalab)",
            "eambrosia": "© Union européenne — réutilisation autorisée (décision 2011/833/UE)"}

CHAMPS = ("nom", "parent", "signe", "pays", "identifiant", "statut", "categories")


# ---------------------------------------------------------------- INAO
def depuis_inao(texte_csv: str) -> list[dict]:
    """CSV SIQO de l'INAO -> une ligne par appellation ou dénomination viticole."""
    echantillon = texte_csv[:4096]
    sep = ";" if echantillon.count(";") > echantillon.count(",") else ","
    lignes = csv.DictReader(io.StringIO(texte_csv.lstrip("﻿")), delimiter=sep)
    par_nom: dict[tuple, dict] = {}
    for r in lignes:
        if (r.get("classe_ue") or "").strip() != "Vins":
            continue
        appellation = (r.get("appellation") or "").strip()
        denomination = (r.get("denomination") or "").strip() or appellation
        if not denomination:
            continue
        signe = ((r.get("signe_ue") or "").strip() or (r.get("signe_fr") or "").strip())
        for nom, parent, ident in ((appellation, None, r.get("id_appellation")),
                                   (denomination, appellation if denomination != appellation
                                    else None, r.get("id_denomination_geo"))):
            if not nom:
                continue
            cle = (nom, parent)
            e = par_nom.setdefault(cle, {"nom": nom, "parent": parent, "signe": signe,
                                         "pays": "FR", "identifiant": (ident or "").strip(),
                                         "statut": (r.get("lib_etat") or "").strip(),
                                         "categories": set()})
            cat = (r.get("categorie") or "").strip()
            if cat:
                e["categories"].add(cat)
    sortie = []
    for e in par_nom.values():
        e["categories"] = "; ".join(sorted(e["categories"]))
        sortie.append(e)
    sortie.sort(key=lambda e: (e["parent"] or e["nom"], e["parent"] is not None, e["nom"]))
    return sortie


def url_csv_inao(client) -> str:
    """Adresse du CSV le plus récent du jeu de données (API de data.gouv.fr)."""
    jeu = client.json(URL_INAO_JEU)
    ressources = [r for r in jeu.get("resources", [])
                  if (r.get("format") or "").lower() == "csv"]
    if not ressources:
        raise ValueError("aucun CSV dans le jeu de données de l'INAO")
    ressources.sort(key=lambda r: r.get("last_modified") or "", reverse=True)
    return ressources[0]["url"]


# ---------------------------------------------------------------- eAmbrosia
def depuis_eambrosia(donnees: list[dict]) -> list[dict]:
    """Réponse JSON de l'API eAmbrosia (vins) -> une ligne par nom protégé."""
    sortie = []
    for gi in donnees:
        # « WINE » à l'extraction du 26/10/2026, « Wine » trois jours plus tard : casse ignorée
        if gi.get("removedFlag") or (gi.get("productType") or "WINE").strip().upper() != "WINE":
            continue
        for nom in gi.get("protectedNames") or []:
            nom = (nom or "").strip()
            if nom:
                sortie.append({"nom": nom, "parent": None, "signe": gi.get("giType"),
                               "pays": ",".join(gi.get("countries") or []),
                               "identifiant": gi.get("fileNumber") or gi.get("giIdentifier"),
                               "statut": gi.get("status"), "categories": ""})
    sortie.sort(key=lambda e: (e["pays"], e["nom"]))
    return sortie


# ---------------------------------------------------------------- fichiers
def ecrire_csv(lignes: Iterable[dict], chemin: Path) -> int:
    n = 0
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS, delimiter=";", lineterminator="\n")
        w.writeheader()
        for l in lignes:
            w.writerow({k: l.get(k) or "" for k in CHAMPS})
            n += 1
    return n


def lire_csv(chemin: Path) -> Iterator[dict]:
    with open(chemin, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            yield {k: (r.get(k) or None) for k in CHAMPS}


def sources_embarquees() -> dict:
    try:
        return json.loads((DOSSIER_DONNEES / "sources.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def charger_embarques(refs) -> dict[str, int]:
    """Remplit la base de référence avec les registres livrés (si elle n'en a
    pas encore, ou s'ils sont plus récents que ceux qu'elle a)."""
    sources = sources_embarquees()
    faits = {}
    for registre, nom in FICHIERS.items():
        chemin = DOSSIER_DONNEES / nom
        if not chemin.exists():
            continue
        date_livree = (sources.get(registre) or {}).get("date_extraction", "")
        deja = refs.meta(f"appellations_{registre}_extraction") or ""
        if refs.nb_appellations(registre) and deja >= date_livree:
            continue
        faits[registre] = refs.remplacer_appellations(registre, lire_csv(chemin),
                                                      source=f"embarqué {date_livree}")
        refs.definir_meta(f"appellations_{registre}_extraction", date_livree)
    return faits


def mettre_a_jour_en_ligne(refs, client) -> dict[str, int]:
    """Télécharge les registres à jour (INAO et eAmbrosia) et remplace la copie
    locale. Lecture réseau d'abord, écriture ensuite (jamais l'inverse)."""
    from datetime import date
    url = url_csv_inao(client)
    brut = client.get(url).corps
    try:
        texte = brut.decode("utf-8-sig")
    except UnicodeDecodeError:
        texte = brut.decode("cp1252")
    inao = depuis_inao(texte)
    eambrosia = depuis_eambrosia(client.json(URL_EAMBROSIA))
    vides = [nom for nom, l in (("INAO", inao), ("eAmbrosia", eambrosia)) if not l]
    if vides:
        raise ValueError(f"registre vide ({', '.join(vides)}) : copie locale gardée")
    jour = date.today().isoformat()
    faits = {"inao": refs.remplacer_appellations("inao", inao, source=url),
             "eambrosia": refs.remplacer_appellations("eambrosia", eambrosia,
                                                      source=URL_EAMBROSIA)}
    for registre in faits:
        refs.definir_meta(f"appellations_{registre}_extraction", jour)
    return faits
