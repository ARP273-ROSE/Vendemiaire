# -*- coding: utf-8 -*-
"""Cave de démonstration, générée (jamais de vraies données dans le dépôt).

Les producteurs sont INVENTÉS ; les appellations, régions et cépages sont réels
(noms publics). Le tirage est déterministe : mêmes données à chaque
génération, donc des captures d'écran et des tests reproductibles.

    python -m vendemiaire.demo chemin/vers/demo.db
"""
from __future__ import annotations

import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from .base import Base
from .modele import Cave

#: (producteur inventé, cuvée, appellation, région, pays, couleur, type, cépages, degré, prix)
CATALOGUE = [
    ("Château des Trois Chênes", "Grand vin", "Pauillac", "Bordeaux", "France", "rouge", "tranquille",
     [("Cabernet sauvignon", 70), ("Merlot", 25), ("Petit verdot", 5)], 13.5, 85),
    ("Château des Trois Chênes", "Second vin", "Pauillac", "Bordeaux", "France", "rouge", "tranquille",
     [("Cabernet sauvignon", 60), ("Merlot", 40)], 13.0, 38),
    ("Château la Garenne", "", "Saint-Émilion grand cru", "Bordeaux", "France", "rouge", "tranquille",
     [("Merlot", 75), ("Cabernet franc", 25)], 14.0, 42),
    ("Clos du Vieux Puits", "", "Pessac-Léognan", "Bordeaux", "France", "blanc", "tranquille",
     [("Sauvignon blanc", 60), ("Sémillon", 40)], 13.0, 36),
    ("Château Bel-Orme du Sud", "", "Sauternes", "Bordeaux", "France", "blanc", "doux",
     [("Sémillon", 85), ("Sauvignon blanc", 15)], 13.5, 45),
    ("Domaine Marchand-Lavaux", "Les Combes", "Gevrey-Chambertin", "Bourgogne", "France", "rouge",
     "tranquille", [("Pinot noir", 100)], 13.0, 55),
    ("Domaine Marchand-Lavaux", "Clos de la Fontaine", "Vosne-Romanée premier cru", "Bourgogne",
     "France", "rouge", "tranquille", [("Pinot noir", 100)], 13.5, 120),
    ("Domaine de la Combe Haute", "", "Meursault", "Bourgogne", "France", "blanc", "tranquille",
     [("Chardonnay", 100)], 13.0, 48),
    ("Domaine de la Combe Haute", "Les Perrières", "Puligny-Montrachet premier cru", "Bourgogne",
     "France", "blanc", "tranquille", [("Chardonnay", 100)], 13.5, 95),
    ("Domaine Petit-Roc", "Vieilles vignes", "Chablis premier cru", "Bourgogne", "France", "blanc",
     "tranquille", [("Chardonnay", 100)], 12.5, 28),
    ("Domaine du Grand Mûrier", "", "Morgon", "Beaujolais", "France", "rouge", "tranquille",
     [("Gamay", 100)], 13.0, 17),
    ("Maison Aubertin & Fils", "Brut réserve", "Champagne", "Champagne", "France", "blanc",
     "effervescent", [("Chardonnay", 40), ("Pinot noir", 40), ("Pinot meunier", 20)], 12.0, 39),
    ("Maison Aubertin & Fils", "Blanc de blancs", "Champagne grand cru", "Champagne", "France",
     "blanc", "effervescent", [("Chardonnay", 100)], 12.0, 65),
    ("Maison Aubertin & Fils", "Rosé de saignée", "Champagne", "Champagne", "France", "rose",
     "effervescent", [("Pinot noir", 100)], 12.0, 58),
    ("Domaine des Galets Roulés", "", "Châteauneuf-du-Pape", "Vallée du Rhône", "France", "rouge",
     "tranquille", [("Grenache", 70), ("Syrah", 15), ("Mourvèdre", 15)], 15.0, 44),
    ("Domaine de la Serre Noire", "La Landonne du Bas", "Côte-Rôtie", "Vallée du Rhône", "France",
     "rouge", "tranquille", [("Syrah", 95), ("Viognier", 5)], 13.5, 70),
    ("Domaine de la Serre Noire", "", "Condrieu", "Vallée du Rhône", "France", "blanc", "tranquille",
     [("Viognier", 100)], 14.0, 49),
    ("Domaine du Coteau Fleuri", "", "Vouvray", "Val de Loire", "France", "blanc", "doux",
     [("Chenin blanc", 100)], 12.0, 24),
    ("Domaine du Coteau Fleuri", "Les Silex", "Sancerre", "Val de Loire", "France", "blanc",
     "tranquille", [("Sauvignon blanc", 100)], 13.0, 22),
    ("Domaine des Rochettes", "", "Chinon", "Val de Loire", "France", "rouge", "tranquille",
     [("Cabernet franc", 100)], 13.0, 16),
    ("Domaine Weinberg-Hoff", "Grand cru Schlossberg", "Alsace grand cru", "Alsace", "France", "blanc",
     "tranquille", [("Riesling", 100)], 12.5, 32),
    ("Domaine du Plateau de Lune", "", "Bandol", "Provence", "France", "rose", "tranquille",
     [("Mourvèdre", 60), ("Grenache", 25), ("Cinsault", 15)], 13.0, 21),
    ("Domaine des Lauzes", "", "Château-Chalon", "Jura", "France", "blanc", "tranquille",
     [("Savagnin", 100)], 14.0, 52),
    ("Mas de l'Olivette", "", "Pic-Saint-Loup", "Languedoc", "France", "rouge", "tranquille",
     [("Syrah", 50), ("Grenache", 30), ("Mourvèdre", 20)], 14.0, 19),
    ("Tenuta Collealto", "", "Barolo", "Piémont", "Italie", "rouge", "tranquille",
     [("Nebbiolo", 100)], 14.5, 58),
    ("Tenuta Collealto", "", "Brunello di Montalcino", "Toscane", "Italie", "rouge", "tranquille",
     [("Sangiovese", 100)], 14.0, 49),
    ("Bodegas Peña Alta", "Reserva", "Rioja", "Rioja", "Espagne", "rouge", "tranquille",
     [("Tempranillo", 90), ("Graciano", 10)], 14.0, 23),
    ("Quinta do Vale Escuro", "Vintage", "Porto", "Douro", "Portugal", "rouge", "mute",
     [("Touriga nacional", 50), ("Touriga franca", 50)], 20.0, 55),
    ("Weingut Sonnenhang", "Kabinett", "Mosel", "Moselle", "Allemagne", "blanc", "tranquille",
     [("Riesling", 100)], 8.5, 19),
    ("Ridgeback Cellars", "Estate", "Napa Valley", "Californie", "États-Unis", "rouge", "tranquille",
     [("Cabernet sauvignon", 85), ("Merlot", 15)], 14.5, 75),
]

