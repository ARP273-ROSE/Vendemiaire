# -*- coding: utf-8 -*-
"""Interface de la phase 2 (sous Xvfb en CI) : identification avec candidats et
confirmation, photos (recadrage auto, original gardé), mur d'étiquettes,
liste d'envies, critiques, conditions, inventaire, bases de référence — et
aucun français dans l'interface anglaise de ces fenêtres."""
import re

import pytest
from PyQt6 import QtCore, QtWidgets

from vendemiaire import demo, demo_photos, i18n, images, reseau


@pytest.fixture
def fenetre(app, cave_demo):
    i18n.definir_langue("fr")
    from vendemiaire.ui.fenetre import FenetrePrincipale
    QtCore.QSettings().clear()
    demo.references_demo(cave_demo)
    w = FenetrePrincipale(cave_demo, aide_kit=False)
    w.show()
    app.processEvents()
    yield w
    w.minuteur.stop()
    w.hide()
    w.deleteLater()
    app.processEvents()


def _textes(w) -> list[str]:
    t = [w.windowTitle()]
    for b in w.findChildren(QtWidgets.QAbstractButton):
        t.append(b.text())
    for g in w.findChildren(QtWidgets.QGroupBox):
        t.append(g.title())
    for e in w.findChildren(QtWidgets.QLineEdit):
        t.append(e.placeholderText())
    for l in w.findChildren(QtWidgets.QLabel):
        t.append(l.text())
    for v in w.findChildren(QtWidgets.QTableWidget):
        t += [v.horizontalHeaderItem(c).text() for c in range(v.columnCount()) if v.horizontalHeaderItem(c)]
    return [x for x in t if x]


FRANCAIS = re.compile(r"[éèàçêôûùîœ«»]|\b(le|la|les|des|du|une|vin|cave|fermer|annuler)\b", re.I)


def _sans_francais(textes, admis=("Vendémiaire", "Cuvée", "cuvée", "Rosé", "Château", "Chênes",
                                  "Margaux", "Pauillac", "Liv-ex", '"Le vin"')):
    fautes = []
    for x in textes:
        nu = re.sub(r"<[^>]+>", " ", x)
        for a in admis:
            nu = nu.replace(a, "")
        if FRANCAIS.search(nu):
            fautes.append(x)
    return fautes


def _vin(cave, nom):
    return cave.base.valeur("SELECT v.id FROM vin v JOIN producteur p ON p.id=v.producteur_id "
                            "WHERE p.nom=? ORDER BY v.millesime LIMIT 1", (nom,))


def test_onglets_phase2(fenetre):
    noms = [fenetre.onglets.tabText(i) for i in range(fenetre.onglets.count())]
    assert noms[2] == "Mur d'étiquettes" and "Liste d'envies" in noms and "Conditions de cave" in noms
    fenetre.onglets.setCurrentWidget(fenetre.mur)
    assert fenetre.mur.modele.rowCount() > 30
    assert fenetre.envies.table.rowCount() == 2                       # envies de la démonstration
    assert fenetre.conditions.courbe.mesures and "mesures" in fenetre.conditions.resume.text()
    menus = [a.text() for a in fenetre.menuBar().actions()]
    assert "&Références" in menus


def test_identifier_puis_confirmer(app, fenetre):
    from vendemiaire.ui.identifier import DialogueIdentifier
    cave = fenetre.cave
    vin = _vin(cave, "Château des Trois Chênes")
    d = DialogueIdentifier(cave, vin, parent=fenetre)
    d.chercher_lwin()
    assert d.decision.motif == "sur"
    c = d.candidat()
    assert c is not None and c.libelle.startswith("Château des Trois Chênes")
    assert "domaine" in d.explication.toPlainText()
    etats = {d.t_champs.item(i, 0).data(QtCore.Qt.ItemDataRole.UserRole): d.t_champs.item(i, 3).text()
             for i in range(d.t_champs.rowCount())}
    assert etats["lwin"] == "rempli si coché" and etats["appellation"] == "saisi à la main : intouchable" \
        or etats["appellation"] == "identique"
    d.confirmer()
    assert d.result() == QtWidgets.QDialog.DialogCode.Accepted
    v = cave.vin(vin)
    assert v["lwin"] == c.identifiant and v["appellation"] == "Pauillac"
    assert cave.identifiants(vin)[0]["explication"].startswith("+ domaine")
    fenetre.vue_cave.fiche.afficher(vin)
    assert "lwin" in fenetre.vue_cave.fiche.references.text()
    assert fenetre.vue_cave.fiche.t_journal.rowCount() >= 1


