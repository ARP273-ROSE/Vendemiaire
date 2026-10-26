# -*- coding: utf-8 -*-
"""Schéma versionné : chaque migration s'applique une fois, dans l'ordre, sans
perte ; une base plus récente est refusée ; une migration ratée n'abîme rien."""
import sqlite3

import pytest

from vendemiaire import base as module_base
from vendemiaire.base import VERSION_SCHEMA, Base, BaseTropRecente


def test_base_neuve_a_la_derniere_version(tmp_path):
    b = Base(tmp_path / "n.db")
    assert b.version() == VERSION_SCHEMA >= 3
    assert b.migrer() == []                                   # rien à refaire


def test_migration_depuis_v1_garde_les_donnees(tmp_path):
    chemin = tmp_path / "ancienne.db"
    b = Base(chemin, jusqu_a=1)
    assert b.version() == 1
    with b.ecriture() as c:
        c.execute("INSERT INTO producteur(nom, cree_le, modifie_le) VALUES('Château Ancien', 'x', 'x')")
        c.execute("INSERT INTO vin(producteur_id, cuvee, millesime, cree_le, modifie_le) "
                  "VALUES(1, 'Réserve Spéciale', 1990, 'x', 'x')")
        c.execute("INSERT INTO bouteille(vin_id, cree_le, modifie_le) VALUES(1, 'x', 'x')")
    b.fermer()
    b = Base(chemin)
    assert b.version() == VERSION_SCHEMA
    p = b.un("SELECT * FROM producteur")
    assert p["nom"] == "Château Ancien" and p["nom_normalise"] == "ancien"
    assert b.valeur("SELECT cuvee_normalisee FROM vin") == "reserve speciale"
    assert b.valeur("SELECT COUNT(*) FROM bouteille") == 1
    assert b.un("SELECT domaine, millesime FROM v_dossier_vin")["domaine"] == "Château Ancien"


def test_base_plus_recente_refusee(tmp_path):
    chemin = tmp_path / "future.db"
    Base(chemin).fermer()
    c = sqlite3.connect(chemin)
    c.execute(f"PRAGMA user_version={VERSION_SCHEMA + 5}")
    c.close()
    with pytest.raises(BaseTropRecente):
        Base(chemin)


def test_migration_ratee_annulee(tmp_path, monkeypatch):
    chemin = tmp_path / "m.db"
    Base(chemin).fermer()

    def casse(c):
        c.execute("CREATE TABLE temoin(x)")
        raise RuntimeError("migration cassée")

    monkeypatch.setattr(module_base, "MIGRATIONS", module_base.MIGRATIONS + [casse])
    monkeypatch.setattr(module_base, "VERSION_SCHEMA", VERSION_SCHEMA + 1)
    with pytest.raises(RuntimeError):
        Base(chemin)
    b = Base(chemin, migrer=False)
    assert b.version() == VERSION_SCHEMA                      # inchangée
    assert not b.lire("SELECT name FROM sqlite_master WHERE name='temoin'")


def test_migrations_jamais_modifiees():
    """Une migration publiée ne change plus : on en ajoute une nouvelle. Les
    empreintes du schéma v1 et des vues v3 le rappellent à qui y toucherait."""
    import hashlib
    assert hashlib.sha256(module_base.SCHEMA_V1.encode()).hexdigest()[:12] == EMPREINTE_V1
    assert hashlib.sha256(module_base.VUES_DOSSIER.encode()).hexdigest()[:12] == EMPREINTE_V3


EMPREINTE_V1 = "0d2c1269a646"
EMPREINTE_V3 = "bd9bc28d3ee5"
