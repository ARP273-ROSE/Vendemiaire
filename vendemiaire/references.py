# -*- coding: utf-8 -*-
"""Base de RÉFÉRENCE locale : copie de LWIN et registres officiels des appellations.

Fichier séparé de la cave (`references.db`, à côté de `cave.db`) :

* ce sont des données **publiques et retéléchargeables** : elles n'ont rien à
  faire dans les sauvegardes de la cave (copiées toutes les 30 minutes) ni
  dans ses exports ;
* l'importation de LWIN (≈ 200 000 vins) se fait dans UNE transaction de ce
  fichier-ci, dans un fil de fond : la cave reste disponible pendant ce temps,
  et un import interrompu laisse l'ancienne copie intacte ;
* recherche **hors ligne** en texte intégral (FTS5 de SQLite quand il est
  présent, sinon une recherche par mots sur les formes normalisées).

Les formes normalisées sont celles de `base.normaliser` (accents, casse,
« Château », « Domaine », abréviations « St », « 1er »…), les mêmes que celles
de la cave : on compare toujours des formes normalisées, jamais l'orthographe
brute.
"""
from __future__ import annotations

import contextlib
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Callable, Iterable

from .base import maintenant, normaliser

log = logging.getLogger(__name__)

VERSION_REFERENCES = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (cle TEXT PRIMARY KEY, valeur TEXT);

-- Copie locale de la base LWIN de Liv-ex (licence CC BY 4.0)
CREATE TABLE IF NOT EXISTS lwin (
    id                  INTEGER PRIMARY KEY,   -- = int(lwin)
    lwin                TEXT NOT NULL,         -- LWIN-7, tel que publié
    statut              TEXT,
    nom                 TEXT,                  -- DISPLAY_NAME
    titre_producteur    TEXT,                  -- « Chateau », « Domaine »…
    producteur          TEXT,
    vin                 TEXT,
    pays                TEXT,
    region              TEXT,
    sous_region         TEXT,
    site                TEXT,
    parcelle            TEXT,
    couleur             TEXT,                  -- codes Vendémiaire (rouge, blanc…) ou NULL
    type                TEXT,                  -- codes Vendémiaire (tranquille, effervescent…)
    type_lwin           TEXT,                  -- TYPE et SUB_TYPE d'origine
    designation         TEXT,
    classement          TEXT,
    config_millesime    TEXT,
    premier_millesime   INTEGER,
    dernier_millesime   INTEGER,
    maj                 TEXT,
    producteur_norm     TEXT,
    vin_norm            TEXT,
    texte               TEXT                   -- forme normalisée de tout ce qui se cherche
);
CREATE INDEX IF NOT EXISTS lwin_producteur ON lwin(producteur_norm);

-- Registres officiels des appellations (INAO, eAmbrosia)
CREATE TABLE IF NOT EXISTS appellation (
    id              INTEGER PRIMARY KEY,
    registre        TEXT NOT NULL,          -- inao, eambrosia
    nom             TEXT NOT NULL,          -- orthographe officielle
    nom_norm        TEXT NOT NULL,
    parent          TEXT,                   -- appellation dont c'est une dénomination
    signe           TEXT,                   -- AOP, IGP, AOC, IG, PDO, PGI, GI
    pays            TEXT,                   -- code ISO (FR, IT…)
    identifiant     TEXT,                   -- PDO-FR-A0994, id INAO…
    statut          TEXT,
    categories      TEXT
);
CREATE INDEX IF NOT EXISTS appellation_norm ON appellation(nom_norm);
CREATE INDEX IF NOT EXISTS appellation_registre ON appellation(registre);

