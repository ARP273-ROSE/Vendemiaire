# -*- coding: utf-8 -*-
"""Exemples de documents sur la cave de DÉMONSTRATION (producteurs inventés),
rangés dans docs/exemples/ : trois cartes des vins (classique A4 en français,
moderne A4 en anglais, bistrot A5 en français), le rapport d'assurance et une
planche d'étiquettes QR. Demande un moteur LaTeX (sinon : repli Qt, dit).

    xvfb-run -a python outils/exemples.py
"""
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
SORTIE = RACINE / "docs" / "exemples"


PRECHAUFFAGE = RACINE / "docs" / "prechauffage"


def prechauffage(cave, carte, assurance, options, reglages) -> None:
    """Sources LaTeX (moteur Unicode, comme Tectonic) des documents de
    l'application, rangées dans docs/prechauffage/<nom>/document.tex avec leurs
    fichiers annexes : la construction des paquets les compile avec le Tectonic
    embarqué pour remplir son cache (kit.json « outils », « prechauffer »), si
    bien que l'application compile ensuite HORS LIGNE."""
    import shutil
    shutil.rmtree(PRECHAUFFAGE, ignore_errors=True)
    docs = []
    for nom, change in (("carte-classique-a4-fr", {"modele": "classique", "format": "a4", "langue": "fr"}),
                        ("carte-moderne-a5-en", {"modele": "moderne", "format": "a5", "langue": "en"}),
                        ("carte-bistrot-simple-fr", {"modele": "bistrot", "format": "simple", "langue": "fr"})):
        k = carte.construire(cave, dict(options, **change), None, reglages)
        docs.append((nom, *carte.latex(k, True)))
    for lg in ("fr", "en"):
        inv = assurance.construire(cave, lg)
        inv.vins = inv.vins[:6]                      # quelques vins suffisent (photos comprises)
        docs.append((f"assurance-{lg}", *assurance.latex(inv, "", True)))
    for nom, source, annexes in docs:
        d = PRECHAUFFAGE / nom
        d.mkdir(parents=True)
        (d / "document.tex").write_text(source, encoding="utf-8")
        for fichier, contenu in annexes.items():
            cible = d / fichier
            cible.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(contenu, bytes):
                cible.write_bytes(contenu)
            else:
                shutil.copyfile(contenu, cible)
    print(f"prechauffage : {len(docs)} documents dans {PRECHAUFFAGE}")


def main() -> int:
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)  # noqa: F841 — photos dessinées, planche d'étiquettes
    from vendemiaire import demo
    from vendemiaire.documents import assurance, carte, etiquettes
    SORTIE.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp())
    cave = demo.generer(temp / "demo.db")
    demo.photos_demo(cave, 12)
    _r, options, vins = carte.lire(cave, 1)
    reglages = {x["vin_id"]: dict(x) for x in cave.base.lire("SELECT * FROM carte_vin WHERE carte_id=1")}
    for nom, change in (("carte-classique-a4-fr", {"modele": "classique", "format": "a4", "langue": "fr"}),
                        ("carte-moderne-a4-en", {"modele": "moderne", "format": "a4", "langue": "en",
                                                 "lieu": "The harvest house",
                                                 "mot": "Welcome! Tonight the cellar opens for you.",
                                                 "menu": ["Oysters", "Roast leg of lamb", "Cheese board", "Lemon tart"]}),
                        ("carte-bistrot-a5-fr", {"modele": "bistrot", "format": "a5", "langue": "fr"})):
        k = carte.construire(cave, dict(options, **change), None, reglages)
        moteur = carte.ecrire_pdf(k, SORTIE / f"{nom}.pdf")
        print(nom, moteur)
    inv = assurance.construire(cave, "fr")
    print("rapport-assurance", assurance.ecrire_pdf(inv, SORTIE / "rapport-assurance-fr.pdf"))
    prechauffage(cave, carte, assurance, options, reglages)
    bs = etiquettes.bouteilles_pour_etiquettes(cave)[:24]
    etiquettes.ecrire_planche(bs, SORTIE / "etiquettes-qr-3x8.pdf", "3x8")
    cave.base.fermer()
    print(f"exemples écrits dans {SORTIE}")
    return 0


if __name__ == "__main__":
    os.environ.pop("QT_QPA_PLATFORM", None)
    code = main()
    sys.stdout.flush()
    os._exit(code)
