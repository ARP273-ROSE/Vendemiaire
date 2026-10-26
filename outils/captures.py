# -*- coding: utf-8 -*-
"""Captures d'écran RÉELLES de l'interface (cave de démonstration), FR et EN,
pour le README et le manuel. À lancer sous un vrai serveur X (Xvfb) :

    xvfb-run -a -s "-screen 0 1920x1080x24" python outils/captures.py
"""
import os
import sys
import tempfile
from pathlib import Path

from PyQt6 import QtCore, QtWidgets  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
SORTIE = RACINE / "docs" / "captures"


def phase2(app, w, cave, langue, attendre):
    """Captures de la phase 2 : mur, identification, photo, envies, conditions,
    critiques, inventaire, bases de référence."""
    from PyQt6 import QtWidgets
    from vendemiaire import demo_photos, images
    from vendemiaire.ui.critiques import DialogueCritique
    from vendemiaire.ui.identifier import DialogueIdentifier
    from vendemiaire.ui.inventaire import DialogueInventaire
    from vendemiaire.ui.photos import DialogueRetouche
    from vendemiaire.ui.references import DialogueReferences

    def capture(widget, nom):
        widget.show()
        attendre()
        widget.grab().save(str(SORTIE / f"{langue}-{nom}.png"))

    w.onglets.setCurrentWidget(w.mur)
    w.mur.rafraichir()
    attendre()
    w.grab().save(str(SORTIE / f"{langue}-mur.png"))
    for vue, nom in ((w.envies, "envies"), (w.conditions, "conditions")):
        w.onglets.setCurrentWidget(vue)
        attendre()
        w.grab().save(str(SORTIE / f"{langue}-{nom}.png"))

    vin = cave.base.valeur("SELECT v.id FROM vin v JOIN producteur p ON p.id=v.producteur_id "
                           "WHERE p.nom='Château des Trois Chênes' ORDER BY millesime LIMIT 1")
    # une photo prise de travers : détection des bords, redressement, OCR
    photo, _ = demo_photos.generer(dict(cave.vin(vin)), SORTIE.parent / "_photo_demo.jpg", graine=5)
    r = DialogueRetouche(images.charger(photo), parent=w)
    r.resize(1180, 760)
    capture(r, "retouche")
    if r.b_ocr.isEnabled():
        r.lire_texte()
        from vendemiaire.ui import travail
        travail.attendre(r._travail)
        capture(r, "retouche-ocr")
    r.close()
    photo.unlink()
    # identification : candidats, score expliqué, champs proposés
    d = DialogueIdentifier(cave, vin, parent=w)
    d.chercher_lwin()
    capture(d, "identifier")
    d.confirmer()
    w.onglets.setCurrentWidget(w.vue_cave)
    w.vue_cave.statut.setCurrentIndex(1)
    w.tout_rafraichir(vin)
    attendre()
    fiche = w.vue_cave.fiche
    fiche.verticalScrollBar().setValue(fiche.g_references.y() - 40)
    attendre()
    w.grab().save(str(SORTIE / f"{langue}-fiche-references.png"))
    fiche.verticalScrollBar().setValue(0)
    c = DialogueCritique(cave, vin, None, w)
    c.critique.setCurrentIndex(c.critique.findData("DEC"))
    c.note.setValue(93)
    capture(c, "critique")
    c.close()
    casier = cave.base.valeur("SELECT id FROM emplacement WHERE nom='Clayette 1'")
    inv = DialogueInventaire(cave, casier, w)
    for i in range(max(0, inv.liste.count() - 1)):
        inv.liste.item(i).setCheckState(QtCore.Qt.CheckState.Checked)
    inv.enregistrer()
    capture(inv, "inventaire")
    inv.close()
    ref = DialogueReferences(cave, w)
    capture(ref, "references")
    ref.close()
    QtWidgets.QApplication.processEvents()


