# -*- coding: utf-8 -*-
"""Phase 5 : photos du livre de cave, liste d'achats (seuils de réassort,
envies), alertes de prix (saisie ou import, jamais d'aspirateur), outils
embarqués (Tesseract, Tectonic hors ligne), accessibilité au clavier,
robustesse (base vide, grosse base)."""
import stat
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from PyQt6 import QtCore, QtGui, QtWidgets

from vendemiaire import achats, i18n


def _vin(cave, nom="Domaine Témoin", cuvee="Cuvée A", seuil=None, millesime=2018):
    return cave.enregistrer_vin({"producteur": nom, "cuvee": cuvee, "appellation": "Bourgogne",
                                 "couleur": "rouge", "millesime": millesime, "seuil_reassort": seuil})


def _image(chemin: Path, couleur="#8E2A3D") -> Path:
    img = QtGui.QImage(64, 48, QtGui.QImage.Format.Format_RGB32)
    img.fill(QtGui.QColor(couleur))
    img.save(str(chemin), "PNG")
    return chemin


# ------------------------------------------------------------------ liste d'achats
def test_liste_d_achats_par_les_seuils_et_les_envies(cave):
    v1 = _vin(cave, cuvee="Brut", seuil=6)
    cave.ajouter_bouteilles(v1, 2, {"prix_achat": 31.5, "lieu_achat": "Caviste du port"})
    v2 = _vin(cave, cuvee="Assez", seuil=2)
    cave.ajouter_bouteilles(v2, 3)
    cave.ajouter_envie({"producteur": "Clos Rêvé", "cuvee": "Vieilles vignes", "quantite": 3, "prix_max": 40,
                        "priorite": 1})
    cave.ajouter_envie({"producteur": "Un jour", "cuvee": "Peut-être", "priorite": 3})
    lignes = achats.liste_achats(cave, avec_envies=True, priorite_max=2)
    assert [(l.origine, l.a_acheter) for l in lignes] == [("reassort", 4), ("envie", 3)]
    r = lignes[0]
    assert (r.en_cave, r.seuil, r.dernier_prix, r.lieu) == (2, 6, 31.5, "Caviste du port")
    assert len(achats.liste_achats(cave, avec_envies=True, priorite_max=3)) == 3
    assert [l.origine for l in achats.liste_achats(cave, avec_envies=False)] == ["reassort"]


def test_liste_d_achats_imprimable_et_csv(cave, tmp_path, app):
    v1 = _vin(cave, cuvee="Brut", seuil=6)
    cave.ajouter_bouteilles(v1, 1, {"prix_achat": 20})
    i18n.definir_langue("fr")
    from vendemiaire.ui.achats import DialogueAchats, textes
    lignes = achats.liste_achats(cave)
    html = achats.html_liste(lignes, "Liste d'achats", textes(), i18n.argent)
    assert "Brut" in html and "1 en cave, seuil 6" in html and "&#9744;" in html
    assert achats.exporter_csv(lignes, tmp_path / "l.csv") == 1
    assert "reassort;Domaine Témoin · Brut" in (tmp_path / "l.csv").read_text(encoding="utf-8-sig")
    d = DialogueAchats(cave)
    assert "1 vins à réassortir" in d.bilan.text() and d.b_pdf.isEnabled()
    from vendemiaire.documents.qt_pdf import html_vers_pdf
    html_vers_pdf(html, tmp_path / "l.pdf")
    assert (tmp_path / "l.pdf").read_bytes()[:4] == b"%PDF"
    d.deleteLater()


