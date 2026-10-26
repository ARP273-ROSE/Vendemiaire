# -*- coding: utf-8 -*-
"""Travaux lents hors du fil de l'interface (réseau, OCR, import LWIN).

Règles payées sur MusicOthèque (voir PROGRESSION.md) : signaux en `object`
(jamais `list`/`dict`, recopiés par Qt), dans le slot de fin `quit()` PUIS
`wait()`, et jamais un QThread détruit pendant qu'il tourne (on garde la
référence tant qu'il n'a pas fini).
"""
from __future__ import annotations

import logging
import traceback

from PyQt6.QtCore import QObject, QThread, pyqtSignal

log = logging.getLogger(__name__)
_en_cours: set = set()          # références gardées jusqu'à la fin de chaque fil


class _Ouvrier(QObject):
    fini = pyqtSignal(object)
    echec = pyqtSignal(object)
    progression = pyqtSignal(object)

    def __init__(self, fonction, args, kwargs):
        super().__init__()
        self.fonction, self.args, self.kwargs = fonction, args, kwargs

    def executer(self):
        try:
            self.fini.emit(self.fonction(*self.args, **self.kwargs))
        except BaseException as e:                       # noqa: BLE001 — rendu à l'interface
            log.info("travail en échec : %s", traceback.format_exc())
            self.echec.emit(e)


class Travail(QObject):
    """Lance `fonction(*args)` dans un fil ; `fini(résultat)` ou `echec(exception)`
    sont émis dans le fil de l'interface."""
    fini = pyqtSignal(object)
    echec = pyqtSignal(object)

    def __init__(self, fonction, *args, parent=None, **kwargs):
        super().__init__(parent)
        self.fil = QThread()
        self.ouvrier = _Ouvrier(fonction, args, kwargs)
        self.ouvrier.moveToThread(self.fil)
        self.fil.started.connect(self.ouvrier.executer)
        self.ouvrier.fini.connect(self._fini)
        self.ouvrier.echec.connect(self._echec)
        self.termine = False

    def lancer(self) -> "Travail":
        _en_cours.add(self)
        self.fil.start()
        return self

    def _arreter(self):
        self.fil.quit()
        self.fil.wait(5000)
        self.termine = True
        _en_cours.discard(self)

    def _fini(self, resultat):
        self._arreter()
        self.fini.emit(resultat)

    def _echec(self, erreur):
        self._arreter()
        self.echec.emit(erreur)


def lancer(fonction, *args, fini=None, echec=None, parent=None, **kwargs) -> Travail:
    t = Travail(fonction, *args, parent=parent, **kwargs)
    if fini is not None:
        t.fini.connect(fini)
    if echec is not None:
        t.echec.connect(echec)
    return t.lancer()


def attendre(travail: Travail, delai_ms: int = 60000) -> None:
    """Pour les essais : fait tourner la boucle d'événements jusqu'à la fin."""
    from PyQt6.QtCore import QCoreApplication, QElapsedTimer
    chrono = QElapsedTimer()
    chrono.start()
    while not travail.termine and chrono.elapsed() < delai_ms:
        QCoreApplication.processEvents()
        QThread.msleep(5)
    QCoreApplication.processEvents()
