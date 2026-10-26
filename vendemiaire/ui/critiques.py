# -*- coding: utf-8 -*-
"""Saisie des notes des critiques (avec leur échelle, et l'équivalence sourcée
quand une table publiée existe) et des valeurs datées et sourcées."""
from __future__ import annotations

from datetime import date

from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
                             QLabel, QLineEdit, QMessageBox, QPlainTextEdit)

from .. import referentiels, regles
from ..i18n import langue, lib, nombre, tr
from .saisie import _combo_enum, _date, _reel


def equivalence(note: float | None, echelle: str) -> str:
    """Équivalence d'une note dans l'autre échelle, d'après la règle du dossier
    « Le vin » (table publiée) — ou rien, si aucune table ne le permet."""
    if not note:
        return tr("critique.equiv_vide")
    vers = {"100": "20", "20": "100", "3": "mention"}.get(str(echelle))
    e = regles.demander("convertir_note", note, str(echelle), vers) if vers else None
    if e is None:
        return tr("critique.equiv_aucune")
    v = e.valeur
    if vers == "mention":
        texte = v.get("mention") or ""
    else:
        texte = nombre(v["note"], 2)
        if v.get("note_max") and v["note_max"] != v["note"]:
            texte += f"–{nombre(v['note_max'], 2)}"
        texte += " " + lib("echelle", vers)
        if v.get("mention"):
            texte += f" ({v['mention']})"
    pourquoi = e.explication_fr if langue() == "fr" else e.explication_en
    return tr("critique.equiv", texte=texte, regle=e.regle) + "\n" + pourquoi


class DialogueCritique(QDialog):
    def __init__(self, cave, vin_id: int, note: dict | None = None, parent=None):
        super().__init__(parent)
        self.cave, self.vin_id, self.note_existante = cave, vin_id, note
        self.setWindowTitle(tr("critique.titre", vin=cave.nom_vin(vin_id)))
        self.resize(560, 460)
        n = note or {}
        f = QFormLayout(self)
        self.critique = QComboBox()
        self.critique.setEditable(True)
        for code, (nom, _ech) in referentiels.CRITIQUES.items():
            self.critique.addItem(nom, code)
        self.critique.setCurrentText(referentiels.CRITIQUES.get(n.get("critique"), (n.get("critique"),))[0]
                                     if n.get("critique") else "")
        self.echelle = _combo_enum("echelle", vide=False, valeur=n.get("echelle") or "100")
        self.note = _reel(n.get("note"), 100, 2)
        self.note_max = _reel(n.get("note_max"), 100, 2)
        fourchette = QHBoxLayout()
        fourchette.addWidget(self.note)
        fourchette.addWidget(QLabel(tr("critique.a")))
        fourchette.addWidget(self.note_max)
        self.date = _date(n.get("date") or date.today().isoformat())
        self.source = QLineEdit(n.get("source") or "")
        self.source.setPlaceholderText(tr("critique.source_aide"))
        self.texte = QPlainTextEdit(n.get("texte") or "")
        self.texte.setMaximumHeight(100)
        self.equiv = QLabel()
        self.equiv.setWordWrap(True)
        self.equiv.setObjectName("legende")
        f.addRow(tr("critique.critique"), self.critique)
        f.addRow(tr("critique.echelle"), self.echelle)
        f.addRow(tr("critique.note"), fourchette)
        f.addRow(tr("critique.equivalence"), self.equiv)
        f.addRow(tr("critique.date"), self.date)
        f.addRow(tr("critique.source"), self.source)
        f.addRow(tr("critique.texte"), self.texte)
        boutons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        boutons.button(QDialogButtonBox.StandardButton.Save).setText(tr("bouton.enregistrer"))
        boutons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("bouton.annuler"))
        boutons.accepted.connect(self.accepter)
        boutons.rejected.connect(self.reject)
        f.addRow(boutons)
        self.critique.currentIndexChanged.connect(self._echelle_du_critique)
        for w in (self.note, self.note_max):
            w.valueChanged.connect(lambda _v: self._maj())
        self.echelle.currentIndexChanged.connect(lambda _i: self._maj())
        self._maj()

    def _echelle_du_critique(self, _i) -> None:
        code = self.critique.currentData()
        if code in referentiels.CRITIQUES:
            self.echelle.setCurrentIndex(self.echelle.findData(referentiels.CRITIQUES[code][1]))

    def _maj(self) -> None:
        maxi = {"20": 20, "100": 100, "5": 5, "3": 3}.get(self.echelle.currentData(), 100)
        for w in (self.note, self.note_max):
            w.setMaximum(maxi)
        self.equiv.setText(equivalence(self.note.value() or None, self.echelle.currentData()))

    def _code_critique(self) -> str:
        texte = self.critique.currentText().strip()
        for code, (nom, _e) in referentiels.CRITIQUES.items():
            if texte == nom:
                return code
        return texte

    def accepter(self) -> None:
        critique = self._code_critique()
        if not critique or not self.note.value():
            QMessageBox.warning(self, self.windowTitle(), tr("critique.erreur"))
            return
        note_max = self.note_max.value() or None
        if note_max is not None and note_max <= self.note.value():
            note_max = None
        args = (critique, self.note.value(), self.echelle.currentData(), note_max,
                self.texte.toPlainText(), self.date.date().toString("yyyy-MM-dd")
                if self.date.date() != self.date.minimumDate() else None, self.source.text())
        if self.note_existante:
            self.cave.modifier_note_critique(self.note_existante["id"], *args)
        else:
            self.cave.ajouter_note_critique(self.vin_id, args[0], args[1], args[2], args[3], args[4],
                                            args[5], args[6])
        self.accept()


