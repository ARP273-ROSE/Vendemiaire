# -*- coding: utf-8 -*-
"""Phase 3 dans la cave et dans l'interface (sous Xvfb en CI) : fenêtres
calculées rangées dans la base sans toucher aux autres, alertes, courbe
d'apogée, température de cave mesurée, bouteille entamée, dégustation,
« que boire ce soir ? », fiche « ce soir » en HTML et en PDF, et aucun
français dans l'interface anglaise de ces écrans."""
import re
from datetime import date

import pytest
from PyQt6 import QtCore, QtWidgets

from vendemiaire import i18n

LEOVILLE = {"producteur": "Château Léoville Las Cases", "cuvee": "Grand vin", "appellation": "Saint-Julien",
            "region": "Bordeaux", "pays": "France", "couleur": "rouge", "type": "tranquille",
            "millesime": 2010, "cepages": [("Cabernet sauvignon", 75), ("Merlot", 25)]}
MUSCADET = {"producteur": "Domaine témoin", "appellation": "Muscadet Sèvre et Maine", "region": "Val de Loire",
            "couleur": "blanc", "type": "tranquille", "millesime": 2025, "cepages": [("Melon de Bourgogne", 100)]}


def _vin(cave, donnees, n=3, prix=None):
    vid = cave.enregistrer_vin(donnees)
    cave.ajouter_bouteilles(vid, n, {"prix_achat": prix} if prix else None)
    return vid


# ---------------------------------------------------------------------------- modèle
def test_fenetre_calculee_rangee_sans_toucher_la_mienne(cave):
    vid = _vin(cave, LEOVILLE)
    cave.definir_fenetre(vid, "perso", 2020, 2050)
    assert cave.enregistrer_fenetres_calculees() == 1
    lignes = {r["source"]: dict(r) for r in cave.fenetres(vid)}
    assert lignes["perso"]["debut"] == 2020 and lignes["perso"]["fin"] == 2050
    calc = lignes["calcul"]
    assert calc["detail_source"] == "rouge_bordeaux/garde" and calc["modele"] == "plateau"
    f = cave.fenetre_calculee(vid)
    assert (calc["debut"], calc["fin"]) == (f.annees["debut"], f.annees["fin"])
    assert "Bordeaux classé" in calc["explication"]
    assert cave.fenetre_effective(vid)["source"] == "perso"         # la mienne passe avant
    # changer de style remplace la ligne calculée au lieu d'en ajouter une
    cave.enregistrer_vin({"niveau_garde": "courant"}, vid)
    cave.enregistrer_fenetres_calculees([vid])
    calc = [r for r in cave.fenetres(vid) if r["source"] == "calcul"]
    assert len(calc) == 1 and calc[0]["detail_source"] == "rouge_bordeaux/courant"


def test_temperature_mesuree_accelere_la_garde(cave):
    vid = _vin(cave, LEOVILLE)
    sans = cave.fenetre_calculee(vid)
    cave.ajouter_conditions([(None, f"2026-0{m}-01 08:00", 18.0, 70) for m in range(1, 10)])
    assert cave.temperature_du_vin(vid) == pytest.approx(18.0)
    avec = cave.fenetre_calculee(vid)
    assert avec.facteur_cave == pytest.approx(2 ** 0.6)
    assert avec.ans["fin"] == pytest.approx(sans.ans["fin"] / 2 ** 0.6)
    assert len(cave.conditions_hors_plage()) == 9                   # 18 °C > 15 °C


def test_alertes_et_courbe(cave):
    vieux = _vin(cave, dict(LEOVILLE, millesime=1985), 2)
    jeune = _vin(cave, dict(LEOVILLE, millesime=2024), 1)
    _vin(cave, MUSCADET, 2)
    cave.enregistrer_fenetres_calculees()
    a = cave.alertes_garde(2026)
    assert {b["vin_id"] for b in a["declin"]} == {vieux}
    assert {b["vin_id"] for b in a["trop_jeune"]} == {jeune}
    courbe = cave.courbe_apogee(2026, 20)
    assert len(courbe) == 20 and sum(x[1] for x in courbe) == pytest.approx(5)
    assert cave.bouchons_a_controler(2026)[0]["vin_id"] == vieux


def test_entamer_une_bouteille(cave):
    vid = _vin(cave, MUSCADET, 1)
    bid = cave.bouteilles(vid)[0]["id"]
    # date du jour (et non une date fixe) : la bouteille entre en cave aujourd'hui, l'ouverture
    # doit venir après dans le livre de cave — le test cassait dès le lendemain du 26/10/2026
    from datetime import date, timedelta
    jour = date.today()
    oid = cave.entamer(bid, "bouchon", 40, jour.isoformat(), plat="Huîtres")
    o = cave.bouteilles_ouvertes()[0]
    assert o["id"] == oid and o["a_finir_avant"] == (jour + timedelta(days=7)).isoformat()  # blanc frais : 2 à 7 jours
    assert cave.bouteille(bid)["statut"] == "bue"
    assert cave.mouvements(limite=1)[0]["plat"] == "Huîtres"
    cave.finir_ouverte(oid)
    assert cave.bouteilles_ouvertes() == []


