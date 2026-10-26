# -*- coding: utf-8 -*-
"""Produit les copies EMBARQUÉES des registres d'appellations
(vendemiaire/donnees/appellations_*.csv et sources.json) depuis les sources
officielles, avec les mêmes fonctions que la mise à jour de l'application :

    python outils/registres_appellations.py            # télécharge (réseau)
    python outils/registres_appellations.py --inao f.csv --eambrosia f.json   # fichiers déjà là
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from vendemiaire import reseau  # noqa: E402
from vendemiaire.mondial import appellations as ap  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--inao", help="CSV SIQO de l'INAO déjà téléchargé")
    p.add_argument("--eambrosia", help="JSON de l'API eAmbrosia (vins) déjà téléchargé")
    a = p.parse_args()
    client = reseau.Client(ignorer_accord=True)
    sources = ap.sources_embarquees()
    jour = date.today().isoformat()
    if a.inao:
        texte, url_inao = Path(a.inao).read_text(encoding="utf-8-sig"), a.inao
    else:
        url_inao = ap.url_csv_inao(client)
        texte = client.get(url_inao).corps.decode("utf-8-sig")
    inao = ap.depuis_inao(texte)
    donnees = json.loads(Path(a.eambrosia).read_text(encoding="utf-8")) if a.eambrosia \
        else client.json(ap.URL_EAMBROSIA)
    eamb = ap.depuis_eambrosia(donnees)
    n1 = ap.ecrire_csv(inao, ap.DOSSIER_DONNEES / ap.FICHIERS["inao"])
    n2 = ap.ecrire_csv(eamb, ap.DOSSIER_DONNEES / ap.FICHIERS["eambrosia"])
    sources["inao"] = {
        "titre": "INAO — Référentiel des produits sous SIQO (vins)", "page": ap.PAGE_INAO,
        "fichier": Path(url_inao).name, "licence": ap.LICENCES["inao"],
        "date_extraction": jour, "lignes": n1}
    sources["eambrosia"] = {
        "titre": "eAmbrosia — registre des indications géographiques de l'UE (vins)",
        "page": ap.PAGE_EAMBROSIA, "api": ap.URL_EAMBROSIA, "licence": ap.LICENCES["eambrosia"],
        "date_extraction": jour, "lignes": n2}
    (ap.DOSSIER_DONNEES / "sources.json").write_text(
        json.dumps(sources, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"INAO : {n1} appellations et dénominations ; eAmbrosia : {n2} noms protégés")
    return 0


if __name__ == "__main__":
    sys.exit(main())
