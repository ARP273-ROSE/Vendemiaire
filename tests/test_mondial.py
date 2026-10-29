# -*- coding: utf-8 -*-
"""Bases mondiales (phase 2) : LWIN (lecture XLSX, copie locale, recherche hors
ligne), registres d'appellations, appariement (score expliqué, renoncement,
confirmation sans écrasement), Wikidata et Open Food Facts sur un réseau
SIMULÉ (aucune requête réelle), politesse du client (User-Agent, débit, 429)."""
import json
import zipfile

import pytest

from vendemiaire import reseau
from vendemiaire.base import normaliser
from vendemiaire.mondial import appariement, appellations, lwin, off, wikidata
from vendemiaire.references import References, normaliser_appellation


# ---------------------------------------------------------------- outils
def ecrire_xlsx(chemin, lignes):
    """Classeur XLSX minimal (chaînes partagées ET en ligne, nombres), comme Excel."""
    partagees, index = [], {}

    def ref(col, rang):
        lettres = ""
        col += 1
        while col:
            col, r = divmod(col - 1, 26)
            lettres = chr(65 + r) + lettres
        return f"{lettres}{rang}"
    xml_lignes = []
    for r, ligne in enumerate(lignes, 1):
        cellules = []
        for c, v in enumerate(ligne):
            if v is None or v == "":
                continue                       # cellule absente : la colonne suivante garde sa place
            if isinstance(v, (int, float)):
                cellules.append(f'<c r="{ref(c, r)}"><v>{v}</v></c>')
            elif c % 2:
                cellules.append(f'<c r="{ref(c, r)}" t="inlineStr"><is><t>{v}</t></is></c>')
            else:
                if v not in index:
                    index[v] = len(partagees)
                    partagees.append(v)
                cellules.append(f'<c r="{ref(c, r)}" t="s"><v>{index[v]}</v></c>')
        xml_lignes.append(f'<row r="{r}">{"".join(cellules)}</row>')
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rel = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    with zipfile.ZipFile(chemin, "w") as z:
        z.writestr("xl/workbook.xml", f'<workbook {ns} {rel}><sheets><sheet name="LWIN" sheetId="1" '
                                      f'r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="x"/></Relationships>')
        z.writestr("xl/sharedStrings.xml", f'<sst {ns}>' + "".join(
            f"<si><t>{s}</t></si>" for s in partagees) + "</sst>")
        z.writestr("xl/worksheets/sheet1.xml", f'<worksheet {ns}><sheetData>{"".join(xml_lignes)}'
                                               f'</sheetData></worksheet>')


ENTETES = ["LWIN", "STATUS", "DISPLAY_NAME", "PRODUCER_TITLE", "PRODUCER_NAME", "WINE", "COUNTRY",
           "REGION", "SUB_REGION", "SITE", "PARCEL", "COLOUR", "TYPE", "SUB_TYPE", "DESIGNATION",
           "CLASSIFICATION", "VINTAGE_CONFIG", "FIRST_VINTAGE", "FINAL_VINTAGE", "DATE_ADDED",
           "DATE_UPDATED"]
LIGNES = [
    [1012361, "Live", "Chateau des Trois Chenes, Pauillac", "Chateau", "des Trois Chenes", "", "France",
     "Bordeaux", "Pauillac", "", "", "Red", "Wine", "Still", "AOP", "5eme Cru Classe", "", 1950, "", "", ""],
    [1012362, "Live", "Chateau des Trois Chenes, Les Ailes", "Chateau", "des Trois Chenes", "Les Ailes",
     "France", "Bordeaux", "Pauillac", "", "", "Red", "Wine", "Still", "", "", "", 1990, "", "", ""],
    [1012363, "Live", "Chateau des Trois Ormes, Pauillac", "Chateau", "des Trois Ormes", "", "France",
     "Bordeaux", "Pauillac", "", "", "Red", "Wine", "Still", "", "", "", "", "", "", ""],
    [1099999, "Deleted", "Chateau Efface", "Chateau", "Efface", "", "France", "Bordeaux", "", "", "",
     "Red", "Wine", "Still", "", "", "", "", "", "", ""],
    [1023456, "Live", "Domaine Petit-Roc, Chablis Premier Cru Vieilles Vignes", "Domaine", "Petit-Roc",
     "Vieilles Vignes", "France", "Burgundy", "Chablis", "Chablis 1er Cru", "", "White", "Wine", "Still",
     "", "", "", 1985, 2019, "", ""],
    [1034567, "Live", "Distillerie du Val, Marc", "", "Distillerie du Val", "Marc", "France", "Burgundy", "",
     "", "", "", "Spirit", "Marc", "", "", "", "", "", "", ""],
]


