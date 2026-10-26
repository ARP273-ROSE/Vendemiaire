# -*- coding: utf-8 -*-
"""Validation de robustesse : une très grosse cave (20 000 bouteilles par
défaut, producteurs inventés), puis les temps de l'interface — ouverture de la
fenêtre, chaque onglet, recherche, tableau de bord, statistiques, plan, livre,
liste d'achats. Chaque durée est le temps pendant lequel le fil de l'interface
est occupé (donc un gel s'il dépasse quelques dixièmes de seconde).

    xvfb-run -a -s "-screen 0 1920x1080x24" python outils/grosse_cave.py [nombre]
"""
from __future__ import annotations

import random
import sys
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

APPELLATIONS = [("Pauillac", "Bordeaux", "rouge"), ("Margaux", "Bordeaux", "rouge"),
                ("Saint-Émilion grand cru", "Bordeaux", "rouge"), ("Sauternes", "Bordeaux", "blanc"),
                ("Gevrey-Chambertin", "Bourgogne", "rouge"), ("Meursault", "Bourgogne", "blanc"),
                ("Chablis premier cru", "Bourgogne", "blanc"), ("Champagne", "Champagne", "blanc"),
                ("Côte-Rôtie", "Vallée du Rhône", "rouge"), ("Châteauneuf-du-Pape", "Vallée du Rhône", "rouge"),
                ("Sancerre", "Vallée de la Loire", "blanc"), ("Bandol", "Provence", "rose"),
                ("Riesling grand cru", "Alsace", "blanc"), ("Barolo", "Piémont", "rouge"),
                ("Rioja", "Rioja", "rouge"), ("Porto", "Douro", "rouge")]


