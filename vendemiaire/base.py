# -*- coding: utf-8 -*-
"""Base SQLite de Vendémiaire : schéma versionné, un seul écrivain, transactions courtes.

Règles (payées sur d'autres applications, voir PROGRESSION.md) :

* **Un seul écrivain.** SQLite n'admet qu'une écriture à la fois. L'application
  pose un verrou d'instance unique (QLockFile) ; la base vérifie en plus, avec
  une connexion jetable et quatre secondes de patience, que personne d'autre
  ne tient le verrou d'écriture (`ecrivain_disponible`) — jamais deux minutes
  d'écran noir muet.
* **Lire, puis écrire d'un bloc.** `ecriture()` ouvre une transaction
  `BEGIN IMMEDIATE`, la valide ou l'annule ; on n'y fait JAMAIS d'entrée-sortie
  de fichier ni de réseau. Les lectures passent par `lire()` / `un()`.
* **Journal en mode DELETE**, jamais WAL : la base peut vivre sur un partage
  réseau (SMB), où le fichier `-shm` du mode WAL n'existe pas.
* **Schéma versionné** par `PRAGMA user_version` ; chaque migration est une
  fonction numérotée, appliquée dans l'ordre, dans sa propre transaction. Une
  base plus récente que l'application est refusée (jamais « réparée » en
  silence).
"""
from __future__ import annotations

import collections
import contextlib
import logging
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

log = logging.getLogger(__name__)


class BaseTropRecente(RuntimeError):
    """La base a été écrite par une version plus récente de l'application."""


class EcrivainOccupe(RuntimeError):
    """Une autre copie de l'application écrit dans la base."""


class _VerrouEquitable:
    """Verrou réentrant qui sert les fils dans leur ordre d'arrivée.

    `threading.Lock` n'est pas équitable : un travail de fond qui enchaîne les
    écritures reprend le verrou aussitôt relâché et affame l'interface
    (repris de MusicOthèque, mesure : attente médiane 1,03 ms -> 0,04 ms).
    """

    def __init__(self):
        self._interne = threading.Lock()
        self._file: collections.deque = collections.deque()
        self._proprietaire = None
        self._compte = 0

    def acquire(self):
        moi = threading.get_ident()
        with self._interne:
            if self._proprietaire == moi:
                self._compte += 1
                return True
            jeton = threading.Event()
            libre = not self._file
            self._file.append(jeton)
            if libre:
                self._proprietaire, self._compte = moi, 1
        if not libre:
            jeton.wait()
            with self._interne:
                self._proprietaire, self._compte = moi, 1
        return True

    def release(self):
        with self._interne:
            if self._proprietaire != threading.get_ident():
                return
            self._compte -= 1
            if self._compte > 0:
                return
            self._proprietaire = None
            if self._file:
                self._file.popleft()
            if self._file:
                self._file[0].set()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *_):
        self.release()


def maintenant() -> str:
    """Horodatage local ISO, à la seconde."""
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


# ---------------------------------------------------------------------------
# Schéma
# ---------------------------------------------------------------------------