@pytest.fixture
def refs(tmp_path):
    r = References(tmp_path / "references.db")
    yield r
    r.fermer()


@pytest.fixture
def refs_lwin(refs, tmp_path):
    f = tmp_path / "LWINdatabase.xlsx"
    ecrire_xlsx(f, [ENTETES] + LIGNES)
    refs.remplacer_lwin(lwin.lignes_fichier(f), source=f.name)
    appellations.charger_embarques(refs)
    return refs


# ---------------------------------------------------------------- normalisation
def test_normalisation_des_noms():
    assert normaliser("St-Julien") == normaliser("Saint-Julien") == "saint julien"
    assert normaliser("Ch. Léoville Las Cases") == normaliser("Chateau Leoville-Las-Cases")
    assert normaliser("Domaine de la Romanée-Conti") == "romanee conti"
    assert normaliser("Chablis 1er Cru") == normaliser("Chablis Premier Cru")
    assert normaliser_appellation("Côtes du Rhône") == "cotes du rhone"     # articles gardés


# ---------------------------------------------------------------- LWIN
def test_lecture_xlsx_et_conversion(tmp_path):
    f = tmp_path / "l.xlsx"
    ecrire_xlsx(f, [ENTETES] + LIGNES)
    brutes = list(lwin.lire_xlsx(f))
    assert brutes[0][:3] == ["LWIN", "STATUS", "DISPLAY_NAME"]
    assert brutes[1][0] == "1012361" and brutes[1][17] == "1950"
    lignes = list(lwin.lignes_fichier(f))
    assert len(lignes) == 5                                   # la ligne « Deleted » est écartée
    l = lignes[0]
    assert l["lwin"] == "1012361" and l["couleur"] == "rouge" and l["type"] == "tranquille"
    assert l["producteur_norm"] == "trois chenes" and l["premier_millesime"] == 1950
    chablis = next(x for x in lignes if x["lwin"] == "1023456")
    assert chablis["region"] == "Bourgogne" and chablis["dernier_millesime"] == 2019
    assert next(x for x in lignes if x["lwin"] == "1034567")["type"] == "autre"


def test_fichier_qui_n_est_pas_lwin(tmp_path):
    f = tmp_path / "autre.xlsx"
    ecrire_xlsx(f, [["Nom", "Prix"], ["x", 3]])
    with pytest.raises(ValueError):
        list(lwin.lignes_fichier(f))


def test_copie_locale_et_recherche_hors_ligne(refs_lwin):
    assert refs_lwin.nb_lwin() == 5
    assert refs_lwin.meta("lwin_source") == "LWINdatabase.xlsx"
    trouves = [r["lwin"] for r in refs_lwin.rechercher_lwin("Château des Trois-Chênes")]
    assert "1012361" in trouves and "1012362" in trouves
    assert refs_lwin.lwin("10123612015")["producteur"] == "des Trois Chenes"   # LWIN-11 accepté
    assert lwin.lwin11("1012361", 2015) == "10123612015"
    assert lwin.lwin11("1012361", None, non_millesime=True) == "10123611000"


def test_import_lwin_tout_ou_rien(refs_lwin, tmp_path):
    def casse():
        yield from lwin.lignes_fichier(tmp_path / "x.xlsx")
    ecrire_xlsx(tmp_path / "x.xlsx", [ENTETES] + LIGNES[:2])

    def lignes_puis_erreur():
        yield from casse()
        raise RuntimeError("fichier tronqué")
    with pytest.raises(RuntimeError):
        refs_lwin.remplacer_lwin(lignes_puis_erreur())
    assert refs_lwin.nb_lwin() == 5                            # l'ancienne copie est intacte


