# -*- coding: utf-8 -*-
"""Wikidata (données CC0) : fiches des producteurs, châteaux, appellations et
cépages — fondation, coordonnées, propriétaires, site, image de Wikimedia
Commons (avec auteur et licence), liens Wikipédia.

Deux requêtes, toujours par le client poli de `reseau` (User-Agent identifié,
une requête par seconde au plus) :

1. recherche des éléments par leur nom (API `wbsearchentities`) ;
2. détail des éléments retenus (une requête SPARQL pour tous).

Le choix entre les candidats suit les règles de l'appariement : score calculé
ici (ressemblance du nom, nature de l'élément, pays), score expliqué,
renoncement si deux candidats se valent — et confirmation de l'utilisateur.
"""
from __future__ import annotations

import re
import urllib.parse

from ..base import normaliser
from .appariement import Candidat, Raison, ressemblance

API = "https://www.wikidata.org/w/api.php"
SPARQL = "https://query.wikidata.org/sparql"
COMMONS = "https://commons.wikimedia.org/w/api.php"
LICENCE = "CC0 1.0"

#: mots qui, dans la nature (P31) d'un élément, disent ce qu'il est
NATURES = {
    "producteur": ("winery", "domaine viticole", "wine estate", "château", "chateau", "maison de champagne",
                   "champagne house", "wine producer", "producteur de vin", "vignoble", "vineyard",
                   "cave coopérative", "bodega", "entreprise", "company", "business"),
    "appellation": ("appellation", "aoc", "aop", "protected designation", "indication géographique",
                    "geographical indication", "wine region", "région viticole", "dénomination",
                    "vignoble", "wine-producing region", "american viticultural area",
                    "vin", "wine", "vin rouge", "vin blanc"),
    "cepage": ("cépage", "grape variety", "variété de raisin", "cultivar", "vitis"),
}


def chercher(client, nom: str, langue: str = "fr", limite: int = 8) -> list[dict]:
    """Éléments dont le libellé ressemble à `nom` : [{id, label, description}]."""
    if not (nom or "").strip():
        return []
    d = client.json(API, {"action": "wbsearchentities", "search": nom, "language": langue,
                          "uselang": langue, "type": "item", "limit": limite, "format": "json"})
    return [{"id": r.get("id"), "label": r.get("label") or "", "description": r.get("description") or ""}
            for r in d.get("search", []) if r.get("id")]


REQUETE = """
SELECT ?item ?itemLabel ?itemDescription
  (GROUP_CONCAT(DISTINCT ?natureLabel; separator="|") AS ?natures)
  (SAMPLE(?fondation) AS ?fondation)
  (SAMPLE(?coord) AS ?coord)
  (GROUP_CONCAT(DISTINCT ?proprietaireLabel; separator="|") AS ?proprietaires)
  (SAMPLE(?image) AS ?image)
  (SAMPLE(?site) AS ?site)
  (SAMPLE(?paysLabel) AS ?pays)
  (SAMPLE(?lieuLabel) AS ?lieu)
  (SAMPLE(?wpfr) AS ?wpfr) (SAMPLE(?wpen) AS ?wpen)
WHERE {
  VALUES ?item { %s }
  OPTIONAL { ?item wdt:P31 ?nature . }
  OPTIONAL { ?item wdt:P571 ?fondation . }
  OPTIONAL { ?item wdt:P625 ?coord . }
  OPTIONAL { ?item wdt:P127 ?proprietaire . }
  OPTIONAL { ?item wdt:P18 ?image . }
  OPTIONAL { ?item wdt:P856 ?site . }
  OPTIONAL { ?item wdt:P17 ?pays_ . }
  OPTIONAL { ?item wdt:P131 ?lieu_ . }
  OPTIONAL { ?wpfr schema:about ?item ; schema:isPartOf <https://fr.wikipedia.org/> . }
  OPTIONAL { ?wpen schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . }
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "%s,en" .
    ?item rdfs:label ?itemLabel . ?item schema:description ?itemDescription .
    ?nature rdfs:label ?natureLabel . ?proprietaire rdfs:label ?proprietaireLabel .
    ?pays_ rdfs:label ?paysLabel . ?lieu_ rdfs:label ?lieuLabel .
  }
}
GROUP BY ?item ?itemLabel ?itemDescription
"""


def details(client, qids: list[str], langue: str = "fr") -> dict[str, dict]:
    """Fiches de plusieurs éléments, en une requête SPARQL."""
    qids = [q for q in qids if re.fullmatch(r"Q\d+", q or "")]
    if not qids:
        return {}
    requete = REQUETE % (" ".join(f"wd:{q}" for q in qids), "fr" if langue == "fr" else "en")
    d = client.get(SPARQL, {"query": requete, "format": "json"},
                   accepter="application/sparql-results+json").json()
    sortie = {}
    for b in d.get("results", {}).get("bindings", []):
        v = {k: x.get("value") for k, x in b.items()}
        qid = v.get("item", "").rsplit("/", 1)[-1]
        fiche = {
            "qid": qid,
            "nom": v.get("itemLabel"),
            "description": v.get("itemDescription"),
            "natures": [x for x in (v.get("natures") or "").split("|") if x],
            "fondation": _annee(v.get("fondation")),
            "coordonnees": _point(v.get("coord")),
            "proprietaires": [x for x in (v.get("proprietaires") or "").split("|") if x],
            "image": _fichier_commons(v.get("image")),
            "site": v.get("site"),
            "pays": v.get("pays"),
            "lieu": v.get("lieu"),
            "wikipedia_fr": v.get("wpfr"),
            "wikipedia_en": v.get("wpen"),
            "url": f"https://www.wikidata.org/wiki/{qid}",
        }
        sortie[qid] = fiche
    return sortie