def test_degustation_avec_aromes(cave):
    vid = _vin(cave, LEOVILLE, 1)
    did = cave.enregistrer_degustation({"vin_id": vid, "nez": "cassis", "aromes": "P.FNR:cassis;S.BOI",
                                        "note": 17.5, "echelle": "20"})
    d = cave.degustations(vid)[0]
    assert d["id"] == did and d["aromes"] == "P.FNR:cassis;S.BOI"
    cave.enregistrer_degustation({"note": 18}, did)
    assert cave.degustations(vid)[0]["note"] == 18
    cave.supprimer_degustation(did)
    assert cave.degustations(vid) == []


def test_que_boire_ce_soir(cave):
    leo = _vin(cave, dict(LEOVILLE, millesime=2008), 2, prix=120)
    _vin(cave, dict(LEOVILLE, millesime=2024), 2, prix=150)              # trop jeune
    mus = _vin(cave, MUSCADET, 3, prix=12)
    cave.enregistrer_fenetres_calculees()
    r = cave.que_boire("agneau")
    assert r["plats"][0].id == "agneau"
    assert [p.bouteille["vin_id"] for p in r["propositions"]] == [leo]
    assert cave.que_boire("huitres")["propositions"][0].bouteille["vin_id"] == mus
    assert cave.que_boire("", budget=50)["propositions"][0].bouteille["vin_id"] == mus
    assert cave.que_boire("", couleur="rouge", avec_trop_jeunes=True)["propositions"][-1].bouteille["phase"] \
        == "trop_jeune"
    assert [p.bouteille["vin_id"] for p in cave.que_boire("", occasion="aperitif")["propositions"]] == [mus]
    assert cave.que_boire("artichaut")["difficiles"][0].regle["id"] == "imp.artichaut"


# ---------------------------------------------------------------------------- interface
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


def _un_vin(cave, nom="Château des Trois Chênes"):
    return cave.base.valeur("SELECT v.id FROM vin v JOIN producteur p ON p.id=v.producteur_id WHERE p.nom=? "
                            "AND EXISTS(SELECT 1 FROM bouteille b WHERE b.vin_id=v.id AND b.statut='en_cave') "
                            "ORDER BY v.millesime LIMIT 1", (nom,))


def test_fiche_montre_les_regles(app, fenetre):
    c = fenetre.cave
    vid = _un_vin(c)
    fenetre.montrer_vin(vid)
    fiche = fenetre.vue_cave.fiche
    fiche.afficher(vid)
    texte = fiche.panneau.text()
    assert "Rouge de Bordeaux classé" in texte and "pourquoi" in texte and "°C" in texte
    assert any(fiche.t_fenetres.item(r, 0).text().startswith("Calculée")
               for r in range(fiche.t_fenetres.rowCount()))
    from vendemiaire.ui import regles_ui
    for sujet in ("style", "fenetre", "service", "accords"):
        assert regles_ui.pourquoi_html(c, vid, sujet)
    assert "WE2018" in regles_ui.pourquoi_html(c, vid, "fenetre")


def test_onglet_ce_soir_et_fiche_imprimable(app, fenetre, tmp_path):
    from vendemiaire.ui.ce_soir import DialogueFicheCeSoir
    v = fenetre.ce_soir
    fenetre.onglets.setCurrentWidget(v)
    v.plat.setText("agneau")
    app.processEvents()
    assert v.table.rowCount() > 0 and "Agneau" in v.explication.toHtml()
    d = DialogueFicheCeSoir(fenetre.cave, v.vins_choisis(), "agneau", parent=fenetre)
    html = d.html()
    assert "Ce soir" in html and "°C" in html and "Sources" in html
    h = d.enregistrer_html(str(tmp_path / "ce-soir.html"))
    p = d.enregistrer_pdf(str(tmp_path / "ce-soir.pdf"))
    assert (tmp_path / "ce-soir.html").read_text(encoding="utf-8").startswith("<!doctype html>") and h
    assert (tmp_path / "ce-soir.pdf").read_bytes()[:5] == b"%PDF-" and p
    d.close()