# ---------------------------------------------------------------- registres
def test_registres_embarques(refs):
    faits = appellations.charger_embarques(refs)
    assert faits["inao"] > 1000 and faits["eambrosia"] > 1000
    assert appellations.charger_embarques(refs) == {}            # déjà à jour : rien à refaire
    assert refs.appellation_officielle("saint julien")["nom"] == "Saint-Julien"
    assert refs.appellation_officielle("Chateauneuf du Pape")["nom"] == "Châteauneuf-du-Pape"
    assert refs.appellation_officielle("Barolo")["registre"] == "eambrosia"
    noms = [a["nom"] for a in refs.appellations_dans("GRAND VIN\nAPPELLATION PAUILLAC CONTRÔLÉE\n2015")]
    assert noms[0] == "Pauillac"
    sources = appellations.sources_embarquees()
    assert "Licence Ouverte" in sources["inao"]["licence"] and sources["eambrosia"]["date_extraction"]


def test_lecture_des_formats_officiels():
    csv_inao = ("signe_fr,signe_ue,categorie,classe_ue,appellation,id_appellation,denomination,"
                "id_denomination_geo,lib_etat\n"
                "AOC  ,AOP  ,Vin tranquille,Vins,Chablis,1,Chablis premier cru Vaillons,2,Publié\n"
                "AOC  ,AOP  ,Vin tranquille,Vins,Chablis,1,Chablis,1,Publié\n"
                "AOC  ,AOP  ,Fromage,Fromages,Comté,9,Comté,9,Publié\n")
    lignes = appellations.depuis_inao(csv_inao)
    assert {(l["nom"], l["parent"]) for l in lignes} == {("Chablis", None),
                                                         ("Chablis premier cru Vaillons", "Chablis")}
    eamb = appellations.depuis_eambrosia([
        {"protectedNames": ["Rioja"], "giType": "PDO", "countries": ["ES"], "fileNumber": "PDO-ES-A0117",
         "productType": "WINE", "status": "registered"},
        {"protectedNames": ["Feta"], "productType": "FOOD"},
        {"protectedNames": ["Ancien"], "productType": "WINE", "removedFlag": True}])
    assert [(e["nom"], e["signe"], e["pays"]) for e in eamb] == [("Rioja", "PDO", "ES")]


# ---------------------------------------------------------------- appariement
def test_appariement_score_explique_et_preselection(refs_lwin):
    r = {"producteur": "Château des Trois Chênes", "appellation": "Pauillac", "couleur": "rouge",
         "millesime": 2015, "pays": "France"}
    candidats = appariement.candidats_lwin(refs_lwin, r)
    d = appariement.decider(candidats)
    assert d.motif == "sur" and d.choisi.identifiant == "1012361"
    cles = [x.cle for x in d.choisi.raisons]
    assert "appariement.r_producteur" in cles and "appariement.r_grand_vin" in cles
    assert "appariement.r_millesime_ok" in cles
    # le second vin et le voisin trompeur viennent après
    ordre = [c.identifiant for c in d.candidats]
    assert ordre.index("1012361") < ordre.index("1012363")
    assert ordre.index("1012361") < ordre.index("1012362")
    texte = appariement.explication_texte(d.choisi.raisons, lambda cle, **v: cle)
    assert texte.count("\n") == len(d.choisi.raisons) - 1


def test_appariement_renonce_si_deux_candidats_se_valent():
    a = appariement.Candidat("lwin", "1", "A", 0.81, [], {})
    b = appariement.Candidat("lwin", "2", "B", 0.79, [], {})
    assert appariement.decider([a, b]).motif == "ambigu"
    assert appariement.decider([a, b]).choisi is None
    faible = appariement.Candidat("lwin", "3", "C", 0.30, [], {})
    assert appariement.decider([faible]).motif == "faible"
    assert appariement.decider([]).motif == "aucun"


def test_contradiction_de_couleur_et_millesime(refs_lwin):
    ligne = refs_lwin.lwin("1023456")
    bon, _ = appariement.score_lwin({"producteur": "Domaine Petit-Roc", "couleur": "blanc",
                                     "millesime": 2015, "cuvee": "Vieilles vignes"}, ligne)
    rouge, raisons = appariement.score_lwin({"producteur": "Domaine Petit-Roc", "couleur": "rouge",
                                             "millesime": 2022, "cuvee": "Vieilles vignes"}, ligne)
    assert bon > 0.85 and rouge < bon * 0.6
    cles = [r.cle for r in raisons]
    assert "appariement.r_couleur_non" in cles and "appariement.r_millesime_non" in cles


def test_spiritueux_ecarte(refs_lwin):
    s, raisons = appariement.score_lwin({"producteur": "Distillerie du Val"}, refs_lwin.lwin("1034567"))
    assert "appariement.r_pas_un_vin" in [r.cle for r in raisons] and s < 0.5