SCHEMA_V1 = """
-- Réglages internes de la base (pas ceux de l'interface, qui vivent dans QSettings)
CREATE TABLE meta (
    cle     TEXT PRIMARY KEY,
    valeur  TEXT
);

-- Producteurs : domaines, châteaux, maisons, coopératives
CREATE TABLE producteur (
    id              INTEGER PRIMARY KEY,
    nom             TEXT NOT NULL,
    pays            TEXT,
    region          TEXT,
    adresse         TEXT,
    site_web        TEXT,
    notes           TEXT,
    cree_le         TEXT NOT NULL,
    modifie_le      TEXT NOT NULL
);
CREATE INDEX producteur_nom ON producteur(nom COLLATE NOCASE);

-- Un vin = une cuvée d'un producteur dans un millésime (comme « iWine » chez CellarTracker)
CREATE TABLE vin (
    id              INTEGER PRIMARY KEY,
    producteur_id   INTEGER REFERENCES producteur(id) ON DELETE SET NULL,
    cuvee           TEXT,
    appellation     TEXT,
    region          TEXT,
    sous_region     TEXT,
    pays            TEXT,
    classement      TEXT,                      -- grand cru classé, premier cru…
    couleur         TEXT,                      -- referentiels.ENUMS['couleur']
    type            TEXT DEFAULT 'tranquille', -- referentiels.ENUMS['type']
    millesime       INTEGER,                   -- NULL = non millésimé (voir non_millesime)
    non_millesime   INTEGER NOT NULL DEFAULT 0,
    degre           REAL,
    lwin            TEXT,                      -- LWIN-7 (vin), le LWIN-11 s'en déduit avec le millésime
    ean             TEXT,                      -- code-barres de la bouteille
    seuil_reassort  INTEGER,                   -- « garder au moins N bouteilles »
    coup_de_coeur   INTEGER NOT NULL DEFAULT 0,
    notes           TEXT,
    cree_le         TEXT NOT NULL,
    modifie_le      TEXT NOT NULL,
    CHECK (millesime IS NULL OR (millesime BETWEEN 1700 AND 2200)),
    CHECK (degre IS NULL OR (degre >= 0 AND degre <= 30))
);
CREATE INDEX vin_producteur ON vin(producteur_id);
CREATE INDEX vin_appellation ON vin(appellation COLLATE NOCASE);
CREATE INDEX vin_lwin ON vin(lwin);

CREATE TABLE vin_cepage (
    vin_id          INTEGER NOT NULL REFERENCES vin(id) ON DELETE CASCADE,
    rang            INTEGER NOT NULL,
    cepage          TEXT NOT NULL,
    pourcentage     REAL,
    PRIMARY KEY (vin_id, rang),
    CHECK (pourcentage IS NULL OR (pourcentage >= 0 AND pourcentage <= 100))
);

-- Identifiants mondiaux et externes (LWIN, Wikidata, Open Food Facts, CellarTracker…)
CREATE TABLE identifiant_externe (
    id              INTEGER PRIMARY KEY,
    vin_id          INTEGER REFERENCES vin(id) ON DELETE CASCADE,
    producteur_id   INTEGER REFERENCES producteur(id) ON DELETE CASCADE,
    source          TEXT NOT NULL,             -- lwin, wikidata, off, cellartracker, url…
    valeur          TEXT NOT NULL,
    confirme        INTEGER NOT NULL DEFAULT 0, -- 1 = confirmé par l'utilisateur
    score           REAL,
    explication     TEXT,
    date            TEXT NOT NULL,
    CHECK (vin_id IS NOT NULL OR producteur_id IS NOT NULL)
);
CREATE UNIQUE INDEX identifiant_unique ON identifiant_externe(
    COALESCE(vin_id, 0), COALESCE(producteur_id, 0), source, valeur);

-- Caves et emplacements hiérarchiques : cave › meuble › casier (rangées × colonnes)
CREATE TABLE emplacement (
    id              INTEGER PRIMARY KEY,
    parent_id       INTEGER REFERENCES emplacement(id) ON DELETE RESTRICT,
    niveau          TEXT NOT NULL,             -- cave, meuble, casier
    nom             TEXT NOT NULL,
    rangees         INTEGER,                   -- casier seulement
    colonnes        INTEGER,
    ordre           INTEGER NOT NULL DEFAULT 0,
    notes           TEXT,
    CHECK (niveau IN ('cave', 'meuble', 'casier')),
    CHECK (rangees IS NULL OR rangees BETWEEN 1 AND 200),
    CHECK (colonnes IS NULL OR colonnes BETWEEN 1 AND 200)
);
CREATE INDEX emplacement_parent ON emplacement(parent_id);

-- Bouteilles individuelles
CREATE TABLE bouteille (
    id                  INTEGER PRIMARY KEY,
    vin_id              INTEGER NOT NULL REFERENCES vin(id) ON DELETE RESTRICT,
    format              TEXT NOT NULL DEFAULT 'bouteille',
    statut              TEXT NOT NULL DEFAULT 'en_cave',
    emplacement_id      INTEGER REFERENCES emplacement(id) ON DELETE SET NULL,
    rangee              INTEGER,
    colonne             INTEGER,
    prix_achat          REAL,
    devise              TEXT NOT NULL DEFAULT 'EUR',
    lieu_achat          TEXT,
    date_achat          TEXT,
    date_entree         TEXT,
    date_livraison_prevue TEXT,                -- primeurs et commandes en attente
    date_sortie         TEXT,
    niveau              TEXT,                  -- échelle bordelaise (referentiels 'niveau')
    niveau_cm           REAL,                  -- bouteille bourguignonne : cm sous le bouchon
    etat_etiquette      TEXT,
    etat_capsule        TEXT,
    etat_bouchon        TEXT,
    caisse              TEXT,                  -- cbo, carton_origine…
    caisse_complete     INTEGER,
    caisse_ref          TEXT,                  -- repère de la caisse (même caisse = même repère)
    provenance          TEXT,                  -- origine de l'achat
    historique_stockage TEXT,                  -- « achetée au domaine, jamais déplacée »
    facture             TEXT,                  -- référence ou fichier de la facture
    code_interne        TEXT UNIQUE,           -- code QR des étiquettes de casier
    bin                 TEXT,                  -- numéro de référence (carte des vins)
    notes               TEXT,
    cree_le             TEXT NOT NULL,
    modifie_le          TEXT NOT NULL,
    CHECK (rangee IS NULL OR rangee >= 1),
    CHECK (colonne IS NULL OR colonne >= 1),
    CHECK (niveau_cm IS NULL OR niveau_cm >= 0),
    CHECK (prix_achat IS NULL OR prix_achat >= 0)
);
CREATE INDEX bouteille_vin ON bouteille(vin_id);
CREATE INDEX bouteille_statut ON bouteille(statut);
-- une case de casier ne porte qu'une bouteille présente
CREATE UNIQUE INDEX bouteille_case ON bouteille(emplacement_id, rangee, colonne)
    WHERE rangee IS NOT NULL AND colonne IS NOT NULL AND statut = 'en_cave';

-- Historique des déplacements (un « lot » regroupe un déplacement en masse)
CREATE TABLE deplacement (
    id              INTEGER PRIMARY KEY,
    bouteille_id    INTEGER NOT NULL REFERENCES bouteille(id) ON DELETE CASCADE,
    date            TEXT NOT NULL,
    de_emplacement  INTEGER,
    de_rangee       INTEGER,
    de_colonne      INTEGER,
    vers_emplacement INTEGER,
    vers_rangee     INTEGER,
    vers_colonne    INTEGER,
    lot             TEXT,
    motif           TEXT
);
CREATE INDEX deplacement_bouteille ON deplacement(bouteille_id);

-- Séances de dégustation (verticale, horizontale, à l'aveugle) — utilisées en phase 3
CREATE TABLE seance (
    id              INTEGER PRIMARY KEY,
    type            TEXT NOT NULL,             -- verticale, horizontale, aveugle, libre
    titre           TEXT,
    date            TEXT,
    notes           TEXT
);

-- Fiche de dégustation structurée (robe, nez, bouche, finale, arômes)
CREATE TABLE degustation (
    id              INTEGER PRIMARY KEY,
    vin_id          INTEGER NOT NULL REFERENCES vin(id) ON DELETE CASCADE,
    bouteille_id    INTEGER REFERENCES bouteille(id) ON DELETE SET NULL,
    seance_id       INTEGER REFERENCES seance(id) ON DELETE SET NULL,
    date            TEXT NOT NULL,
    robe            TEXT,
    nez             TEXT,
    bouche          TEXT,
    finale          TEXT,
    aromes          TEXT,                      -- codes de la roue des arômes, séparés par « ; »
    note            REAL,
    echelle         TEXT,                      -- 20, 100, 5
    commentaire     TEXT,
    privee          INTEGER NOT NULL DEFAULT 1,
    aveugle         INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX degustation_vin ON degustation(vin_id);

-- Livre de cave : toutes les entrées et sorties
CREATE TABLE mouvement (
    id              INTEGER PRIMARY KEY,
    date            TEXT NOT NULL,
    type            TEXT NOT NULL,             -- referentiels.ENUMS['mouvement']
    vin_id          INTEGER REFERENCES vin(id) ON DELETE SET NULL,
    bouteille_id    INTEGER REFERENCES bouteille(id) ON DELETE SET NULL,
    quantite        INTEGER NOT NULL DEFAULT 1,
    prix            REAL,
    occasion        TEXT,
    convives        TEXT,
    plat            TEXT,
    lieu            TEXT,
    note            REAL,
    echelle         TEXT,
    commentaire     TEXT,
    degustation_id  INTEGER REFERENCES degustation(id) ON DELETE SET NULL,
    cree_le         TEXT NOT NULL
);
CREATE INDEX mouvement_date ON mouvement(date);
CREATE INDEX mouvement_vin ON mouvement(vin_id);

-- Notes des critiques, avec leur échelle
CREATE TABLE note_critique (
    id              INTEGER PRIMARY KEY,
    vin_id          INTEGER NOT NULL REFERENCES vin(id) ON DELETE CASCADE,
    critique        TEXT NOT NULL,             -- RP, WS, JR… ou nom libre
    note            REAL,
    note_max        REAL,                      -- haut d'une fourchette « 94-96 »
    echelle         TEXT NOT NULL,             -- 20, 100, 5, 3
    texte           TEXT,
    date            TEXT,
    source          TEXT
);
CREATE INDEX note_critique_vin ON note_critique(vin_id);

-- Fenêtres de dégustation : la mienne, celle des critiques, celle calculée
CREATE TABLE fenetre_degustation (
    id              INTEGER PRIMARY KEY,
    vin_id          INTEGER NOT NULL REFERENCES vin(id) ON DELETE CASCADE,
    source          TEXT NOT NULL,             -- perso, critique, calcul
    detail_source   TEXT NOT NULL DEFAULT '',  -- nom du critique, identifiant de la règle
    debut           INTEGER,                   -- années
    apogee_debut    INTEGER,
    apogee_fin      INTEGER,
    fin             INTEGER,
    modele          TEXT,                      -- cloche, plateau (phase 3)
    explication     TEXT,                      -- le « pourquoi » de l'estimation
    date            TEXT NOT NULL,
    UNIQUE (vin_id, source, detail_source),
    CHECK (debut IS NULL OR fin IS NULL OR debut <= fin)
);

-- Valeurs datées et sourcées (prix de marché, estimation)
CREATE TABLE valeur (
    id              INTEGER PRIMARY KEY,
    vin_id          INTEGER NOT NULL REFERENCES vin(id) ON DELETE CASCADE,
    format          TEXT NOT NULL DEFAULT 'bouteille',
    montant         REAL NOT NULL,
    devise          TEXT NOT NULL DEFAULT 'EUR',
    date            TEXT NOT NULL,
    source          TEXT NOT NULL,             -- saisie, import, nom du site…
    url             TEXT,
    note            TEXT,
    CHECK (montant >= 0)
);
CREATE INDEX valeur_vin ON valeur(vin_id, date);

-- Liste d'envies (et « cave idéale »)
CREATE TABLE envie (
    id              INTEGER PRIMARY KEY,
    vin_id          INTEGER REFERENCES vin(id) ON DELETE SET NULL,
    producteur      TEXT,
    cuvee           TEXT,
    appellation     TEXT,
    millesime       INTEGER,
    quantite        INTEGER,
    prix_max        REAL,
    priorite        INTEGER NOT NULL DEFAULT 2,
    notes           TEXT,
    cree_le         TEXT NOT NULL,
    satisfaite_le   TEXT
);

-- Bouteilles ouvertes : ce qui reste, comment elle est conservée
CREATE TABLE bouteille_ouverte (
    id              INTEGER PRIMARY KEY,
    bouteille_id    INTEGER NOT NULL REFERENCES bouteille(id) ON DELETE CASCADE,
    ouverte_le      TEXT NOT NULL,
    reste_cl        REAL,
    conservation    TEXT,                      -- bouchon, gaz, coravin, vide
    a_finir_avant   TEXT,                      -- estimation (phase 3, règles du dossier)
    finie_le        TEXT
);

-- Conditions de cave : température, hygrométrie (saisie ou import)
CREATE TABLE condition_cave (
    id              INTEGER PRIMARY KEY,
    emplacement_id  INTEGER REFERENCES emplacement(id) ON DELETE CASCADE,
    date_heure      TEXT NOT NULL,
    temperature     REAL,
    hygrometrie     REAL,
    source          TEXT,
    CHECK (hygrometrie IS NULL OR (hygrometrie >= 0 AND hygrometrie <= 100))
);
CREATE INDEX condition_cave_date ON condition_cave(emplacement_id, date_heure);

-- Inventaires de contrôle (compter un casier, écarts)
CREATE TABLE inventaire (
    id              INTEGER PRIMARY KEY,
    emplacement_id  INTEGER REFERENCES emplacement(id) ON DELETE CASCADE,
    date            TEXT NOT NULL,
    attendu         INTEGER,
    compte          INTEGER,
    ecarts          TEXT
);

-- Images : étiquette, contre-étiquette, capsule, caisse… avec crédit et licence
CREATE TABLE image (
    id              INTEGER PRIMARY KEY,
    vin_id          INTEGER REFERENCES vin(id) ON DELETE CASCADE,
    bouteille_id    INTEGER REFERENCES bouteille(id) ON DELETE CASCADE,
    mouvement_id    INTEGER REFERENCES mouvement(id) ON DELETE CASCADE,
    type            TEXT NOT NULL DEFAULT 'etiquette',
    fichier         TEXT NOT NULL,             -- relatif au dossier images/ des données
    sha256          TEXT NOT NULL,
    largeur         INTEGER,
    hauteur         INTEGER,
    origine         TEXT NOT NULL DEFAULT 'perso', -- perso, off, commons, manuel
    credit          TEXT,
    licence         TEXT,
    url_source      TEXT,
    principale      INTEGER NOT NULL DEFAULT 0,
    cree_le         TEXT NOT NULL
);
CREATE INDEX image_vin ON image(vin_id);

-- D'où vient la valeur de chaque champ : une saisie manuelle n'est JAMAIS
-- écrasée par une donnée importée
CREATE TABLE origine_champ (
    table_nom       TEXT NOT NULL,
    ligne_id        INTEGER NOT NULL,
    champ           TEXT NOT NULL,
    origine         TEXT NOT NULL,             -- manuel, csv, cellartracker, lwin…
    date            TEXT NOT NULL,
    PRIMARY KEY (table_nom, ligne_id, champ)
);

-- Journal de ce qui a été rempli automatiquement, et d'où
CREATE TABLE journal_enrichissement (
    id              INTEGER PRIMARY KEY,
    date            TEXT NOT NULL,
    table_nom       TEXT NOT NULL,
    ligne_id        INTEGER NOT NULL,
    champ           TEXT NOT NULL,
    valeur          TEXT,
    source          TEXT NOT NULL,
    detail          TEXT
);
"""


