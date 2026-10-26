# -*- coding: utf-8 -*-
"""Copie (ou vérifie) les règles du dossier « Le vin » dans Vendémiaire.

Les règles d'œnologie de Vendémiaire ne sont PAS écrites dans le code : ce sont
les fichiers `data/regles/*.json` du dossier « Le vin », copiés TELS QUELS
(octet pour octet) dans `vendemiaire/regles/donnees/`, avec un manifeste
(`MANIFESTE.json`) qui garde l'empreinte SHA-256 de chaque fichier, sa version,
sa date et la date de l'audit des règles.

    python outils/synchroniser_regles.py              # copier depuis le dossier
    python outils/synchroniser_regles.py --verifier   # comparer, sans rien écrire

Le dossier est cherché dans la variable VENDEMIAIRE_DOSSIER_VIN, sinon à côté
du dépôt (`../_docs/Vin`). Code de sortie : 0 = identiques (ou copiés), 1 =
différences (mode --verifier), 2 = dossier introuvable.

Une règle se corrige DANS LE DOSSIER (script `scripts/regles.py`), jamais ici.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
CIBLE = RACINE / "vendemiaire" / "regles" / "donnees"
#: fichiers du jeu de règles (sources.json : registre des sources)
FICHIERS = ("LISEZMOI.md", "sources.json", "styles.json", "service.json", "garde.json",
            "millesimes.json", "conservation.json", "bouteille_ouverte.json", "niveaux.json",
            "notes.json", "defauts.json", "aromes.json", "accords.json", "accords_corpus.json")


def dossier_vin() -> Path:
    env = os.environ.get("VENDEMIAIRE_DOSSIER_VIN")
    return Path(env) if env else RACINE.parent / "_docs" / "Vin"


def empreinte(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def date_audit(dossier: Path) -> str | None:
    """Date de l'audit des règles, lue dans le journal d'audit du dossier
    (« … (phase 7, 26/10/2026) ») ; ISO."""
    journal = dossier / "audit" / "faits_regles.md"
    if not journal.exists():
        return None
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", journal.read_text(encoding="utf-8").splitlines()[0])
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def manifeste(dossier: Path, ancien: dict | None = None) -> dict:
    fichiers = {}
    for nom in FICHIERS:
        p = dossier / "data" / "regles" / nom
        entree = {"sha256": empreinte(p), "octets": p.stat().st_size}
        if p.suffix == ".json":
            d = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                entree["version"] = d.get("version")
                entree["date"] = d.get("date")
        fichiers[nom] = entree
    return {
        "origine": "dossier « Le vin », data/regles (copie octet pour octet)",
        "date_audit": date_audit(dossier) or (ancien or {}).get("date_audit"),
        "fichiers": fichiers,
    }


def differences(dossier: Path) -> list[str]:
    """Fichiers de l'application qui ne sont pas identiques au dossier."""
    ecarts = []
    for nom in FICHIERS:
        source, copie = dossier / "data" / "regles" / nom, CIBLE / nom
        if not copie.exists():
            ecarts.append(f"{nom} : absent de l'application")
        elif not source.exists():
            ecarts.append(f"{nom} : absent du dossier")
        elif empreinte(source) != empreinte(copie):
            ecarts.append(f"{nom} : différent du dossier")
    man = CIBLE / "MANIFESTE.json"
    if man.exists():
        m = json.loads(man.read_text(encoding="utf-8"))
        for nom in FICHIERS:
            copie = CIBLE / nom
            if copie.exists() and m["fichiers"].get(nom, {}).get("sha256") != empreinte(copie):
                ecarts.append(f"{nom} : empreinte du manifeste périmée")
    else:
        ecarts.append("MANIFESTE.json absent")
    return ecarts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--verifier", action="store_true", help="comparer sans rien écrire")
    ap.add_argument("--dossier", help="dossier « Le vin » (contient data/regles)")
    a = ap.parse_args(argv)
    dossier = Path(a.dossier) if a.dossier else dossier_vin()
    if not (dossier / "data" / "regles").is_dir():
        print(f"dossier « Le vin » introuvable : {dossier}", file=sys.stderr)
        return 2
    ecarts = differences(dossier)
    if a.verifier:
        for e in ecarts:
            print(e)
        print("identiques au dossier" if not ecarts else f"{len(ecarts)} différence(s)")
        return 1 if ecarts else 0
    CIBLE.mkdir(parents=True, exist_ok=True)
    ancien = None
    if (CIBLE / "MANIFESTE.json").exists():
        ancien = json.loads((CIBLE / "MANIFESTE.json").read_text(encoding="utf-8"))
    for nom in FICHIERS:
        shutil.copyfile(dossier / "data" / "regles" / nom, CIBLE / nom)
    (CIBLE / "MANIFESTE.json").write_text(
        json.dumps(manifeste(dossier, ancien), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(FICHIERS)} fichiers copiés dans {CIBLE.relative_to(RACINE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