def test_appariement_depuis_le_texte_d_une_etiquette(refs_lwin):
    r = {"texte": "CHÂTEAU DES\nTROIS CHENES\nPauillac\n2015", "appellation": "Pauillac",
         "millesime": 2015}
    d = appariement.decider(appariement.candidats_lwin(refs_lwin, r))
    assert d.candidats[0].identifiant == "1012361"


def test_confirmation_ne_remplace_jamais_une_saisie_manuelle(cave, refs_lwin):
    vin = cave.enregistrer_vin({"producteur": "Château des Trois Chênes", "millesime": 2015,
                                "pays": "Royaume de France"})            # saisi à la main
    c = appariement.candidats_lwin(refs_lwin, appariement.requete_depuis_vin(cave, vin),
                                   appellation_officielle=refs_lwin.appellation_officielle)[0]
    assert c.identifiant == "1012361" and c.donnees["appellation"] == "Pauillac"
    etats = {champ: etat for champ, _p, _a, etat in appariement.apercu(cave, vin, c.donnees)}
    assert etats["pays"] == "manuel" and etats["lwin"] == "remplira" and etats["producteur"] == "identique"
    remplis = appariement.confirmer(cave, vin, c, list(c.donnees), "explication")
    v = cave.vin(vin)
    assert v["pays"] == "Royaume de France"                    # intouché
    assert v["lwin"] == "1012361" and v["appellation"] == "Pauillac" and v["couleur"] == "rouge"
    assert "pays" not in remplis and "lwin" in remplis
    journal = {j["champ"]: j for j in cave.journal(vin)}
    assert journal["lwin"]["source"] == "lwin" and "1012361" in journal["lwin"]["detail"]
    ident = cave.identifiants(vin)[0]
    assert (ident["source"], ident["valeur"], ident["confirme"]) == ("lwin", "1012361", 1)
    # une seconde confirmation (autre candidat) ne remplace pas ce qui est rempli
    autre = appariement.candidats_lwin(refs_lwin, {"producteur": "Trois Ormes"})[0]
    appariement.confirmer(cave, vin, autre, list(autre.donnees), "x")
    assert cave.vin(vin)["lwin"] == "1012361"
    assert [i["valeur"] for i in cave.identifiants(vin)] == [autre.identifiant]   # un identifiant par source


# ---------------------------------------------------------------- réseau simulé
class FauxReseau:
    """Transport simulé : répond selon l'adresse, note chaque requête."""

    def __init__(self, reponses):
        self.reponses = reponses
        self.requetes = []

    def __call__(self, url, entetes, delai):
        self.requetes.append((url, dict(entetes)))
        for motif, rep in self.reponses:
            if motif in url:
                if callable(rep):
                    rep = rep(url)
                if isinstance(rep, reseau.Reponse):
                    return rep
                return reseau.Reponse(200, {}, json.dumps(rep).encode())
        return reseau.Reponse(404, {}, b"")


class Horloge:
    def __init__(self):
        self.t = 0.0
        self.attentes = []

    def __call__(self):
        return self.t

    def dormir(self, s):
        self.attentes.append(s)
        self.t += s


def client(reponses):
    h = Horloge()
    faux = FauxReseau(reponses)
    return reseau.Client(transport=faux, horloge=h, dormir=h.dormir, ignorer_accord=True), faux, h


def test_hors_ligne_sans_accord():
    reseau.autoriser(False)
    c = reseau.Client(transport=FauxReseau([]))
    with pytest.raises(reseau.HorsLigne):
        c.get("https://www.wikidata.org/w/api.php")


def test_client_identifie_et_limite_le_debit():
    c, faux, h = client([("wikidata.org", {"ok": 1}), ("openfoodfacts", {"ok": 2})])
    for _ in range(3):
        c.json("https://www.wikidata.org/w/api.php", {"a": "b"})
    c.json("https://world.openfoodfacts.org/api/v2/product/1.json")
    ua = faux.requetes[0][1]["User-Agent"]
    assert ua.startswith("Vendemiaire/") and "github.com/ARP273-ROSE/Vendemiaire" in ua
    assert h.attentes == [1.0, 1.0]           # une requête par seconde vers Wikidata ; OFF : autre hôte
    assert faux.requetes[0][0].endswith("?a=b")


