# -*- coding: utf-8 -*-
"""Fournisseur des règles du dossier « Le vin » (contrat `FournisseurRegles`).

Chaque méthode renvoie une `Estimation` (valeur, explication FR/EN, sources,
identifiant de règle, confiance, marges, détail du calcul) ou None quand la
règle ne sait pas répondre — jamais une valeur inventée.
"""
from __future__ import annotations

from datetime import date

from . import Estimation
from . import accords as module_accords
from . import conservation as module_conservation
from . import garde as module_garde
from . import niveaux as module_niveaux
from . import service as module_service
from .jeu import JeuRegles, jeu
from .styles import classer


class FournisseurDossier:
    identifiant = "dossier-le-vin"

    def __init__(self, regles: JeuRegles | None = None):
        self.regles = regles or jeu()

    # -- classement -----------------------------------------------------------
    def style(self, vin: dict):
        return classer(vin, self.regles)

    # -- garde ----------------------------------------------------------------
    def fenetre(self, vin: dict, **contexte):
        return module_garde.fenetre(vin, regles=self.regles, **contexte)

    def fenetre_degustation(self, vin: dict, bouteille: dict | None = None) -> Estimation | None:
        formats = (bouteille or {}).get("format")
        f = module_garde.fenetre(vin, formats=(formats,) if formats else (), regles=self.regles)
        return f.estimation() if f else None

    # -- service --------------------------------------------------------------
    def service(self, vin: dict, annee: int | None = None, **contexte):
        return module_service.service(vin, annee or date.today().year, regles=self.regles, **contexte)

    # -- conservation ---------------------------------------------------------
    def conservation(self, vin: dict, bouteille: dict | None = None) -> Estimation | None:
        conseils = module_conservation.conseils(self.regles)
        if not conseils:
            return None
        e = conseils[0]
        return Estimation({"regles": [c.regle for c in conseils]}, e.explication_fr, e.explication_en,
                          sorted({s for c in conseils for s in c.sources}), "cave", None, None, {})

    def bouteille_ouverte(self, vin: dict, conservation: str = "bouchon",
                          ouverte_le: date | None = None) -> Estimation | None:
        return module_conservation.bouteille_ouverte(vin, conservation, ouverte_le, self.regles)

    # -- niveaux --------------------------------------------------------------
    def sens_niveau(self, code_niveau: str | None, age: int | None, cm: float | None = None):
        return module_niveaux.sens_niveau(code_niveau, age, cm, self.regles)

    # -- accords --------------------------------------------------------------
    def accords_pour_vin(self, vin: dict) -> list[Estimation]:
        cl = classer(vin, self.regles)
        if cl is None:
            return []
        return [p.estimation() for p in module_accords.plats_pour_style(cl.id, self.regles)]

    def vins_pour_plat(self, plat: str, vins: list[dict]) -> list[tuple[int, Estimation]]:
        trouves = module_accords.chercher_plats(plat, self.regles)
        if not trouves:
            return []
        p = trouves[0]
        sortie = []
        for v in vins:
            cl = classer(v, self.regles)
            if cl is not None and cl.id in p.styles:
                sortie.append((v.get("id"), p.estimation()))
        return sortie
