# -*- coding: utf-8 -*-
"""Interface (sous Xvfb en CI) : fenêtre, liste et filtres, fiche, saisie,
sortie au livre de cave, plan des casiers avec glisser-déposer et lot,
colonnes retenues, changement de langue."""
import re

import pytest
from PyQt6 import QtCore, QtWidgets

from vendemiaire import i18n


@pytest.fixture
def fenetre(app, cave_demo):
    i18n.definir_langue("fr")
    from vendemiaire.ui.fenetre import FenetrePrincipale
    QtCore.QSettings().clear()
    w = FenetrePrincipale(cave_demo, aide_kit=False)
    w.show()
    app.processEvents()
    yield w
    w.minuteur.stop()
    w.hide()
    w.deleteLater()
    app.processEvents()


def _textes_d_interface(w) -> list[str]:
    """Textes « de l'application » (pas les données) : menus, onglets, boutons,
    cadres, en-têtes, invites."""
    t = []
    for a in w.findChildren(QtWidgets.QMenu):
        t += [x.text() for x in a.actions()] + [a.title()]
    tabs = w.onglets
    t += [tabs.tabText(i) for i in range(tabs.count())]
    for b in w.findChildren(QtWidgets.QAbstractButton):
        t.append(b.text())
    for g in w.findChildren(QtWidgets.QGroupBox):
        t.append(g.title())
    for e in w.findChildren(QtWidgets.QLineEdit):
        t.append(e.placeholderText())
    for v in w.findChildren(QtWidgets.QTableView):
        m = v.model()
        t += [str(m.headerData(c, QtCore.Qt.Orientation.Horizontal) or "") for c in range(m.columnCount())]
    for c in (w.vue_cave.couleur, w.vue_cave.statut, w.livre.filtre):
        t += [c.itemText(i) for i in range(c.count())]
    return [x for x in t if x]


def test_fenetre_et_onglets(fenetre):
    assert fenetre.onglets.count() == 10
    assert fenetre.vue_cave.modele.rowCount() > 30
    assert not [x for x in _textes_d_interface(fenetre) if re.match(r"^<[a-z_]+\.[a-z0-9_.]+>$", x)]


def test_anglais_sans_francais(fenetre):
    fenetre.changer_langue("en")
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete.value)
    QtWidgets.QApplication.processEvents()
    try:
        assert fenetre.onglets.tabText(1) == "Cellar"
        admis = {"Vendémiaire", "Cuvée", "cuvée", "Rosé", "rosé", "Français"}
        fautes = []
        for x in _textes_d_interface(fenetre):
            nu = x
            for mot in admis:
                nu = nu.replace(mot, "")
            if re.search(r"[éèàçêôûùîïœ«»]", nu):
                fautes.append(x)
        assert not fautes, fautes
    finally:
        fenetre.changer_langue("fr")
    assert fenetre.onglets.tabText(1) == "Cave"


def test_recherche_et_filtres(fenetre):
    vue = fenetre.vue_cave
    tous = vue.modele.rowCount()
    vue.recherche.setText("pauillac")
    assert 0 < vue.modele.rowCount() < tous
    assert all(l["appellation"] == "Pauillac" for l in vue.modele.lignes)
    vue.recherche.clear()
    vue.couleur.setCurrentIndex(vue.couleur.findData("blanc"))
    assert all(l["couleur"] == "blanc" for l in vue.modele.lignes)
    vue.couleur.setCurrentIndex(0)
    vue.statut.setCurrentIndex(vue.statut.findData("bue"))
    assert vue.modele.rowCount() > 0


def test_fiche_affiche_le_vin_choisi(fenetre):
    vue = fenetre.vue_cave
    vue.table.selectRow(0)
    vid = vue.vin_courant()
    assert vue.fiche.vin_id == vid
    assert vue.fiche.t_bouteilles.rowCount() == len(fenetre.cave.bouteilles(vid))
    assert not vue.fiche.image.pixmap().isNull()          # pochette dessinée


