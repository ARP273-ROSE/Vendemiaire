# -*- coding: utf-8 -*-
"""Identification de toute la cave en une fois (1.0.2).

Deux temps, jamais mêlés :

1. `preparer` — LECTURES seulement (cave, copie LWIN, registres
   d'appellations ; Wikidata si l'utilisateur l'a permis), en tâche de fond,
   avec progression et annulation. Rien n'est écrit.
2. `appliquer` — après la validation de l'utilisateur, les choix cochés sont
   confirmés un par un : UNE transaction courte par vin (champs remplis,
   journal, identifiant), par la règle habituelle (`appariement.confirmer` :
   champs vides et non saisis à la main seulement, COALESCE).

Une ligne est « sûre » quand `appariement.decider` présélectionne un candidat
(score au-dessus du seuil, nettement devant le suivant, domaine et cuvée
concordants) : elle est cochée d'avance. Les autres sont « douteuses »
(signalées, non cochées) ou « sans candidat ».
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from . import appariement
from .appariement import Candidat, Decision

#: deuxième candidat montré à côté du premier s'il en est à moins de 0,10
ECART_PROCHE = 0.10

SURE, DOUTEUSE, AUCUN, DEJA = "sure", "douteuse", "aucun", "deja"


class Annule(Exception):
    """L'utilisateur a annulé la préparation : rien n'a été écrit."""


@dataclass
class LigneLot:
    vin_id: int
    nom: str
    decision: Decision
    lwin_actuel: str | None = None          # vin déjà identifié (option « aussi ceux-là »)
    wikidata: Decision | None = None        # domaine trouvé dans Wikidata (si permis)

    @property
    def active(self) -> Decision:
        """La décision montrée : LWIN, ou Wikidata (le domaine) quand LWIN n'a
        aucun candidat et que la recherche en ligne a été permise."""
        if not self.decision.candidats and self.wikidata is not None and self.wikidata.candidats:
            return self.wikidata
        return self.decision

    @property
    def meilleur(self) -> Candidat | None:
        c = self.active.candidats
        return c[0] if c else None

    @property
    def second(self) -> Candidat | None:
        """Le deuxième candidat, s'il est proche du premier (à montrer)."""
        c = self.active.candidats
        if len(c) > 1 and c[0].score - c[1].score < ECART_PROCHE:
            return c[1]
        return None

    @property
    def categorie(self) -> str:
        if self.lwin_actuel and self.meilleur is not None and self.meilleur.source == "lwin" \
                and self.meilleur.identifiant == self.lwin_actuel:
            return DEJA
        if self.active.choisi is not None and not self.lwin_actuel:
            return SURE
        return DOUTEUSE if self.active.candidats else AUCUN

    @property
    def coche_d_avance(self) -> bool:
        return self.categorie == SURE


@dataclass
class Bilan:
    """Ce que la validation a fait, vin par vin."""
    vins: int = 0
    champs: int = 0
    lignes: list = field(default_factory=list)      # (vin_id, nom, candidat, champs remplis)
    echecs: list = field(default_factory=list)      # (vin_id, nom, erreur)


# ---------------------------------------------------------------- choix des vins
def lwin_actuel(cave, vin_id: int) -> str | None:
    v = cave.vin(vin_id)
    if v is not None and v["lwin"]:
        return str(v["lwin"])
    ident = cave.base.valeur("SELECT valeur FROM identifiant_externe WHERE vin_id=? AND source='lwin'",
                             (vin_id,))
    return str(ident) if ident else None


def vins_a_identifier(cave, inclure_identifies: bool = False) -> list[int]:
    """Les vins sans identifiant LWIN (ni dans la fiche, ni confirmé) ; tous
    avec `inclure_identifies`."""
    if inclure_identifies:
        return [r[0] for r in cave.base.lire("SELECT id FROM vin ORDER BY id")]
    return [r[0] for r in cave.base.lire(
        "SELECT v.id FROM vin v WHERE COALESCE(v.lwin, '')='' AND NOT EXISTS ("
        "SELECT 1 FROM identifiant_externe i WHERE i.vin_id=v.id AND i.source='lwin') ORDER BY v.id")]


