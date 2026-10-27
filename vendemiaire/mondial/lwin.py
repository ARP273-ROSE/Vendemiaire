# -*- coding: utf-8 -*-
"""LWIN (Liv-ex Wine Identification Number) : lecture du fichier publié par
Liv-ex et conversion en table locale.

La base est gratuite, sous licence Creative Commons Attribution 4.0, mais Liv-ex
la remet par un formulaire (nom, adresse électronique) : l'application ouvre
cette page dans le navigateur, l'utilisateur télécharge le fichier XLSX, puis
l'importe (menu Références). Si Liv-ex lui donne un lien direct, il peut le
retenir pour une mise à jour périodique (facultative, avec son accord).

Le lecteur XLSX est écrit ici (zip + XML, en flux) : aucune dépendance de
plus, et 200 000 lignes passent sans tout charger en mémoire.

Codes : LWIN-7 = le vin (cuvée d'un producteur) ; LWIN-11 = LWIN-7 suivi du
millésime sur 4 chiffres (« 1000 » pour un non-millésimé) ; LWIN-16 et 18
ajoutent le conditionnement (non utilisés ici).
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path
from typing import Iterator
from xml.etree import ElementTree as ET

from ..base import normaliser

PAGE_TELECHARGEMENT = "https://www.liv-ex.com/lwin-database-download/"
PAGE_LICENCE = "https://www.liv-ex.com/lwin-creative-commons-licence/"
PAGE_LWIN = "https://www.liv-ex.com/lwin/"
LICENCE = "CC BY 4.0"
CREDIT = "LWIN © Liv-ex Ltd"

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

#: en-têtes du fichier Liv-ex -> clés internes (comparaison sans casse, espaces = _)
COLONNES = {
    "LWIN": "lwin", "STATUS": "statut", "DISPLAY_NAME": "nom",
    "PRODUCER_TITLE": "titre_producteur", "PRODUCER_NAME": "producteur", "WINE": "vin",
    "COUNTRY": "pays", "REGION": "region", "SUB_REGION": "sous_region", "SITE": "site",
    "PARCEL": "parcelle", "COLOUR": "couleur", "COLOR": "couleur", "TYPE": "type",
    "SUB_TYPE": "sous_type", "DESIGNATION": "designation", "CLASSIFICATION": "classement",
    "VINTAGE_CONFIG": "config_millesime", "FIRST_VINTAGE": "premier_millesime",
    "FINAL_VINTAGE": "dernier_millesime", "DATE_UPDATED": "maj", "DATE_ADDED": "ajout",
    # variantes d'en-têtes (versions du fichier, exports retravaillés) : à valider sur le vrai fichier
    "LWIN7": "lwin", "LWIN_7": "lwin", "PRODUCER": "producteur", "WINE_NAME": "vin",
    "SUBREGION": "sous_region", "WINE_TYPE": "type", "WINE_SUB_TYPE": "sous_type",
    "VINEYARD": "site", "NAME": "nom",
}

#: noms anglais de Liv-ex -> noms usuels de la cave (français)
PAYS = {
    "France": "France", "Italy": "Italie", "Spain": "Espagne", "Portugal": "Portugal",
    "Germany": "Allemagne", "Austria": "Autriche", "Switzerland": "Suisse", "Hungary": "Hongrie",
    "Greece": "Grèce", "United States": "États-Unis", "USA": "États-Unis",
    "Australia": "Australie", "New Zealand": "Nouvelle-Zélande", "South Africa": "Afrique du Sud",
    "Chile": "Chili", "Argentina": "Argentine", "Lebanon": "Liban", "Georgia": "Géorgie",
    "Armenia": "Arménie", "England": "Angleterre", "United Kingdom": "Royaume-Uni",
    "Canada": "Canada", "Israel": "Israël", "Slovenia": "Slovénie", "Croatia": "Croatie",
    "Romania": "Roumanie", "Uruguay": "Uruguay", "China": "Chine", "Japan": "Japon",
}
REGIONS = {
    "Burgundy": "Bourgogne", "Rhone": "Vallée du Rhône", "Loire": "Val de Loire",
    "Southwest France": "Sud-Ouest", "South West France": "Sud-Ouest",
    "Languedoc": "Languedoc", "Roussillon": "Roussillon", "Provence": "Provence",
    "Corsica": "Corse", "Jura": "Jura", "Savoie": "Savoie", "Beaujolais": "Beaujolais",
    "Tuscany": "Toscane", "Piedmont": "Piémont", "Sicily": "Sicile", "Sardinia": "Sardaigne",
    "Veneto": "Vénétie",
}


def _col(ref: str) -> int:
    """« AB12 » -> 27 (colonnes numérotées à partir de 0)."""
    n = 0
    for ch in ref:
        if ch.isalpha():
            n = n * 26 + (ord(ch.upper()) - 64)
        else:
            break
    return n - 1


def lire_xlsx(chemin: str | Path) -> Iterator[list[str]]:
    """Lignes de la première feuille d'un classeur XLSX, en flux (valeurs en texte)."""
    with zipfile.ZipFile(chemin) as z:
        noms = set(z.namelist())
        partages: list[str] = []
        if "xl/sharedStrings.xml" in noms:
            with z.open("xl/sharedStrings.xml") as f:
                for _, el in ET.iterparse(f, events=("end",)):
                    if el.tag == _NS + "si":
                        partages.append("".join(t.text or "" for t in el.iter(_NS + "t")))
                        el.clear()
        feuille = _premiere_feuille(z, noms)
        with z.open(feuille) as f:
            for _, el in ET.iterparse(f, events=("end",)):
                if el.tag != _NS + "row":
                    continue
                valeurs: dict[int, str] = {}
                for i, c in enumerate(el.iter(_NS + "c")):
                    ref = c.get("r")
                    col = _col(ref) if ref else i
                    t = c.get("t")
                    if t == "inlineStr":
                        v = "".join(x.text or "" for x in c.iter(_NS + "t"))
                    else:
                        ve = c.find(_NS + "v")
                        v = ve.text if ve is not None and ve.text is not None else ""
                        if t == "s" and v:
                            v = partages[int(v)]
                        elif t not in ("s", "str") and v.endswith(".0") and v[:-2].isdigit():
                            v = v[:-2]
                    valeurs[col] = v
                el.clear()
                if valeurs:
                    yield [valeurs.get(i, "") for i in range(max(valeurs) + 1)]