# ------------------------------------------------------------------ alertes de prix
def test_alertes_de_prix_saisie_validite_et_valeur_du_vin(cave):
    e = cave.ajouter_envie({"producteur": "Clos Rêvé", "cuvee": "VV", "prix_max": 50})
    with pytest.raises(ValueError):
        achats.ajouter_prix(cave, e, 40, "  ")              # source obligatoire
    achats.ajouter_prix(cave, e, 65, "Caviste", date.today().isoformat())
    assert achats.alertes_prix(cave) == []
    vieux = (date.today() - timedelta(days=achats.JOURS_VALIDITE + 5)).isoformat()
    achats.ajouter_prix(cave, e, 30, "Ancien catalogue", vieux)
    assert achats.alertes_prix(cave) == []                   # trop ancien : plus d'alerte
    achats.ajouter_prix(cave, e, 48, "Salon", date.today().isoformat())
    a = achats.alertes_prix(cave)
    assert [(x["prix"], x["source"], x["origine"]) for x in a] == [(48, "Salon", "releve")]
    # envie liée à un vin : sa dernière valeur saisie compte aussi
    v = _vin(cave, cuvee="Lié")
    e2 = cave.ajouter_envie({"vin_id": v, "prix_max": 30})
    cave.ajouter_valeur_complete(v, 28, "Cote d'un caviste", date.today().isoformat())
    assert any(x["envie_id"] == e2 and x["origine"] == "valeur" for x in achats.alertes_prix(cave))
    cave.satisfaire_envie(e)
    assert not any(x["envie_id"] == e for x in achats.alertes_prix(cave))


def test_import_csv_de_prix_releves(cave, tmp_path):
    e1 = cave.ajouter_envie({"producteur": "Château Témoin", "cuvee": "Grand vin", "millesime": 2016,
                             "prix_max": 90})
    e2 = cave.ajouter_envie({"producteur": "Clos Rêvé", "cuvee": "VV"})
    f = tmp_path / "prix.csv"
    f.write_text("producteur;cuvee;millesime;prix;date;source;url\n"
                 f"Chateau temoin;GRAND VIN;2016;85,00 €;{date.today().isoformat()};Caviste A;https://exemple.org/a\n"
                 "Château Témoin;Grand vin;2015;70;2026-10-01;Caviste B;\n"
                 f"Inconnu;Rien;;12;;Caviste C;\n"
                 f"envie;;;;;;\n", encoding="utf-8")
    f2 = tmp_path / "par_id.csv"
    f2.write_text(f"envie,prix,source\n{e2},33,Foire aux vins\n", encoding="utf-8")
    r = achats.importer_prix_csv(cave, f)
    assert r.importes == 1 and len(r.non_rapproches) == 2 and len(r.erreurs) == 1
    assert achats.prix_releves(cave, e1)[0]["url"] == "https://exemple.org/a"
    assert achats.importer_prix_csv(cave, f2).importes == 1
    assert achats.prix_releves(cave, e2)[0]["source"] == "Foire aux vins"
    assert [a["envie_id"] for a in achats.alertes_prix(cave)] == [e1]


def test_vue_envies_alerte_doree_et_dialogue_prix(app, cave):
    i18n.definir_langue("fr")
    from vendemiaire.ui.envies import DialoguePrix, VueEnvies
    e = cave.ajouter_envie({"producteur": "Clos Rêvé", "cuvee": "VV", "prix_max": 50})
    v = VueEnvies(cave)
    assert v.table.columnCount() == 8 and v.table.item(0, 7).text() == ""
    envie = v.lignes[0]
    d = DialoguePrix(cave, envie, v)
    d.montant.setValue(45)
    d.source.setText("Salon des vignerons")
    d.ajouter()
    assert d.modifie and d.table.rowCount() == 1
    v.rafraichir()
    assert "prix atteint" in v.table.item(0, 7).text()
    assert v.table.item(0, 0).background().color().name().lower() == "#f3d58a"
    assert "Salon des vignerons" in v.table.item(0, 6).text()
    d.deleteLater()
    v.deleteLater()
    assert e


