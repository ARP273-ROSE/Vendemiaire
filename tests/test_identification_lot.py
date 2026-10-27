# -*- coding: utf-8 -*-
"""Identification de toute la cave (1.0.2) : appariement au vrai format LWIN
(climat dans SITE, « Blanc » comme WINE, producteur entre parenthèses), lot
préparé sans rien écrire, décisions sûres / douteuses, validation sans
écrasement d'une saisie manuelle, annulation, et l'écran sous Xvfb.

Producteurs, climats et codes INVENTÉS (format du vrai fichier de Liv-ex)."""
import pytest
from PyQt6 import QtCore, QtWidgets

from vendemiaire import i18n, reseau
from vendemiaire.mondial import appariement, lot
from vendemiaire.mondial.lwin import convertir


def _l(code, titre, prod, vin="", sous_region="", site="", couleur="Red", classement=""):
    nom = ", ".join(x for x in (" ".join(y for y in (titre, prod) if y), sous_region, site, vin) if x)
    return convertir({"lwin": str(code), "statut": "Live", "nom": nom, "titre_producteur": titre,
                      "producteur": prod, "vin": vin or None, "pays": "France", "region": "Burgundy",
                      "sous_region": sous_region, "site": site or None, "couleur": couleur,
                      "type": "Wine", "sous_type": "Still", "classement": classement or None})


LWIN = [
    # le domaine écrit « Domaine Paul Verdier (Source) » ; la cave dira « Domaine de la Source (Paul Verdier) »
    _l(9810001, "Domaine", "Paul Verdier (Source)", "Rouge", "Aloxe-Corton"),
    _l(9810002, "Domaine", "Paul Verdier (Source)", "", "Aloxe-Corton", "Les Valtieres", classement="Premier Cru"),
    _l(9810003, "Domaine", "Paul Verdier (Source)", "Blanc", "Meursault", couleur="White"),
    _l(9810004, "Domaine", "Paul Verdier (Source)", "", "Meursault", "Charmettes", couleur="White"),
    _l(9810005, "", "Paul Verdier", "Blanc", "Meursault", couleur="White"),
    # climat dans SITE, sans WINE
    _l(9810010, "", "Maison Arnolet", "", "Nuits-Saint-Georges", "Grandes Vignottes", classement="Premier Cru"),
    _l(9810011, "", "Maison Arnolet", "", "Nuits-Saint-Georges", "Les Porrieres", classement="Premier Cru"),
    _l(9810012, "", "Maison Arnolet", "Rouge", "Nuits-Saint-Georges"),
    # « Le Clos » du même producteur, et le « Clos Marnier » chez d'autres
    _l(9810020, "", "Maison Arnolet", "", "Pouilly-Fuisse", "Le Clos", couleur="White"),
    _l(9810021, "", "Maison Arnolet", "", "Pouilly-Fuisse", couleur="White"),
    _l(9810022, "", "Freres Tavel", "", "Pouilly-Fuisse", "Le Clos Marnier", couleur="White"),
    _l(9810023, "", "Domaine Lusset", "", "Pouilly-Fuisse", "Le Clos Marnier", couleur="White"),
    # nom exact contre nom augmenté d'un éleveur
    _l(9810030, "", "Hospices de Morvan", "Cuvee Lagrange", "Beaune", classement="Premier Cru"),
    _l(9810031, "", "Hospices de Morvan (Maison Arnolet)", "Cuvee Lagrange", "Beaune"),
    _l(9810032, "", "Hospices de Morvan (Paul Verdier)", "Cuvee Lagrange", "Beaune"),
    # site qui n'est que l'appellation, cuvée dans WINE
    _l(9810040, "", "Maison Arnolet", "Dames Ursulines", "Bourgogne", "Hautes Cotes de Nuits"),
    _l(9810041, "", "Maison Arnolet", "", "Bourgogne", "Hautes Cotes de Nuits"),
]


@pytest.fixture
def refs(cave):
    cave.references.remplacer_lwin(LWIN, source="essai")
    return cave.references


def _vin(cave, producteur, cuvee, appellation, couleur="rouge", millesime=2022, **autres):
    d = {"producteur": producteur, "cuvee": cuvee, "appellation": appellation, "couleur": couleur,
         "millesime": millesime, "pays": "France"}
    d.update(autres)
    return cave.enregistrer_vin(d)


def _decision(cave, refs, vin_id):
    r = appariement.requete_depuis_vin(cave, vin_id)
    return appariement.decider(appariement.candidats_lwin(
        refs, r, appellation_officielle=refs.appellation_officielle))


