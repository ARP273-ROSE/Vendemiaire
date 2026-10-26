# -*- coding: utf-8 -*-
"""Interface des règles d'œnologie (apogée, service, conservation, accords, niveaux).

PHASE 1 : seulement l'emplacement et le contrat. Aucune règle n'est écrite
ici : elles viendront du dossier « Le vin » (parties « millésimes »,
« conservation », V et VI), AVEC leurs sources, pour que l'application et le
dossier disent la même chose. Tant qu'aucun fournisseur n'est inscrit,
l'interface affiche « règles à venir » au lieu d'inventer une estimation.

Contrat d'un fournisseur de règles (phase 3) :

* chaque réponse porte son **explication** (le « pourquoi ») et ses
  **sources** (références du dossier) ; l'interface les affiche toujours ;
* une estimation calculée est rangée dans `fenetre_degustation` avec
  `source='calcul'` et `detail_source=<identifiant de la règle>` — jamais à la
  place de la fenêtre saisie par l'utilisateur (`source='perso'`) ni de celle
  d'un critique ;
* les règles sont des DONNÉES versionnées (fichiers du dossier `donnees/`
  à venir), pas du code dispersé : une règle se corrige à un seul endroit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Estimation:
    """Réponse sourcée d'une règle."""
    valeur: dict                      # ex. {"debut": 2028, "apogee_debut": 2032, ...}
    explication_fr: str
    explication_en: str
    sources: list[str] = field(default_factory=list)
    regle: str = ""                   # identifiant stable de la règle appliquée
    modele: str | None = None         # « cloche », « plateau »… pour une fenêtre


class FournisseurRegles(Protocol):
    """Ce que la phase 3 implémentera. Chaque méthode renvoie None quand la
    règle ne sait pas répondre : jamais une valeur par défaut inventée."""

    identifiant: str

    def fenetre_degustation(self, vin: dict, bouteille: dict | None = None) -> Estimation | None: ...
    def service(self, vin: dict) -> Estimation | None: ...              # température, carafe, verre
    def conservation(self, vin: dict, bouteille: dict | None = None) -> Estimation | None: ...
    def accords_pour_vin(self, vin: dict) -> list[Estimation]: ...      # « j'ouvre ce vin »
    def vins_pour_plat(self, plat: str, vins: list[dict]) -> list[tuple[int, Estimation]]: ...
    def sens_niveau(self, code_niveau: str, age: int | None) -> Estimation | None: ...
    def bouteille_ouverte(self, vin: dict, conservation: str) -> Estimation | None: ...
    def convertir_note(self, note: float, de: str, vers: str) -> Estimation | None: ...


_fournisseurs: list[FournisseurRegles] = []


def inscrire(fournisseur: FournisseurRegles) -> None:
    _fournisseurs.append(fournisseur)


def retirer_tout() -> None:
    _fournisseurs.clear()


def disponibles() -> bool:
    return bool(_fournisseurs)


def demander(methode: str, *args, **kwargs):
    """Premier fournisseur qui sait répondre ; None si aucun (phase 1)."""
    for f in _fournisseurs:
        fn = getattr(f, methode, None)
        if fn is None:
            continue
        r = fn(*args, **kwargs)
        if r:
            return r
    return None