def test_client_respecte_retry_after():
    etat = {"n": 0}

    def sature(_url):
        etat["n"] += 1
        return reseau.Reponse(429, {"retry-after": "7"}, b"") if etat["n"] == 1 else \
            reseau.Reponse(200, {}, b'{"ok": true}')
    c, _faux, h = client([("wikidata", sature)])
    assert c.json("https://query.wikidata.org/sparql") == {"ok": True}
    assert 7.0 in h.attentes
    c2, _f, _h = client([("wikidata", reseau.Reponse(500, {}, b""))])
    with pytest.raises(reseau.ErreurReseau):
        c2.json("https://query.wikidata.org/sparql")


RECHERCHE_WD = {"search": [
    {"id": "Q1063236", "label": "château Margaux", "description": "château à Margaux (Gironde)"},
    {"id": "Q11913741", "label": "Chateau Margaux", "description": "zarzuela de 1887"}]}
SPARQL_WD = {"results": {"bindings": [
    {"item": {"value": "http://www.wikidata.org/entity/Q1063236"}, "itemLabel": {"value": "château Margaux"},
     "itemDescription": {"value": "château à Margaux (Gironde)"},
     "natures": {"value": "domaine viticole|château"}, "coord": {"value": "Point(-0.6687 45.0444)"},
     "fondation": {"value": "1590-01-01T00:00:00Z"},
     "proprietaires": {"value": "Corinne Mentzelopoulos"},
     "image": {"value": "http://commons.wikimedia.org/wiki/Special:FilePath/Margaux%20exterior.jpg"},
     "site": {"value": "http://www.chateau-margaux.com"}, "pays": {"value": "France"},
     "lieu": {"value": "Margaux"},
     "wpfr": {"value": "https://fr.wikipedia.org/wiki/Ch%C3%A2teau_Margaux"}},
    {"item": {"value": "http://www.wikidata.org/entity/Q11913741"}, "itemLabel": {"value": "Chateau Margaux"},
     "itemDescription": {"value": "zarzuela de 1887"}, "natures": {"value": "zarzuela"}}]}}
COMMONS = {"query": {"pages": {"1": {"imageinfo": [{
    "thumburl": "https://upload.wikimedia.org/x/800px-Margaux.jpg",
    "descriptionurl": "https://commons.wikimedia.org/wiki/File:Margaux_exterior.jpg",
    "extmetadata": {"Artist": {"value": "<a href='//x'>BillBl</a>"},
                    "LicenseShortName": {"value": "CC BY 2.0"},
                    "LicenseUrl": {"value": "https://creativecommons.org/licenses/by/2.0"}}}]}}}}


def test_wikidata_simule():
    c, faux, _h = client([("wbsearchentities", RECHERCHE_WD), ("query.wikidata.org", SPARQL_WD),
                          ("commons.wikimedia.org", COMMONS)])
    cands = wikidata.candidats(c, "producteur", "Château Margaux", "France")
    assert cands[0].identifiant == "Q1063236" and cands[0].score > 0.9
    assert cands[1].score < 0.7                                   # une zarzuela n'est pas un domaine
    f = cands[0].brut
    assert f["fondation"] == 1590 and f["coordonnees"] == (45.0444, -0.6687)
    assert f["image"] == "Margaux exterior.jpg" and f["proprietaires"] == ["Corinne Mentzelopoulos"]
    assert cands[0].donnees == {"site_web": "http://www.chateau-margaux.com", "pays": "France",
                                "adresse": "Margaux"}
    credit = wikidata.credit_commons(c, f["image"])
    assert credit["auteur"] == "BillBl" and credit["licence"] == "CC BY 2.0"
    assert all("User-Agent" in e for _u, e in faux.requetes)


def test_fiche_wikidata_et_completion_du_producteur(cave):
    vin = cave.enregistrer_vin({"producteur": "Château Margaux"})
    pid = cave.vin(vin)["producteur_id"]
    cave.enregistrer_fiche("wikidata", "Q1063236", "producteur", {"nom": "château Margaux"},
                           producteur_id=pid, licence="CC0 1.0", url="https://www.wikidata.org/wiki/Q1063236")
    cave.enregistrer_fiche("wikidata", "Q1063236", "producteur", {"nom": "remplacée"}, producteur_id=pid)
    assert [f["donnees"]["nom"] for f in cave.fiches(vin)] == ["remplacée"]
    assert cave.completer_producteur(pid, {"site_web": "http://x", "pays": "France"}, "wikidata") == \
        ["site_web", "pays"]
    assert cave.completer_producteur(pid, {"site_web": "http://autre"}, "wikidata") == []
    assert {j["champ"] for j in cave.journal(vin)} == {"site_web", "pays"}