OCCASIONS = ["Dîner entre amis", "Anniversaire", "Repas de famille", "Dimanche midi", "Noël",
             "Réveillon", "Barbecue", "Soirée dégustation", "Pique-nique", "Fête des pères"]
PLATS = ["Côte de bœuf", "Gigot d'agneau", "Poulet de Bresse rôti", "Plateau de fromages",
         "Sole meunière", "Huîtres", "Risotto aux cèpes", "Magret de canard", "Tarte au citron",
         "Bœuf bourguignon", "Saumon grillé", "Foie gras", "Pâtes aux truffes", "Choucroute"]
CONVIVES = ["Paul et Anne", "les voisins", "Marc", "la famille", "Claire, Hugo", "collègues",
            "Léa et Tom", "Jeanne"]
LIEUX_ACHAT = ["Au domaine", "Caviste", "Foire aux vins", "Vente aux enchères", "En ligne",
               "Salon des vins", "Cadeau"]
COMMENTAIRES = ["Superbe, encore jeune.", "À son apogée, magnifique.", "Un peu fatigué.",
                "Très bel équilibre, finale longue.", "Fermé à l'ouverture, s'ouvre en carafe.",
                "Fruit éclatant.", "Belle surprise pour le prix."]


def generer(chemin: str | Path, graine: int = 1792) -> Cave:
    """Crée (ou recrée) une base de démonstration au chemin donné."""
    chemin = Path(chemin)
    if chemin.exists():
        chemin.unlink()
    base = Base(chemin)
    cave = Cave(base)
    hasard = random.Random(graine)
    aujourdhui = date(2026, 10, 26)

    # --- emplacements : cave › meuble › casier ---------------------------
    maison = cave.creer_emplacement("Cave de la maison", "cave")
    mur = cave.creer_emplacement("Mur nord", "meuble", maison)
    casiers = [cave.creer_emplacement("Casier A", "casier", mur, 6, 10),
               cave.creer_emplacement("Casier B", "casier", mur, 6, 8)]
    armoire = cave.creer_emplacement("Armoire à vin", "meuble", maison)
    casiers.append(cave.creer_emplacement("Clayette 1", "casier", armoire, 3, 8))
    casiers.append(cave.creer_emplacement("Clayette 2", "casier", armoire, 3, 8))
    montagne = cave.creer_emplacement("Cave de la maison de montagne", "cave")
    etagere = cave.creer_emplacement("Étagère", "meuble", montagne)
    casiers.append(cave.creer_emplacement("Rayonnage", "casier", etagere, 4, 6))
    garde = cave.creer_emplacement("Cave de vieillissement", "cave")
    caisses = cave.creer_emplacement("Caisses", "meuble", garde)
    casiers.append(cave.creer_emplacement("Palette 1", "casier", caisses, 3, 12))
    libres = {c: cave.cases_libres(c) for c in casiers}

    def case(casier=None):
        ordre = [casier] if casier else hasard.sample(casiers, len(casiers))
        for c in ordre:
            if libres[c]:
                r, co = libres[c].pop(hasard.randrange(len(libres[c])))
                return (c, r, co)
        return None

    for i, (prod, cuvee, appel, region, pays, couleur, typ, cepages, degre, prix) in enumerate(CATALOGUE):
        millesimes = sorted(hasard.sample(range(2005, 2025), hasard.choice([1, 1, 2, 3])))
        for mil in millesimes:
            vin_id = cave.enregistrer_vin({
                "producteur": prod, "cuvee": cuvee, "appellation": appel, "region": region,
                "pays": pays, "couleur": couleur, "type": typ, "millesime": mil,
                "degre": degre, "cepages": cepages,
                "non_millesime": 0,
                "coup_de_coeur": 1 if hasard.random() < 0.12 else 0,
                "seuil_reassort": 6 if (typ == "effervescent" and cuvee == "Brut réserve") else None,
            })
            n = hasard.choice([1, 2, 3, 3, 6, 6, 6, 12]) if prix < 60 else hasard.choice([1, 2, 3, 6])
            achat = aujourdhui - timedelta(days=hasard.randrange(60, 3200))
            fmt = "magnum" if (prix > 40 and hasard.random() < 0.12) else "bouteille"
            prix_unitaire = round(prix * (1 + hasard.uniform(-0.15, 0.25)) * (2.1 if fmt == "magnum" else 1), 2)
            caisse_cbo = typ == "tranquille" and region == "Bordeaux" and n in (6, 12)
            primeur = (mil >= 2023 and region in ("Bordeaux", "Bourgogne", "Vallée du Rhône"))
            attributs = {
                "format": fmt, "prix_achat": prix_unitaire, "lieu_achat": hasard.choice(LIEUX_ACHAT),
                "date_achat": achat.isoformat(),
                "statut": "primeur" if primeur else "en_cave",
                "caisse": "cbo" if caisse_cbo else hasard.choice(["aucune", "carton", "aucune"]),
                "caisse_complete": 1 if caisse_cbo else None,
                "provenance": "Achetée au domaine, jamais déplacée" if hasard.random() < 0.3 else None,
                "etat_etiquette": hasard.choice(["parfaite"] * 6 + ["legere", "tachee"]),
                "etat_capsule": "intacte",
                "niveau": (hasard.choice(["IN", "BN", "BN", "VTS", "TS"]) if mil < 2012 else "IN"),
            }
            if primeur:
                attributs["date_livraison_prevue"] = date(mil + 3, 3, 1).isoformat()
                cave.ajouter_bouteilles(vin_id, n, attributs, mouvement=None)
            else:
                casier = casiers[-1] if caisse_cbo else None
                positions = [case(casier) or case() for _ in range(n)]
                cave.ajouter_bouteilles(vin_id, n, attributs, positions,
                                        date_mouvement=achat.isoformat())
            # notes de critiques et fenêtres (exemples ; valeurs inventées)
            if prix > 40 and hasard.random() < 0.7:
                cave.ajouter_note_critique(vin_id, hasard.choice(["RP", "WS", "JS"]),
                                           hasard.randrange(89, 98), "100", source="démonstration")
            if hasard.random() < 0.4:
                cave.ajouter_note_critique(vin_id, hasard.choice(["BD", "RVF", "JR"]),
                                           hasard.choice([15.5, 16, 16.5, 17, 17.5, 18]), "20",
                                           source="démonstration")
            if hasard.random() < 0.5:
                d = mil + hasard.randrange(2, 8)
                cave.definir_fenetre(vin_id, "perso", d, d + hasard.randrange(6, 20))
            if hasard.random() < 0.35:
                cave.ajouter_valeur(vin_id, round(prix_unitaire * hasard.uniform(1.0, 1.8), 0),
                                    "estimation (démonstration)", (aujourdhui - timedelta(days=30)).isoformat())

    # --- livre de cave : des sorties étalées sur deux ans ---------------
    presentes = [r["id"] for r in base.lire("SELECT id FROM bouteille WHERE statut='en_cave'")]
    hasard.shuffle(presentes)
    for bid in presentes[: len(presentes) // 4]:
        jour = aujourdhui - timedelta(days=hasard.randrange(1, 700))
        b = cave.bouteille(bid)
        if b["date_entree"] and b["date_entree"] > jour.isoformat():
            continue
        genre = hasard.choices(["sortie_bue", "sortie_offerte", "sortie_bouchonnee", "sortie_cassee"],
                               [20, 4, 1, 0.5])[0]
        if genre == "sortie_bue":
            cave.sortir(bid, genre, jour.isoformat(), occasion=hasard.choice(OCCASIONS),
                        convives=hasard.choice(CONVIVES), plat=hasard.choice(PLATS),
                        note=hasard.choice([15, 16, 16.5, 17, 17.5, 18, 18.5]), echelle="20",
                        commentaire=hasard.choice(COMMENTAIRES))
        else:
            cave.sortir(bid, genre, jour.isoformat(), occasion=hasard.choice(OCCASIONS))
    # une bouteille ouverte
    reste = base.un("SELECT id FROM bouteille WHERE statut='bue' ORDER BY date_sortie DESC LIMIT 1")
    if reste:
        with base.ecriture() as c:
            c.execute("INSERT INTO bouteille_ouverte(bouteille_id, ouverte_le, reste_cl, conservation) "
                      "VALUES(?,?,?,?)", (reste["id"], aujourdhui.isoformat(), 35, "gaz"))
    # liste d'envies
    with base.ecriture() as c:
        for prod, cuv, app, mil in (("Domaine Marchand-Lavaux", "Clos de la Fontaine",
                                     "Vosne-Romanée premier cru", 2020),
                                    ("Maison Aubertin & Fils", "Blanc de blancs", "Champagne grand cru", None)):
            c.execute("INSERT INTO envie(producteur, cuvee, appellation, millesime, quantite, cree_le) "
                      "VALUES(?,?,?,?,?,?)", (prod, cuv, app, mil, 6, aujourdhui.isoformat()))
    # conditions de cave : quatre mois de mesures quotidiennes (inventées)
    mesures = []
    for j in range(120):
        jour = aujourdhui - timedelta(days=120 - j)
        saison = 1.6 * math.sin((jour.timetuple().tm_yday - 120) / 365 * 2 * math.pi)
        mesures.append((maison, f"{jour.isoformat()} 08:00:00",
                        round(12.5 + saison + hasard.uniform(-0.4, 0.4), 1),
                        round(72 + hasard.uniform(-5, 5))))
    cave.ajouter_conditions(mesures, source="démonstration")
    base.definir_meta("demonstration", "1")
    return cave


def references_demo(cave) -> int:
    """Une petite copie « LWIN » de DÉMONSTRATION pour les producteurs inventés
    du catalogue (codes 99xxxxx, fictifs) et quelques voisins trompeurs : de
    quoi essayer l'appariement sans le vrai fichier de Liv-ex."""
    from .mondial.lwin import convertir
    lignes = []
    vus = set()
    code = 9900001
    couleurs = {"rouge": "Red", "blanc": "White", "rose": "Rose"}
    types = {"effervescent": "Sparkling", "doux": "Sweet", "mute": "Fortified"}
    for prod, cuvee, appel, region, pays, couleur, typ, *_ in CATALOGUE:
        if (prod, cuvee) in vus:
            continue
        vus.add((prod, cuvee))
        titre, _, nom = prod.partition(" ") if prod.split(" ")[0] in ("Château", "Domaine", "Maison",
                                                                       "Clos", "Tenuta", "Bodegas",
                                                                       "Weingut", "Quinta", "Mas") \
            else ("", "", prod)
        lignes.append(convertir({"lwin": str(code), "statut": "Live", "titre_producteur": titre,
                                 "producteur": nom, "vin": cuvee, "pays": pays, "region": region,
                                 "sous_region": appel, "couleur": couleurs.get(couleur, ""),
                                 "type": "Wine", "sous_type": types.get(typ, "Still"),
                                 "premier_millesime": "1990", "nom": " ".join(x for x in (prod, cuvee) if x)}))
        code += 1
    for prod, vin, appel, couleur in (("Château des Trois Ormes", "", "Pauillac", "Red"),
                                      ("Château des Trois Chênes", "Blanc des Chênes", "Bordeaux", "White"),
                                      ("Domaine Marchand", "Les Combes", "Gevrey-Chambertin", "Red"),
                                      ("Maison Aubertin", "Brut", "Champagne", "White")):
        titre, _, nom = prod.partition(" ")
        lignes.append(convertir({"lwin": str(code), "statut": "Live", "titre_producteur": titre,
                                 "producteur": nom, "vin": vin, "pays": "France", "region": "",
                                 "sous_region": appel, "couleur": couleur, "type": "Wine",
                                 "sous_type": "Still", "nom": " ".join(x for x in (prod, vin) if x)}))
        code += 1
    return cave.references.remplacer_lwin(lignes, source="Vendémiaire (demo)")


def photos_demo(cave, nombre: int = 8) -> int:
    """Photos d'étiquette DESSINÉES (libres) pour quelques vins, redressées
    automatiquement comme le ferait l'utilisateur. Demande une QGuiApplication."""
    import tempfile
    from . import demo_photos, images
    vins = cave.base.lire("SELECT v.id FROM vin v JOIN bouteille b ON b.vin_id=v.id "
                          "WHERE b.statut='en_cave' GROUP BY v.id ORDER BY v.id")
    pas = max(1, len(vins) // nombre)
    n = 0
    with tempfile.TemporaryDirectory() as tmp:
        for i, r in enumerate(vins[::pas][:nombre]):
            v = dict(cave.vin(r["id"]))
            photo, _coins = demo_photos.generer(v, Path(tmp) / f"photo{i}.jpg", graine=i + 3)
            img = images.charger(photo)
            d = images.detecter_etiquette(img)
            retouche = images.Retouche(coins=d.coins if d else None, auto=bool(d))
            traite = images.enregistrer(images.appliquer(img, retouche), Path(tmp) / f"etiquette{i}.jpg")
            cave.ajouter_image(traite, vin_id=r["id"], original=photo, retouche=retouche.json(),
                               credit="Vendémiaire (démonstration)", licence="CC0 1.0")
            n += 1
    return n


if __name__ == "__main__":
    cible = sys.argv[1] if len(sys.argv) > 1 else "demo.db"
    c = generer(cible)
    s = c.statistiques()
    print(f"{cible} : {s['bouteilles']} bouteilles en cave, {s['vins']} vins")