# ---------------------------------------------------------------- appariement
def test_ressemblance_ordre_des_mots_et_mot_presque_identique():
    assert appariement.ressemblance("Domaine de la Source (Paul Verdier)",
                                    "Domaine Paul Verdier (Source)") == 1.0
    assert appariement.ressemblance("Clos Marnié", "Le Clos Marnier") >= 0.85
    assert appariement.ressemblance("Les Chaînes Vignottes", "Chaines Vignottes") == 1.0
    # un seul mot commun ne prouve presque rien ; un nom augmenté passe après le nom exact
    assert appariement.ressemblance("Le Clos", "Clos Marnié") < 0.8
    exact = appariement.ressemblance("Hospices de Morvan", "Hospices de Morvan")
    augmente = appariement.ressemblance("Hospices de Morvan", "Hospices de Morvan (Maison Arnolet)")
    assert exact - augmente > 0.11


def test_climat_dans_site_et_producteur_inverse(cave, refs):
    v = _vin(cave, "Maison Arnolet", "Les Grandes Vignottes", "Nuits-Saint-Georges")
    d = _decision(cave, refs, v)
    assert d.motif == "sur" and d.choisi.identifiant == "9810010"
    assert d.choisi.donnees["cuvee"] == "Grandes Vignottes"
    # sans cuvée : le village (« Blanc » n'est pas une cuvée), pas un premier cru au hasard
    v = _vin(cave, "Domaine de la Source (Paul Verdier)", None, "Meursault", "blanc", 2023)
    d = _decision(cave, refs, v)
    assert d.motif == "sur" and d.choisi.identifiant == "9810003"
    assert "cuvee" not in d.choisi.donnees


def test_cuvee_dans_wine_quand_site_est_l_appellation(cave, refs):
    v = _vin(cave, "Maison Arnolet", "Les Dames Ursulines", "Bourgogne Hautes-Côtes de Nuits")
    d = _decision(cave, refs, v)
    assert d.motif == "sur" and d.choisi.identifiant == "9810040"


def test_nom_exact_devant_le_nom_augmente(cave, refs):
    v = _vin(cave, "Hospices de Morvan", "Cuvée Lagrange", "Beaune")
    d = _decision(cave, refs, v)
    assert d.motif == "sur" and d.choisi.identifiant == "9810030"


def test_pas_de_faux_positif(cave, refs):
    # climat absent de la base : ni le village du domaine, ni un autre climat
    v = _vin(cave, "Domaine de la Source (Paul Verdier)", "Les Fournelles", "Aloxe-Corton")
    d = _decision(cave, refs, v)
    assert d.choisi is None and d.candidats[0].identifiant in ("9810001", "9810002")
    # même cuvée, autre producteur : jamais
    v = _vin(cave, "Maison Arnolet", "Clos Marnié", "Pouilly-Fuissé", "blanc")
    d = _decision(cave, refs, v)
    assert d.choisi is None
    autres = {c.identifiant: c for c in d.candidats}
    assert autres["9810022"].score < appariement.SEUIL                     # bonne cuvée, autre domaine
    assert "appariement.r_autre_producteur" in [r.cle for r in autres["9810022"].raisons]
    # le « Clos Marnié » d'un autre producteur, cherché sous son nom : trouvé
    v = _vin(cave, "Frères Tavel", "Clos Marnié", "Pouilly-Fuissé", "blanc")
    d = _decision(cave, refs, v)
    assert d.motif == "sur" and d.choisi.identifiant == "9810022"
    # producteur inconnu de la base : rien de présélectionné
    v = _vin(cave, "Domaine Imaginaire", "Grandes Vignottes", "Nuits-Saint-Georges")
    assert _decision(cave, refs, v).choisi is None


# ---------------------------------------------------------------- lot
@pytest.fixture
def cave_lot(cave, refs):
    ids = {
        "sur": _vin(cave, "Maison Arnolet", "Grandes Vignottes", "Nuits-Saint-Georges"),
        "sur2": _vin(cave, "Hospices de Morvan", "Cuvée Lagrange", "Beaune"),
        "douteux": _vin(cave, "Domaine de la Source (Paul Verdier)", "Les Fournelles", "Aloxe-Corton"),
        "aucun": _vin(cave, "Xyzzy Qwerty", "Plugh", "Zork"),
    }
    # vin déjà identifié : hors du lot par défaut
    ids["deja"] = _vin(cave, "Maison Arnolet", "Les Porrières", "Nuits-Saint-Georges", lwin="9810011")
    return cave, ids


def _instantane(cave):
    tables = ("vin", "producteur", "identifiant_externe", "journal_enrichissement", "origine_champ",
              "fiche_externe")
    return {t: [tuple(r) for r in cave.base.lire(f"SELECT * FROM {t} ORDER BY 1")] for t in tables}


