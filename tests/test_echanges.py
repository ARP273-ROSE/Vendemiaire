# -*- coding: utf-8 -*-
"""Import et export : aller-retour CSV sans perte, exports CellarTracker
(inventaire et liste), export complet JSON, export du dossier « Le vin »."""
import json
from pathlib import Path

import pytest

from vendemiaire import echanges, export_dossier
from vendemiaire.base import Base
from vendemiaire.modele import Cave

DONNEES = Path(__file__).resolve().parent / "donnees"


def _resume(cave):
    return sorted(cave.base.lire(
        "SELECT p.nom, v.cuvee, v.millesime, v.couleur, b.format, b.statut, b.prix_achat, "
        "b.rangee, b.colonne, b.niveau, b.caisse, b.code_interne FROM bouteille b "
        "JOIN vin v ON v.id=b.vin_id LEFT JOIN producteur p ON p.id=v.producteur_id"),
        key=lambda r: r["code_interne"])


def test_aller_retour_csv(cave_demo, tmp_path):
    fichier = tmp_path / "cave.csv"
    n = echanges.exporter_csv(cave_demo, fichier)
    assert n == cave_demo.base.valeur("SELECT COUNT(*) FROM bouteille")
    assert fichier.read_bytes()[:3] == b"\xef\xbb\xbf"           # BOM : Excel l'ouvre en UTF-8
    neuve = Cave(Base(tmp_path / "neuve.db"), tmp_path / "img")
    r = echanges.importer_csv(neuve, fichier)
    assert r.bouteilles == n and not r.avertissements
    assert [tuple(x) for x in _resume(neuve)] == [tuple(x) for x in _resume(cave_demo)]
    assert neuve.base.valeur("SELECT COUNT(*) FROM vin") == \
        cave_demo.base.valeur("SELECT COUNT(DISTINCT vin_id) FROM bouteille")
    assert neuve.cepages(1) and neuve.chemin_emplacement(
        neuve.base.valeur("SELECT emplacement_id FROM bouteille WHERE emplacement_id IS NOT NULL LIMIT 1"))
    # réimporter le même fichier ne crée rien
    r2 = echanges.importer_csv(neuve, fichier)
    assert r2.bouteilles == 0 and r2.deja_presentes == n


def test_cellartracker_inventaire(cave):
    vid = cave.enregistrer_vin({"producteur": "Château Fictif des Graves", "cuvee": "",
                                "appellation": "Pessac-Léognan", "millesime": 2018,
                                "pays": "France", "region": "Mes notes : Graves"})
    r = echanges.importer_cellartracker(cave, DONNEES / "cellartracker_inventaire.csv")
    assert (r.lignes, r.bouteilles, r.vins_crees) == (3, 3, 1)
    v = cave.vin(vid)
    assert v["region"] == "Mes notes : Graves"                  # saisie manuelle intacte
    assert v["sous_region"] == "Graves" and v["couleur"] == "rouge"   # champs vides complétés
    assert len(cave.bouteilles(vid)) == 2
    b = cave.bouteilles(vid)[0]
    assert (b["prix_achat"], b["date_achat"], b["lieu_achat"]) == (45, "2021-03-15", "Caviste du Port")
    assert cave.chemin_emplacement(b["emplacement_id"]) == ["Cellar", "A1"]
    assert cave.valeurs(vid)[0]["montant"] == 60
    f = cave.fenetres(vid)[0]
    assert (f["debut"], f["fin"], f["detail_source"]) == (2026, 2040, "CellarTracker")
    champagne = cave.base.un("SELECT * FROM vin WHERE type='effervescent'")
    assert champagne["millesime"] is None and champagne["non_millesime"] == 1
    assert cave.bouteilles(champagne["id"])[0]["format"] == "magnum"
    assert cave.base.valeur("SELECT valeur FROM identifiant_externe WHERE vin_id=?", (vid,)) == "5001"
    # second import du même fichier : les identifiants d'inventaire évitent les doublons
    r2 = echanges.importer_cellartracker(cave, DONNEES / "cellartracker_inventaire.csv")
    assert r2.deja_presentes == 3 and r2.bouteilles == 0


def test_cellartracker_liste_quantites_et_critiques(cave):
    r = echanges.importer_cellartracker(cave, DONNEES / "cellartracker_liste.csv")
    assert r.bouteilles == 6
    toscan = cave.base.un("SELECT * FROM vin WHERE appellation='Toscana IGT'")
    statuts = sorted(b["statut"] for b in cave.bouteilles(toscan["id"]))
    assert statuts == ["en_attente", "en_attente", "en_cave", "en_cave", "en_cave"]
    notes = {(n["critique"], n["note"], n["echelle"]) for n in cave.notes_critiques(toscan["id"])}
    assert notes == {("RP", 92, "100"), ("JR", 16.5, "20"), ("CellarTracker", 90.5, "100")}
    doux = cave.base.un("SELECT * FROM vin WHERE appellation='Coteaux du Layon'")
    assert doux["type"] == "doux" and cave.bouteilles(doux["id"])[0]["format"] == "demi"


def test_fichier_qui_n_est_pas_cellartracker(cave, tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("a;b\n1;2\n", encoding="utf-8")
    r = echanges.importer_cellartracker(cave, f)
    assert r.bouteilles == 0 and r.avertissements


def test_cepages_texte():
    assert echanges.texte_vers_cepages("Merlot 70 %; Cabernet franc 30%") == \
        [("Merlot", 70.0), ("Cabernet franc", 30.0)]
    assert echanges.cepages_vers_texte([("Syrah", 95.0), ("Viognier", None)]) == "Syrah 95%; Viognier"


def test_export_json_complet(cave_demo, tmp_path):
    comptes = echanges.exporter_json(cave_demo, tmp_path / "tout.json")
    d = json.loads((tmp_path / "tout.json").read_text(encoding="utf-8"))
    assert d["format"] == "vendemiaire-export" and d["tables"]["note_critique"]
    assert comptes["bouteille"] == cave_demo.base.valeur("SELECT COUNT(*) FROM bouteille")


def test_export_dossier_le_vin(cave_demo, tmp_path):
    """Format stable lu par le dossier LaTeX, en lecture seule."""
    d = export_dossier.exporter(cave_demo.base.chemin, tmp_path / "dossier.json", sorties_seulement=True)
    assert d["format"] == "vendemiaire-dossier" and d["version"] == 1
    cles_vin = {"vin_id", "domaine", "cuvee", "appellation", "region", "sous_region", "pays",
                "couleur", "type", "millesime", "cepages", "photo_etiquette", "photo_credit",
                "photo_licence", "notes", "bouteilles_en_cave", "photo_etiquette_absolue"}
    assert cles_vin <= set(d["vins"][0])
    cles_livre = {"mouvement_id", "date", "type", "vin_id", "domaine", "cuvee", "appellation",
                  "region", "pays", "millesime", "occasion", "convives", "plat", "lieu", "note",
                  "echelle", "commentaire", "photo_etiquette"}
    assert cles_livre <= set(d["livre"][0])
    assert all(l["type"].startswith("sortie") for l in d["livre"])
    assert json.loads((tmp_path / "dossier.json").read_text(encoding="utf-8"))["vins"]