def phase3(app, w, cave, langue, attendre):
    """Captures de la phase 3 : règles du dossier « Le vin » dans la fiche,
    tableau de bord (garde, courbe d'apogée), « ce soir », fiche imprimable,
    niveaux, dégustation et roue des arômes, défauts, bouteille entamée, règles."""
    from vendemiaire.ui.ce_soir import DialogueEntamer, DialogueFicheCeSoir
    from vendemiaire.ui.degustation import DialogueDegustation, DialogueDiagnostic
    from vendemiaire.ui.regles_ui import DialogueRegles
    from vendemiaire.ui.saisie import DialogueBouteille

    def capture(widget, nom):
        widget.show()
        attendre()
        widget.grab().save(str(SORTIE / f"{langue}-{nom}.png"))

    vin = cave.base.valeur("SELECT v.id FROM vin v JOIN producteur p ON p.id=v.producteur_id "
                           "WHERE p.nom='Château des Trois Chênes' AND v.cuvee='Grand vin' AND EXISTS("
                           "SELECT 1 FROM bouteille b WHERE b.vin_id=v.id AND b.statut='en_cave') "
                           "ORDER BY millesime LIMIT 1")
    bid = cave.base.valeur("SELECT id FROM bouteille WHERE vin_id=? AND statut='en_cave' ORDER BY id", (vin,))
    cave.enregistrer_degustation({"vin_id": vin, "robe": "grenat, reflets tuilés" if langue == "fr" else
                                  "garnet, brick rim", "aromes": "P.FNR:cassis;S.BOI:cèdre;T.BTR:cuir;T.BTR:tabac",
                                  "note": 17.5, "echelle": "20"})
    # la fiche : panneau des règles
    w.onglets.setCurrentWidget(w.vue_cave)
    w.vue_cave.statut.setCurrentIndex(1)
    w.tout_rafraichir(vin)
    attendre()
    fiche = w.vue_cave.fiche
    fiche.verticalScrollBar().setValue(fiche.g_fenetres.y() - 10)
    attendre()
    w.grab().save(str(SORTIE / f"{langue}-fiche-regles.png"))
    fiche.verticalScrollBar().setValue(0)
    # tableau de bord : garde et courbe d'apogée
    w.onglets.setCurrentWidget(w.tableau)
    w.tableau.rafraichir()
    attendre()
    w.tableau.verticalScrollBar().setValue(w.tableau.g_garde.y() - 10)
    attendre()
    w.grab().save(str(SORTIE / f"{langue}-garde.png"))
    w.tableau.verticalScrollBar().setValue(0)
    # que boire ce soir ?
    w.onglets.setCurrentWidget(w.ce_soir)
    w.ce_soir.plat.setText("agneau" if langue == "fr" else "lamb")
    attendre()
    w.grab().save(str(SORTIE / f"{langue}-ce-soir.png"))
    d = DialogueFicheCeSoir(cave, w.ce_soir.vins_choisis()[:2], w.ce_soir.plat.text(), parent=w)
    capture(d, "fiche-ce-soir")
    d.close()
    b = DialogueBouteille(cave, bid, w)
    b.resize(760, 640)
    onglets = b.findChild(QtWidgets.QTabWidget)
    onglets.setCurrentIndex(1)
    b.niveau.setCurrentIndex(b.niveau.findData("HS"))
    capture(b, "niveaux")
    b.close()
    g = DialogueDegustation(cave, vin, cave.degustations(vin)[0], parent=w)
    capture(g, "degustation")
    g.close()
    x = DialogueDiagnostic(cave, bid, w)
    x.recherche.setText("carton mouillé" if langue == "fr" else "wet cardboard")
    capture(x, "defauts")
    x.close()
    e = DialogueEntamer(cave, bid, w)
    capture(e, "entamer")
    e.close()
    r = DialogueRegles(w)
    capture(r, "regles")
    r.close()
    QtWidgets.QApplication.processEvents()


def main() -> int:
    from PyQt6 import QtWidgets
    temp = Path(tempfile.mkdtemp())
    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.Format.IniFormat)
    QtCore.QSettings.setPath(QtCore.QSettings.Format.IniFormat,
                             QtCore.QSettings.Scope.UserScope, str(temp))
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName("VendemiaireCaptures")
    app.setApplicationName("VendemiaireCaptures")
    from vendemiaire import demo, i18n, style
    from vendemiaire.ui.fenetre import FenetrePrincipale
    from vendemiaire.ui.saisie import DialogueBouteille, DialogueSortie, DialogueVin
    style.appliquer(app)
    SORTIE.mkdir(parents=True, exist_ok=True)

    def attendre():
        for _ in range(8):
            app.processEvents()

    for langue in ("fr", "en"):
        i18n.definir_langue(langue)
        cave = demo.generer(temp / f"demo-{langue}.db")
        demo.references_demo(cave)
        demo.photos_demo(cave, 10)
        w = FenetrePrincipale(cave, aide_kit=False)
        w.statusBar().showMessage("")
        w.resize(1440, 900)
        w.show()
        attendre()
        noms = ["tableau-de-bord", "cave", "plan", "livre"]
        for i, nom in enumerate(noms):
            w.onglets.setCurrentIndex(i)
            if nom == "cave":
                vue = w.vue_cave
                vue.recherche.setText("")
                vid = cave.base.valeur("SELECT v.id FROM vin v JOIN producteur p ON p.id=v.producteur_id "
                                       "WHERE p.nom LIKE 'Domaine Marchand%' ORDER BY millesime LIMIT 1")
                vue.selectionner(vid)
            attendre()
            w.grab().save(str(SORTIE / f"{langue}-{nom}.png"))
        w.onglets.setCurrentIndex(1)
        vid = w.vue_cave.vin_courant()
        bid = cave.base.valeur("SELECT id FROM bouteille WHERE vin_id=? AND statut='en_cave'", (vid,))
        for nom, d in (("saisie-vin", DialogueVin(cave, vid, w)),
                       ("sortie", DialogueSortie(cave, bid, w)),
                       ("bouteille", DialogueBouteille(cave, bid, w))):
            if nom == "sortie":
                d.occasion.setText("Dîner entre amis" if langue == "fr" else "Dinner with friends")
                d.plat.setText("Bœuf bourguignon" if langue == "fr" else "Beef bourguignon")
                d.note.setValue(17.5)
            d.show()
            attendre()
            d.grab().save(str(SORTIE / f"{langue}-{nom}.png"))
            d.close()
        phase2(app, w, cave, langue, attendre)
        phase3(app, w, cave, langue, attendre)
        w.minuteur.stop()
        w.close()
        cave.fermer_references()
        cave.base.fermer()
    print(f"captures écrites dans {SORTIE}")
    return 0


if __name__ == "__main__":
    os.environ.pop("QT_QPA_PLATFORM", None)
    code = main()
    sys.stdout.flush()
    os._exit(code)