def test_recherche_en_ligne_demande_l_accord(app, fenetre, monkeypatch):
    from vendemiaire.ui import identifier
    reseau.autoriser(False)
    monkeypatch.setattr(QtWidgets.QMessageBox, "question",
                        lambda *a, **k: QtWidgets.QMessageBox.StandardButton.No)
    d = identifier.DialogueIdentifier(fenetre.cave, _vin(fenetre.cave, "Domaine Petit-Roc"), parent=fenetre)
    d.chercher_wikidata("producteur")
    assert d._travail is None and not reseau.autorise()               # refusé : rien n'est parti


def test_identifier_par_code_barres_reseau_simule(app, fenetre, monkeypatch):
    import json
    from vendemiaire.ui import identifier, travail
    produit = {"status": 1, "product": {"code": "3012345678902", "product_name": "Vin exemple",
                                        "brands": "Domaine Exemple", "nutriments": {"alcohol_100g": 12.5}}}
    faux = reseau.Client(transport=lambda url, e, d: reseau.Reponse(200, {}, json.dumps(produit).encode()),
                         dormir=lambda s: None, ignorer_accord=True)
    monkeypatch.setattr(reseau, "_client", faux)
    reseau.autoriser(True)
    try:
        cave = fenetre.cave
        vin = _vin(cave, "Domaine du Grand Mûrier")
        d = identifier.DialogueIdentifier(cave, vin, {"ean": "3012345678902"}, parent=fenetre)
        d.chercher_off()
        travail.attendre(d._travail)
        assert d.decision.motif == "ean" and d.candidat().identifiant == "3012345678902"
        d.confirmer()
        assert cave.vin(vin)["ean"] == "3012345678902"
        assert cave.vin(vin)["degre"] == 13.0                        # degré déjà rempli : gardé
    finally:
        reseau.autoriser(False)


def test_photos_recadrage_et_mur(app, fenetre, tmp_path, monkeypatch):
    from vendemiaire.ui import photos
    cave = fenetre.cave
    vin = _vin(cave, "Domaine Petit-Roc")
    chemin, vrais = demo_photos.generer(dict(cave.vin(vin)), tmp_path / "p.jpg")
    vus = {}

    def executer(dialogue):
        vus["coins"] = list(dialogue.vue.coins)
        vus["etat"] = dialogue.etat.text()
        dialogue.accepter()
        return QtWidgets.QDialog.DialogCode.Accepted
    monkeypatch.setattr(photos.DialogueRetouche, "exec", executer)
    fenetre.photo_deposee((vin, str(chemin)))
    assert "Étiquette trouvée" in vus["etat"]
    im = cave.images(vin)[0]
    assert im["fichier_original"] and im["retouche"] and '"auto": true' in im["retouche"]
    plat = images.charger(cave.chemin_image(im["fichier"]))
    assert abs(plat.width() / plat.height() - 0.75) < 0.08
    d = photos.DialoguePhotos(cave, vin, fenetre)
    assert d.liste.count() == 1 and "photo d'origine gardée" in d.credit.text()
    d.close()
    fenetre.onglets.setCurrentWidget(fenetre.mur)
    fenetre.mur.rafraichir()
    assert "1 photos" in fenetre.mur.compte.text()


