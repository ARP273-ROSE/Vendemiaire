#!/usr/bin/env python3
"""
Lanceur — Vendémiaire, gestion de cave à vin.
Launcher — Vendémiaire, wine cellar manager.

    python run.py                 démarrer
    python run.py --lang en       English interface
    python run.py --demo          ouvrir une cave de démonstration (générée)
    python run.py --donnees DOSS  dossier des données (base, images, sauvegardes)
    python run.py --check         vérifier l'installation et sortir
    python run.py --version       afficher la version
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")

#: nom du programme : dossier de données, verrou nommé lu par l'installeur
NOM = "Vendemiaire"
_fichier_faulthandler = None
_LANGUE = "fr"


def _demarrer_rapports(dossier) -> None:
    """Remontée d'incidents (kit commun) : installation, plantage, crash natif, gel."""
    trace_native = dossier / "_crash_natif.log"
    # Relever la trace de la session précédente AVANT d'armer faulthandler :
    # l'ouverture du fichier en écriture la vide.
    try:
        import reporting
        from vendemiaire import __version__
        reporting.init(dossier, application="vendemiaire", version=__version__)
        reporting.relever_crash_natif(trace_native)
        reporting.reprendre_file_en_fond()
    except Exception:
        pass
    try:
        import faulthandler
        global _fichier_faulthandler
        _fichier_faulthandler = open(trace_native, "w", encoding="utf-8")
        faulthandler.enable(file=_fichier_faulthandler, all_threads=True)
    except Exception:
        pass