# ---------------------------------------------------------------- préparation (lectures)
def preparer(cave, vin_ids: list[int], *, wikidata_client=None, langue: str = "fr",
             progression: Callable[[int, int], None] | None = None,
             annule: Callable[[], bool] | None = None) -> list[LigneLot]:
    """Candidats de chaque vin, SANS RIEN ÉCRIRE. LWIN local d'abord (avec les
    registres d'appellations pour l'appellation proposée) ; puis, seulement si
    `wikidata_client` est fourni (accord réseau donné), le domaine dans
    Wikidata pour les vins sans aucun candidat LWIN — une recherche par
    domaine, au débit du client (une requête par seconde au plus).

    `annule()` vrai : lève `Annule` (rien n'a été écrit, il n'y a rien à défaire)."""
    refs = cave.references
    avec_lwin = bool(refs.nb_lwin())
    officielle = refs.appellation_officielle
    sortie: list[LigneLot] = []
    deja_vus: dict[str, Decision] = {}
    total = len(vin_ids)
    for i, vin_id in enumerate(vin_ids):
        if annule and annule():
            raise Annule()
        requete = appariement.requete_depuis_vin(cave, vin_id)
        if not requete:
            continue
        candidats = appariement.candidats_lwin(refs, requete, appellation_officielle=officielle) \
            if avec_lwin else []
        ligne = LigneLot(vin_id, cave.nom_vin(vin_id), appariement.decider(candidats),
                         lwin_actuel(cave, vin_id))
        if wikidata_client is not None and not ligne.decision.candidats and requete.get("producteur"):
            cle = (requete["producteur"] or "").strip().lower()
            if cle not in deja_vus:
                from . import wikidata
                try:
                    deja_vus[cle] = appariement.decider(wikidata.candidats(
                        wikidata_client, "producteur", requete["producteur"], requete.get("pays"),
                        langue))
                except Exception:                       # réseau : le lot continue sans Wikidata
                    deja_vus[cle] = Decision([], None, "aucun")
            ligne.wikidata = deja_vus[cle]
        sortie.append(ligne)
        if progression:
            progression(i + 1, total)
        if i % 20 == 19:
            time.sleep(0)                               # rendre la main au fil de l'interface
    return sortie


# ---------------------------------------------------------------- validation (écritures)
def appliquer(cave, choix: list[tuple[int, Candidat]], explication: Callable[[Candidat], str],
              nom: Callable[[int], str] | None = None,
              annule: Callable[[], bool] | None = None) -> Bilan:
    """Confirme chaque (vin, candidat LWIN) choisi par l'utilisateur. Une
    transaction par vin (`appariement.confirmer`) : un vin en échec n'empêche
    pas les autres et ne laisse rien à moitié écrit. Tous les champs proposés
    sont demandés ; `completer_vin` ne remplit que les vides non manuels."""
    bilan = Bilan()
    for vin_id, c in choix:
        if annule and annule():
            break
        libelle = nom(vin_id) if nom else str(vin_id)
        try:
            if c.source == "wikidata":
                remplis = _confirmer_wikidata(cave, vin_id, c, explication(c))
            else:
                remplis = appariement.confirmer(cave, vin_id, c, list(c.donnees), explication(c))
        except Exception as e:                          # noqa: BLE001 — noté au bilan
            bilan.echecs.append((vin_id, libelle, str(e)))
            continue
        bilan.vins += 1
        bilan.champs += len(remplis)
        bilan.lignes.append((vin_id, libelle, c, remplis))
        time.sleep(0.02)                                # le verrou de la base pour les autres fils
    return bilan


def _confirmer_wikidata(cave, vin_id: int, c: Candidat, explication: str) -> list[str]:
    """Le domaine trouvé dans Wikidata : fiche, champs vides du producteur et
    identifiant, dans une seule transaction. L'image de Commons n'est pas
    téléchargée ici (écran d'identification du vin, à la demande)."""
    from . import wikidata
    pid = cave.vin(vin_id)["producteur_id"]
    if not pid:
        raise KeyError("producteur")
    fiche = {"source": "wikidata", "identifiant": c.identifiant, "objet": "producteur",
             "donnees": dict(c.brut), "nom": c.brut.get("nom"), "licence": wikidata.LICENCE,
             "url": c.url}
    return cave.completer_producteur(pid, c.donnees, "wikidata", f"wikidata:{c.identifiant}",
                                     fiche=fiche, identifiant={
                                         "vin_id": vin_id, "source": "wikidata_producteur",
                                         "valeur": c.identifiant, "score": c.score,
                                         "explication": explication})