# ------------------------------------------------------------------ photos du livre de cave
def test_photos_du_livre_de_cave(app, cave, tmp_path):
    i18n.definir_langue("fr")
    v = _vin(cave)
    bid = cave.ajouter_bouteilles(v, 1)[0]
    mid = cave.sortir(bid, "sortie_bue", occasion="Anniversaire")
    i1 = cave.ajouter_photo_mouvement(mid, _image(tmp_path / "a.png"))
    cave.ajouter_photo_mouvement(mid, _image(tmp_path / "b.png", "#C99A3B"))
    assert cave.nombre_photos_mouvements() == {mid: 2}
    im = cave.image(i1)
    assert (im["type"], im["vin_id"], im["principale"]) == ("moment", v, 0)
    assert cave.image_principale(v) is None                 # la pochette reste l'étiquette
    from vendemiaire.ui.livre import VueLivre
    vue = VueLivre(cave)
    ligne = next(r for r, m in enumerate(vue.lignes) if m["id"] == mid)
    assert "2" in vue.table.item(ligne, 4).text()
    vue.table.setCurrentCell(ligne, 0)
    assert vue.photos.liste.count() == 2 and vue.photos.b_ajouter.isEnabled()
    assert vue.photos.ajouter_fichiers([str(_image(tmp_path / "c.png", "#2A1A14")), "x.txt"]) == 1
    assert cave.nombre_photos_mouvements()[mid] == 3
    vue.photos.liste.setCurrentRow(0)
    iid = vue.photos._choisie()
    cave.supprimer_image(iid)
    vue.photos.afficher(vue.lignes[ligne])
    assert vue.photos.liste.count() == 2
    vue.deleteLater()


def test_demonstration_avec_alerte_et_photos(cave_demo):
    assert [a["origine"] for a in achats.alertes_prix(cave_demo)] == ["releve"]
    assert any(l.origine == "reassort" for l in achats.liste_achats(cave_demo))


# ------------------------------------------------------------------ outils embarqués
def _faux_outil(dossier: Path, nom: str, script: str) -> Path:
    exe = dossier / nom / "bin" / nom
    exe.parent.mkdir(parents=True)
    exe.write_text("#!/bin/sh\n" + script)
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return exe


@pytest.mark.skipif(sys.platform == "win32", reason="scripts shell")
def test_tesseract_du_paquet_avec_ses_modeles(tmp_path, monkeypatch):
    outils = tmp_path / "outils"
    journal = tmp_path / "args.txt"
    exe = _faux_outil(outils, "tesseract",
                      f'echo "$@" >> "{journal}"\n'
                      'case "$*" in *--list-langs*) printf "List of available languages (2):\\neng\\nfra\\n";; esac\n')
    (outils / "tesseract" / "tessdata").mkdir()
    monkeypatch.setenv("VENDEMIAIRE_OUTILS", str(outils))
    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    from vendemiaire import ocr, outils_embarques
    ocr.definir_chemin(None)
    assert ocr.moteur() == str(exe) and outils_embarques.est_embarque(ocr.moteur())
    assert ocr.langues() == ["eng", "fra"]
    assert f"--tessdata-dir {outils / 'tesseract' / 'tessdata'} --list-langs" in journal.read_text()
    img = tmp_path / "e.png"
    _image(img)
    ocr.lire(str(img), "eng")
    derniere = journal.read_text().splitlines()[-1]
    # pas de fichier de configuration « tsv » (absent du tessdata du paquet) : une variable
    assert derniere.endswith("-c tessedit_create_tsv=1") and "--tessdata-dir" in derniere
    monkeypatch.setenv("VENDEMIAIRE_OUTILS", str(tmp_path / "rien"))
    assert ocr.moteur() != str(exe)                          # sans paquet : celui du système