def generer(chemin: str | Path, nombre: int = 20000, graine: int = 7):
    """Base de `nombre` bouteilles en cave (et autant de lignes d'entrée au livre),
    écrite en une transaction (quelques secondes)."""
    from vendemiaire.base import Base, maintenant, normaliser
    from vendemiaire.modele import Cave
    chemin = Path(chemin)
    if chemin.exists():
        chemin.unlink()
    cave = Cave(Base(chemin), chemin.parent / "images")
    h = random.Random(graine)
    t = maintenant()
    n_vins = max(1, nombre // 6)
    n_prod = max(1, n_vins // 4)
    casiers_par_cave = 10
    with cave.base.ecriture() as c:
        caves = []
        for k in range(1 + nombre // 2400):
            cid = c.execute("INSERT INTO emplacement(niveau, nom, ordre) VALUES('cave', ?, ?)",
                            (f"Cave {k + 1}", k)).lastrowid
            mid = c.execute("INSERT INTO emplacement(parent_id, niveau, nom) VALUES(?, 'meuble', 'Mur')",
                            (cid,)).lastrowid
            for j in range(casiers_par_cave):
                caves.append(c.execute("INSERT INTO emplacement(parent_id, niveau, nom, rangees, colonnes, ordre) "
                                       "VALUES(?, 'casier', ?, 12, 20, ?)", (mid, f"Casier {j + 1}", j)).lastrowid)
        for p in range(n_prod):
            nom = f"Domaine Essai {p + 1:04d}"
            c.execute("INSERT INTO producteur(id, nom, nom_normalise, cree_le, modifie_le) VALUES(?,?,?,?,?)",
                      (p + 1, nom, normaliser(nom), t, t))
        for v in range(n_vins):
            app, region, couleur = h.choice(APPELLATIONS)
            typ = "effervescent" if app == "Champagne" else ("mute" if app == "Porto" else
                                                              ("doux" if app == "Sauternes" else "tranquille"))
            cuvee = f"Cuvée {h.choice(['Réserve', 'Vieilles vignes', 'Clos', 'Prestige', 'Tradition'])} {v % 97}"
            c.execute("INSERT INTO vin(id, producteur_id, cuvee, cuvee_normalisee, appellation, region, pays, "
                      "couleur, type, millesime, seuil_reassort, cree_le, modifie_le) "
                      "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (v + 1, h.randint(1, n_prod), cuvee, normaliser(cuvee), app, region,
                       "Italie" if app == "Barolo" else ("Espagne" if app == "Rioja" else
                                                         ("Portugal" if app == "Porto" else "France")),
                       couleur, typ, h.randint(1985, 2023), 6 if v % 50 == 0 else None, t, t))
        cases = [(cas, r, co) for cas in caves for r in range(1, 13) for co in range(1, 21)]
        h.shuffle(cases)
        debut = date(2005, 1, 1)
        for b in range(nombre):
            vin = h.randint(1, n_vins)
            entree = (debut + timedelta(days=h.randint(0, 7600))).isoformat()
            cas, r, co = cases[b] if b < len(cases) else (None, None, None)
            bid = c.execute("INSERT INTO bouteille(vin_id, statut, emplacement_id, rangee, colonne, prix_achat, "
                            "lieu_achat, date_entree, code_interne, cree_le, modifie_le) "
                            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                            (vin, "en_cave", cas, r, co, round(h.uniform(8, 300), 2), "Caviste",
                             entree, f"V{b:010X}", t, t)).lastrowid
            c.execute("INSERT INTO mouvement(date, type, vin_id, bouteille_id, cree_le) "
                      "VALUES(?, 'entree_achat', ?, ?, ?)", (entree, vin, bid, t))
    return cave


def mesurer(cave, app) -> dict:
    """Temps (s) de chaque opération de l'interface sur cette cave."""
    from PyQt6 import QtCore
    from vendemiaire import achats, i18n
    from vendemiaire.ui.fenetre import FenetrePrincipale
    i18n.definir_langue("fr")
    QtCore.QSettings().clear()
    durees: dict[str, float] = {}

    def chrono(nom, fonction):
        t0 = time.perf_counter()
        r = fonction()
        app.processEvents()
        durees[nom] = round(time.perf_counter() - t0, 3)
        return r

    w = chrono("ouverture de la fenêtre", lambda: FenetrePrincipale(cave, aide_kit=False))
    chrono("affichage", w.show)
    for i in range(w.onglets.count()):
        chrono(f"onglet « {w.onglets.tabText(i)} »", lambda i=i: w.onglets.setCurrentIndex(i))
    chrono("recherche dans la cave", lambda: w.vue_cave.recherche.setText("pauillac"))
    chrono("recherche effacée", lambda: w.vue_cave.recherche.setText(""))
    chrono("tableau de bord (rafraîchir)", w.tableau.rafraichir)
    chrono("livre de cave (rafraîchir)", w.livre.rafraichir)
    casier = cave.base.valeur("SELECT id FROM emplacement WHERE niveau='casier' ORDER BY id LIMIT 1")
    chrono("plan : un casier de 240 cases", lambda: w.plan.afficher_casier(casier))
    chrono("statistiques (rafraîchir)", w.statistiques.rafraichir)
    chrono("liste d'achats", lambda: achats.liste_achats(cave))
    chrono("tout rafraîchir (après une saisie)", w.tout_rafraichir)
    n = cave.base.valeur("SELECT COUNT(*) FROM bouteille WHERE statut='en_cave'")
    w.minuteur.stop()
    w.hide()
    w.deleteLater()
    app.processEvents()
    return {"bouteilles": n, "durees": durees}


def main() -> int:
    from PyQt6 import QtWidgets
    nombre = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    app = QtWidgets.QApplication(sys.argv[:1])
    app.setOrganizationName("VendemiaireMesure")
    with tempfile.TemporaryDirectory() as tmp:
        t0 = time.perf_counter()
        cave = generer(Path(tmp) / "grosse.db", nombre)
        print(f"base de {nombre} bouteilles écrite en {time.perf_counter() - t0:.1f} s "
              f"({(Path(tmp) / 'grosse.db').stat().st_size / 1e6:.1f} Mo)")
        m = mesurer(cave, app)
        for cle, d in m["durees"].items():
            print(f"  {d:7.3f} s  {cle}")
        print(f"plus long : {max(m['durees'].values()):.3f} s")
        cave.base.fermer()
    return 0


if __name__ == "__main__":
    sys.exit(main())