def _script(c: sqlite3.Connection, script: str) -> None:
    """executescript() valide la transaction en cours : on découpe à la main
    pour rester dans la transaction de la migration (tout ou rien)."""
    for instruction in _instructions(script):
        c.execute(instruction)


def _instructions(script: str) -> Iterable[str]:
    tampon = []
    for ligne in script.splitlines():
        if ligne.strip().startswith("--") and not tampon:
            continue
        tampon.append(ligne)
        texte = "\n".join(tampon)
        if sqlite3.complete_statement(texte):
            yield texte
            tampon = []
    reste = "\n".join(tampon).strip()
    if reste and not all(l.strip().startswith("--") or not l.strip() for l in tampon):
        yield reste


def normaliser(texte: str | None) -> str:
    """Forme de comparaison d'un nom : minuscules, sans accents ni ponctuation,
    sans les mots génériques (château, domaine…). Sert à la recherche et à
    l'appariement (règles reprises de MusicOthèque : on compare des formes
    normalisées, jamais l'orthographe brute)."""
    import re
    import unicodedata
    if not texte:
        return ""
    t = unicodedata.normalize("NFKD", texte)
    t = "".join(ch for ch in t if not unicodedata.combining(ch)).lower()
    t = t.replace("œ", "oe").replace("æ", "ae").replace("&", " et ")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    mots = [_ABREVIATIONS.get(m, m) for m in t.split()]
    mots = [m for m in mots if m not in _MOTS_GENERIQUES]
    return " ".join(mots)