def _premiere_feuille(z: zipfile.ZipFile, noms: set[str]) -> str:
    try:
        classeur = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        premiere = classeur.find(f"{_NS}sheets/{_NS}sheet")
        rid = premiere.get(_NS_REL + "id")
        for r in rels:
            if r.get("Id") == rid:
                cible = r.get("Target").lstrip("/")
                return cible if cible.startswith("xl/") else "xl/" + cible
    except (KeyError, ET.ParseError, AttributeError):
        pass
    feuilles = sorted(n for n in noms if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
    if not feuilles:
        raise ValueError("classeur sans feuille")
    return feuilles[0]


def lire_csv(chemin: str | Path) -> Iterator[list[str]]:
    brut = Path(chemin).read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            texte = brut.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    echantillon = texte[:4096]
    sep = max((",", ";", "\t"), key=echantillon.count)
    yield from csv.reader(io.StringIO(texte), delimiter=sep)


def lignes_fichier(chemin: str | Path) -> Iterator[dict]:
    """Lignes du fichier LWIN (XLSX ou CSV) converties pour `References.remplacer_lwin`."""
    chemin = Path(chemin)
    source = lire_xlsx(chemin) if chemin.suffix.lower() in (".xlsx", ".xlsm") else lire_csv(chemin)
    entetes = None
    for brute in source:
        if entetes is None:
            cles = [re.sub(r"[\s\-]+", "_", (x or "").strip().upper()) for x in brute]
            if "LWIN" in cles or "LWIN7" in cles or "LWIN_7" in cles:
                entetes = [COLONNES.get(k) for k in cles]
            continue
        d = {k: (v.strip() if isinstance(v, str) else v) for k, v in zip(entetes, brute) if k}
        # Le vrai fichier de Liv-ex (vu le 28/10/2026, 212 208 lignes) écrit « NA » pour une case
        # vide : sans ce nettoyage, « NA » entrait dans les noms (« NA Schieferkopf ») et la recherche.
        d = {k: (None if isinstance(v, str) and v.upper() in ("NA", "N/A") else v) for k, v in d.items()}
        ligne = convertir(d)
        if ligne:
            yield ligne
    if entetes is None:
        raise ValueError("colonne « LWIN » introuvable : ce n'est pas le fichier de Liv-ex")


def _entier(v) -> int | None:
    try:
        n = int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None
    return n if 1000 <= n <= 2200 else None


def _date_excel(v) -> str | None:
    """Le fichier de Liv-ex donne ses dates en numéro de série Excel (45849.46… = 11/07/2025)."""
    if v in (None, ""):
        return None
    try:
        n = float(str(v).strip())
    except ValueError:
        return str(v)
    import datetime as _dt
    return (_dt.date(1899, 12, 30) + _dt.timedelta(days=int(n))).isoformat()


def couleur_vers_code(couleur: str | None) -> str | None:
    c = (couleur or "").strip().lower()
    return {"red": "rouge", "white": "blanc", "rose": "rose", "rosé": "rose",
            "orange": "orange"}.get(c)


def type_vers_code(type_: str | None, sous_type: str | None) -> str:
    t = f"{type_ or ''} {sous_type or ''}".lower()
    if any(m in t for m in ("spirit", "liqueur", "beer", "sake", "cider")):
        return "autre"
    if any(m in t for m in ("fortified", "port", "sherry", "madeira")):
        return "mute"
    if any(m in t for m in ("sparkling", "champagne")):
        return "effervescent"
    if any(m in t for m in ("sweet", "dessert", "botrytis")):
        return "doux"
    return "tranquille"


def convertir(d: dict) -> dict | None:
    """Une ligne brute de Liv-ex -> une ligne de la table `lwin`."""
    code = re.sub(r"\D", "", str(d.get("lwin") or ""))
    if not code:
        return None
    statut = (d.get("statut") or "").strip()
    if statut.lower() == "deleted":
        return None
    producteur = " ".join(x for x in (d.get("titre_producteur"), d.get("producteur")) if x)
    vin = d.get("vin") or ""
    region = d.get("region") or ""
    ligne = {
        "id": int(code[:7]),
        "lwin": code[:7].zfill(7),
        "statut": statut or None,
        "nom": d.get("nom") or None,
        "titre_producteur": d.get("titre_producteur") or None,
        "producteur": d.get("producteur") or None,
        "vin": vin or None,
        "pays": PAYS.get(d.get("pays") or "", d.get("pays") or None),
        "region": REGIONS.get(region, region or None),
        "sous_region": d.get("sous_region") or None,
        "site": d.get("site") or None,
        "parcelle": d.get("parcelle") or None,
        "couleur": couleur_vers_code(d.get("couleur")),
        "type": type_vers_code(d.get("type"), d.get("sous_type")),
        "type_lwin": " / ".join(x for x in (d.get("type"), d.get("sous_type")) if x) or None,
        "designation": d.get("designation") or None,
        "classement": d.get("classement") or None,
        "config_millesime": d.get("config_millesime") or None,
        "premier_millesime": _entier(d.get("premier_millesime")),
        "dernier_millesime": _entier(d.get("dernier_millesime")),
        "maj": _date_excel(d.get("maj") or d.get("ajout")),
    }
    ligne["producteur_norm"] = normaliser(producteur)
    ligne["vin_norm"] = normaliser(vin)
    ligne["texte"] = normaliser(" ".join(str(x) for x in (
        producteur, vin, d.get("nom"), region, d.get("sous_region"), d.get("site"),
        d.get("parcelle"), d.get("classement")) if x))
    return ligne


def lwin11(lwin7: str, millesime: int | None, non_millesime: bool = False) -> str | None:
    """LWIN-11 : LWIN-7 + millésime (« 1000 » pour un non-millésimé)."""
    if not lwin7 or not re.fullmatch(r"\d{7}", str(lwin7)):
        return None
    if millesime:
        return f"{lwin7}{int(millesime):04d}"
    return f"{lwin7}1000" if non_millesime else None


def donnees_pour_vin(ligne: dict, appellation_officielle=None) -> dict:
    """Ce qu'une ligne LWIN peut apporter à la fiche d'un vin (champs de
    CHAMPS_VIN + producteur). L'appellation n'est proposée que si la
    sous-région ou le site LWIN EST une appellation officielle du registre
    (`appellation_officielle(nom) -> dict | None`) : sinon on se tait."""
    d = {
        "lwin": ligne.get("lwin"),
        "producteur": " ".join(x for x in (ligne.get("titre_producteur"),
                                            ligne.get("producteur")) if x) or None,
        "pays": ligne.get("pays"),
        "region": ligne.get("region"),
        "sous_region": ligne.get("sous_region"),
        "classement": ligne.get("classement"),
        "couleur": ligne.get("couleur"),
        "type": ligne.get("type") if ligne.get("type") != "autre" else None,
    }
    if ligne.get("vin") and normaliser(ligne["vin"]) != normaliser(d["producteur"]):
        d["cuvee"] = ligne["vin"]
    if appellation_officielle is not None:
        for candidat in (ligne.get("site"), ligne.get("sous_region")):
            off = appellation_officielle(candidat) if candidat else None
            if off:
                d["appellation"] = off["nom"]
                break
    if d.get("appellation") and normaliser(d.get("sous_region")) == normaliser(d["appellation"]):
        del d["sous_region"]                    # « Pauillac » n'est pas aussi une sous-région
    return {k: v for k, v in d.items() if v not in (None, "")}