def test_lot_prepare_sans_rien_ecrire(cave_lot):
    cave, ids = cave_lot
    avant = _instantane(cave)
    vus = []
    lignes = lot.preparer(cave, lot.vins_a_identifier(cave), progression=lambda i, n: vus.append((i, n)))
    assert _instantane(cave) == avant                                   # lectures seulement
    assert vus[-1] == (4, 4)
    par_vin = {l.vin_id: l for l in lignes}
    assert ids["deja"] not in par_vin
    assert par_vin[ids["sur"]].categorie == lot.SURE and par_vin[ids["sur"]].coche_d_avance
    assert par_vin[ids["sur2"]].categorie == lot.SURE
    assert par_vin[ids["douteux"]].categorie == lot.DOUTEUSE and not par_vin[ids["douteux"]].coche_d_avance
    assert par_vin[ids["aucun"]].categorie == lot.AUCUN
    # avec l'option « aussi les vins déjà identifiés »
    tous = {l.vin_id: l for l in lot.preparer(cave, lot.vins_a_identifier(cave, True))}
    assert tous[ids["deja"]].categorie == lot.DEJA and not tous[ids["deja"]].coche_d_avance


def test_lot_valide_sans_ecraser_la_saisie_manuelle(cave_lot):
    cave, ids = cave_lot
    # le millésime et la cuvée du premier vin sont saisis à la main ; la région aussi, vidée exprès
    cave.enregistrer_vin({"producteur": "Maison Arnolet", "cuvee": "Grandes Vignottes",
                          "appellation": "Nuits-Saint-Georges", "couleur": "rouge", "millesime": 2022,
                          "pays": "France", "region": "Côte de Nuits"}, ids["sur"])
    cave.enregistrer_vin({"producteur": "Maison Arnolet", "cuvee": "Grandes Vignottes",
                          "appellation": "Nuits-Saint-Georges", "couleur": "rouge", "millesime": 2022,
                          "pays": "France", "region": ""}, ids["sur"])
    lignes = lot.preparer(cave, lot.vins_a_identifier(cave))
    choix = [(l.vin_id, l.meilleur) for l in lignes if l.coche_d_avance]
    assert {v for v, _ in choix} == {ids["sur"], ids["sur2"]}
    bilan = lot.appliquer(cave, choix, lambda c: "explication", nom=cave.nom_vin)
    assert bilan.vins == 2 and not bilan.echecs
    v = cave.vin(ids["sur"])
    assert v["lwin"] == "9810010" and v["classement"] == "Premier Cru"
    assert v["region"] in (None, "")                                    # vidé à la main : intouchable
    assert v["cuvee"] == "Grandes Vignottes"                            # saisi : gardé tel quel
    journal = {j["champ"]: j for j in cave.journal(ids["sur"])}
    assert journal["lwin"]["source"] == "lwin" and "9810010" in journal["lwin"]["detail"]
    ident = cave.identifiants(ids["sur"])[0]
    assert (ident["source"], ident["valeur"], ident["confirme"]) == ("lwin", "9810010", 1)
    # rien n'est écrit pour les vins non cochés
    assert cave.vin(ids["douteux"])["lwin"] is None and not cave.identifiants(ids["douteux"])
    # une seconde passe ne retrouve que les vins restés sans identifiant
    assert set(lot.vins_a_identifier(cave)) == {ids["douteux"], ids["aucun"]}


def test_lot_annule_rien_d_ecrit(cave_lot):
    cave, _ids = cave_lot
    avant = _instantane(cave)
    appels = []

    def annule():
        appels.append(1)
        return len(appels) > 2
    with pytest.raises(lot.Annule):
        lot.preparer(cave, lot.vins_a_identifier(cave), annule=annule)
    assert _instantane(cave) == avant
    # une validation interrompue s'arrête entre deux vins : chacun est tout ou rien
    lignes = lot.preparer(cave, lot.vins_a_identifier(cave))
    choix = [(l.vin_id, l.meilleur) for l in lignes if l.coche_d_avance]
    n = []
    bilan = lot.appliquer(cave, choix, lambda c: "x", annule=lambda: n.append(1) or len(n) > 1)
    assert bilan.vins == 1
    faits = [vid for vid, _c in choix if cave.vin(vid)["lwin"]]
    assert len(faits) == 1 and cave.identifiants(faits[0])