#: abréviations courantes des étiquettes et des bases (LWIN écrit « St »,
#: « Ste », « 1er Cru »…) : développées AVANT la comparaison, pour que
#: « St-Julien » et « Saint-Julien » aient la même forme normalisée
_ABREVIATIONS = {
    "st": "saint", "ste": "sainte", "sts": "saints", "mt": "mont", "gd": "grand",
    "gde": "grande", "gds": "grands", "1er": "premier", "1ere": "premiere",
    "1ers": "premiers", "2eme": "deuxieme", "2nd": "second", "vv": "vieilles vignes",
    "vve": "veuve", "cuv": "cuvee", "res": "reserve",
}


_MOTS_GENERIQUES = {
    "chateau", "ch", "chteau", "domaine", "dom", "dne", "maison", "les", "le", "la",
    "de", "du", "des", "d", "l", "et", "the", "estate", "winery", "bodega", "bodegas",
    "weingut", "tenuta", "cave", "caves",
}


def _v2(c: sqlite3.Connection) -> None:
    """v2 : formes normalisées des noms, pour la recherche et l'appariement aux
    bases mondiales (phase 2). Remplit les lignes existantes."""
    c.execute("ALTER TABLE producteur ADD COLUMN nom_normalise TEXT")
    c.execute("ALTER TABLE vin ADD COLUMN cuvee_normalisee TEXT")
    c.execute("CREATE INDEX producteur_norm ON producteur(nom_normalise)")
    for pid, nom in c.execute("SELECT id, nom FROM producteur").fetchall():
        c.execute("UPDATE producteur SET nom_normalise=? WHERE id=?", (normaliser(nom), pid))
    for vid, cuvee in c.execute("SELECT id, cuvee FROM vin").fetchall():
        c.execute("UPDATE vin SET cuvee_normalisee=? WHERE id=?", (normaliser(cuvee), vid))