def test_dialogues_phase3(app, fenetre):
    from vendemiaire.ui.ce_soir import DialogueEntamer
    from vendemiaire.ui.degustation import DialogueDegustation, DialogueDiagnostic
    from vendemiaire.ui.regles_ui import DialogueRegles
    c = fenetre.cave
    vid = _un_vin(c)
    bid = c.base.valeur("SELECT id FROM bouteille WHERE vin_id=? AND statut='en_cave'", (vid,))
    e = DialogueEntamer(c, bid, fenetre)
    assert "jours" in e.conseil.text()
    e.accepter()
    assert c.bouteille(bid)["statut"] == "bue" and c.bouteilles_ouvertes()
    d = DialogueDegustation(c, vid, parent=fenetre)
    racine = d.roue.topLevelItem(0)
    racine.child(0).child(0).setCheckState(0, QtCore.Qt.CheckState.Checked)
    d.accepter()
    assert c.degustations(vid)[0]["aromes"].startswith("P.")
    g = DialogueDiagnostic(c, None, fenetre)
    g.recherche.setText("carton mouillé")
    assert g.liste.count() >= 1 and "TCA" in g.detail.toHtml()
    r = DialogueRegles(fenetre)
    assert "194" in r.texte.toHtml() and "WINEBID" in r.texte.toHtml()
    for x in (d, g, r):
        x.close()


def test_saisie_style_et_niveau(app, fenetre):
    from vendemiaire.ui.saisie import DialogueBouteille, DialogueVin
    c = fenetre.cave
    vid = _un_vin(c)
    d = DialogueVin(c, vid, fenetre)
    d.niveau_garde.setCurrentIndex(d.niveau_garde.findData("courant"))
    d.accepter()
    assert c.vin(vid)["niveau_garde"] == "courant"
    bid = c.base.valeur("SELECT id FROM bouteille WHERE vin_id=? AND statut='en_cave'", (vid,))
    b = DialogueBouteille(c, bid, fenetre)
    b.niveau.setCurrentIndex(b.niveau.findData("MS"))
    assert b.illustration.code == "MS" and "Mi-épaule" not in b.sens.text() and "âge" in b.sens.text()
    b.close()


def test_tableau_de_bord_garde(app, fenetre):
    t = fenetre.tableau
    t.rafraichir()
    assert t.courbe.donnees and t.chiffres["garde_declin"].text() != "–"
    textes = [t.alertes.item(i).text() for i in range(t.alertes.count())]
    assert any("déclin" in x or "À boire" in x for x in textes)


def test_anglais_sans_francais_phase3(app, fenetre):
    from vendemiaire.ui.ce_soir import DialogueFicheCeSoir
    from vendemiaire.ui.degustation import DialogueDegustation, DialogueDiagnostic
    fenetre.changer_langue("en")
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete.value)
    app.processEvents()
    try:
        c = fenetre.cave
        vid = _un_vin(c)
        fenetre.vue_cave.fiche.afficher(vid)
        fenetre.ce_soir.plat.setText("lamb")
        app.processEvents()
        textes = [fenetre.vue_cave.fiche.panneau.text(), fenetre.ce_soir.explication.toPlainText(),
                  fenetre.tableau.legende_courbe.text()]
        textes += [fenetre.ce_soir.table.item(r, 2).text() for r in range(fenetre.ce_soir.table.rowCount())]
        d = DialogueFicheCeSoir(c, [vid], "lamb", parent=fenetre)
        textes.append(re.sub(r"<[^>]+>", " ", d.html()))
        g = DialogueDiagnostic(c, None, fenetre)
        textes.append(g.detail.toPlainText())
        dg = DialogueDegustation(c, vid, parent=fenetre)
        it = dg.roue.topLevelItem(0)
        textes += [it.text(0), it.child(0).text(0), it.child(0).child(0).text(0)]
        admis = ("Vendémiaire", "Château des Trois Chênes", "Chênes", "Médoc", "Émilion", "Pessac-Léognan",
                 "Rosé", "rosé", "Côte", "Rhône", "Pérignon", "Estèphe", "cuvée", "Cuvée", '"Le vin"',
                 "&quot;Le vin&quot;", "Second vin", "Grand vin")
        fautes = []
        for x in textes:
            nu = x
            for a in admis:
                nu = nu.replace(a, "")
            nu = re.sub(r"«[^»]*»", "", nu)        # citations du corpus, laissées dans leur langue
            # titres des sources : références bibliographiques, dans la langue du document cité
            nu = re.sub(r"\b[A-Z][A-Z0-9_]+ — [^\n]*", "", nu)
            if re.search(r"[éèàçêôûùîïœ]|\b(cave|vin|boire|dossier)\b", nu):
                fautes.append(x[:200])
        assert not fautes, fautes
        for x in (d, g, dg):
            x.close()
    finally:
        fenetre.changer_langue("fr")
    _ = date
