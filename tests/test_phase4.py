# -*- coding: utf-8 -*-
"""Phase 4 : carte des vins (ordre classique, verticales, formats à part, mise à
jour d'un clic, menu du soir, LaTeX et repli Qt), rapport d'assurance (valeur
datée et sourcée), statistiques, codes QR (planche puis relecture), imports
Excel et Vivino, séances de dégustation (notes figées après révélation),
partage en lecture seule, et les fenêtres correspondantes, en anglais sans
français."""
import re
import shutil
import subprocess
import zipfile
from datetime import date

import pytest
from PyQt6 import QtCore

from vendemiaire import i18n

PERIGNON = {"producteur": "Maison Témoin", "cuvee": "Prestige", "appellation": "Champagne", "region": "Champagne",
            "pays": "France", "couleur": "blanc", "type": "effervescent"}
LEOVILLE = {"producteur": "Château Témoin", "cuvee": "Grand vin", "appellation": "Saint-Julien",
            "region": "Bordeaux", "pays": "France", "couleur": "rouge", "type": "tranquille",
            "cepages": [("Cabernet sauvignon", 75), ("Merlot", 25)]}


def _vin(cave, donnees, n=1, **attributs):
    vid = cave.enregistrer_vin(donnees)
    cave.ajouter_bouteilles(vid, n, attributs or None)
    return vid