def _annee(v: str | None) -> int | None:
    m = re.match(r"^-?(\d{3,4})", v or "")
    return int(m.group(1)) if m else None


def _point(v: str | None) -> tuple[float, float] | None:
    """« Point(lon lat) » -> (lat, lon)."""
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", v or "")
    return (float(m.group(2)), float(m.group(1))) if m else None


def _fichier_commons(v: str | None) -> str | None:
    """URL Special:FilePath -> nom du fichier (« Margaux exterior.jpg »)."""
    if not v:
        return None
    return urllib.parse.unquote(v.rsplit("/", 1)[-1])


def score_element(objet: str, nom: str, fiche: dict, pays: str | None = None) -> tuple[float, list[Raison]]:
    raisons = []
    s_nom = ressemblance(nom, fiche.get("nom"))
    raisons.append(Raison("appariement.r_nom_wikidata", {"pct": int(round(100 * s_nom)),
                                                         "nom": fiche.get("nom") or ""},
                          1 if s_nom >= 0.8 else (-1 if s_nom < 0.5 else 0)))
    natures = " ".join(fiche.get("natures") or []).lower() + " " + (fiche.get("description") or "").lower()
    bonne_nature = any(re.search(rf"(?<!\w){re.escape(m)}(?!\w)", natures)
                       for m in NATURES.get(objet, ()))
    raisons.append(Raison("appariement.r_nature_ok" if bonne_nature else "appariement.r_nature_non",
                          {"nature": ", ".join((fiche.get("natures") or [])[:3]) or "?"},
                          1 if bonne_nature else -1))
    score = 0.65 * s_nom + (0.30 if bonne_nature else 0.0)
    if pays and fiche.get("pays"):
        if normaliser(pays) == normaliser(fiche["pays"]):
            score += 0.05
        else:
            score -= 0.15
            raisons.append(Raison("appariement.r_pays_non", {"nom": fiche["pays"]}, -1))
    if "homonymie" in natures or "disambiguation" in natures:
        score = 0.0
    return round(max(0.0, min(1.0, score)), 3), raisons


def candidats(client, objet: str, nom: str, pays: str | None = None, langue: str = "fr",
              limite: int = 6) -> list[Candidat]:
    """Candidats Wikidata pour un producteur, une appellation ou un cépage."""
    trouves = chercher(client, nom, langue)
    if not trouves and normaliser(nom) != (nom or "").lower():
        trouves = chercher(client, normaliser(nom), langue)
    fiches = details(client, [t["id"] for t in trouves], langue)
    sortie = []
    for t in trouves:
        f = fiches.get(t["id"]) or {"qid": t["id"], "nom": t["label"], "description": t["description"],
                                    "natures": [], "url": f"https://www.wikidata.org/wiki/{t['id']}"}
        score, raisons = score_element(objet, nom, f, pays)
        libelle = f.get("nom") or t["label"]
        if f.get("description"):
            libelle += f" — {f['description']}"
        sortie.append(Candidat("wikidata", f["qid"], libelle, score, raisons,
                               donnees_producteur(f) if objet == "producteur" else {},
                               brut=f, url=f.get("url", "")))
    sortie.sort(key=lambda c: c.score, reverse=True)
    return sortie[:limite]


def donnees_producteur(fiche: dict) -> dict:
    """Champs de la table producteur qu'une fiche Wikidata peut compléter."""
    d = {"site_web": fiche.get("site"), "pays": fiche.get("pays")}
    if fiche.get("lieu"):
        d["adresse"] = fiche["lieu"]
    return {k: v for k, v in d.items() if v}


def credit_commons(client, fichier: str, largeur: int = 1024) -> dict | None:
    """Auteur, licence et vignette d'un fichier de Commons (API imageinfo)."""
    if not fichier:
        return None
    d = client.json(COMMONS, {"action": "query", "titles": f"File:{fichier}", "prop": "imageinfo",
                              "iiprop": "url|extmetadata", "iiurlwidth": largeur, "format": "json"})
    for page in (d.get("query", {}).get("pages") or {}).values():
        infos = (page.get("imageinfo") or [None])[0]
        if not infos:
            continue
        meta = infos.get("extmetadata") or {}

        def champ(nom):
            return _sans_html((meta.get(nom) or {}).get("value"))
        return {"fichier": fichier,
                "auteur": champ("Artist") or champ("Credit") or "?",
                "licence": champ("LicenseShortName") or "?",
                "url_licence": (meta.get("LicenseUrl") or {}).get("value"),
                "vignette": infos.get("thumburl") or infos.get("url"),
                "page": infos.get("descriptionurl")}
    return None


def _sans_html(v: str | None) -> str:
    if not v:
        return ""
    import html
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", v))).strip()