PRODUIT_OFF = {"status": 1, "product": {
    "code": "3012345678902", "product_name": "Château Exemple 2019", "brands": "Château Exemple",
    "quantity": "75 cl", "nutriments": {"alcohol_100g": 13.5},
    "image_front_url": "https://images.openfoodfacts.org/x/front.jpg"}}


def test_open_food_facts_simule():
    assert off.ean_valide("3017620422003") and not off.ean_valide("3017620422004")
    assert off.ean_valide("96385074") and off.ean_valide("036000291452")
    assert off.eans_dans("lot 12 — EAN 3 017620 422003") == ["3017620422003"]
    c, faux, _h = client([("api/v2/product/3012345678902", PRODUIT_OFF),
                          ("api/v2/product/", {"status": 0})])
    p = off.produit(c, "3012345678902")
    cand = off.candidat(p)
    assert cand.donnees == {"ean": "3012345678902", "degre": 13.5}
    assert cand.source == "off" and "photo" in cand.raisons[-1].cle
    assert off.produit(c, "0000000000000") is None
    assert "fields=" in faux.requetes[0][0]
    # page « temporairement indisponible » (HTML) : erreur propre, pas un plantage
    c2, _f, _h = client([("openfoodfacts", reseau.Reponse(200, {}, b"<!DOCTYPE html><html>"))])
    with pytest.raises(reseau.ErreurReseau):
        off.produit(c2, "3012345678902")


def test_aucune_adresse_d_aspirateur():
    """Vivino et Wine-Searcher ne sont jamais interrogés : seulement ouverts
    dans le navigateur par l'utilisateur."""
    from pathlib import Path
    racine = Path(__file__).resolve().parent.parent / "vendemiaire"
    for p in racine.rglob("*.py"):
        texte = p.read_text(encoding="utf-8")
        if "vivino.com" in texte or "wine-searcher.com" in texte:
            assert p.name == "identifier.py" and "QDesktopServices.openUrl" in texte, p
    assert "vivino" not in json.dumps(reseau.INTERVALLES)


def test_lwin_vrai_format_na_et_dates_excel(tmp_path):
    """Format réel du fichier de Liv-ex (vu le 28/10/2026) : « NA » = case vide, dates en série Excel."""
    from vendemiaire.mondial import lwin
    f = tmp_path / "lwin.csv"
    f.write_text(
        "LWIN,STATUS,DISPLAY_NAME,PRODUCER_TITLE,PRODUCER_NAME,WINE,COUNTRY,REGION,SUB_REGION,SITE,"
        "PARCEL,COLOUR,TYPE,SUB_TYPE,DESIGNATION,CLASSIFICATION,VINTAGE_CONFIG,FIRST_VINTAGE,"
        "FINAL_VINTAGE,DATE_ADDED,DATE_UPDATED,REFERENCE\n"
        "1000001,Live,\"Exemple, Riesling\",NA,Exemple,Riesling,France,Alsace,NA,NA,NA,White,Wine,"
        "Still,AOP,NA,sequential,NA,NA,40702,45849.46644675926,\n", encoding="utf-8")
    (ligne,) = list(lwin.lignes_fichier(f))
    assert ligne["producteur_norm"] == "exemple"
    assert ligne["sous_region"] is None and ligne["classement"] is None
    assert "na" not in ligne["texte"].split()
    assert ligne["couleur"] == "blanc"
    assert ligne["maj"] == "2025-07-11"


def test_reseau_passe_par_la_cascade_de_certificats(monkeypatch):
    """Les bases mondiales passent par reporting.ouvrir_url (repli sur certifi si le magasin du
    système refuse un certificat) : sans cela, « certificate has expired » sous Windows."""
    import io
    import reporting
    from vendemiaire import reseau
    vues = []

    class Rep(io.BytesIO):
        status, headers = 200, {}

    monkeypatch.setattr(reporting, "ouvrir_url", lambda req, timeout: vues.append(req.full_url) or Rep(b"{}"))
    r = reseau.transport_urllib("https://exemple.invalid/x", {}, 5)
    assert vues == ["https://exemple.invalid/x"] and r.statut == 200