def test_lot_wikidata_seulement_si_permis_et_sans_candidat(cave_lot, monkeypatch):
    cave, ids = cave_lot
    from vendemiaire.mondial import wikidata
    appels = []

    def faux(client, objet, nom, pays=None, langue="fr", limite=6):
        appels.append(nom)
        return [appariement.Candidat("wikidata", "Q1", "Xyzzy Qwerty — domaine viticole", 0.95,
                                     [appariement.Raison("appariement.r_nom_wikidata", {"pct": 100, "nom": nom}, 1)],
                                     {"site_web": "https://exemple.invalid"}, brut={"nom": nom}, url="u")]
    monkeypatch.setattr(wikidata, "candidats", faux)
    lot.preparer(cave, lot.vins_a_identifier(cave))
    assert appels == []                                                  # pas de client : hors ligne
    lignes = {l.vin_id: l for l in lot.preparer(cave, lot.vins_a_identifier(cave), wikidata_client=object())}
    assert appels == ["Xyzzy Qwerty"]                                    # seulement le vin sans candidat LWIN
    l = lignes[ids["aucun"]]
    assert l.categorie == lot.SURE and l.meilleur.source == "wikidata"
    bilan = lot.appliquer(cave, [(l.vin_id, l.meilleur)], lambda c: "x")
    assert bilan.vins == 1
    pid = cave.vin(ids["aucun"])["producteur_id"]
    assert cave.producteur(pid)["site_web"] == "https://exemple.invalid"
    assert [i["source"] for i in cave.identifiants(ids["aucun"])] == ["wikidata_producteur"]


# ---------------------------------------------------------------- interface
@pytest.fixture
def dialogue(app, cave_lot):
    from vendemiaire.ui import identifier_lot, travail
    i18n.definir_langue("fr")
    cave, ids = cave_lot
    d = identifier_lot.DialogueIdentifierLot(cave, demarrer=False)
    yield d, cave, ids, travail
    d.done(0)
    d.deleteLater()
    app.processEvents()


def test_ecran_recapitulatif_et_validation(app, dialogue):
    d, cave, ids, travail = dialogue
    d.show()
    d.chercher()
    travail.attendre(d._travail)
    assert d.table.rowCount() == 3 and d.aucun.count() == 1                # sûrs + douteux ; sans candidat à part
    coches = {vid for vid, _c in d.choix()}
    assert coches == {ids["sur"], ids["sur2"]}
    assert "2 sûrs" in d.etat.text() and "1 douteux" in d.etat.text()
    etats = [d.table.item(r, 5).text() for r in range(d.table.rowCount())]
    assert any(e.startswith("douteuse") for e in etats)
    assert d.b_valider.text() == "Valider la sélection (2)"
    assert cave.vin(ids["sur"])["lwin"] is None                         # rien d'écrit avant la validation
    d._cocher(aucune=True)
    assert not d.b_valider.isEnabled()
    d._cocher(seulement_sures=True)
    d.valider()
    travail.attendre(d._travail)
    assert d.bilan.vins == 2 and d.modifie
    assert cave.vin(ids["sur"])["lwin"] == "9810010" and cave.vin(ids["sur2"])["lwin"] == "9810030"
    assert cave.vin(ids["douteux"])["lwin"] is None
    assert "LWIN 9810010" in d.journal.toPlainText() and d.journal.isVisible()
    assert not d.choix()                                                 # lignes faites : grisées


def test_ecran_annulation(app, dialogue, monkeypatch):
    d, cave, ids, travail = dialogue

    def lent(cave_, vin_ids, annule=None, progression=None, **_k):
        for i in range(500):
            if annule():
                raise lot.Annule()
            progression(i, 500)
            QtCore.QThread.msleep(10)
        return []
    monkeypatch.setattr(lot, "preparer", lent)
    d.chercher()
    assert d.b_annuler.isEnabled() and not d.b_valider.isEnabled()
    d.annuler()
    travail.attendre(d._travail)
    assert "annulée" in d.etat.text() and d.table.rowCount() == 0
    assert not d.b_annuler.isEnabled() and cave.vin(ids["sur"])["lwin"] is None


def test_ecran_en_anglais_et_menu(app, cave_lot):
    import re
    from vendemiaire.ui import identifier_lot, travail
    cave, _ids = cave_lot
    i18n.definir_langue("en")
    try:
        reseau.autoriser(False)
        d = identifier_lot.DialogueIdentifierLot(cave)
        travail.attendre(d._travail)
        textes = [d.windowTitle(), d.etat.text(), d.titre_aucun.text()]
        textes += [b.text() for b in d.findChildren(QtWidgets.QAbstractButton)]
        textes += [d.table.horizontalHeaderItem(c).text() for c in range(d.table.columnCount())]
        textes += [d.table.item(r, c).text() for r in range(d.table.rowCount()) for c in (2, 3, 5)]
        nu = [re.sub(r"Cuvée|cuvée", "", x) for x in textes]
        assert not [x for x in nu if re.search(r"[éèàçêôûùîœ«»]|\b(le|la|les|des|du|vin|sûre?s?)\b", x)], textes
        assert not d.o_wikidata.isEnabled()                                  # pas d'accord : pas de Wikidata
        d.done(0)
    finally:
        i18n.definir_langue("fr")
