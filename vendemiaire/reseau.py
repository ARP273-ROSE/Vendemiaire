# -*- coding: utf-8 -*-
"""Accès réseau des bases mondiales : poli, identifié, limité, et facultatif.

* **Hors ligne par défaut.** Rien ne part sur le réseau sans l'accord de
  l'utilisateur (`autoriser(True)`, demandé une fois par l'interface et retenu
  dans les réglages). Sans accord, toute requête lève `HorsLigne` ; la copie
  locale de LWIN et les registres d'appellations embarqués marchent sans réseau.
* **Identifié** : chaque requête porte un User-Agent qui nomme l'application,
  sa version et l'adresse de son dépôt (exigence de Wikimedia et d'Open Food
  Facts pour les clients automatiques).
* **Débit limité par hôte** : au plus une requête par seconde vers Wikidata,
  Wikimedia Commons et Open Food Facts ; une réponse 429/503 est respectée
  (en-tête Retry-After, plafonné) puis la requête est retentée une fois.
* **Jamais dans une transaction** : ces appels sont lents ; on lit le réseau,
  PUIS on écrit la base d'un bloc court (voir base.py).
* **Aucun aspirateur** : seuls des services qui publient une API ouverte sont
  interrogés (Wikidata, Commons, Open Food Facts, eAmbrosia, data.gouv). Ni
  Vivino ni Wine-Searcher : un bouton ouvre au plus leur page dans le
  navigateur.

Le transport est remplaçable (`Client(transport=...)`) : les essais simulent
le réseau sans jamais le toucher.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable

from . import __version__

log = logging.getLogger(__name__)

DEPOT = "https://github.com/ARP273-ROSE/Vendemiaire"
USER_AGENT = f"Vendemiaire/{__version__} (+{DEPOT})"

#: intervalle minimal entre deux requêtes vers un même hôte (secondes)
INTERVALLES = {
    "query.wikidata.org": 1.0,
    "www.wikidata.org": 1.0,
    "commons.wikimedia.org": 1.0,
    "upload.wikimedia.org": 1.0,
    "world.openfoodfacts.org": 1.0,
    "images.openfoodfacts.org": 0.5,
    "static.openfoodfacts.org": 0.5,
}
INTERVALLE_DEFAUT = 1.0
ATTENTE_MAX = 30.0          # Retry-After plafonné : jamais une minute d'interface muette
TAILLE_MAX = 64 * 1024 * 1024


class ErreurReseau(RuntimeError):
    """Le service n'a pas répondu ce qu'on attendait (code, délai, contenu)."""


class HorsLigne(ErreurReseau):
    """L'utilisateur n'a pas autorisé l'accès au réseau."""


@dataclass
class Reponse:
    statut: int
    entetes: dict
    corps: bytes

    def json(self):
        try:
            return json.loads(self.corps.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as e:
            # Open Food Facts répond une page HTML « temporairement indisponible »
            raise ErreurReseau(f"réponse non JSON ({self.corps[:60]!r})") from e


Transport = Callable[[str, dict, float], Reponse]


def transport_urllib(url: str, entetes: dict, delai: float) -> Reponse:
    req = urllib.request.Request(url, headers=entetes)
    try:
        with urllib.request.urlopen(req, timeout=delai) as r:
            corps = r.read(TAILLE_MAX + 1)
            if len(corps) > TAILLE_MAX:
                raise ErreurReseau(f"réponse trop grande : {url}")
            return Reponse(r.status, {k.lower(): v for k, v in r.headers.items()}, corps)
    except urllib.error.HTTPError as e:
        return Reponse(e.code, {k.lower(): v for k, v in (e.headers or {}).items()},
                       e.read() if hasattr(e, "read") else b"")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ErreurReseau(f"{url} : {e}") from e


_autorise = False


def autoriser(oui: bool) -> None:
    """Accord de l'utilisateur pour les recherches en ligne (retenu par l'interface)."""
    global _autorise
    _autorise = bool(oui)


def autorise() -> bool:
    return _autorise


class Client:
    """Requêtes HTTP GET identifiées, limitées par hôte, retentées une fois sur 429/503."""

    def __init__(self, transport: Transport | None = None, horloge=time.monotonic,
                 dormir=time.sleep, delai: float = 30.0, ignorer_accord: bool = False):
        self.transport = transport or transport_urllib
        self.horloge = horloge
        self.dormir = dormir
        self.delai = delai
        self.ignorer_accord = ignorer_accord
        self._derniere: dict[str, float] = {}
        self._verrou = threading.Lock()
        self.journal: list[str] = []          # URL demandées (essais, diagnostic)

    def _attendre_tour(self, hote: str) -> None:
        intervalle = INTERVALLES.get(hote, INTERVALLE_DEFAUT)
        with self._verrou:
            maintenant = self.horloge()
            prochain = self._derniere.get(hote, -1e9) + intervalle
            attente = max(0.0, prochain - maintenant)
            self._derniere[hote] = maintenant + attente
        if attente:
            self.dormir(attente)

    def get(self, url: str, params: dict | None = None, accepter: str = "*/*") -> Reponse:
        if not (self.ignorer_accord or _autorise):
            raise HorsLigne(url)
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        hote = urllib.parse.urlsplit(url).hostname or ""
        entetes = {"User-Agent": USER_AGENT, "Accept": accepter}
        for essai in (1, 2):
            self._attendre_tour(hote)
            self.journal.append(url)
            r = self.transport(url, entetes, self.delai)
            if r.statut in (429, 503) and essai == 1:
                try:
                    pause = float(r.entetes.get("retry-after", "5"))
                except ValueError:
                    pause = 5.0
                log.info("%s : %s, nouvel essai dans %.0f s", hote, r.statut, pause)
                self.dormir(min(ATTENTE_MAX, max(1.0, pause)))
                continue
            if r.statut >= 400:
                raise ErreurReseau(f"{hote} : HTTP {r.statut}")
            return r
        raise ErreurReseau(f"{hote} : service saturé")

    def json(self, url: str, params: dict | None = None):
        return self.get(url, params, accepter="application/json").json()


_client: Client | None = None


def client() -> Client:
    """Client partagé de l'application (le débit par hôte vaut pour tous)."""
    global _client
    if _client is None:
        _client = Client()
    return _client


def definir_client(c: Client | None) -> None:
    """Remplace le client partagé (essais : réseau simulé)."""
    global _client
    _client = c