class DialogueValeur(QDialog):
    """Une valeur de marché DATÉE et SOURCÉE (la source est obligatoire)."""

    def __init__(self, cave, vin_id: int, parent=None):
        super().__init__(parent)
        self.cave, self.vin_id = cave, vin_id
        self.setWindowTitle(tr("valeur.titre", vin=cave.nom_vin(vin_id)))
        self.resize(520, 360)
        f = QFormLayout(self)
        self.montant = _reel(None, 1000000, 2)
        self.devise = QComboBox()
        for d in ("EUR", "USD", "GBP", "CHF"):
            self.devise.addItem(d, d)
        ligne = QHBoxLayout()
        ligne.addWidget(self.montant)
        ligne.addWidget(self.devise)
        self.format = _combo_enum("format", vide=False, valeur="bouteille")
        self.date = _date(date.today().isoformat(), vide_permis=False)
        self.source = QLineEdit()
        self.source.setPlaceholderText(tr("valeur.source_aide"))
        self.url = QLineEdit()
        self.note = QLineEdit()
        f.addRow(tr("valeur.montant"), ligne)
        f.addRow(tr("valeur.format"), self.format)
        f.addRow(tr("valeur.date"), self.date)
        f.addRow(tr("valeur.source"), self.source)
        f.addRow(tr("valeur.url"), self.url)
        f.addRow(tr("valeur.note"), self.note)
        boutons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        boutons.button(QDialogButtonBox.StandardButton.Save).setText(tr("bouton.enregistrer"))
        boutons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("bouton.annuler"))
        boutons.accepted.connect(self.accepter)
        boutons.rejected.connect(self.reject)
        f.addRow(boutons)

    def accepter(self) -> None:
        if not self.montant.value() or not self.source.text().strip():
            QMessageBox.warning(self, self.windowTitle(), tr("valeur.erreur"))
            return
        self.cave.ajouter_valeur_complete(self.vin_id, self.montant.value(), self.source.text().strip(),
                                          self.date.date().toString("yyyy-MM-dd"),
                                          self.format.currentData(), self.devise.currentData(),
                                          self.url.text().strip(), self.note.text().strip())
        self.accept()