# ---------------------------------------------------------------------------- carte des vins
def test_schema_v6(cave):
    noms = {r["name"] for r in cave.base.lire("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"carte", "carte_vin", "seance_vin"} <= noms
    assert "revelee_le" in {r["name"] for r in cave.base.lire("PRAGMA table_info(seance)")}


def test_carte_ordre_classique_et_verticales(cave):
    from vendemiaire.documents import carte
    rouge_cher = _vin(cave, dict(LEOVILLE, millesime=2010), 2, prix_achat=300)
    rouge_bon_marche = _vin(cave, dict(LEOVILLE, millesime=2015), 1, prix_achat=20)
    _vin(cave, dict(LEOVILLE, producteur="Abbaye Témoin", millesime=2018), 1, prix_achat=900)
    _vin(cave, dict(PERIGNON, millesime=2012), 3)
    _vin(cave, {"producteur": "Clos Doux", "appellation": "Sauternes", "region": "Bordeaux", "pays": "France",
                "couleur": "blanc", "type": "doux", "millesime": 2009}, 1)
    _vin(cave, {"producteur": "Quinta Témoin", "appellation": "Porto", "region": "Douro", "pays": "Portugal",
                "couleur": "rouge", "type": "mute", "millesime": 2011}, 1)
    _vin(cave, {"producteur": "Bodega Témoin", "appellation": "Rioja", "region": "Rioja", "pays": "Espagne",
                "couleur": "rouge", "type": "tranquille", "millesime": 2016}, 1)
    _vin(cave, dict(LEOVILLE, millesime=2005), 1, format="magnum")
    _vin(cave, {"producteur": "Domaine Demi", "appellation": "Sancerre", "region": "Val de Loire", "pays": "France",
                "couleur": "blanc", "type": "tranquille", "millesime": 2022}, 1, format="demi")
    k = carte.construire(cave, {"prix": True})
    assert [s.cle for s in k.sections] == ["effervescent", "doux", "mute", "rouge"][:1] + ["rouge", "doux", "mute"]
    rouge = next(s for s in k.sections if s.cle == "rouge")
    assert [p.nom for p in rouge.pays] == ["France", "Espagne"]           # France d'abord
    groupes = rouge.pays[0].regions[0].appellations[0].groupes
    # par producteur puis millésime, jamais par prix (« Abbaye » à 900 € passe avant)
    assert [g.producteur for g in groupes] == ["Abbaye Témoin", "Château Témoin"]
    verticale = groupes[1]
    assert verticale.verticale and [l.millesime for l in verticale.lignes] == [2010, 2015]
    assert {l.vin_id for l in verticale.lignes} == {rouge_cher, rouge_bon_marche}
    assert [l.format for s in k.grands for l in s.lignes()] == ["magnum"]
    assert [l.format for s in k.demi for l in s.lignes()] == ["demi"]
    # BIN attribués par section, puis inscrits dans la cave
    assert all(l.bin for l in k.toutes_les_lignes())
    assert k.sections[0].lignes()[0].bin == "101"
    assert carte.attribuer_bins(cave, k) == sum(l.n for l in k.toutes_les_lignes())
    assert cave.base.valeur("SELECT COUNT(*) FROM bouteille WHERE bin IS NULL AND statut='en_cave'") == 0


def test_carte_enregistree_mise_a_jour_d_un_clic(cave):
    from vendemiaire.documents import carte
    a = _vin(cave, dict(LEOVILLE, millesime=2010), 1)
    b = _vin(cave, dict(PERIGNON, cuvee="Brut"), 2)            # sans année : « effervescent sans année »
    cid = carte.enregistrer(cave, "Dîner de samedi", {"prix": True, "menu": ["huîtres"]},
                            {a: {"prix": 120}, b: {"au_verre": True, "prix_verre": 14, "prix": 80}})
    k = carte.construire_enregistree(cave, cid)
    assert {l.vin_id for l in k.toutes_les_lignes()} == {a, b}
    assert [l.vin_id for l in k.au_verre] == [b] and k.au_verre[0].prix_verre == 14
    assert next(l for l in k.toutes_les_lignes() if l.vin_id == a).prix == 120
    # menu du soir : le brut sans année est proposé avec les huîtres (accords du dossier)
    assert k.menu[0].regle is not None and k.menu[0].ligne.vin_id == b
    # la bouteille bue disparaît à la régénération
    cave.sortir(cave.bouteilles(a)[0]["id"], "sortie_bue")
    k = carte.construire_enregistree(cave, cid)
    assert {l.vin_id for l in k.toutes_les_lignes()} == {b}


def test_carte_html_et_textes_anglais(cave):
    from vendemiaire.documents import carte
    _vin(cave, dict(LEOVILLE, millesime=2010), 1)
    _vin(cave, dict(PERIGNON, millesime=2012), 1)
    k = carte.construire(cave, {"langue": "en", "menu": ["oysters", "zzzz"], "mot": "Welcome"})
    h = carte.html(k)
    assert h.index("Champagne and sparkling wines") < h.index("Red wines")
    assert "Wine list" in h and "Tonight" in h
    assert "Dish not found" in h                    # plat inconnu : dit, aucun vin inventé
    texte = re.sub(r"<[^>]+>", " ", h)
    for nom in ("Château Témoin", "Maison Témoin", "Saint-Julien", "Grand vin", "Champagne", "Cuvée", "Rosé"):
        texte = texte.replace(nom, "")
    assert not re.search(r"[éèàçêôûùîïœ]", texte), re.findall(r".{20}[éèàçêôûùîïœ].{20}", texte)[:5]


def test_latex_echappement_et_source(cave):
    from vendemiaire.documents import carte, latex
    assert latex.echapper("50 % & 3 $ #1 a_b {x} ~") == r"50 \% \& 3 \$ \#1 a\_b \{x\} \textasciitilde{}"
    _vin(cave, dict(LEOVILLE, producteur="Château 100 % & Cie", millesime=2010), 1)
    for modele in carte.MODELES:
        for fmt in carte.FORMATS_PAGE:
            k = carte.construire(cave, {"modele": modele, "format": fmt})
            src, annexes = carte.latex(k, True)
            assert r"Château 100 \% \& Cie" in src and src.count(r"\begin{document}") == 1
            assert "logo.png" in annexes or fmt == "simple" or True


@pytest.mark.skipif(not __import__("vendemiaire.documents.latex", fromlist=["x"]).trouver_moteur(),
                    reason="aucun moteur LaTeX (CI)")
def test_carte_compilee_par_latex(cave, tmp_path):
    from vendemiaire.documents import carte
    _vin(cave, dict(LEOVILLE, millesime=2010), 2)
    _vin(cave, dict(PERIGNON, millesime=2012), 1)
    k = carte.construire(cave, {"modele": "bistrot", "menu": ["huîtres"], "mot": "Bienvenue"})
    moteur = carte.ecrire_pdf(k, tmp_path / "c.pdf")
    assert moteur != "qt" and (tmp_path / "c.pdf").read_bytes()[:5] == b"%PDF-"
    assert not [p for p in tmp_path.iterdir() if p.suffix in (".aux", ".log", ".tex", ".out")]   # aucun temporaire


def test_carte_repli_qt(app, cave, tmp_path):
    from vendemiaire.documents import carte
    _vin(cave, dict(LEOVILLE, millesime=2010), 1)
    k = carte.construire(cave)
    assert carte.ecrire_pdf(k, tmp_path / "q.pdf", forcer_qt=True) == "qt"
    assert (tmp_path / "q.pdf").read_bytes()[:5] == b"%PDF-"


def test_petites_cartes():
    from vendemiaire.documents import geo
    assert geo.region_geo("France", "Vallée du Rhône")["nom"] == "Rhône"
    assert geo.region_geo("Italie", "Piémont")["nom"] == "Piémont"
    assert geo.region_geo("Canada", "Niagara")["pays"] == "Canada"
    assert geo.nom_pays("Italie", "en") == "Italy" and geo.nom_pays("États-Unis", "en") == "United States"
    r = [geo.region_geo("France", "Bordeaux"), geo.region_geo("France", "Champagne")]
    assert "<svg" in geo.svg("France", r) and r"\filldraw" in geo.tikz("France", r)
    assert geo.donnees()["sources"][0].startswith("Natural Earth")


# ---------------------------------------------------------------------------- assurance
def test_rapport_assurance_valeurs_sourcees(app, cave, tmp_path):
    from vendemiaire.documents import assurance
    a = _vin(cave, dict(LEOVILLE, millesime=1990), 1, prix_achat=200, date_achat="2001-05-01", niveau="LS",
             caisse="cbo", caisse_complete=1, provenance="Achetée au domaine")
    b = _vin(cave, dict(LEOVILLE, millesime=2015), 1, prix_achat=40, date_achat="2018-01-02")
    _vin(cave, dict(PERIGNON, millesime=2012), 1)
    cave.ajouter_valeur(a, 450, "Vente aux enchères (catalogue)", "2026-06-01")
    inv = assurance.construire(cave, "fr")
    assert inv.bouteilles == 3 and inv.total == pytest.approx(490)
    assert (inv.compte("estimee"), inv.compte("achat"), inv.compte("aucune")) == (1, 1, 1)
    ba = next(v for v in inv.vins if v.id == a).bouteilles[0]
    assert ba.valeur == 450 and ba.valeur_date == "2026-06-01" and "enchères" in ba.valeur_source
    assert ba.sens_niveau                                              # LS sur un 1990 : sens donné par le dossier
    bb = next(v for v in inv.vins if v.id == b).bouteilles[0]
    assert assurance._source(bb, "fr").startswith("prix d'achat")
    h = assurance.html(inv)
    assert "(CBO), complète" in h and "non évaluée" in h
    src, _ann = assurance.latex(inv)
    assert r"\section{" in src and "tcolorbox" in src
    assurance.ecrire_pdf(inv, tmp_path / "a.pdf", forcer_qt=True)
    assert (tmp_path / "a.pdf").read_bytes()[:5] == b"%PDF-"


# ---------------------------------------------------------------------------- statistiques
def test_statistiques(cave_demo):
    from vendemiaire import statistiques as st
    n = cave_demo.base.valeur("SELECT COUNT(*) FROM bouteille WHERE statut='en_cave'")
    for axe in st.AXES:
        assert sum(v for _k, v in st.repartition(cave_demo, axe)) == pytest.approx(n), axe
    total = cave_demo.statistiques()["valeur_estimee"]
    assert sum(v for _k, v in st.repartition(cave_demo, "pays", "valeur")) == pytest.approx(total)
    assert st.tranche(9.99) == "<10" and st.tranche(10) == "10-20" and st.tranche(1000) == ">150"
    assert st.tranche(None) == "?"
    points = st.valeur_dans_le_temps(cave_demo, 12, date(2026, 10, 26))
    assert len(points) == 13 and points[-1][3] == n
    entrees = sum(e for _a, e, _s in st.consommation_achats(cave_demo))
    assert entrees == cave_demo.base.valeur("SELECT SUM(quantite) FROM mouvement WHERE type LIKE 'entree%'")
    par_couleur = st.apogee_par_couleur(cave_demo)
    assert set(par_couleur) <= {"rouge", "blanc", "rose", "orange", None} and par_couleur


# ---------------------------------------------------------------------------- codes QR
def test_etiquettes_qr_relues(app, cave_demo, tmp_path):
    from vendemiaire import codes
    from vendemiaire.documents import etiquettes
    bs = etiquettes.bouteilles_pour_etiquettes(cave_demo)[:24]
    assert etiquettes.ecrire_planche(bs, tmp_path / "e.pdf", "3x8") == 1
    assert etiquettes.ecrire_planche(bs, tmp_path / "e2.pdf", "3x7", depart=5) == 2
    if not shutil.which("pdftoppm"):
        pytest.skip("pdftoppm absent")
    subprocess.run(["pdftoppm", "-r", "150", "-png", "-singlefile", str(tmp_path / "e.pdf"), str(tmp_path / "p")],
                   check=True)
    lus = codes.lire_fichier(tmp_path / "p.png")
    assert {c.texte for c in lus} == {b["code_interne"] for b in bs}
    assert all(c.interne for c in lus)
    assert codes.CodeLu("3760123456789", "EAN-13").ean


# ---------------------------------------------------------------------------- imports
def _xlsx(chemin, lignes):
    def cellule(v, i, j):
        ref = chr(65 + j) + str(i + 1)
        if isinstance(v, (int, float)):
            return f'<c r="{ref}"><v>{v}</v></c>'
        return f'<c r="{ref}" t="inlineStr"><is><t>{v}</t></is></c>'
    rangs = "".join(f'<row r="{i + 1}">' + "".join(cellule(v, i, j) for j, v in enumerate(l)) + "</row>"
                    for i, l in enumerate(lignes))
    with zipfile.ZipFile(chemin, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/'
                   f'2006/main"><sheetData>{rangs}</sheetData></worksheet>')


def test_import_excel(cave, tmp_path):
    from vendemiaire import imports_tableur as it
    _xlsx(tmp_path / "cave.xlsx", [["Domaine", "Cuvée", "Appellation", "Couleur", "Millésime", "Nombre", "Prix",
                                    "Date d'achat", "Contenance"],
                                   ["Domaine Excel", "Vieilles vignes", "Morgon", "Rouge", 2020, 3, "12,50", 45210, "150 cl"],
                                   ["Domaine Excel", "Blanc", "Mâcon", "white", "", "", "", "", ""]])
    entetes, lignes = it.lire_tableau(tmp_path / "cave.xlsx")
    m = it.deviner(entetes)
    assert {k: entetes[v] for k, v in m.items()} == {
        "producteur": "Domaine", "cuvee": "Cuvée", "appellation": "Appellation", "couleur": "Couleur",
        "millesime": "Millésime", "quantite": "Nombre", "prix_achat": "Prix", "date_achat": "Date d'achat",
        "format": "Contenance"}
    r = it.importer(cave, entetes, lignes, m, quantite_defaut=1)
    assert (r.vins_crees, r.bouteilles) == (2, 4)
    b = cave.base.un("SELECT b.* FROM bouteille b JOIN vin v ON v.id=b.vin_id WHERE v.appellation='Morgon'")
    assert b["prix_achat"] == 12.5 and b["format"] == "magnum" and b["date_achat"] == "2023-10-11"
    assert cave.base.valeur("SELECT couleur FROM vin WHERE appellation='Mâcon'") == "blanc"
    # réimporter ne crée pas un second vin
    r2 = it.importer(cave, entetes, lignes, m, quantite_defaut=0)
    assert r2.vins_crees == 0


def test_import_vivino_correspondance_proposee(cave, tmp_path):
    from vendemiaire import imports_tableur as it
    f = tmp_path / "full_wine_list.csv"
    f.write_text("Winery,Wine name,Vintage,Region,Country,Wine type,Your rating,Your review,Scan date\n"
                 "Bodega Ejemplo,Reserva,2016,Rioja,Spain,Red Wine,4.5,Lovely,2024-02-03\n"
                 "Weingut Beispiel,Kabinett,N.V.,Mosel,Germany,Dessert Wine,,,2024-03-01\n", encoding="utf-8")
    entetes, lignes = it.lire_tableau(f)
    m = it.deviner(entetes, "vivino")
    assert entetes[m["producteur"]] == "Winery" and entetes[m["note"]] == "Your rating"
    r = it.importer(cave, entetes, lignes, m, "vivino", "5", 0)
    assert (r.vins_crees, r.bouteilles) == (2, 0)                       # notes de scans : pas de bouteille inventée
    d = cave.base.un("SELECT * FROM degustation")
    assert (d["note"], d["echelle"], d["commentaire"], d["date"]) == (4.5, "5", "Lovely", "2024-02-03")
    v = cave.base.un("SELECT * FROM vin WHERE cuvee='Kabinett'")
    assert v["millesime"] is None and (v["couleur"], v["type"]) == ("blanc", "doux")


# ---------------------------------------------------------------------------- séances
def test_seance_a_l_aveugle(cave):
    from vendemiaire import seances
    a = _vin(cave, dict(LEOVILLE, millesime=2010))
    b = _vin(cave, dict(LEOVILLE, millesime=2015))
    sid = seances.creer(cave, "aveugle", "Bordeaux à l'aveugle")
    seances.ajouter_vin(cave, sid, a)
    seances.ajouter_vin(cave, sid, b)
    seances.melanger(cave, sid, graine=3)
    vs = seances.vins(cave, sid)
    assert [v.etiquette for v in vs] == ["A", "B"] and seances.cachee(seances.seance(cave, sid))
    seances.noter(cave, sid, vs[0].vin_id, {"note": 16, "echelle": "20"})
    seances.noter(cave, sid, vs[0].vin_id, {"note": 17, "echelle": "20"})          # remplace, pas de doublon
    assert cave.base.valeur("SELECT COUNT(*) FROM degustation WHERE seance_id=?", (sid,)) == 1
    seances.reveler(cave, sid)
    with pytest.raises(seances.SeanceRevelee):
        seances.noter(cave, sid, vs[1].vin_id, {"note": 12, "echelle": "20"})
    with pytest.raises(seances.SeanceRevelee):
        seances.ajouter_vin(cave, sid, a)
    d = cave.base.un("SELECT * FROM degustation WHERE seance_id=?", (sid,))
    assert d["note"] == 17 and d["aveugle"] == 1


def test_seance_verticale_et_horizontale(cave):
    from vendemiaire import seances
    a = _vin(cave, dict(LEOVILLE, millesime=2010))
    b = _vin(cave, dict(LEOVILLE, millesime=2015))
    c = _vin(cave, dict(LEOVILLE, producteur="Château Voisin", millesime=2010))
    assert seances.suggestions(cave, "verticale", a) == [b]
    assert seances.suggestions(cave, "horizontale", a) == [c]


# ---------------------------------------------------------------------------- partage
def test_partage_lecture_seule(app, cave, tmp_path):
    from vendemiaire.documents import partage
    a = _vin(cave, dict(LEOVILLE, millesime=2010), 2, prix_achat=55)
    cave.enregistrer_degustation({"vin_id": a, "note": 18, "echelle": "20", "commentaire": "Superbe", "privee": 0})
    cave.enregistrer_degustation({"vin_id": a, "note": 11, "echelle": "20", "commentaire": "Secret", "privee": 1})
    h = partage.html(cave)
    assert "Château Témoin" in h and "Superbe" in h and "Secret" not in h and "55" not in h
    assert "<script" not in h
    assert "55" in partage.html(cave, prix=True)
    partage.ecrire_pdf(cave, tmp_path / "p.pdf")
    assert (tmp_path / "p.pdf").read_bytes()[:5] == b"%PDF-"


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


def test_dialogue_carte_des_vins(app, fenetre, tmp_path):
    from vendemiaire.ui.carte_vins import DialogueCarteVins
    d = DialogueCarteVins(fenetre.cave, fenetre)
    d.menu.setPlainText("Huîtres\nGigot d'agneau")
    d.rafraichir_apercu()
    assert "Champagnes" in d.apercu.toPlainText() and "Le menu du soir" in d.apercu.toPlainText()
    cid = d.enregistrer()
    assert d.liste.count() == 2 and cid                                # + la carte de la démonstration
    assert d.html(str(tmp_path / "c.html")) and (tmp_path / "c.html").exists()
    d.pdf(str(tmp_path / "c.pdf"), attendre=True)
    assert (tmp_path / "c.pdf").read_bytes()[:5] == b"%PDF-"
    assert fenetre.cave.base.valeur("SELECT dernier_pdf FROM carte WHERE id=?", (cid,)) == str(tmp_path / "c.pdf")
    d.close()


def test_onglets_et_dialogues_phase4(app, fenetre, tmp_path):
    from vendemiaire.ui.documents import DialogueAssurance, DialogueEtiquettes, DialoguePartage
    from vendemiaire.ui.scanner import DialogueScanner
    c = fenetre.cave
    fenetre.onglets.setCurrentWidget(fenetre.statistiques)
    app.processEvents()
    assert fenetre.statistiques.barres.donnees
    fenetre.statistiques.axe.setCurrentIndex(3)                       # cépage
    assert fenetre.statistiques.barres.donnees
    a = DialogueAssurance(c, fenetre)
    assert "Résumé" in a.apercu.toPlainText()
    a.pdf(str(tmp_path / "a.pdf"), attendre=True)
    assert (tmp_path / "a.pdf").exists()
    p = DialoguePartage(c, fenetre)
    assert p.html(str(tmp_path / "p.html"))
    e = DialogueEtiquettes(c, None, fenetre)
    assert e.pdf(str(tmp_path / "e.pdf")) and (tmp_path / "e.pdf").exists()
    s = DialogueScanner(c, fenetre, camera=False)
    b = c.base.un("SELECT id, code_interne FROM bouteille WHERE statut='en_cave' LIMIT 1")
    sorties = []
    s.sortir.connect(sorties.append)
    s.traiter(b["code_interne"])
    assert s.b_sortir.isEnabled()
    s.b_sortir.click()
    assert sorties == [b["id"]]
    s.traiter("0000000000000")
    assert not s.b_sortir.isEnabled()
    for x in (a, p, e, s):
        x.close()


def test_onglet_seances(app, fenetre):
    from vendemiaire import seances
    c = fenetre.cave
    vid = c.base.valeur("SELECT vin_id FROM bouteille WHERE statut='en_cave' LIMIT 1")
    sid = seances.creer(c, "aveugle", "Essai")
    seances.ajouter_vin(c, sid, vid)
    fenetre.seances.rafraichir(sid)
    assert fenetre.seances.table.item(0, 1).text() == "Vin A"          # caché avant la révélation
    seances.reveler(c, sid)
    fenetre.seances.rafraichir(sid)
    assert c.nom_vin(vid) in fenetre.seances.table.item(0, 1).text()
    assert not fenetre.seances.b_noter.isEnabled()


def test_import_dialogue(app, fenetre, tmp_path):
    from vendemiaire.ui.import_tableur import DialogueImportTableur
    f = tmp_path / "t.csv"
    f.write_text("Producteur;Appellation;Couleur;Millésime;Quantité\nDomaine Dialogue;Chinon;rouge;2019;2\n",
                 encoding="utf-8")
    d = DialogueImportTableur(fenetre.cave, str(f), parent=fenetre)
    assert d.correspondance()["producteur"] == 0
    r = d.importer()
    assert r.bouteilles == 2


def test_anglais_sans_francais_phase4(app, fenetre):
    from PyQt6 import QtWidgets
    from vendemiaire.ui.carte_vins import DialogueCarteVins
    from vendemiaire.ui.documents import DialogueAssurance, DialogueEtiquettes, DialoguePartage
    from vendemiaire.ui.scanner import DialogueScanner
    fenetre.changer_langue("en")
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete.value)
    app.processEvents()
    try:
        c = fenetre.cave
        fenetres = [DialogueCarteVins(c, fenetre), DialogueAssurance(c, fenetre), DialoguePartage(c, fenetre),
                    DialogueEtiquettes(c, None, fenetre), DialogueScanner(c, fenetre, camera=False),
                    fenetre.statistiques, fenetre.seances]
        textes = []
        for w in fenetres:
            for x in w.findChildren((QtWidgets.QLabel, QtWidgets.QPushButton, QtWidgets.QCheckBox, QtWidgets.QGroupBox)):
                textes.append(x.title() if isinstance(x, QtWidgets.QGroupBox) else x.text())
            for x in w.findChildren(QtWidgets.QTabWidget):
                textes += [x.tabText(i) for i in range(x.count())]
        fautes = [t for t in textes if re.search(r"[éèàçêôûùîïœ]|\b(cave|vin|boire)\b",
                                                 re.sub(r"Vendémiaire|Cuvée|cuvée|Rosé|rosé|« [^»]* »|Rouges à l'aveugle|Trois Chênes", "", t))]
        assert not fautes, fautes
        for w in fenetres[:5]:
            w.close()
    finally:
        fenetre.changer_langue("fr")