@pytest.mark.skipif(sys.platform == "win32", reason="scripts shell")
def test_tectonic_du_paquet_hors_ligne_puis_reseau(tmp_path, monkeypatch):
    """Le Tectonic embarqué compile d'abord SANS réseau sur une copie de son
    cache dans le profil (jamais dans le dossier d'installation) ; un paquet
    absent du cache déclenche une seconde tentative avec réseau."""
    outils = tmp_path / "outils"
    journal = tmp_path / "args.txt"
    _faux_outil(outils, "tectonic",
                f'echo "$TECTONIC_CACHE_DIR $@" >> "{journal}"\n'
                'case "$*" in *--only-cached*) test -f "$TECTONIC_CACHE_DIR/paquet.sty" || exit 1;; esac\n'
                'echo "%PDF-1.5" > document.pdf\n')
    modele = outils / "tectonic" / "cache"
    modele.mkdir()
    (modele / "format.fmt").write_text("f")
    monkeypatch.setenv("VENDEMIAIRE_OUTILS", str(outils))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "profil"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "profil"))
    monkeypatch.delenv("VENDEMIAIRE_LATEX", raising=False)
    from vendemiaire import chemins
    monkeypatch.setattr(chemins.Path, "home", lambda: tmp_path / "maison")
    from vendemiaire.documents import latex
    m = latex.trouver_moteur()
    assert m.nom == "tectonic" and str(outils) in m.chemin
    r = latex.compiler("x", tmp_path / "a.pdf", moteur=m)
    lignes = journal.read_text().splitlines()
    copie = chemins.dossier_profil() / "cache" / "tectonic"
    assert lignes[0].startswith(str(copie)) and "--only-cached" in lignes[0]
    assert "--only-cached" not in lignes[1] and r.pdf.is_file()           # 2e tentative, réseau
    assert (copie / "format.fmt").is_file() and not (modele / ".modele").exists()
    with pytest.raises(latex.ErreurLatex):
        latex.compiler("x", tmp_path / "b.pdf", moteur=m, reseau=False)
    (modele / "paquet.sty").write_text("p")                  # nouveau modèle : la copie est refaite
    journal.unlink()
    latex.compiler("x", tmp_path / "c.pdf", moteur=m, reseau=False)
    assert len(journal.read_text().splitlines()) == 1 and (copie / "paquet.sty").is_file()


def test_kit_json_embarque_tesseract_et_tectonic_partout():
    import json
    kit = json.loads((Path(__file__).resolve().parent.parent / "kit.json").read_text(encoding="utf-8"))
    outils = {o["nom"]: o for o in kit["outils"]}
    assert set(outils) == {"tesseract", "tectonic"}
    assert outils["tesseract"]["conda"] and {f["vers"] for f in outils["tesseract"]["fichiers"]} == {
        "tessdata/fra.traineddata", "tessdata/eng.traineddata"}
    assert all(len(f["sha256"]) == 64 for f in outils["tesseract"]["fichiers"])
    archives = outils["tectonic"]["archives"]
    assert set(archives) == {"windows-x86_64", "macos-arm64", "macos-x86_64", "linux-x86_64", "linux-arm64"}
    assert all(len(a["sha256"]) == 64 and "tectonic-typesetting/tectonic" in a["url"] for a in archives.values())
    docs = [d["tex"] for d in outils["tectonic"]["prechauffer"]["documents"]]
    assert "docs/manuel-fr.tex" in docs and "docs/manuel-en.tex" in docs
    assert "--only-cached" in outils["tectonic"]["prechauffer"]["controle"]
    racine = Path(__file__).resolve().parent.parent
    assert len(list((racine / "docs" / "prechauffage").glob("*/document.tex"))) >= 5
    assert kit["essai_embarquees"] == "vendemiaire.outils_embarques:essai"


# ------------------------------------------------------------------ clavier
@pytest.fixture
def fenetre5(app, cave_demo):
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


def test_clavier_onglets_raccourcis_et_focus(fenetre5, app):
    w = fenetre5
    assert len(w._raccourcis) == 10
    assert [r.key().toString() for r in w._raccourcis][:3] == ["Ctrl+1", "Ctrl+2", "Ctrl+3"]
    w._raccourcis[4].activated.emit()
    assert w.onglets.currentWidget() is w.livre
    w._raccourcis[9].activated.emit()
    assert w.onglets.currentWidget() is w.conditions
    raccourcis = {a.text(): a.shortcut().toString() for m in w.findChildren(QtWidgets.QMenu)
                  for a in m.actions()}
    assert raccourcis[i18n.tr("menu.liste_achats")] == "Ctrl+Shift+L"
    assert raccourcis[i18n.tr("menu.sortir")] == "Ctrl+Shift+D"
    # aucun bouton hors d'atteinte du clavier
    for b in w.findChildren(QtWidgets.QPushButton):
        assert b.focusPolicy() & QtCore.Qt.FocusPolicy.TabFocus, b.text()
    from vendemiaire import style
    assert "QPushButton:focus" in style.FEUILLE and "QTableView:focus" in style.FEUILLE