def test_colonnes_retenues_et_deplacables(app, fenetre, cave_demo):
    from vendemiaire.ui.liste import COLONNES, VueCave
    i = [c[0] for c in COLONNES].index("region")
    fenetre.vue_cave.table.setColumnHidden(i, True)
    fenetre.vue_cave._retenir()
    autre = VueCave(cave_demo)
    h = autre.table.horizontalHeader()
    assert autre.table.isColumnHidden(i)
    assert h.sectionsMovable()                            # réglé APRÈS restoreState
    autre.deleteLater()


def test_saisie_d_un_vin_avec_bouteilles(fenetre):
    from vendemiaire.ui.saisie import DialogueVin
    cave = fenetre.cave
    d = DialogueVin(cave, None, fenetre)
    d.producteur.setText("Domaine Saisi")
    d.appellation.setText("Chinon")
    d.couleur.setCurrentIndex(d.couleur.findData("rouge"))
    d.millesime.setValue(2020)
    d.cepages.setText("Cabernet franc 100 %")
    d.bloc.nombre.setValue(3)
    d.bloc.prix.setValue(14.5)
    casier = cave.base.valeur("SELECT id FROM emplacement WHERE nom='Rayonnage'")
    d.bloc.casier.setCurrentIndex(d.bloc.casier.findData(casier))
    d.accepter()
    v = cave.vin(d.vin_id)
    assert v["producteur"] == "Domaine Saisi" and v["millesime"] == 2020
    bouteilles = cave.bouteilles(d.vin_id)
    assert len(bouteilles) == 3 and all(b["emplacement_id"] == casier for b in bouteilles)
    assert sum(1 for b in bouteilles if b["rangee"]) == min(3, len(cave.cases_libres(casier)) + 3)
    assert cave.cepages(d.vin_id) == [("Cabernet franc", 100.0)]
    # modification : la saisie est marquée manuelle
    d2 = DialogueVin(cave, d.vin_id, fenetre)
    d2.cuvee.setText("Les Galets")
    d2.accepter()
    assert cave.vin(d.vin_id)["cuvee"] == "Les Galets"
    assert cave.origines(d.vin_id)["cuvee"] == "manuel"


def test_sortie_au_livre_de_cave(fenetre):
    from vendemiaire.ui.saisie import DialogueSortie
    cave = fenetre.cave
    bid = cave.base.valeur("SELECT id FROM bouteille WHERE statut='en_cave' LIMIT 1")
    d = DialogueSortie(cave, bid, fenetre)
    d.occasion.setText("Essai d'interface")
    d.plat.setText("Gratin dauphinois")
    d.note.setValue(16.5)
    d.accepter()
    assert cave.bouteille(bid)["statut"] == "bue"
    fenetre.livre.rafraichir()
    assert fenetre.livre.table.item(0, 6).text() == "Gratin dauphinois" or \
        any(m["plat"] == "Gratin dauphinois" for m in fenetre.livre.lignes)


def test_detail_d_une_bouteille(fenetre):
    from vendemiaire.ui.saisie import DialogueBouteille
    cave = fenetre.cave
    bid = cave.base.valeur("SELECT id FROM bouteille WHERE statut='en_cave' LIMIT 1")
    d = DialogueBouteille(cave, bid, fenetre)
    d.niveau.setCurrentIndex(d.niveau.findData("TS"))
    d.caisse.setCurrentIndex(d.caisse.findData("cbo"))
    d.provenance.setText("Achetée au domaine")
    d.accepter()
    b = cave.bouteille(bid)
    assert (b["niveau"], b["caisse"], b["provenance"]) == ("TS", "cbo", "Achetée au domaine")


