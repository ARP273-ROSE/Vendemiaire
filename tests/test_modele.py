# -*- coding: utf-8 -*-
"""Modèle de données : vins, bouteilles, emplacements, livre de cave, règle
« jamais d'écrasement d'une saisie manuelle », un seul écrivain."""
import sqlite3
import threading
import time

import pytest

from vendemiaire.base import Base, normaliser
from vendemiaire.modele import CaseOccupee


def _vin(cave, **extra):
    d = {"producteur": "Domaine Essai", "cuvee": "Les Pierres", "appellation": "Morgon",
         "region": "Beaujolais", "pays": "France", "couleur": "rouge", "millesime": 2019,
         "cepages": [("Gamay", 100)]}
    d.update(extra)
    return cave.enregistrer_vin(d)


def test_schema_complet(base):
    tables = {r[0] for r in base.lire("SELECT name FROM sqlite_master WHERE type='table'")}
    attendues = {"producteur", "vin", "vin_cepage", "identifiant_externe", "emplacement",
                 "bouteille", "deplacement", "mouvement", "degustation", "seance",
                 "note_critique", "fenetre_degustation", "valeur", "envie", "bouteille_ouverte",
                 "condition_cave", "inventaire", "image", "origine_champ",
                 "journal_enrichissement", "meta"}
    assert attendues <= tables
    vues = {r[0] for r in base.lire("SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"v_dossier_vin", "v_dossier_livre"} <= vues
    assert base.valeur("PRAGMA journal_mode") == "delete"      # jamais WAL (partage réseau)
    assert base.valeur("PRAGMA foreign_keys") == 1


def test_vin_et_cepages(cave):
    vid = _vin(cave)
    v = cave.vin(vid)
    assert v["producteur"] == "Domaine Essai" and v["millesime"] == 2019
    assert cave.cepages(vid) == [("Gamay", 100.0)]
    assert cave.origines(vid)["appellation"] == "manuel"
    # même producteur écrit autrement : un seul producteur
    vid2 = _vin(cave, producteur="DOMAINE  essai", cuvee="Autre")
    assert cave.vin(vid2)["producteur_id"] == cave.vin(vid)["producteur_id"]
    with pytest.raises(sqlite3.IntegrityError):
        _vin(cave, millesime=1500)


def test_normalisation():
    assert normaliser("Château  Léoville-Las Cases") == normaliser("CHATEAU LEOVILLE LAS CASES")
    assert normaliser("Domaine de l'Arlot") == "arlot"


def test_import_n_ecrase_jamais_la_saisie_manuelle(cave):
    vid = _vin(cave, degre=None, classement="Cru")
    cave.enregistrer_vin({"classement": "", "degre": None}, vid)
    # l'utilisateur a VIDÉ le classement à la main : l'import ne doit pas le remplir ;
    # le degré, jamais rempli, reste ouvert aux imports
    remplis = cave.completer_vin(vid, {"appellation": "Fleurie", "degre": 13.5,
                                       "classement": "cru", "lwin": "1234567"}, "lwin", "essai")
    v = cave.vin(vid)
    assert v["appellation"] == "Morgon"                 # saisi à la main : intact
    assert v["classement"] is None                      # vidé à la main : reste vide
    assert v["degre"] == 13.5 and v["lwin"] == "1234567"
    assert set(remplis) == {"degre", "lwin"}
    journal = cave.base.lire("SELECT champ, source FROM journal_enrichissement WHERE ligne_id=?", (vid,))
    assert {(r["champ"], r["source"]) for r in journal} == {("degre", "lwin"), ("lwin", "lwin")}
    # un second import ne touche plus rien
    assert cave.completer_vin(vid, {"degre": 12.0}, "csv") == []
    assert cave.vin(vid)["degre"] == 13.5


def test_bouteilles_cases_et_deplacements(cave):
    vid = _vin(cave)
    c = cave.creer_emplacement("Cave", "cave")
    m = cave.creer_emplacement("Mur", "meuble", c)
    k = cave.creer_emplacement("Casier", "casier", m, 2, 3)
    k2 = cave.creer_emplacement("Autre", "casier", m, 2, 2)
    ids = cave.ajouter_bouteilles(vid, 3, {"prix_achat": 12.5, "format": "magnum"},
                                  [(k, 1, 1), (k, 1, 2), (k, 1, 3)])
    assert len(cave.cases_libres(k)) == 3
    assert cave.chemin_emplacement(k) == ["Cave", "Mur", "Casier"]
    with pytest.raises(CaseOccupee):
        cave.ajouter_bouteilles(vid, 1, {}, [(k, 1, 1)])
    with pytest.raises(ValueError):
        cave.ajouter_bouteilles(vid, 1, {}, [(k, 3, 1)])          # hors du casier
    # échange de deux bouteilles dans un même lot
    cave.deplacer([(ids[0], k, 1, 2), (ids[1], k, 1, 1)])
    assert (cave.bouteille(ids[0])["colonne"], cave.bouteille(ids[1])["colonne"]) == (2, 1)
    # lot invalide (deux bouteilles vers la même case) : rien ne bouge
    with pytest.raises(CaseOccupee):
        cave.deplacer([(ids[0], k2, 1, 1), (ids[2], k2, 1, 1)])
    assert cave.bouteille(ids[0])["emplacement_id"] == k
    lot = cave.deplacer([(i, k2, 1 + n // 2, 1 + n % 2) for n, i in enumerate(ids)], "essai")
    assert {r["lot"] for r in cave.base.lire("SELECT lot FROM deplacement WHERE lot=?", (lot,))} == {lot}
    h = cave.historique_deplacements(ids[0])
    assert [r["motif"] for r in h] == ["entree", "", "essai"]
    assert len(cave.contenu_casier(k2)) == 3 and len(cave.cases_libres(k)) == 6


def test_livre_de_cave_entrees_sorties(cave):
    vid = _vin(cave)
    ids = cave.ajouter_bouteilles(vid, 2, {"prix_achat": 20, "lieu_achat": "Au domaine"},
                                  date_mouvement="2025-01-10")
    assert [m["type"] for m in cave.mouvements()] == ["entree_achat", "entree_achat"]
    cave.sortir(ids[0], "sortie_bue", "2026-10-01", occasion="Anniversaire", convives="amis",
                plat="Poulet rôti", note=17.5, echelle="20", commentaire="Très bon")
    b = cave.bouteille(ids[0])
    assert b["statut"] == "bue" and b["date_sortie"] == "2026-10-01"
    m = cave.mouvements(limite=1)[0]
    assert (m["type"], m["plat"], m["note"]) == ("sortie_bue", "Poulet rôti", 17.5)
    with pytest.raises(ValueError):
        cave.sortir(ids[0], "sortie_bue")                     # déjà sortie
    # la case d'une bouteille bue est libérée
    k = cave.creer_emplacement("K", "casier", None, 1, 1)
    cave.deplacer([(ids[1], k, 1, 1)])
    cave.sortir(ids[1], "sortie_offerte")
    assert cave.cases_libres(k) == [(1, 1)]
    assert len(cave.mouvements(texte="poulet")) == 1


def test_primeur_puis_reception(cave):
    vid = _vin(cave)
    (bid,) = cave.ajouter_bouteilles(vid, 1, {"statut": "primeur",
                                              "date_livraison_prevue": "2027-03-01"})
    assert cave.mouvements() == []                     # pas encore dans la cave
    s = cave.statistiques()
    assert s["a_venir"] == 1 and s["bouteilles"] == 0 and s["primeurs"][0]["n"] == 1
    cave.recevoir(bid, "2027-03-02")
    assert cave.bouteille(bid)["statut"] == "en_cave"
    assert cave.mouvements()[0]["type"] == "entree_primeur"


def test_critiques_fenetres_valeurs_et_statistiques(cave):
    vid = _vin(cave, seuil_reassort=4)
    cave.ajouter_bouteilles(vid, 2, {"prix_achat": 10})
    cave.ajouter_note_critique(vid, "RP", 93, "100")
    cave.ajouter_note_critique(vid, "JR", 17, "20", note_max=17.5)
    cave.definir_fenetre(vid, "perso", 2024, 2032)
    cave.definir_fenetre(vid, "critique", 2025, 2035, detail_source="RP")
    cave.definir_fenetre(vid, "perso", 2025, 2030)              # remplace la mienne
    assert [(f["source"], f["debut"]) for f in cave.fenetres(vid)] == [("perso", 2025), ("critique", 2025)]
    cave.ajouter_valeur(vid, 18, "saisie", "2026-01-01")
    s = cave.statistiques()
    assert s["valeur_estimee"] == 36 and s["prix_total"] == 20 and s["litres"] == 1.5
    assert s["reassort"][0]["n"] == 2
    assert cave.liste_vins("gamay morgon")[0]["valeur_unitaire"] == 18


def test_images_copiees_avec_credit(cave, tmp_path):
    vid = _vin(cave)
    photo = tmp_path / "photo.png"
    from PyQt6.QtGui import QGuiApplication, QImage  # noqa: F401
    photo.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    iid = cave.ajouter_image(photo, vin_id=vid, origine="commons", credit="Auteur X",
                             licence="CC BY-SA 4.0")
    r = cave.base.un("SELECT * FROM image WHERE id=?", (iid,))
    assert r["licence"] == "CC BY-SA 4.0" and (cave.dossier_images / r["fichier"]).exists()
    assert cave.image_principale(vid) == cave.dossier_images / r["fichier"]
    d = cave.base.un("SELECT photo_etiquette, photo_credit FROM v_dossier_vin WHERE vin_id=?", (vid,))
    assert d["photo_etiquette"] == r["fichier"] and d["photo_credit"] == "Auteur X"


def test_un_seul_ecrivain(base):
    """Un autre écrivain tient la base : on le sait en quelques secondes, pas deux minutes."""
    autre = sqlite3.connect(str(base.chemin), isolation_level=None)
    autre.execute("BEGIN IMMEDIATE")
    try:
        t = time.monotonic()
        assert not base.ecrivain_disponible(patience=0.5)
        assert time.monotonic() - t < 3
    finally:
        autre.execute("ROLLBACK")
        autre.close()
    assert base.ecrivain_disponible()


def test_lecture_seule_n_ecrit_pas(base):
    c = Base.lecture_seule(base.chemin)
    with pytest.raises(sqlite3.OperationalError):
        c.execute("INSERT INTO meta VALUES('x', 'y')")
    c.close()


def test_transaction_annulee_en_entier(cave):
    vid = _vin(cave)
    avant = cave.base.valeur("SELECT COUNT(*) FROM bouteille")
    with pytest.raises(RuntimeError):
        with cave.base.ecriture() as c:
            c.execute("INSERT INTO bouteille(vin_id, cree_le, modifie_le) VALUES(?, 'x', 'x')", (vid,))
            raise RuntimeError("panne")
    assert cave.base.valeur("SELECT COUNT(*) FROM bouteille") == avant


def test_verrou_equitable_entre_fils(cave):
    """Un fil de fond qui écrit en boucle n'affame pas les lectures."""
    vid = _vin(cave)
    stop = threading.Event()

    def fond():
        while not stop.is_set():
            with cave.base.ecriture() as c:
                c.execute("UPDATE vin SET notes=? WHERE id=?", (str(time.time()), vid))

    f = threading.Thread(target=fond, daemon=True)
    f.start()
    try:
        pires = []
        for _ in range(20):
            t = time.monotonic()
            cave.base.valeur("SELECT COUNT(*) FROM vin")
            pires.append(time.monotonic() - t)
        assert max(pires) < 1.0
    finally:
        stop.set()
        f.join(5)


def test_demonstration(cave_demo):
    s = cave_demo.statistiques()
    assert s["bouteilles"] > 120 and s["vins"] > 30 and s["a_venir"] > 0
    assert cave_demo.base.meta("demonstration") == "1"
    assert cave_demo.base.valeur("SELECT COUNT(*) FROM mouvement WHERE type='sortie_bue'") > 10
