# -*- coding: utf-8 -*-
"""Conversion des notes des critiques, d'après `donnees/notes.json` du dossier
« Le vin » (copie inchangée ; règle `notes.conversion`).

Ce que dit la règle : une note n'est pas une mesure. La seule table de
correspondance publiée par un même éditeur est celle de Decanter (100 ↔ 20
points, avec mentions) : on l'utilise telle quelle, sans conversion linéaire.
Les étoiles du Guide Hachette sont des mentions, pas des points. Sans table
publiée (étoiles sur 5…), on ne convertit pas : on le dit.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import Estimation

DONNEES = Path(__file__).resolve().parent / "donnees"


def _sur_20(texte: str) -> list[float]:
    return [float(x) for x in str(texte).split("/") if x.strip()]


class FournisseurNotes:
    identifiant = "dossier-le-vin:notes"

    def __init__(self, chemin: Path | None = None):
        d = json.loads((chemin or DONNEES / "notes.json").read_text(encoding="utf-8"))
        self.version = d.get("version")
        self.regle = d.get("regle") or {}
        self.table = d.get("decanter_100_20") or []
        self.hachette = d.get("hachette") or []
        self.echelles_100 = d.get("echelles_100") or {}

    def _estimation(self, valeur: dict, fr: str, en: str) -> Estimation:
        """Le « pourquoi » affiché est celui de la règle du dossier, précédé de
        la table utilisée."""
        return Estimation(valeur, f"{fr} {self.regle.get('explication_fr', '')}".strip(),
                          f"{en} {self.regle.get('explication_en', '')}".strip(),
                          list(self.regle.get("sources") or []),
                          self.regle.get("id", "notes.conversion"))

    def convertir_note(self, note: float, de: str, vers: str) -> Estimation | None:
        if note is None:
            return None
        de, vers = str(de), str(vers)
        if de == "100" and vers == "20":
            for r in self.table:
                bas = r["sur_100"]
                if isinstance(bas, str) and "-" in bas:
                    a, b = (int(x) for x in bas.split("-"))
                    dedans = a <= round(note) <= b
                else:
                    dedans = round(note) == int(bas)
                if dedans:
                    vals = sorted(_sur_20(r["sur_20"]))
                    return self._estimation(
                        {"note": vals[0], "note_max": vals[-1] if len(vals) > 1 else None,
                         "mention": r.get("mention"), "medaille": r.get("medaille")},
                        "Table Decanter 100 → 20.", "Decanter table 100 → 20.")
            return None
        if de == "20" and vers == "100":
            meilleur = None
            for r in self.table:
                if isinstance(r["sur_100"], str):
                    continue
                vals = _sur_20(r["sur_20"])
                ecart = min(abs(v - note) for v in vals)
                if meilleur is None or ecart < meilleur[0]:
                    meilleur = (ecart, r)
            if meilleur is None or meilleur[0] > 0.5:
                return None
            r = meilleur[1]
            return self._estimation(
                {"note": float(r["sur_100"]), "note_max": None, "mention": r.get("mention"),
                 "medaille": r.get("medaille")},
                "Table Decanter 20 → 100 (lue à l'envers).", "Decanter table 20 → 100 (read backwards).")
        if de == "3" and vers == "mention":
            for r in self.hachette:
                if r["etoiles"] == int(note):
                    return self._estimation(
                        {"mention": r["mention"]},
                        "Étoiles du Guide Hachette.", "Guide Hachette stars.")
        return None
