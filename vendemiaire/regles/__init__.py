# -*- coding: utf-8 -*-
"""Interface des règles d'œnologie (apogée, service, conservation, accords, niveaux).

Aucune règle n'est écrite dans le code : elles viennent du dossier « Le vin »
(données `donnees/*.json` copiées TELLES QUELLES depuis le dossier, avec leurs
sources), pour que l'application et le dossier disent la même chose. Tant
qu'aucun fournisseur ne sait répondre, l'interface affiche « règles à venir »
au lieu d'inventer une estimation.

Phase 2 : `donnees/notes.json` (conversion des notes des critiques, table
publiée par Decanter) — fournisseur `notes.FournisseurNotes`.
Phase 3 : tout le jeu du dossier (`donnees/*.json`, 194 règles, 69 sources),
copié par `outils/synchroniser_regles.py` et vérifié au chargement
(`jeu.py` : empreintes, identifiants, sources, styles) ; un module par sujet :
`styles` (classer un vin), `garde` (fenêtre, alertes, courbe d'apogée),
`service` (température, sortie de cave, carafe, verre, fiche « ce soir »),
`conservation` (cave, bouchons, bouteille ouverte), `niveaux`, `accords`,
`degustation` (défauts, roue des arômes). Libellés anglais : `anglais.py`.

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
    confiance: str | None = None      # haute, moyenne, faible (dossier)
    marge: dict = field(default_factory=dict)
    details_fr: list[str] = field(default_factory=list)   # étapes du calcul, lisibles
    details_en: list[str] = field(default_factory=list)

    @property
    def convention(self) -> bool:
        """Règle posée par le dossier faute de chiffre publié (source DOSSIER) :
        l'interface le dit et laisse l'utilisateur la changer."""
        return "DOSSIER" in (self.sources or [])

    def explication(self, langue: str = "fr") -> str:
        return self.explication_fr if langue == "fr" else (self.explication_en or self.explication_fr)

    def details(self, langue: str = "fr") -> list[str]:
        return self.details_fr if langue == "fr" else (self.details_en or self.details_fr)


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


def disponibles(methode: str | None = None) -> bool:
    """Un fournisseur est-il inscrit (et sait-il répondre à `methode`) ?"""
    if methode is None:
        return bool(_fournisseurs)
    return any(callable(getattr(f, methode, None)) for f in _fournisseurs)


def charger_livres() -> None:
    """Inscrit les fournisseurs livrés avec l'application (une seule fois) :
    les règles du dossier « Le vin », puis la conversion des notes."""
    from .dossier import FournisseurDossier
    from .notes import FournisseurNotes
    if not any(isinstance(f, FournisseurDossier) for f in _fournisseurs):
        inscrire(FournisseurDossier())
    if not any(isinstance(f, FournisseurNotes) for f in _fournisseurs):
        inscrire(FournisseurNotes())


def fournisseur_dossier():
    """Le fournisseur des règles du dossier (inscrit au besoin)."""
    from .dossier import FournisseurDossier
    charger_livres()
    return next(f for f in _fournisseurs if isinstance(f, FournisseurDossier))


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
