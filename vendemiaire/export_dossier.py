# -*- coding: utf-8 -*-
"""Export stable pour le dossier LaTeX « Le vin » (encadrés sur les bouteilles de la cave).

Lit la base en LECTURE SEULE (aucun verrou d'écriture : l'application peut
rester ouverte) et écrit un JSON au format `vendemiaire-dossier`, version 1,
décrit dans docs/export_dossier.md. Les chemins des photos sont rendus
absolus quand le dossier images/ est trouvé à côté de la base.

    python -m vendemiaire.export_dossier <cave.db> <sortie.json> [--sorties-seulement]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .base import Base

FORMAT = "vendemiaire-dossier"
VERSION_FORMAT = 1


def exporter(chemin_base: str | Path, sortie: str | Path | None = None,
             sorties_seulement: bool = False) -> dict:
    chemin_base = Path(chemin_base)
    images = chemin_base.parent / "images"
    c = Base.lecture_seule(chemin_base)
    try:
        version = c.execute("PRAGMA user_version").fetchone()[0]
        if version < 3:
            raise SystemExit(f"base en schéma v{version} : ouvrir une fois avec Vendémiaire "
                             "pour la migrer (vues du dossier en v3)")
        vins = [dict(r) for r in c.execute("SELECT * FROM v_dossier_vin ORDER BY pays, region, "
                                           "domaine, cuvee, millesime")]
        sql = "SELECT * FROM v_dossier_livre"
        if sorties_seulement:
            sql += " WHERE type LIKE 'sortie%'"
        livre = [dict(r) for r in c.execute(sql + " ORDER BY date, mouvement_id")]
    finally:
        c.close()
    for ligne in vins + livre:
        rel = ligne.get("photo_etiquette")
        ligne["photo_etiquette_absolue"] = str(images / rel) if rel and (images / rel).exists() else None
    donnees = {"format": FORMAT, "version": VERSION_FORMAT, "schema_base": version,
               "date": date.today().isoformat(), "vins": vins, "livre": livre}
    if sortie:
        Path(sortie).write_text(json.dumps(donnees, ensure_ascii=False, indent=1),
                                encoding="utf-8")
    return donnees


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export de la cave pour le dossier « Le vin »")
    ap.add_argument("base")
    ap.add_argument("sortie")
    ap.add_argument("--sorties-seulement", action="store_true",
                    help="livre de cave : seulement les sorties (bues, offertes…)")
    a = ap.parse_args(argv)
    d = exporter(a.base, a.sortie, a.sorties_seulement)
    print(f"{a.sortie} : {len(d['vins'])} vins, {len(d['livre'])} lignes du livre de cave")
    return 0


if __name__ == "__main__":
    sys.exit(main())