#: Vues STABLES lues par le dossier LaTeX « Le vin » (encadrés sur les bouteilles
#: de la cave), en lecture seule. Contrat documenté dans docs/export_dossier.md :
#: on peut AJOUTER des colonnes en fin de vue, jamais en retirer ni en renommer
#: (une nouvelle forme = une nouvelle vue suffixée _v2).
VUES_DOSSIER = """
CREATE VIEW v_dossier_vin AS
SELECT v.id                AS vin_id,
       p.nom               AS domaine,
       v.cuvee             AS cuvee,
       v.appellation       AS appellation,
       v.region            AS region,
       v.sous_region       AS sous_region,
       v.pays              AS pays,
       v.couleur           AS couleur,
       v.type              AS type,
       v.millesime         AS millesime,
       (SELECT GROUP_CONCAT(cepage || COALESCE(' ' || CAST(pourcentage AS INTEGER) || '%', ''), '; ')
          FROM (SELECT cepage, pourcentage FROM vin_cepage vc WHERE vc.vin_id = v.id ORDER BY rang))
                           AS cepages,
       (SELECT fichier FROM image i WHERE i.vin_id = v.id AND i.type = 'etiquette'
          ORDER BY i.principale DESC, i.id DESC LIMIT 1)
                           AS photo_etiquette,      -- relatif au dossier images/ des données
       (SELECT credit FROM image i WHERE i.vin_id = v.id AND i.type = 'etiquette'
          ORDER BY i.principale DESC, i.id DESC LIMIT 1)
                           AS photo_credit,
       (SELECT licence FROM image i WHERE i.vin_id = v.id AND i.type = 'etiquette'
          ORDER BY i.principale DESC, i.id DESC LIMIT 1)
                           AS photo_licence,
       v.notes             AS notes,
       (SELECT COUNT(*) FROM bouteille b WHERE b.vin_id = v.id AND b.statut = 'en_cave')
                           AS bouteilles_en_cave
FROM vin v LEFT JOIN producteur p ON p.id = v.producteur_id;

CREATE VIEW v_dossier_livre AS
SELECT m.id                AS mouvement_id,
       m.date              AS date,
       m.type              AS type,
       d.vin_id, d.domaine, d.cuvee, d.appellation, d.region, d.pays, d.millesime,
       m.occasion          AS occasion,
       m.convives          AS convives,
       m.plat              AS plat,
       m.lieu              AS lieu,
       m.note              AS note,
       m.echelle           AS echelle,
       m.commentaire       AS commentaire,
       d.photo_etiquette   AS photo_etiquette
FROM mouvement m LEFT JOIN v_dossier_vin d ON d.vin_id = m.vin_id;
"""


