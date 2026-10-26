# -*- coding: utf-8 -*-
"""Écrans de la phase 1 qui manquaient (données) : liste d'envies, critiques
et conversions, valeurs datées et sourcées, conditions de cave (saisie et
import CSV), inventaire de contrôle."""
import json

from vendemiaire import echanges, regles


def test_liste_d_envies(cave):
    e = cave.ajouter_envie({"producteur": " Domaine Exemple ", "cuvee": "", "millesime": 2019,
                            "prix_max": 45.0, "priorite": 1, "quantite": 6})
    l = cave.envies()
    assert len(l) == 1 and l[0]["producteur"] == "Domaine Exemple" and l[0]["cuvee"] is None
    cave.modifier_envie(e, {"prix_max": 50.0})
    assert cave.envies()[0]["prix_max"] == 50.0
    cave.satisfaire_envie(e, "2026-10-26")
    assert cave.envies() == [] and cave.envies(avec_satisfaites=True)[0]["satisfaite_le"] == "2026-10-26"
    cave.supprimer_envie(e)
    assert cave.envies(avec_satisfaites=True) == []


def test_critiques_et_conversion_sourcee(cave):
    from vendemiaire.ui.critiques import equivalence
    from vendemiaire import i18n
    vin = cave.enregistrer_vin({"producteur": "Domaine Exemple"})
    n = cave.ajouter_note_critique(vin, "RP", 94, "100", 96, "texte", "2026-01-01", "magazine")
    cave.modifier_note_critique(n, "WS", 91, "100", None, "", "2026-02-01", "")
    note = cave.notes_critiques(vin)[0]
    assert (note["critique"], note["note"], note["note_max"], note["source"]) == ("WS", 91, None, None)
    regles.charger_livres()
    i18n.definir_langue("fr")
    texte = equivalence(91, "100")
    assert "17,5" in texte and "notes.conversion" in texte
    assert "Decanter" in texte                                 # le pourquoi vient de la règle du dossier
    assert "pas de conversion" in equivalence(4, "5")
    assert "remarquable" in equivalence(2, "3")
    cave.supprimer_note_critique(n)
    assert cave.notes_critiques(vin) == []


def test_valeurs_datees_et_sourcees(cave):
    vin = cave.enregistrer_vin({"producteur": "Domaine Exemple"})
    v = cave.ajouter_valeur_complete(vin, 120, "vente aux enchères", "2026-03-01", "magnum", "EUR",
                                     "https://exemple.org/lot/12", "lot 12")
    r = cave.valeurs(vin)[0]
    assert (r["montant"], r["format"], r["source"], r["url"], r["note"]) == \
        (120, "magnum", "vente aux enchères", "https://exemple.org/lot/12", "lot 12")
    cave.supprimer_valeur(v)
    assert cave.valeurs(vin) == []


def test_conditions_saisie_et_import_csv(cave, tmp_path):
    lieu = cave.creer_emplacement("Cave", "cave")
    assert cave.ajouter_conditions([(lieu, "2026-10-01 08:00:00", 12.5, 71)]) == 1
    assert cave.ajouter_conditions([(lieu, "2026-10-01 08:00:00", 12.5, 71)]) == 0   # pas de doublon
    f = tmp_path / "sonde.csv"
    f.write_text("Date;Température (°C);Humidité (%)\n"
                 "02/10/2026 08:00;12,8;70\n03/10/2026 08:00;13,1;69\n"
                 "date illisible;12;70\n04/10/2026 08:00;13,4;140\n", encoding="utf-8")
    r = echanges.importer_conditions(cave, f, lieu)
    assert r.mesures == 2 and len(r.avertissements) == 1          # humidité 140 % écartée
    assert cave.conditions(lieu)[0]["temperature"] == 13.1
    ha = tmp_path / "ha.csv"
    ha.write_text("entity_id,state,last_changed\n"
                  "sensor.cave_temperature,12.9,2026-10-05T06:00:00.000Z\n"
                  "sensor.cave_humidity,68,2026-10-05T06:00:00.000Z\n", encoding="utf-8")
    r = echanges.importer_conditions(cave, ha, lieu)
    assert r.mesures == 1
    m = cave.conditions(lieu)[0]
    assert (m["date_heure"], m["temperature"], m["hygrometrie"], m["source"]) == \
        ("2026-10-05 06:00:00", 12.9, 68, "csv")
    s = cave.resume_conditions(lieu)
    assert s["n"] == 4 and s["tmin"] == 12.5 and s["tmax"] == 13.1
    cave.supprimer_condition(m["id"])
    assert cave.resume_conditions(lieu)["n"] == 3


def test_inventaire_de_controle(cave):
    lieu = cave.creer_emplacement("Cave", "cave")
    meuble = cave.creer_emplacement("Mur", "meuble", lieu)
    casier = cave.creer_emplacement("A", "casier", meuble, 2, 2)
    vin = cave.enregistrer_vin({"producteur": "Domaine Exemple"})
    ids = cave.ajouter_bouteilles(vin, 3, positions=[(casier, 1, 1), (casier, 1, 2), (casier, 2, 1)])
    assert [b["id"] for b in cave.attendues(lieu)] == ids          # la cave entière compte ses casiers
    code = cave.bouteille(ids[0])["code_interne"]
    assert cave.bouteille_par_code(code)["id"] == ids[0]
    ecarts = cave.enregistrer_inventaire(casier, [ids[0], ids[1]], ["bouteille sans étiquette"])
    assert ecarts == {"manquantes": [ids[2]], "ailleurs": [], "en_trop": ["bouteille sans étiquette"]}
    inv = cave.inventaires(casier)[0]
    assert (inv["attendu"], inv["compte"]) == (3, 3) and json.loads(inv["ecarts"]) == ecarts
    assert cave.bouteille(ids[2])["statut"] == "en_cave"            # rien ne change sans décision
    assert cave.marquer_manquantes(ecarts["manquantes"]) == 1
    assert cave.bouteille(ids[2])["statut"] == "manquante"
    assert cave.mouvements(limite=1)[0]["type"] == "sortie_inventaire"
