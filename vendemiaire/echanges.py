# -*- coding: utf-8 -*-
"""Import et export : CSV de Vendémiaire (aller-retour sans perte) et export CellarTracker.

Aucune donnée prisonnière : l'export CSV contient UNE LIGNE PAR BOUTEILLE avec
tout ce qui la décrit (vin, cépages, emplacement, état, provenance), et il se
réimporte tel quel dans une base vide. Séparateur « ; » et UTF-8 avec BOM :
Excel en français l'ouvre directement.

Import CellarTracker : voir docs/import_cellartracker.md (colonnes reconnues,
conversions, ce qui est ignoré). Un import ne remplace JAMAIS une donnée
saisie à la main (`Cave.completer_vin`) et ne crée pas deux fois la même
bouteille (code interne, ou identifiant d'inventaire CellarTracker).
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .modele import Cave, CaseOccupee
from .referentiels import FORMATS

#: colonnes de l'export CSV, dans l'ordre
COLONNES = (
    "producteur", "cuvee", "appellation", "region", "sous_region", "pays", "classement",
    "couleur", "type", "millesime", "non_millesime", "degre", "lwin", "ean", "cepages",
    "seuil_reassort", "coup_de_coeur", "notes_vin",
    "format", "statut", "emplacement", "rangee", "colonne", "prix_achat", "devise",
    "lieu_achat", "date_achat", "date_entree", "date_livraison_prevue", "date_sortie",
    "niveau", "niveau_cm", "etat_etiquette", "etat_capsule", "etat_bouchon", "caisse",
    "caisse_complete", "caisse_ref", "provenance", "historique_stockage", "facture", "bin",
    "notes_bouteille", "code_interne",
)
SEPARATEUR_CHEMIN = " › "
CHAMPS_ENTIERS = {"millesime", "non_millesime", "seuil_reassort", "coup_de_coeur", "rangee",
                  "colonne", "caisse_complete"}
CHAMPS_REELS = {"degre", "prix_achat", "niveau_cm"}


@dataclass
class Rapport:
    vins_crees: int = 0
    vins_completes: int = 0
    bouteilles: int = 0
    deja_presentes: int = 0
    lignes: int = 0
    avertissements: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------

def lire_texte(chemin: str | Path) -> str:
    """UTF-8 (avec ou sans BOM), sinon Windows-1252 — l'encodage des exports
    Excel et de bien des sites américains."""
    brut = Path(chemin).read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return brut.decode(enc)
        except UnicodeDecodeError:
            continue
    return brut.decode("latin-1")


def lire_csv(chemin: str | Path) -> list[dict[str, str]]:
    texte = lire_texte(chemin)
    echantillon = texte[:8192]
    try:
        dialecte = csv.Sniffer().sniff(echantillon, delimiters=";,\t")
    except csv.Error:
        dialecte = csv.excel
        dialecte.delimiter = ";" if echantillon.count(";") > echantillon.count(",") else ","
    lecteur = csv.DictReader(io.StringIO(texte), dialect=dialecte)
    return [{(k or "").strip(): (v or "").strip() for k, v in ligne.items() if k is not None}
            for ligne in lecteur]


def _entier(v):
    if v in (None, ""):
        return None
    try:
        return int(float(str(v).replace(",", ".")))
    except ValueError:
        return None


def _reel(v):
    if v in (None, ""):
        return None
    t = re.sub(r"[^\d,.\-]", "", str(v))
    if t.count(",") == 1 and t.count(".") == 0:
        t = t.replace(",", ".")
    else:
        t = t.replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


def cepages_vers_texte(cepages) -> str:
    morceaux = []
    for nom, pct in cepages:
        morceaux.append(f"{nom} {pct:g}%" if pct is not None else nom)
    return "; ".join(morceaux)


def texte_vers_cepages(texte: str) -> list[tuple[str, float | None]]:
    resultat = []
    for morceau in re.split(r"[;/]", texte or ""):
        morceau = morceau.strip()
        if not morceau:
            continue
        m = re.match(r"^(.*?)\s*(\d+(?:[.,]\d+)?)\s*%$", morceau)
        if m:
            resultat.append((m.group(1).strip(), float(m.group(2).replace(",", "."))))
        else:
            resultat.append((morceau, None))
    return resultat


def format_le_plus_proche(litres: float | None) -> str:
    if not litres:
        return "bouteille"
    return min(FORMATS, key=lambda f: abs(f.litres - litres)).code


def _emplacement_depuis_chemin(cave: Cave, chemin: str, rangee, colonne,
                               cache: dict) -> int | None:
    """Retrouve (ou crée) l'emplacement « Cave › Meuble › Casier ». Un casier
    créé ou trop petit est agrandi pour contenir la case demandée."""
    noms = [n.strip() for n in chemin.split(SEPARATEUR_CHEMIN.strip()) if n.strip()]
    if not noms:
        return None
    parent = None
    for i, nom in enumerate(noms):
        cle = (parent, nom)
        if cle in cache:
            parent = cache[cle]
            continue
        niveau = "cave" if i == 0 else ("casier" if i == len(noms) - 1 else "meuble")
        if len(noms) == 1:
            niveau = "cave"
        ligne = cave.base.un("SELECT id FROM emplacement WHERE nom=? AND parent_id IS ?",
                             (nom, parent))
        eid = ligne["id"] if ligne else cave.creer_emplacement(nom, niveau, parent)
        cache[cle] = eid
        parent = eid
    if rangee and colonne:
        e = cave.emplacement(parent)
        if e["niveau"] != "casier":
            with cave.base.ecriture() as c:
                c.execute("UPDATE emplacement SET niveau='casier' WHERE id=?", (parent,))
        r, co = max(e["rangees"] or 0, rangee), max(e["colonnes"] or 0, colonne)
        if (r, co) != (e["rangees"], e["colonnes"]):
            with cave.base.ecriture() as c:
                c.execute("UPDATE emplacement SET rangees=?, colonnes=? WHERE id=?",
                          (r, co, parent))
    return parent


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def exporter_csv(cave: Cave, chemin: str | Path) -> int:
    """Une ligne par bouteille (tous statuts). Renvoie le nombre de lignes."""
    lignes = cave.base.lire(
        "SELECT b.*, b.notes AS notes_bouteille, v.cuvee, v.appellation, v.region, v.sous_region, "
        "v.pays, v.classement, v.couleur, v.type, v.millesime, v.non_millesime, v.degre, v.lwin, "
        "v.ean, v.seuil_reassort, v.coup_de_coeur, v.notes AS notes_vin, p.nom AS producteur "
        "FROM bouteille b JOIN vin v ON v.id=b.vin_id LEFT JOIN producteur p ON p.id=v.producteur_id "
        "ORDER BY p.nom, v.cuvee, v.millesime, b.id")
    cache_cep: dict[int, str] = {}
    cache_emp: dict[int, str] = {}
    with open(chemin, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(COLONNES)
        for l in lignes:
            if l["vin_id"] not in cache_cep:
                cache_cep[l["vin_id"]] = cepages_vers_texte(cave.cepages(l["vin_id"]))
            eid = l["emplacement_id"]
            if eid is not None and eid not in cache_emp:
                cache_emp[eid] = SEPARATEUR_CHEMIN.join(cave.chemin_emplacement(eid))
            ligne = []
            for col in COLONNES:
                if col == "cepages":
                    v = cache_cep[l["vin_id"]]
                elif col == "emplacement":
                    v = cache_emp.get(eid, "")
                else:
                    v = l[col]
                ligne.append("" if v is None else (f"{v:g}" if isinstance(v, float) else v))
            w.writerow(ligne)
    return len(lignes)


def exporter_json(cave: Cave, chemin: str | Path) -> dict[str, int]:
    """Export COMPLET (toutes les tables, y compris notes des critiques,
    valeurs, fenêtres, livre de cave, déplacements) en JSON lisible : rien ne
    reste prisonnier de l'application. Renvoie le nombre de lignes par table."""
    import json
    tables = [r[0] for r in cave.base.lire(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name")]
    donnees = {"format": "vendemiaire-export", "version_schema": cave.base.version(),
               "date": date.today().isoformat(), "tables": {}}
    for t in tables:
        donnees["tables"][t] = [dict(r) for r in cave.base.lire(f"SELECT * FROM {t}")]
    Path(chemin).write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8")
    return {t: len(v) for t, v in donnees["tables"].items()}


# ---------------------------------------------------------------------------
# Import du CSV de Vendémiaire
# ---------------------------------------------------------------------------

def importer_csv(cave: Cave, chemin: str | Path, source: str = "csv") -> Rapport:
    rapport = Rapport()
    cache_emp: dict = {}
    for n, l in enumerate(lire_csv(chemin), 2):
        rapport.lignes += 1
        if l.get("code_interne") and cave.base.valeur(
                "SELECT 1 FROM bouteille WHERE code_interne=?", (l["code_interne"],)):
            rapport.deja_presentes += 1
            continue
        vin = {k: l.get(k, "") for k in ("cuvee", "appellation", "region", "sous_region", "pays",
                                         "classement", "couleur", "type", "lwin", "ean")}
        for k in ("millesime", "non_millesime", "seuil_reassort", "coup_de_coeur"):
            vin[k] = _entier(l.get(k))
        vin["degre"] = _reel(l.get("degre"))
        vin["notes"] = l.get("notes_vin", "")
        vin["cepages"] = texte_vers_cepages(l.get("cepages", ""))
        vin["producteur"] = l.get("producteur", "")
        vin_id = _vin_pour_import(cave, vin, source, rapport, f"ligne {n}")
        bouteille = {}
        for col in COLONNES[18:]:
            if col in ("emplacement", "code_interne", "notes_bouteille", "rangee", "colonne"):
                continue
            v = l.get(col, "")
            if col in CHAMPS_ENTIERS:
                v = _entier(v)
            elif col in CHAMPS_REELS:
                v = _reel(v)
            if v not in (None, ""):
                bouteille[col] = v
        if l.get("notes_bouteille"):
            bouteille["notes"] = l["notes_bouteille"]
        rangee, colonne = _entier(l.get("rangee")), _entier(l.get("colonne"))
        position = None
        if l.get("emplacement"):
            eid = _emplacement_depuis_chemin(cave, l["emplacement"], rangee, colonne, cache_emp)
            bouteille["emplacement_id"] = eid
            if rangee and colonne:
                position = (eid, rangee, colonne)
        try:
            ids = _ajouter(cave, vin_id, bouteille, position)
        except CaseOccupee:
            rapport.avertissements.append(f"ligne {n} : case {rangee},{colonne} déjà occupée, "
                                          "bouteille rangée sans case")
            ids = _ajouter(cave, vin_id, bouteille, None)
        if l.get("code_interne"):
            with cave.base.ecriture() as c:
                c.execute("UPDATE bouteille SET code_interne=? WHERE id=?",
                          (l["code_interne"], ids[0]))
        rapport.bouteilles += 1
    return rapport


def _ajouter(cave: Cave, vin_id: int, bouteille: dict, position) -> list[int]:
    # un import reprend l'historique tel quel : pas de nouvelle ligne au livre de cave
    return cave.ajouter_bouteilles(vin_id, 1, bouteille, [position] if position else None,
                                   mouvement=None)


def _vin_pour_import(cave: Cave, vin: dict, source: str, rapport: Rapport, ou: str) -> int:
    vin_id = cave.trouver_vin(vin.get("producteur"), vin.get("cuvee"), vin.get("millesime"),
                              vin.get("appellation"))
    if vin_id is None:
        propre = {k: v for k, v in vin.items() if v not in (None, "", [])}
        propre.setdefault("producteur", "")
        rapport.vins_crees += 1
        return cave.enregistrer_vin(propre, origine=source)
    if cave.completer_vin(vin_id, vin, source, ou):
        rapport.vins_completes += 1
    return vin_id


# ---------------------------------------------------------------------------
# Import d'un export CellarTracker
# ---------------------------------------------------------------------------

#: notes des critiques présentes dans les exports CellarTracker -> (code, échelle)
CRITIQUES_CT = {"WA": ("RP", "100"), "WS": ("WS", "100"), "JR": ("JR", "20"),
                "IWC": ("IWC", "100"), "BH": ("BH", "100"), "AG": ("AG", "100"),
                "WE": ("WE", "100"), "JS": ("JS", "100"), "VM": ("VIN", "100"),
                "DEC": ("DEC", "100"), "CT": ("CellarTracker", "100")}
#: CellarTracker note « 1001 » le millésime d'un vin non millésimé
NV_CELLARTRACKER = 1001


#: CellarTracker écrit « Unknown » dans les champs non renseignés (Designation,
#: Vineyard, SubRegion…) : c'est un champ vide, pas une valeur
VIDES_CT = {"", "unknown", "n/a"}


def _cle(ligne: dict, *noms: str) -> str:
    bas = {k.lower(): v for k, v in ligne.items()}
    for n in noms:
        v = bas.get(n.lower())
        if v is not None and v.strip().lower() not in VIDES_CT:
            return v.strip()
    return ""


def _couleur_ct(couleur: str, type_: str) -> str | None:
    t = f"{couleur} {type_}".lower()
    if "ros" in t:
        return "rose"
    if "white" in t or "blanc" in t:
        return "blanc"
    if "red" in t or "rouge" in t:
        return "rouge"
    if "amber" in t or "orange" in t:
        return "orange"
    return None


def _type_ct(categorie: str, type_: str) -> str:
    t = f"{categorie} {type_}".lower()
    if "sparkling" in t:
        return "effervescent"
    if "fortified" in t:
        return "mute"
    if "sweet" in t or "dessert" in t:
        return "doux"
    return "tranquille"


def _litres(taille: str) -> float | None:
    m = re.match(r"^\s*(\d+(?:[.,]\d+)?)\s*(ml|cl|l)\b", (taille or "").lower())
    if not m:
        return None
    v = float(m.group(1).replace(",", "."))
    return {"ml": v / 1000, "cl": v / 100, "l": v}[m.group(2)]


def _date_ct(texte: str) -> str | None:
    """Dates CellarTracker : « 3/15/2021 » (mois/jour/année) ou ISO."""
    texte = (texte or "").strip()
    if not texte:
        return None
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", texte)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", texte)
    if m:
        return f"{int(m.group(3)):04d}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return None


def importer_cellartracker(cave: Cave, chemin: str | Path) -> Rapport:
    """Export « Inventory » (une ligne par bouteille, colonne iInventory) ou
    « My Cellar / List » (une ligne par vin, colonnes Quantity et Pending)."""
    rapport = Rapport()
    lignes = lire_csv(chemin)
    if lignes and not any(k.lower() in ("wine", "producer") for k in lignes[0]):
        rapport.avertissements.append("fichier sans colonne « Wine » ni « Producer » : "
                                      "ce n'est pas un export CellarTracker")
        return rapport
    aujourdhui = date.today().isoformat()
    cache_emp: dict = {}
    for n, l in enumerate(lignes, 2):
        rapport.lignes += 1
        inventaire = _cle(l, "iInventory")
        if inventaire and cave.base.valeur(
                "SELECT 1 FROM bouteille WHERE code_interne=?", ("CT" + inventaire,)):
            rapport.deja_presentes += 1
            continue
        producteur = _cle(l, "Producer")
        nom_complet = _cle(l, "Wine")
        cuvee = _cle(l, "Designation")
        appellation = _cle(l, "Appellation")
        if not cuvee and nom_complet:
            reste = nom_complet
            if producteur and reste.lower().startswith(producteur.lower()):
                reste = reste[len(producteur):].strip(" ,-")
            if reste and reste.lower() not in (appellation.lower(), _cle(l, "Region").lower()):
                cuvee = reste
        if not producteur and not cuvee:
            cuvee = nom_complet
        millesime = _entier(_cle(l, "Vintage"))
        non_millesime = 1 if millesime in (None, NV_CELLARTRACKER) else 0
        if millesime == NV_CELLARTRACKER:
            millesime = None
        cepage = _cle(l, "Varietal", "MasterVarietal")
        vin = {
            "producteur": producteur, "cuvee": cuvee, "appellation": appellation,
            "region": _cle(l, "Region"), "sous_region": _cle(l, "SubRegion"),
            "pays": _cle(l, "Country"), "couleur": _couleur_ct(_cle(l, "Color"), _cle(l, "Type")),
            "type": _type_ct(_cle(l, "Category"), _cle(l, "Type")),
            "millesime": millesime, "non_millesime": non_millesime,
            "ean": _cle(l, "UPC", "EAN") or None,
            "cepages": [(cepage, None)] if cepage else [],
        }
        vin_id = _vin_pour_import(cave, vin, "cellartracker", rapport, f"ligne {n}")
        iwine = _cle(l, "iWine")
        if iwine:
            with cave.base.ecriture() as c:
                c.execute("INSERT OR IGNORE INTO identifiant_externe(vin_id, source, valeur, "
                          "confirme, date) VALUES(?,?,?,1,?)",
                          (vin_id, "cellartracker", iwine, aujourdhui))
        # notes des critiques (une seule fois par vin et par critique)
        for col, (code, echelle) in CRITIQUES_CT.items():
            note = _reel(_cle(l, col))
            if note and not cave.base.valeur(
                    "SELECT 1 FROM note_critique WHERE vin_id=? AND critique=?", (vin_id, code)):
                cave.ajouter_note_critique(vin_id, code, note, echelle, source="cellartracker")
        debut, fin = _entier(_cle(l, "BeginConsume")), _entier(_cle(l, "EndConsume"))
        if debut or fin:
            cave.definir_fenetre(vin_id, "critique", debut, fin, detail_source="CellarTracker",
                                 explication="import CellarTracker (BeginConsume / EndConsume)")
        valeur = _reel(_cle(l, "Valuation", "Value"))
        devise = _cle(l, "Currency") or "EUR"
        if valeur and not cave.base.valeur(
                "SELECT 1 FROM valeur WHERE vin_id=? AND source='cellartracker' AND date=?",
                (vin_id, aujourdhui)):
            cave.ajouter_valeur(vin_id, valeur, "cellartracker", aujourdhui, devise=devise)
        bouteille = {
            "format": format_le_plus_proche(_litres(_cle(l, "Size"))),
            "prix_achat": _reel(_cle(l, "Price", "NativePrice")),
            "devise": devise, "lieu_achat": _cle(l, "StoreName") or None,
            "date_achat": _date_ct(_cle(l, "PurchaseDate")),
            "notes": _cle(l, "Note", "PurchaseNote") or None,
            "bin": None,
        }
        bouteille = {k: v for k, v in bouteille.items() if v not in (None, "")}
        lieu, casier = _cle(l, "Location"), _cle(l, "Bin")
        if lieu or casier:
            chemin_emp = SEPARATEUR_CHEMIN.join(x for x in (lieu or "CellarTracker", casier) if x)
            bouteille["emplacement_id"] = _emplacement_depuis_chemin(
                cave, chemin_emp, None, None, cache_emp)
        if inventaire:
            quantite, en_attente = 1, 0
        else:
            quantite = _entier(_cle(l, "Quantity")) or 0
            en_attente = _entier(_cle(l, "Pending")) or 0
            if not quantite and not en_attente:
                quantite = 1
        if quantite:
            ids = _ajouter(cave, vin_id, dict(bouteille, statut="en_cave"), None)
            for _ in range(quantite - 1):
                ids += _ajouter(cave, vin_id, dict(bouteille, statut="en_cave"), None)
            if inventaire:
                with cave.base.ecriture() as c:
                    c.execute("UPDATE bouteille SET code_interne=? WHERE id=?",
                              ("CT" + inventaire, ids[0]))
        for _ in range(en_attente):
            b = dict(bouteille, statut="en_attente")
            b.pop("emplacement_id", None)
            _ajouter(cave, vin_id, b, None)
        rapport.bouteilles += quantite + en_attente
    return rapport