def _v3(c: sqlite3.Connection) -> None:
    """v3 : vues stables pour le dossier « Le vin » (lecture seule)."""
    _script(c, VUES_DOSSIER)


def _v4(c: sqlite3.Connection) -> None:
    """v4 (phase 2) : photos retouchées (l'original est gardé), texte lu par
    l'OCR, fiches des bases mondiales (Wikidata…), formes normalisées
    recalculées (abréviations « St », « 1er »… développées)."""
    _script(c, SCHEMA_V4)
    for pid, nom in c.execute("SELECT id, nom FROM producteur").fetchall():
        c.execute("UPDATE producteur SET nom_normalise=? WHERE id=?", (normaliser(nom), pid))
    for vid, cuvee in c.execute("SELECT id, cuvee FROM vin").fetchall():
        c.execute("UPDATE vin SET cuvee_normalisee=? WHERE id=?", (normaliser(cuvee), vid))


SCHEMA_V4 = """
ALTER TABLE image ADD COLUMN fichier_original TEXT;   -- photo telle que prise (relatif à images/)
ALTER TABLE image ADD COLUMN retouche TEXT;           -- JSON : coins, quarts de tour, déroulage
ALTER TABLE image ADD COLUMN texte_ocr TEXT;          -- texte lu sur l'étiquette

-- Fiches des bases mondiales (Wikidata, Open Food Facts…) rattachées à un
-- producteur, une appellation, un cépage ou un vin ; données en JSON, avec
-- licence et adresse de la source
CREATE TABLE fiche_externe (
    id              INTEGER PRIMARY KEY,
    source          TEXT NOT NULL,             -- wikidata, off…
    identifiant     TEXT NOT NULL,             -- Q1063236, code EAN…
    objet           TEXT NOT NULL,             -- producteur, appellation, cepage, vin
    producteur_id   INTEGER REFERENCES producteur(id) ON DELETE CASCADE,
    vin_id          INTEGER REFERENCES vin(id) ON DELETE CASCADE,
    nom             TEXT,
    donnees         TEXT NOT NULL,             -- JSON
    licence         TEXT,
    url             TEXT,
    date            TEXT NOT NULL
);
CREATE UNIQUE INDEX fiche_externe_unique ON fiche_externe(
    source, identifiant, objet, COALESCE(producteur_id, 0), COALESCE(vin_id, 0));
CREATE INDEX identifiant_source ON identifiant_externe(source, valeur);
CREATE INDEX journal_ligne ON journal_enrichissement(table_nom, ligne_id);
"""