-- Réponses des services en ligne gardées quelque temps (poli envers eux,
-- utile hors ligne)
CREATE TABLE IF NOT EXISTS cache_http (
    url     TEXT PRIMARY KEY,
    date    TEXT NOT NULL,
    corps   BLOB
);
"""

#: colonnes cherchées dans la table plein texte
FTS = ("CREATE VIRTUAL TABLE IF NOT EXISTS lwin_fts USING fts5("
       "texte, content='lwin', content_rowid='id', tokenize='unicode61 remove_diacritics 2')")


def fts5_disponible() -> bool:
    try:
        c = sqlite3.connect(":memory:")
        c.execute("CREATE VIRTUAL TABLE t USING fts5(a)")
        c.close()
        return True
    except sqlite3.Error:
        return False


class References:
    """Accès à references.db. Les lectures sont permises depuis n'importe quel
    fil (une connexion par fil) ; les écritures (imports) sont de longues
    transactions de CE fichier, jamais de la cave."""

    def __init__(self, chemin: str | Path):
        self.chemin = Path(chemin)
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._ecriture = threading.Lock()
        c = self.connexion()
        with self._transaction(c):
            for instr in SCHEMA.split(";"):
                if instr.strip():
                    c.execute(instr)
            self.fts = fts5_disponible()
            if self.fts:
                c.execute(FTS)
            c.execute(f"PRAGMA user_version={VERSION_REFERENCES}")

    # -- connexions -----------------------------------------------------------
    def connexion(self) -> sqlite3.Connection:
        c = getattr(self._local, "c", None)
        if c is None:
            c = sqlite3.connect(str(self.chemin), timeout=10, isolation_level=None,
                                check_same_thread=False)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=DELETE")      # partage réseau : jamais WAL
            c.execute("PRAGMA busy_timeout=10000")
            self._local.c = c
        return c

    def fermer(self) -> None:
        c = getattr(self._local, "c", None)
        if c is not None:
            c.close()
            self._local.c = None

    @contextlib.contextmanager
    def _transaction(self, c):
        with self._ecriture:
            c.execute("BEGIN IMMEDIATE")
            try:
                yield c
            except BaseException:
                c.execute("ROLLBACK")
                raise
            else:
                c.execute("COMMIT")

    def lire(self, sql: str, params: Iterable = ()) -> list[sqlite3.Row]:
        return self.connexion().execute(sql, tuple(params)).fetchall()

    def valeur(self, sql: str, params: Iterable = ()):
        r = self.connexion().execute(sql, tuple(params)).fetchone()
        return None if r is None else r[0]

    def meta(self, cle: str, defaut: str | None = None) -> str | None:
        v = self.valeur("SELECT valeur FROM meta WHERE cle=?", (cle,))
        return defaut if v is None else v

    def definir_meta(self, cle: str, valeur: str) -> None:
        c = self.connexion()
        with self._transaction(c):
            c.execute("INSERT INTO meta(cle, valeur) VALUES(?,?) ON CONFLICT(cle) "
                      "DO UPDATE SET valeur=excluded.valeur", (cle, valeur))

    # =====================================================================
    # LWIN
    # =====================================================================
    def nb_lwin(self) -> int:
        return self.valeur("SELECT COUNT(*) FROM lwin") or 0

    def remplacer_lwin(self, lignes: Iterable[dict], source: str = "",
                       progression: Callable[[int], None] | None = None,
                       annule: Callable[[], bool] | None = None) -> int:
        """Remplace TOUTE la copie LWIN, tout ou rien (une transaction de ce
        fichier). `lignes` : dictionnaires déjà convertis (voir mondial.lwin)."""
        c = self.connexion()
        n = 0
        cols = ("id", "lwin", "statut", "nom", "titre_producteur", "producteur", "vin", "pays",
                "region", "sous_region", "site", "parcelle", "couleur", "type", "type_lwin",
                "designation", "classement", "config_millesime", "premier_millesime",
                "dernier_millesime", "maj", "producteur_norm", "vin_norm", "texte")
        sql = (f"INSERT OR REPLACE INTO lwin({','.join(cols)}) "
               f"VALUES({','.join('?' * len(cols))})")
        with self._transaction(c):
            c.execute("DELETE FROM lwin")
            lot = []
            for l in lignes:
                if annule and annule():
                    raise InterruptedError("import LWIN annulé")
                lot.append(tuple(l.get(k) for k in cols))
                if len(lot) >= 2000:
                    c.executemany(sql, lot)
                    n += len(lot)
                    lot.clear()
                    if progression:
                        progression(n)
            if lot:
                c.executemany(sql, lot)
                n += len(lot)
            if self.fts:
                c.execute("INSERT INTO lwin_fts(lwin_fts) VALUES('rebuild')")
            for cle, val in (("lwin_date", maintenant()), ("lwin_lignes", str(n)),
                             ("lwin_source", source)):
                c.execute("INSERT INTO meta(cle, valeur) VALUES(?,?) ON CONFLICT(cle) "
                          "DO UPDATE SET valeur=excluded.valeur", (cle, val))
        if progression:
            progression(n)
        log.info("LWIN : %d vins importés (%s)", n, source)
        return n

    def lwin(self, code: str | int) -> dict | None:
        try:
            ident = int(str(code)[:7])
        except ValueError:
            return None
        r = self.lire("SELECT * FROM lwin WHERE id=?", (ident,))
        return dict(r[0]) if r else None

    def rechercher_lwin(self, texte: str, limite: int = 60) -> list[dict]:
        """Candidats LWIN pour un texte libre (producteur, cuvée, appellation,
        texte lu sur l'étiquette). Le classement fin est fait par
        `mondial.appariement` : ici on ratisse large, sans juger."""
        mots = [m for m in dict.fromkeys(normaliser(texte).split()) if len(m) >= 2]
        if not mots:
            return []
        if self.fts:
            requete = " OR ".join(f'"{m}"' + ("*" if len(m) >= 4 else "") for m in mots[:12])
            try:
                lignes = self.lire(
                    "SELECT l.* FROM lwin_fts f JOIN lwin l ON l.id=f.rowid "
                    "WHERE lwin_fts MATCH ? ORDER BY bm25(lwin_fts) LIMIT ?",
                    (requete, limite))
                return [dict(r) for r in lignes]
            except sqlite3.OperationalError:
                log.exception("recherche FTS")
        # sans FTS5 : les mots les plus longs (les plus distinctifs) d'abord
        longs = sorted(mots, key=len, reverse=True)[:3]
        sql = "SELECT * FROM lwin WHERE " + " OR ".join("texte LIKE ?" for _ in longs) + " LIMIT ?"
        return [dict(r) for r in self.lire(sql, [f"%{m}%" for m in longs] + [limite * 4])][:limite]

    # =====================================================================
    # Appellations
    # =====================================================================
    def remplacer_appellations(self, registre: str, lignes: Iterable[dict], source: str = "") -> int:
        c = self.connexion()
        n = 0
        with self._transaction(c):
            c.execute("DELETE FROM appellation WHERE registre=?", (registre,))
            for l in lignes:
                nom = (l.get("nom") or "").strip()
                if not nom:
                    continue
                c.execute("INSERT INTO appellation(registre, nom, nom_norm, parent, signe, pays, "
                          "identifiant, statut, categories) VALUES(?,?,?,?,?,?,?,?,?)",
                          (registre, nom, normaliser_appellation(nom), l.get("parent"),
                           l.get("signe"), l.get("pays"), l.get("identifiant"), l.get("statut"),
                           l.get("categories")))
                n += 1
            for cle, val in ((f"appellations_{registre}_date", maintenant()),
                             (f"appellations_{registre}_lignes", str(n)),
                             (f"appellations_{registre}_source", source)):
                c.execute("INSERT INTO meta(cle, valeur) VALUES(?,?) ON CONFLICT(cle) "
                          "DO UPDATE SET valeur=excluded.valeur", (cle, val))
        return n

    def nb_appellations(self, registre: str | None = None) -> int:
        if registre:
            return self.valeur("SELECT COUNT(*) FROM appellation WHERE registre=?", (registre,)) or 0
        return self.valeur("SELECT COUNT(*) FROM appellation") or 0

    def noms_appellations(self, pays: str | None = None) -> list[str]:
        """Orthographes officielles, sans doublon (pour la complétion)."""
        sql = "SELECT DISTINCT nom FROM appellation"
        params: list = []
        if pays:
            sql += " WHERE pays=?"
            params.append(pays)
        return [r[0] for r in self.lire(sql + " ORDER BY nom COLLATE NOCASE", params)]

    def appellation_officielle(self, nom: str | None) -> dict | None:
        """L'appellation officielle dont la forme normalisée est celle-ci (INAO
        d'abord, qui écrit l'orthographe française)."""
        n = normaliser_appellation(nom)
        if not n:
            return None
        r = self.lire("SELECT * FROM appellation WHERE nom_norm=? "
                      "ORDER BY registre='inao' DESC, parent IS NOT NULL, id LIMIT 1", (n,))
        return dict(r[0]) if r else None

    def appellations_dans(self, texte: str) -> list[dict]:
        """Appellations officielles dont le nom figure dans un texte (étiquette
        lue par l'OCR) : les plus longues d'abord (« Puligny-Montrachet
        premier cru » avant « Montrachet »)."""
        t = f" {normaliser_appellation(texte)} "
        if not t.strip():
            return []
        trouvees = []
        for r in self.lire("SELECT DISTINCT nom, nom_norm, signe, pays, registre FROM appellation "
                           "WHERE length(nom_norm) >= 4"):
            if f" {r['nom_norm']} " in t:
                trouvees.append(dict(r))
        trouvees.sort(key=lambda r: len(r["nom_norm"]), reverse=True)
        retenues: list[dict] = []
        for r in trouvees:
            if not any(r["nom_norm"] in x["nom_norm"] for x in retenues) \
                    and all(r["nom"] != x["nom"] for x in retenues):
                retenues.append(r)
        return retenues

    # =====================================================================
    # Cache des réponses en ligne
    # =====================================================================
    def cache_lire(self, url: str, age_max_jours: float = 30) -> bytes | None:
        r = self.lire("SELECT corps FROM cache_http WHERE url=? AND "
                      "julianday('now','localtime') - julianday(date) <= ?", (url, age_max_jours))
        return bytes(r[0][0]) if r else None

    def cache_ecrire(self, url: str, corps: bytes) -> None:
        c = self.connexion()
        with self._transaction(c):
            c.execute("INSERT INTO cache_http(url, date, corps) VALUES(?,?,?) ON CONFLICT(url) "
                      "DO UPDATE SET date=excluded.date, corps=excluded.corps",
                      (url, maintenant(), corps))


def normaliser_appellation(nom: str | None) -> str:
    """Forme de comparaison d'une appellation : celle des noms, mais sans retirer
    les articles (« Côtes du Rhône », « Vin de Savoie » perdraient leur sens)."""
    import re
    import unicodedata
    if not nom:
        return ""
    t = unicodedata.normalize("NFKD", nom)
    t = "".join(ch for ch in t if not unicodedata.combining(ch)).lower()
    t = t.replace("œ", "oe").replace("æ", "ae")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    mots = [{"st": "saint", "ste": "sainte", "1er": "premier"}.get(m, m) for m in t.split()]
    return " ".join(mots)