def test_plan_glisser_deposer_et_echange(app, fenetre):
    from vendemiaire.ui.plan import CASE, position_case
    plan = fenetre.plan
    cave = fenetre.cave
    casier = cave.base.valeur("SELECT id FROM emplacement WHERE nom='Casier A'")
    plan.casier_id = casier
    plan.rafraichir()
    assert plan.pastilles
    libre = cave.cases_libres(casier)[0]
    p = next(iter(plan.pastilles.values()))
    bid = p.bid
    p.setPos(position_case(*libre) + QtCore.QPointF(3, 2))     # lâchée près du centre
    plan.scene.relache.emit()
    b = cave.bouteille(bid)
    assert (b["rangee"], b["colonne"]) == libre
    # échange : glisser une bouteille sur une autre
    a, autre = list(plan.pastilles.values())[:2]
    pos_a, pos_b = (a.rangee, a.colonne), (autre.rangee, autre.colonne)
    a.setPos(position_case(*pos_b))
    plan.scene.relache.emit()
    assert (cave.bouteille(a.bid)["rangee"], cave.bouteille(a.bid)["colonne"]) == pos_b
    assert (cave.bouteille(autre.bid)["rangee"], cave.bouteille(autre.bid)["colonne"]) == pos_a
    # hors du casier : refusé, la pastille revient
    p = plan.pastilles[a.bid]
    p.setPos(QtCore.QPointF(-5 * CASE, -5 * CASE))
    plan.scene.relache.emit()
    assert (cave.bouteille(a.bid)["rangee"], cave.bouteille(a.bid)["colonne"]) == pos_b
    assert cave.base.valeur("SELECT COUNT(*) FROM deplacement WHERE bouteille_id=? AND motif=?",
                            (a.bid, i18n.tr("plan.motif_glisser"))) >= 1


def test_plan_deplacement_en_lot(fenetre):
    cave = fenetre.cave
    plan = fenetre.plan
    source = cave.base.valeur("SELECT id FROM emplacement WHERE nom='Casier B'")
    cible = cave.creer_emplacement("Casier vide", "casier",
                                   cave.base.valeur("SELECT id FROM emplacement WHERE nom='Mur nord'"), 5, 10)
    plan.casier_id = source
    plan.rafraichir()
    ids = list(plan.pastilles)[:5]
    assert plan.deplacer_vers(ids, cible, "lot d'essai")
    assert all(cave.bouteille(i)["emplacement_id"] == cible for i in ids)
    lots = cave.base.lire("SELECT DISTINCT lot FROM deplacement WHERE motif=?", ("lot d'essai",))
    assert len(lots) == 1


def test_plan_ranger_les_bouteilles_sans_case(fenetre):
    cave = fenetre.cave
    sans = cave.base.valeur("SELECT COUNT(*) FROM bouteille WHERE statut='en_cave' AND emplacement_id IS NULL")
    assert sans > 0
    k = cave.creer_emplacement("Grand casier", "casier", None, 10, 10)
    fenetre.plan.casier_id = k
    fenetre.plan.rafraichir()
    fenetre.plan.ranger_sans_case()
    assert cave.base.valeur("SELECT COUNT(*) FROM bouteille WHERE statut='en_cave' "
                            "AND emplacement_id IS NULL") == max(0, sans - 100)


def test_tableau_de_bord(fenetre):
    t = fenetre.tableau
    t.rafraichir()
    assert int(t.chiffres["bouteilles"].text()) == fenetre.cave.statistiques()["bouteilles"]
    assert t.barres["par_couleur"].donnees and t.alertes.count() > 0


def test_point_d_entree_reel_check():
    """Le VRAI point d'entrée en mode vérification (comme le paquet construit)."""
    import os
    import subprocess
    import sys
    from pathlib import Path
    racine = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, "run.py", "--check"], cwd=racine, capture_output=True,
                       text=True, timeout=120, env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "interface OK" in r.stdout
    v = subprocess.run([sys.executable, "run.py", "--version"], cwd=racine, capture_output=True,
                       text=True, timeout=60)
    assert v.stdout.strip() == (racine / "VERSION").read_text(encoding="utf-8").strip()