SCHEMA_V5 = """
-- Phase 3 : règles du dossier « Le vin ». Style et niveau de garde imposés par
-- l'utilisateur (NULL = classement automatique d'après styles.json / garde.json)
ALTER TABLE vin ADD COLUMN style TEXT;
ALTER TABLE vin ADD COLUMN niveau_garde TEXT;           -- garde, courant, primeur, nouveau_monde, tous
CREATE INDEX fenetre_source ON fenetre_degustation(source);
CREATE INDEX degustation_date ON degustation(date);
"""


def _v5(c: sqlite3.Connection) -> None:
    """v5 (phase 3) : style et niveau de garde choisis par l'utilisateur."""
    _script(c, SCHEMA_V5)


#: migrations dans l'ordre : MIGRATIONS[i] fait passer de la version i à i+1.
#: Ne JAMAIS modifier une migration publiée : en ajouter une nouvelle.
MIGRATIONS: list[Callable[[sqlite3.Connection], None]] = [
    lambda c: _script(c, SCHEMA_V1),
    _v2,
    _v3,
    _v4,
    _v5,
]
VERSION_SCHEMA = len(MIGRATIONS)


class Base:
    """Accès à la base. Une instance par fichier ; utilisable depuis plusieurs
    fils (une connexion par fil), mais l'application n'écrit que depuis un seul."""

    def __init__(self, chemin: str | Path, migrer: bool = True,
                 jusqu_a: int | None = None):
        self.chemin = Path(chemin)
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._verrou = _VerrouEquitable()
        if migrer:
            self.migrer(jusqu_a)

    @staticmethod
    def lecture_seule(chemin: str | Path) -> sqlite3.Connection:
        """Connexion qui ne peut PAS écrire (URI mode=ro) : pour les lecteurs
        extérieurs (dossier « Le vin », scripts) — ils ne prennent jamais le
        verrou d'écriture et ne gênent pas l'unique écrivain."""
        uri = Path(chemin).resolve().as_uri() + "?mode=ro"
        c = sqlite3.connect(uri, uri=True, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    # -- connexions -----------------------------------------------------------
    def connexion(self) -> sqlite3.Connection:
        c = getattr(self._local, "c", None)
        if c is None:
            c = sqlite3.connect(str(self.chemin), timeout=10, isolation_level=None,
                                check_same_thread=False)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA foreign_keys=ON")
            c.execute("PRAGMA journal_mode=DELETE")
            c.execute("PRAGMA synchronous=FULL")
            c.execute("PRAGMA busy_timeout=10000")
            self._local.c = c
        return c

    def fermer(self) -> None:
        c = getattr(self._local, "c", None)
        if c is not None:
            try:
                c.close()
            finally:
                self._local.c = None

    # -- version et migrations ------------------------------------------------
    def version(self) -> int:
        return int(self.connexion().execute("PRAGMA user_version").fetchone()[0])

    def migrer(self, jusqu_a: int | None = None) -> list[int]:
        """Applique les migrations manquantes ; renvoie les versions atteintes."""
        cible = VERSION_SCHEMA if jusqu_a is None else jusqu_a
        actuelle = self.version()
        if actuelle > VERSION_SCHEMA:
            raise BaseTropRecente(
                f"schéma v{actuelle} > v{VERSION_SCHEMA} connu de cette version")
        faites = []
        for v in range(actuelle, cible):
            with self.ecriture() as c:
                MIGRATIONS[v](c)
                c.execute(f"PRAGMA user_version={v + 1}")
            log.info("Base migrée en v%d", v + 1)
            faites.append(v + 1)
        if faites:
            # contrôle d'intégrité après migration : une clé étrangère cassée
            # doit se voir tout de suite, pas au premier export
            fautes = self.connexion().execute("PRAGMA foreign_key_check").fetchall()
            if fautes:
                raise RuntimeError(f"clés étrangères invalides après migration : {fautes[:5]}")
        return faites

    # -- lecture / écriture ---------------------------------------------------
    def lire(self, sql: str, params: Iterable = ()) -> list[sqlite3.Row]:
        with self._verrou:
            return self.connexion().execute(sql, tuple(params)).fetchall()

    def un(self, sql: str, params: Iterable = ()):
        lignes = self.lire(sql, params)
        return lignes[0] if lignes else None

    def valeur(self, sql: str, params: Iterable = ()):
        ligne = self.un(sql, params)
        return None if ligne is None else ligne[0]

    @contextlib.contextmanager
    def ecriture(self):
        """Transaction d'écriture courte : BEGIN IMMEDIATE … COMMIT (ou ROLLBACK).

        Rien de lent à l'intérieur : préparer les données AVANT (lire, puis
        écrire d'un bloc)."""
        self._verrou.acquire()
        c = self.connexion()
        try:
            c.execute("BEGIN IMMEDIATE")
            try:
                yield c
            except BaseException:
                c.execute("ROLLBACK")
                raise
            else:
                c.execute("COMMIT")
        finally:
            self._verrou.release()

    def ecrivain_disponible(self, patience: float = 4.0) -> bool:
        """Personne d'autre ne tient le verrou d'écriture ? Connexion jetable,
        quelques secondes de patience — jamais le délai d'attente complet."""
        try:
            c = sqlite3.connect(str(self.chemin), timeout=patience, isolation_level=None)
        except sqlite3.Error:
            return False
        try:
            debut = time.monotonic()
            c.execute("BEGIN IMMEDIATE")
            c.execute("ROLLBACK")
            log.debug("verrou d'écriture libre (%.3f s)", time.monotonic() - debut)
            return True
        except sqlite3.OperationalError:
            return False
        finally:
            c.close()

    # -- méta -----------------------------------------------------------------
    def meta(self, cle: str, defaut: str | None = None) -> str | None:
        v = self.valeur("SELECT valeur FROM meta WHERE cle=?", (cle,))
        return defaut if v is None else v

    def definir_meta(self, cle: str, valeur: str) -> None:
        with self.ecriture() as c:
            c.execute("INSERT INTO meta(cle, valeur) VALUES(?, ?) "
                      "ON CONFLICT(cle) DO UPDATE SET valeur=excluded.valeur", (cle, valeur))