def test_plan_au_clavier(fenetre5, app):
    w = fenetre5
    plan = w.plan
    casier = w.cave.base.valeur("SELECT emplacement_id FROM bouteille WHERE statut='en_cave' AND rangee IS NOT NULL "
                                "GROUP BY emplacement_id ORDER BY COUNT(*) DESC LIMIT 1")
    plan.afficher_casier(casier)
    assert plan.pastilles
    plan.vue.setFocus()
    QtCore.QCoreApplication.sendEvent(plan.vue, QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress,
                                                                 QtCore.Qt.Key.Key_Right,
                                                                 QtCore.Qt.KeyboardModifier.NoModifier))
    choisies = plan._choisies()
    assert len(choisies) == 1
    p = choisies[0]
    e = w.cave.emplacement(casier)
    # une case voisine dans la grille, libre ou non : échange si prise
    for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        r, c = p.rangee + dr, p.colonne + dc
        if 1 <= r <= e["rangees"] and 1 <= c <= e["colonnes"]:
            break
    avant = (p.rangee, p.colonne)
    bid = p.bid
    assert plan.deplacer_d_une_case(dr, dc)
    b = w.cave.bouteille(bid)
    assert (b["rangee"], b["colonne"]) == (avant[0] + dr, avant[1] + dc)
    assert plan._choisies()[0].bid == bid


# ------------------------------------------------------------------ robustesse
def test_base_vide_tous_les_onglets_et_dialogues(app, cave):
    i18n.definir_langue("fr")
    from vendemiaire.ui.achats import DialogueAchats
    from vendemiaire.ui.fenetre import FenetrePrincipale
    QtCore.QSettings().clear()
    w = FenetrePrincipale(cave, aide_kit=False)
    w.show()
    for i in range(w.onglets.count()):
        w.onglets.setCurrentIndex(i)
        app.processEvents()
    w.tout_rafraichir()
    d = DialogueAchats(cave, w)
    assert "Rien à acheter" in d.apercu.toPlainText() and not d.b_pdf.isEnabled()
    d.deleteLater()
    assert w.livre.photos.liste.count() == 0 and not w.livre.photos.b_ajouter.isEnabled()
    w.minuteur.stop()
    w.hide()
    w.deleteLater()
    app.processEvents()


def test_grosse_cave_sans_gel(app, tmp_path):
    """Une cave de 5 000 bouteilles (la mesure à 20 000 : outils/grosse_cave.py)
    s'ouvre, se filtre et se résume sans geler l'interface."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "outils"))
    import grosse_cave
    cave = grosse_cave.generer(tmp_path / "grosse.db", 5000)
    mesures = grosse_cave.mesurer(cave, app)
    assert mesures["bouteilles"] == 5000
    for cle, duree in mesures["durees"].items():
        assert duree < 15, (cle, duree)
    cave.base.fermer()


def test_manuels_a_la_version_et_au_format_maison():
    racine = Path(__file__).resolve().parent.parent
    version = (racine / "VERSION").read_text(encoding="utf-8").strip()
    for lg in ("fr", "en"):
        tex = (racine / "docs" / f"manuel-{lg}.tex").read_text(encoding="utf-8")
        assert "\\newcommand{\\VersionManuel}{" + version + "}" in tex
        assert "\\input{manuel-preambule.tex}" in tex
        for capture in __import__("re").findall(r"\\capture(?:\[[^]]*\])?\{([^}]+)\}", tex):
            assert (racine / "docs" / "captures" / capture).is_file(), capture
            assert capture.startswith(lg + "-"), capture
    pre = (racine / "docs" / "manuel-preambule.tex").read_text(encoding="utf-8")
    for motif in ("fontawesome5", "tcolorbox", "titlesec", "needspace", "fancyhdr", "1C6DB4", "B5382B"):
        assert motif in pre


def test_cave_de_demonstration_dans_une_autre_fenetre(fenetre5):
    exe, args = fenetre5.commande_demonstration()
    assert args[1:3] == ["--demo", "--lang"] and args[0].endswith("run.py")
    assert any(a.text() == i18n.tr("menu.demonstration") for m in fenetre5.findChildren(QtWidgets.QMenu)
               for a in m.actions())
