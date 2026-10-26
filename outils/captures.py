# -*- coding: utf-8 -*-
"""Captures d'écran RÉELLES de l'interface (cave de démonstration), FR et EN,
pour le README et le manuel. À lancer sous un vrai serveur X (Xvfb) :

    xvfb-run -a -s "-screen 0 1920x1080x24" python outils/captures.py
"""
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
SORTIE = RACINE / "docs" / "captures"


def main() -> int:
    from PyQt6 import QtCore, QtWidgets
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
        w.minuteur.stop()
        w.close()
        cave.base.fermer()
    print(f"captures écrites dans {SORTIE}")
    return 0


if __name__ == "__main__":
    os.environ.pop("QT_QPA_PLATFORM", None)
    code = main()
    sys.stdout.flush()
    os._exit(code)