def _verifier() -> int:
    """--check : ce que le paquet doit savoir faire sans écran (lancé par la
    construction des paquets) — imports, style figé, logo, base neuve migrée,
    textes des deux langues."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import tempfile
    from pathlib import Path
    try:
        from PyQt6 import QtWidgets
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
        import interface_kit  # noqa: F401
        import kit_aide  # noqa: F401
        import reporting  # noqa: F401
        import updater  # noqa: F401
        from vendemiaire import i18n, logo, style
        from vendemiaire.base import VERSION_SCHEMA, Base
        style.appliquer(app)
        assert style.style_de_base(app) == "fusion", style.style_de_base(app)
        assert not logo.pixmap(64).isNull(), "logo"
        assert not i18n.cles_manquantes(), i18n.cles_manquantes()[:5]
        with tempfile.TemporaryDirectory() as d:
            b = Base(Path(d) / "essai.db")
            assert b.version() == VERSION_SCHEMA
            # phase 2 : registres d'appellations livrés, base de référence, règles livrées
            from vendemiaire import images, ocr, regles, reseau  # noqa: F401
            from vendemiaire.mondial import appariement, lwin, off, wikidata  # noqa: F401
            from vendemiaire.modele import Cave
            cave = Cave(b)
            assert cave.references.nb_appellations() > 1000, "registres d'appellations"
            regles.charger_livres()
            assert regles.demander("convertir_note", 90, "100", "20") is not None, "notes.json"
            # phase 3 : jeu de règles du dossier « Le vin » intact (empreintes) et complet
            from vendemiaire.regles.jeu import jeu
            assert jeu().nombre_regles() == 194, "règles du dossier"
            f = regles.demander("fenetre_degustation", {"couleur": "rouge", "type": "tranquille",
                                                        "appellation": "Pauillac", "millesime": 2016})
            assert f is not None and f.sources, "garde.json"
            cave.fermer_references()
            b.fermer()
    except Exception as exc:
        print(f"{NOM} : ECHEC / FAILED -- {type(exc).__name__}: {exc}")
        return 1
    print(f"{NOM} : interface OK")
    return 0


def _rapport_erreur(exc: BaseException) -> None:
    """Écrit l'erreur de démarrage dans un fichier ET tente de l'afficher (une
    application fenêtrée n'a pas de console)."""
    import datetime
    import traceback
    texte = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    entete = f"{NOM} — start-up error — {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n"
    chemin = "?"
    try:
        from vendemiaire import chemins
        chemin = str(chemins.dossier_profil() / "vendemiaire-erreur.log")
        with open(chemin, "a", encoding="utf-8") as fh:
            fh.write(entete + texte + "\n")
    except Exception:
        pass
    sys.stderr.write(entete + texte)
    try:
        import reporting
        reporting.signaler_plantage(texte)
    except Exception:
        pass
    try:
        from PyQt6 import QtWidgets
        from vendemiaire.i18n import definir_langue, tr
        definir_langue(_LANGUE)
        _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        QtWidgets.QMessageBox.critical(None, NOM, tr("erreur.demarrage",
                                                     erreur=f"{type(exc).__name__}: {exc}",
                                                     chemin=chemin))
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Vendémiaire — wine cellar manager / gestion de cave")
    ap.add_argument("--lang", choices=["fr", "en"], default=None)
    ap.add_argument("--demo", action="store_true", help="cave de démonstration / demo cellar")
    ap.add_argument("--donnees", default=None, help="dossier des données / data folder")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--version", action="store_true")
    args = ap.parse_args()

    if args.version:
        from vendemiaire import __version__
        print(__version__)
        return 0
    try:
        import PyQt6  # noqa: F401
    except ImportError:
        print("PyQt6 manque / is missing : python -m pip install -r requirements.txt",
              file=sys.stderr)
        return 1
    if args.check:
        return _verifier()

    from pathlib import Path
    from vendemiaire import chemins, i18n
    global _LANGUE
    _LANGUE = args.lang or i18n.detect_language()
    if args.demo:
        os.environ["VENDEMIAIRE_DONNEES"] = str(chemins.dossier_profil() / "demonstration")
    elif args.donnees:
        os.environ["VENDEMIAIRE_DONNEES"] = args.donnees
    dossier = chemins.dossier_donnees()
    _demarrer_rapports(chemins.dossier_profil())

    from PyQt6 import QtCore, QtWidgets
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName(NOM)
    app.setApplicationName(NOM)
    app.setApplicationDisplayName("Vendémiaire")
    # Verrou nommé lu par l'installeur Inno (AppMutex = <nom_fichier>EnCours)
    if sys.platform == "win32":
        try:
            import ctypes
            app._mutex_installeur = ctypes.windll.kernel32.CreateMutexW(
                None, False, f"{NOM}EnCours")
        except Exception:
            pass
    from vendemiaire import style
    style.appliquer(app)
    try:
        import interface_kit
        interface_kit.installer_dialogues_fichiers()
    except Exception:
        pass
    from vendemiaire import logo
    app.setWindowIcon(logo.icone())

    reglage = QtCore.QSettings().value("langue")
    lang = args.lang or (reglage if reglage in ("fr", "en") else i18n.detect_language(
        QtCore.QLocale.system().uiLanguages()))
    i18n.definir_langue(lang)
    _LANGUE = lang
    from vendemiaire.i18n import tr

    # UN SEUL ÉCRIVAIN : verrou d'instance posé DANS le dossier des données
    # (donc sur le partage réseau si la base y vit)
    verrou = QtCore.QLockFile(str(Path(dossier) / "vendemiaire.verrou"))
    verrou.setStaleLockTime(0)
    if not verrou.tryLock(500):
        _ok, pid, hote, _app = verrou.getLockInfo()
        QtWidgets.QMessageBox.warning(None, "Vendémiaire",
                                      tr("erreur.deja_ouverte", hote=hote or "?", pid=pid))
        return 2
    app._verrou_instance = verrou

    from vendemiaire.base import VERSION_SCHEMA, Base, BaseTropRecente
    from vendemiaire.modele import Cave
    from vendemiaire import sauvegarde
    chemin_base = Path(dossier) / "cave.db"
    if args.demo and not chemin_base.exists():
        from vendemiaire import demo
        c = demo.generer(chemin_base)
        demo.references_demo(c)
        demo.photos_demo(c)
        c.fermer_references()
        c.base.fermer()
    if chemin_base.exists():
        sauvegarde.sauvegarder(chemin_base, chemins.dossier_sauvegardes(), "auto",
                               seulement_si_modifiee=True)
    try:
        base = Base(chemin_base, migrer=False)
        if not base.ecrivain_disponible():
            QtWidgets.QMessageBox.warning(None, "Vendémiaire", tr("erreur.base_verrouillee"))
            return 2
        if base.version() and base.version() < VERSION_SCHEMA:
            sauvegarde.sauvegarder(chemin_base, chemins.dossier_sauvegardes(), "avant-migration")
        base.migrer()
    except BaseTropRecente:
        QtWidgets.QMessageBox.critical(None, "Vendémiaire", tr("erreur.base_recente"))
        return 2
    cave = Cave(base, chemins.dossier_images())

    from vendemiaire.ui.fenetre import FenetrePrincipale
    fenetre = FenetrePrincipale(cave)
    fenetre.show()
    if fenetre.aide is not None:
        fenetre.aide.demarrer(accord_ms=1200, maj_ms=3000)
    # Vigie anti-gel (kit) : la pile capturée nomme l'opération fautive
    try:
        import reporting
        vigie = reporting.Vigie(seuil=10.0, periode=2.0)
        vigie.demarrer()
        minuteur = QtCore.QTimer(fenetre)
        minuteur.timeout.connect(vigie.battre)
        minuteur.start(2000)
        fenetre._vigie = vigie
    except Exception:
        pass
    code = app.exec()
    verrou.unlock()
    return code


if __name__ == "__main__":
    try:
        code = main()
    except SystemExit:
        raise
    except BaseException as _exc:           # noqa: BLE001 — filet volontaire
        _rapport_erreur(_exc)
        code = 1
    # Sortie normale de PyQt = segmentation à la destruction des objets : tout
    # a été écrit dans closeEvent, on sort sans détruire.
    import logging
    logging.shutdown()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
