# -*- coding: utf-8 -*-
"""Réglages communs des essais : base temporaire, cave de démonstration,
réglages Qt isolés (jamais ceux de l'utilisateur), Qt sans écran si aucun
serveur X (la CI lance tout sous Xvfb)."""
import os
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def base(tmp_path):
    from vendemiaire.base import Base
    b = Base(tmp_path / "cave.db")
    yield b
    b.fermer()


@pytest.fixture
def cave(base, tmp_path):
    from vendemiaire.modele import Cave
    return Cave(base, tmp_path / "images")


@pytest.fixture(scope="session")
def chemin_demo(tmp_path_factory):
    from vendemiaire import demo
    chemin = tmp_path_factory.mktemp("demo") / "demo.db"
    demo.generer(chemin).base.fermer()
    return chemin


@pytest.fixture
def cave_demo(chemin_demo, tmp_path):
    """Copie fraîche de la démonstration pour chaque essai (elle peut être modifiée)."""
    import shutil
    from vendemiaire.base import Base
    from vendemiaire.modele import Cave
    copie = tmp_path / "demo.db"
    shutil.copy2(chemin_demo, copie)
    c = Cave(Base(copie), tmp_path / "images")
    yield c
    c.base.fermer()


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    from PyQt6 import QtCore, QtWidgets
    reglages = tmp_path_factory.mktemp("reglages")
    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.Format.IniFormat)
    QtCore.QSettings.setPath(QtCore.QSettings.Format.IniFormat,
                             QtCore.QSettings.Scope.UserScope, str(reglages))
    a = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    a.setOrganizationName("VendemiaireEssais")
    a.setApplicationName("VendemiaireEssais")
    from vendemiaire import style
    style.appliquer(a)
    return a
