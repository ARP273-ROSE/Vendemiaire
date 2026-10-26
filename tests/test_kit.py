# -*- coding: utf-8 -*-
"""Cohérence du kit commun et points du standard des applications.

Écarts qui ne se voient que chez l'utilisateur : verrou nommé inconnu de
l'installeur, version écrite deux fois, clé de kit.json oubliée, données dans
le dossier d'installation, second workflow de publication, trace de crash
natif effacée avant lecture, style qui suit le thème du système, boîte de
fichiers réduite sous Linux, deux logos.
"""
import ast
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
KIT = json.loads((RACINE / "kit.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(RACINE))


def test_fichiers_du_kit_identiques_au_gabarit():
    """Aucune copie modifiée à la main (vérifiable là où le gabarit est présent)."""
    gabarits = RACINE.parent / "_kit_windows" / "gabarits"
    if not gabarits.is_dir():
        pytest.skip("gabarit absent")
    for nom in ("reporting.py", "updater.py", "build_package.py", "installer.iss",
                "build_unix.py", "interface_kit.py"):
        assert (RACINE / nom).read_bytes() == (gabarits / nom).read_bytes(), nom
    wf = (RACINE / ".github" / "workflows" / "release.yml").read_bytes()
    assert wf == (gabarits / "release-multiplateforme.yml").read_bytes()
    assert (RACINE / "tests" / "test_confidentialite.py").read_bytes() == \
        (gabarits / "test_confidentialite.py").read_bytes()


def test_verrou_nomme_identique_a_l_installeur():
    iss = (RACINE / "installer.iss").read_text(encoding="utf-8")
    assert "AppMutex={#AppName}EnCours" in iss
    entree = (RACINE / KIT["point_entree"]).read_text(encoding="utf-8")
    assert 'f"{NOM}EnCours"' in entree and f'NOM = "{KIT["nom_fichier"]}"' in entree


def test_version_unique():
    version = (RACINE / KIT["fichier_version"]).read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    journal = (RACINE / KIT["journal_technique"]).read_text(encoding="utf-8")
    assert re.search(rf"^## {re.escape(version)}( |$)", journal, re.M)
    import vendemiaire
    assert vendemiaire.__version__ == version
    for p in (RACINE / "vendemiaire").rglob("*.py"):
        assert not re.search(r"__version__\s*=\s*['\"]\d", p.read_text(encoding="utf-8")), p


def test_kit_json_complet():
    for cle in ("nom_technique", "nom_fichier", "nom_affiche", "depot_distribution",
                "point_entree", "icone", "appid", "icone_png", "icone_grande", "icone_icns",
                "nom_affiche_fr", "nom_affiche_en", "description_fr", "description_en",
                "categories_linux", "tests_ci", "journal_technique"):
        assert KIT.get(cle), cle
    assert "A_COMPLETER" not in json.dumps(KIT)
    for chemin in [KIT["point_entree"], KIT["icone"].replace("\\", "/"), KIT["icone_png"],
                   KIT["icone_grande"], KIT["icone_icns"], *KIT["modules"], *KIT["paquets"],
                   *KIT["assets"], *KIT["tests_ci"]]:
        assert (RACINE / chemin).exists(), chemin
    # rapports : le poste est le nom de la machine (application personnelle)
    assert (KIT.get("rapports") or {}).get("poste", "machine") == "machine"


def test_un_seul_workflow_de_publication():
    wf = RACINE / ".github" / "workflows"
    publient = [p.name for p in wf.glob("*.yml")
                if "action-gh-release" in p.read_text(encoding="utf-8")
                or "gh release create" in p.read_text(encoding="utf-8")]
    assert publient == ["release.yml"], publient


def test_donnees_hors_du_dossier_installe(tmp_path, monkeypatch):
    """Les données vivent dans le profil, jamais dans le dossier de l'application."""
    from vendemiaire import chemins
    monkeypatch.delenv("VENDEMIAIRE_DONNEES", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    d = chemins.dossier_donnees()
    assert RACINE not in d.parents and d != RACINE and d.name == "Vendemiaire"
    # un autre dossier choisi (partage réseau) : retenu dans le profil
    partage = tmp_path / "partage"
    chemins.choisir_emplacement(partage)
    assert chemins.dossier_donnees() == partage and chemins.chemin_base().parent == partage
    chemins.choisir_emplacement(None)
    assert chemins.dossier_donnees() == d


def test_trace_de_crash_natif_relevee_avant_d_armer_faulthandler():
    arbre = ast.parse((RACINE / "run.py").read_text(encoding="utf-8"))
    fn = next(n for n in arbre.body if isinstance(n, ast.FunctionDef) and n.name == "_demarrer_rapports")
    lignes = {}
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            lignes.setdefault(getattr(n.func, "attr", getattr(n.func, "id", "")), n.lineno)
    assert lignes["relever_crash_natif"] < lignes["open"] < lignes["enable"]


def test_sortie_sans_destruction_et_closeevent():
    src = (RACINE / "run.py").read_text(encoding="utf-8")
    assert "os._exit(code)" in src and "atexit" not in src
    fen = (RACINE / "vendemiaire" / "ui" / "fenetre.py").read_text(encoding="utf-8")
    corps = fen[fen.index("def closeEvent"):]
    assert "QSettings().sync()" in corps and "base.fermer()" in corps and "topLevelWidgets" in corps


def test_style_fige_independant_du_systeme(app):
    from PyQt6 import QtGui
    from vendemiaire import style
    app.setPalette(QtGui.QPalette(QtGui.QColor("#202020")))     # le système se dit sombre
    famille = style.appliquer(app)
    assert style.style_de_base(app) == "fusion"
    R, G = QtGui.QPalette.ColorRole, QtGui.QPalette.ColorGroup
    p = app.palette()
    assert p.color(G.Active, R.Window).name().upper() == style.CREME.upper()
    assert p.color(G.Disabled, R.Window).name().upper() == style.CREME.upper()
    assert p.color(G.Active, R.Highlight).name().upper() == style.BORDEAUX.upper()
    assert famille == style.FAMILLE and app.font().family() == style.FAMILLE
    assert "QTabBar" in app.styleSheet()


def test_boite_de_fichiers_complete_sous_linux(app, monkeypatch, tmp_path):
    import interface_kit
    from PyQt6 import QtWidgets
    monkeypatch.setenv("KIT_DIALOGUES", "qt")
    vues = []

    def _exec(self):
        vues.append((self.testOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog),
                     [u.toLocalFile() for u in self.sidebarUrls()]))
        return 0

    monkeypatch.setattr(QtWidgets.QFileDialog, "exec", _exec)
    assert interface_kit.installer_dialogues_fichiers()
    try:
        QtWidgets.QFileDialog.getSaveFileName(None, "csv", str(tmp_path / "a.csv"), "CSV (*.csv)")
        QtWidgets.QFileDialog.getOpenFileName(None, "img", str(tmp_path))
    finally:
        for nom, fn in interface_kit._ORIGINAUX.items():
            setattr(QtWidgets.QFileDialog, nom, fn)
        interface_kit._ORIGINAUX.clear()
    assert len(vues) == 2 and all(q and os.path.expanduser("~") in l for q, l in vues)


def test_fichiers_par_qfiledialog():
    """Imports, exports, photo, sauvegardes : les statiques de QFileDialog, que
    le kit remplace — aucune boîte maison qui échapperait au standard."""
    src = (RACINE / "vendemiaire" / "ui" / "fenetre.py").read_text(encoding="utf-8")
    for fn in ("importer_csv", "importer_cellartracker", "exporter_csv", "exporter_json",
               "choisir_photo", "restaurer", "choisir_dossier_donnees"):
        corps = src[src.index(f"def {fn}("):]
        corps = corps[:corps.index("\n    def ", 10)]
        assert "QFileDialog.get" in corps, fn


def test_une_seule_source_pour_le_logo(app):
    from PyQt6 import QtGui
    from vendemiaire import logo
    assert logo.SOURCE == RACINE / "branding" / "logo.svg"
    # les fichiers dérivés sont à jour de la source
    empreinte = (RACINE / "docs" / "logo.sha256").read_text(encoding="utf-8").split()[0]
    assert empreinte == hashlib.sha256(logo.SOURCE.read_bytes()).hexdigest(), \
        "logo.svg a changé : relancer outils/rendre_logo.js puis python -m vendemiaire.logo --assembler"
    for t in logo.TAILLES:
        assert QtGui.QImage(str(logo.png(t))).width() == t, t
    assert (RACINE / "docs" / "logo.ico").read_bytes()[:4] == b"\x00\x00\x01\x00"
    assert (RACINE / "docs" / "logo.icns").read_bytes()[:4] == b"icns"
    # aucun second dessin du logo dans le code
    for p in (RACINE / "vendemiaire").rglob("*.py"):
        assert "<svg" not in p.read_text(encoding="utf-8"), p
    # le PNG publié ressemble au rendu Qt du SVG (même dessin, pas un autre logo)
    a = QtGui.QImage(str(logo.png(64))).convertToFormat(QtGui.QImage.Format.Format_ARGB32)
    b = logo.rendu_svg(64).toImage().convertToFormat(QtGui.QImage.Format.Format_ARGB32)
    ecarts = sum(abs(QtGui.QColor(a.pixel(x, y)).red() - QtGui.QColor(b.pixel(x, y)).red())
                 for x in range(0, 64, 4) for y in range(0, 64, 4))
    assert ecarts / 256 < 30


def test_regles_d_oenologie_pas_inventees():
    """Phase 1 : aucune règle d'apogée, de service ni d'accord dans le code ;
    l'interface l'annonce au lieu d'estimer."""
    from vendemiaire import regles
    assert not regles.disponibles()
    assert regles.demander("fenetre_degustation", {}) is None


def test_verrou_d_instance_unique(tmp_path):
    """Un seul écrivain : une seconde copie ne prend pas le verrou ; celui d'un
    processus mort sur le même poste est repris (QLockFile)."""
    import subprocess
    from PyQt6 import QtCore
    chemin = str(tmp_path / "vendemiaire.verrou")
    a = QtCore.QLockFile(chemin)
    a.setStaleLockTime(0)
    assert a.tryLock(100)
    code = "import sys;from PyQt6 import QtCore;v=QtCore.QLockFile(sys.argv[1]);v.setStaleLockTime(0);" \
           "sys.exit(0 if v.tryLock(200) else 3)"
    assert subprocess.run([sys.executable, "-c", code, chemin]).returncode == 3
    a.unlock()
    # verrou laissé par un processus tué
    tue = subprocess.run([sys.executable, "-c", "import os,sys;from PyQt6 import QtCore;"
                          "v=QtCore.QLockFile(sys.argv[1]);v.tryLock(100);os._exit(0)", chemin])
    assert tue.returncode == 0 and os.path.exists(chemin)
    assert subprocess.run([sys.executable, "-c", code, chemin]).returncode == 0
