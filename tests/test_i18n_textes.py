# -*- coding: utf-8 -*-
"""Bilinguisme : aucun texte d'interface en dur, aucune clé manquante, aucun
français dans l'anglais, tous les codes des référentiels traduits.

Ce test attrape :
  - un texte littéral passé à un widget (setText, QLabel, QMessageBox, addItem…) ;
  - une clé (« menu.fichier », « plan.aide »…) écrite dans le code mais absente
    de textes.py — elle s'afficherait « <menu.fichier> » ;
  - une moitié vide, du français dans la partie anglaise.
"""
import ast
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from vendemiaire import i18n, referentiels  # noqa: E402
from vendemiaire.textes import T  # noqa: E402

SOURCES = ["run.py", "vendemiaire/ui", "vendemiaire/i18n.py"]
APPELS = {"setText", "setTitle", "setWindowTitle", "setToolTip", "setStatusTip", "setWhatsThis",
          "setPlaceholderText", "showMessage", "addItem", "addItems", "insertItem", "setItemText",
          "setInformativeText", "setDetailedText", "setHorizontalHeaderLabels",
          "setHeaderLabels", "addAction", "addMenu", "addTab", "setTabText", "information",
          "warning", "critical", "question", "about", "setLabelText", "drawText", "setHtml",
          "setPlainText", "addButton", "setPrefix", "setSuffix", "addRow", "getText",
          "getSaveFileName", "getOpenFileName", "getExistingDirectory",
          "QLabel", "QPushButton", "QCheckBox", "QRadioButton", "QGroupBox", "QAction",
          "QMessageBox", "QProgressDialog", "QToolButton", "QMenu", "QTableWidgetItem",
          "QTreeWidgetItem", "_tuile", "_cellule"}
#: textes admis tels quels : unités, noms propres, symboles
NEUTRES = {"Vendémiaire", "Vendemiaire", " cm", " %", " €", "CSV", "JSON", "SQLite", "LWIN", "PyQt6"}
CLE = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")
#: mots anglais d'origine française admis dans la partie anglaise
ADMIS_EN = ("Vendémiaire", "Cuvée", "cuvée", "Rosé", "rosé")
FRANCAIS = re.compile(r"[éèàçêôûùîïœ«»]")


def _fichiers():
    for nom in SOURCES:
        p = RACINE / nom
        yield from (sorted(p.rglob("*.py")) if p.is_dir() else [p])


def _litteral(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        return n.value
    if isinstance(n, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else " " for v in n.values)
    if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Mod)):
        g, d = _litteral(n.left), _litteral(n.right)
        if g is None and d is None:
            return None
        return (g or " ") + (d or " ")
    return None


def textes_en_dur(chemin: Path):
    for n in ast.walk(ast.parse(chemin.read_text(encoding="utf-8"))):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        nom = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
        if nom not in APPELS:
            continue
        args = list(n.args) + [k.value for k in n.keywords]
        if nom == "addItem":                  # addItem(texte, donnée) : la donnée n'est pas affichée
            args = n.args[:1]
        elif nom in ("insertItem", "setItemText"):
            args = n.args[1:2]
        for arg in args:
            t = _litteral(arg)
            if t is None or t.strip() in NEUTRES or t in NEUTRES or CLE.match(t):
                continue
            nu = re.sub(r"<[^>]*>|&\w+;|\{[^}]*\}|%[sdf]|\(\*[^)]*\)", " ", t)
            if re.search(r"[A-Za-zÀ-ÿ]{2,}", nu):
                yield n.lineno, nom, t[:60]


def test_le_scan_attrape_les_textes_en_dur(tmp_path):
    temoin = tmp_path / "temoin.py"
    temoin.write_text("w.setText('Bonjour')\nw.setToolTip(tr('a.b'))\n"
                      "QMessageBox.warning(self, 'Titre', f'{x} mots')\nQLabel('Vendémiaire')\n",
                      encoding="utf-8")
    assert len(list(textes_en_dur(temoin))) == 3


def test_aucun_texte_affiche_en_dur():
    fautes = [f"{p.relative_to(RACINE)}:{l} {appel}({t!r})"
              for p in _fichiers() for l, appel, t in textes_en_dur(p)]
    assert not fautes, "Textes affichés sans traduction :\n  " + "\n  ".join(fautes)


def test_toutes_les_cles_existent():
    """Toute chaîne en forme de clé (« fiche.sortir ») dans le code doit exister."""
    manquantes = []
    for p in list(_fichiers()) + sorted((RACINE / "vendemiaire").glob("*.py")):
        if p.name in ("textes.py", "referentiels.py", "base.py"):
            continue
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and CLE.match(n.value):
                prefixe = n.value.split(".")[0]
                if prefixe in {k.split(".")[0] for k in T} and n.value not in T \
                        and not n.value.endswith((".db", ".json", ".csv", ".png")):
                    manquantes.append(f"{p.relative_to(RACINE)}:{n.lineno} {n.value}")
    # clés fabriquées dans le code (f"tableau.{cle}")
    for cle in ("bouteilles", "vins", "a_venir", "litres", "prix_total", "valeur_estimee",
                "par_couleur", "par_pays", "par_region", "par_decennie"):
        if f"tableau.{cle}" not in T:
            manquantes.append(f"tableau.{cle}")
    assert not manquantes, "Clés absentes de textes.py :\n  " + "\n  ".join(manquantes)


def test_paires_completes_et_anglais_sans_francais():
    fautes = []
    for cle, paire in T.items():
        if not paire.get("fr", "").strip() or not paire.get("en", "").strip():
            fautes.append(f"{cle} : moitié vide")
        en = paire.get("en", "")
        for mot in ADMIS_EN:
            en = en.replace(mot, "")
        if FRANCAIS.search(en):
            fautes.append(f"{cle} : français dans l'anglais : {paire['en'][:60]!r}")
    for enum, codes in referentiels.ENUMS.items():
        for code, (fr, en) in codes.items():
            nu = en
            for mot in ADMIS_EN:
                nu = nu.replace(mot, "")
            if not fr or not en or FRANCAIS.search(nu):
                fautes.append(f"{enum}.{code} : {en!r}")
    for f in referentiels.FORMATS:
        if FRANCAIS.search(f.en):
            fautes.append(f"format {f.code} : {f.en!r}")
    assert not fautes, "\n".join(fautes)


def test_champs_de_format_identiques():
    """« {vin} » en français doit exister aussi en anglais (sinon KeyError à l'affichage)."""
    champs = re.compile(r"\{(\w+)\}")
    fautes = [c for c, p in T.items()
              if set(champs.findall(p["fr"])) != set(champs.findall(p["en"]))]
    assert not fautes, fautes


def test_detection_de_la_langue():
    assert i18n.detect_language(["fr-FR"]) == "fr"
    assert i18n.detect_language(["French_France"]) == "fr"
    assert i18n.detect_language(["en-GB"]) == "en"
    assert i18n.detect_language(["de-DE"]) == "en"
    assert i18n.detect_language([]) == "en"


def test_cle_absente_signalee_visiblement():
    assert i18n.tr("cle.qui_n_existe_pas") == "<cle.qui_n_existe_pas>"


def test_montants_et_dates_selon_la_langue():
    i18n.definir_langue("fr")
    assert i18n.argent(1234.5) == "1 234,50 €" and i18n.date_affichee("2026-10-26") == "26/10/2026"
    i18n.definir_langue("en")
    assert i18n.argent(1234.5) == "€1,234.50" and i18n.date_affichee("2026-10-26") == "2026-10-26"
    i18n.definir_langue("fr")