def test_envies_critiques_inventaire_references(app, fenetre, monkeypatch):
    from vendemiaire.ui.critiques import DialogueCritique, DialogueValeur
    from vendemiaire.ui.envies import DialogueEnvie
    from vendemiaire.ui.inventaire import DialogueInventaire
    from vendemiaire.ui.references import DialogueReferences
    cave = fenetre.cave
    vin = _vin(cave, "Domaine Marchand-Lavaux")
    e = DialogueEnvie(cave, None, fenetre, vin_id=vin)
    assert e.producteur.text() == "Domaine Marchand-Lavaux"
    e.prix.setValue(80)
    e.accepter()
    fenetre.envies.rafraichir()
    assert fenetre.envies.table.rowCount() == 3
    c = DialogueCritique(cave, vin, None, fenetre)
    c.critique.setCurrentIndex(c.critique.findData("RP"))
    c.note.setValue(93)
    assert c.echelle.currentData() == "100" and "18" in c.equiv.text()
    c.accepter()
    assert cave.notes_critiques(vin)[0]["critique"] == "RP"
    v = DialogueValeur(cave, vin, fenetre)
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", lambda *a, **k: None)
    v.montant.setValue(150)
    v.accepter()                                           # sans source : refusé
    assert v.result() != QtWidgets.QDialog.DialogCode.Accepted
    v.source.setText("caviste")
    v.accepter()
    assert cave.valeurs(vin)[0]["source"] == "caviste"
    casier = cave.base.valeur("SELECT id FROM emplacement WHERE nom='Casier A'")
    inv = DialogueInventaire(cave, casier, fenetre)
    n = inv.liste.count()
    assert n > 0
    code = inv.liste.item(0).data(QtCore.Qt.ItemDataRole.UserRole + 1)
    inv.code.setText(code)
    inv.lire_code()
    assert inv.liste.item(0).checkState() == QtCore.Qt.CheckState.Checked
    inv.enregistrer()
    assert inv.b_manquantes.isEnabled() and str(n - 1) in inv.resultat.text()
    r = DialogueReferences(cave, fenetre)
    assert "vins dans la copie locale" in r.etat_lwin.text() and "INAO" in r.etat_registres.text()


def test_saisie_propose_l_orthographe_officielle(app, fenetre):
    from vendemiaire.ui.saisie import DialogueVin
    d = DialogueVin(fenetre.cave, None, fenetre)
    d.appellation.setText("chateauneuf du pape")
    d._verifier_appellation()
    assert "Châteauneuf-du-Pape" in d.appellation_officielle.text()
    d._corriger_appellation("corriger")
    assert d.appellation.text() == "Châteauneuf-du-Pape"


def test_fenetres_phase2_en_anglais(app, fenetre):
    from vendemiaire.ui.critiques import DialogueCritique, DialogueValeur
    from vendemiaire.ui.envies import DialogueEnvie
    from vendemiaire.ui.identifier import DialogueIdentifier
    from vendemiaire.ui.inventaire import DialogueInventaire
    from vendemiaire.ui.photos import DialoguePhotos, DialogueRetouche
    from vendemiaire.ui.references import DialogueReferences
    fenetre.changer_langue("en")
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete.value)
    app.processEvents()
    try:
        cave = fenetre.cave
        vin = _vin(cave, "Château des Trois Chênes")
        img = images.charger(demo_photos.generer(dict(cave.vin(vin)), cave.base.chemin.parent / "x.jpg")[0])
        dialogues = [DialogueIdentifier(cave, vin, parent=fenetre), DialogueCritique(cave, vin, None, fenetre),
                     DialogueValeur(cave, vin, fenetre), DialogueEnvie(cave, None, fenetre),
                     DialogueInventaire(cave, None, fenetre), DialogueReferences(cave, fenetre),
                     DialoguePhotos(cave, vin, fenetre), DialogueRetouche(img, parent=fenetre)]
        dialogues[0].chercher_lwin()
        textes = []
        for d in dialogues:
            textes += [x for x in _textes(d) if not x.startswith(("Château", "Domaine", "Vendemiaire/"))]
        for w in (fenetre.mur, fenetre.envies, fenetre.conditions):
            textes += _textes(w)
        textes = [x for x in textes if "Casier" not in x and "Cave de" not in x and "Mur nord" not in x]
        fautes = [x for x in _sans_francais(textes)
                  if not re.search(r"Domaine|Château|Maison|Clos|Marchand|Trois|Chênes|Combe|Aubertin", x)]
        assert not fautes, "\n".join(fautes)
        assert not [x for x in textes if re.match(r"^<[a-z_]+\.[a-z0-9_]+>$", x)]
    finally:
        fenetre.changer_langue("fr")
