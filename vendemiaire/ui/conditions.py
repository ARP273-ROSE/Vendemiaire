# -*- coding: utf-8 -*-
"""Conditions de cave : température et hygrométrie, saisies à la main ou
importées d'une sonde (CSV, export Home Assistant). Courbe simple, minimum,
maximum, moyenne. Les alertes et les plages conseillées viendront des règles
du dossier « Le vin » (conservation.json, phase 3/4)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QDateTime, QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QDateTimeEdit, QDialog, QDialogButtonBox,
                             QFileDialog, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton,
                             QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from .. import echanges, style
from ..i18n import date_affichee, langue, nombre, tr
from .saisie import _reel

FILTRE_CSV = "CSV (*.csv *.txt *.tsv)"


def _caves(cave) -> list[tuple[int, str]]:
    return [(e["id"], " › ".join(cave.chemin_emplacement(e["id"]))) for e in cave.emplacements()
            if e["niveau"] in ("cave", "meuble")]


class Courbe(QWidget):
    """Température (bordeaux) et hygrométrie (or) dans le temps."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mesures: list = []
        self.setMinimumHeight(220)

    def definir(self, mesures) -> None:
        self.mesures = sorted(mesures, key=lambda m: m["date_heure"])
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(style.CREME))
        zone = QRectF(self.rect()).adjusted(48, 14, -48, -26)
        p.setPen(QPen(QColor(style.BORD), 1))
        p.drawRect(zone)
        points = [(datetime.fromisoformat(m["date_heure"]).timestamp(), m["temperature"], m["hygrometrie"])
                  for m in self.mesures]
        if len(points) < 2:
            p.setPen(QColor(style.ENCRE))
            p.drawText(zone, Qt.AlignmentFlag.AlignCenter, tr("cond.pas_assez"))
            return
        t0, t1 = points[0][0], points[-1][0]
        t1 = t1 if t1 > t0 else t0 + 1
        petite = QFont(p.font())
        petite.setPointSizeF(max(7.0, petite.pointSizeF() - 1))
        p.setFont(petite)
        for indice, couleur, cote in ((1, style.BORDEAUX, "g"), (2, style.OR, "d")):
            valeurs = [x[indice] for x in points if x[indice] is not None]
            if len(valeurs) < 2:
                continue
            bas, haut = min(valeurs), max(valeurs)
            if haut - bas < 1:
                bas, haut = bas - 0.5, haut + 0.5
            chemin = QPainterPath()
            premier = True
            for t, *v in points:
                y = v[indice - 1]
                if y is None:
                    continue
                pt = QPointF(zone.left() + (t - t0) / (t1 - t0) * zone.width(),
                             zone.bottom() - (y - bas) / (haut - bas) * zone.height())
                if premier:
                    chemin.moveTo(pt)
                    premier = False
                else:
                    chemin.lineTo(pt)
            p.setPen(QPen(QColor(couleur), 2))
            p.drawPath(chemin)
            unite = " °C" if indice == 1 else " %"
            x = zone.left() - 46 if cote == "g" else zone.right() + 4
            for valeur, y in ((haut, zone.top()), (bas, zone.bottom() - 12)):
                p.drawText(QRectF(x, y, 44, 14), Qt.AlignmentFlag.AlignCenter, nombre(valeur) + unite)
        p.setPen(QColor(style.ENCRE))
        for t, aligne in ((t0, Qt.AlignmentFlag.AlignLeft), (t1, Qt.AlignmentFlag.AlignRight)):
            texte = date_affichee(datetime.fromtimestamp(t).date().isoformat())
            p.drawText(QRectF(zone.left(), zone.bottom() + 4, zone.width(), 16), aligne, texte)


class DialogueMesure(QDialog):
    def __init__(self, cave, emplacement_id: int | None, parent=None):
        super().__init__(parent)
        self.cave = cave
        self.setWindowTitle(tr("cond.ajouter"))
        f = QFormLayout(self)
        self.lieu = QComboBox()
        for eid, nom in _caves(cave):
            self.lieu.addItem(nom, eid)
        self.lieu.setCurrentIndex(max(0, self.lieu.findData(emplacement_id)))
        self.quand = QDateTimeEdit(QDateTime.currentDateTime())
        self.quand.setCalendarPopup(True)
        self.quand.setDisplayFormat("dd/MM/yyyy HH:mm" if langue() == "fr" else "yyyy-MM-dd HH:mm")
        self.temperature = _reel(None, 40, 1, " °C")
        self.hygrometrie = _reel(None, 100, 0, " %")
        f.addRow(tr("cond.lieu"), self.lieu)
        f.addRow(tr("cond.quand"), self.quand)
        f.addRow(tr("cond.temperature"), self.temperature)
        f.addRow(tr("cond.hygrometrie"), self.hygrometrie)
        boutons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        boutons.button(QDialogButtonBox.StandardButton.Save).setText(tr("bouton.enregistrer"))
        boutons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("bouton.annuler"))
        boutons.accepted.connect(self.accepter)
        boutons.rejected.connect(self.reject)
        f.addRow(boutons)

    def accepter(self) -> None:
        t, h = self.temperature.value() or None, self.hygrometrie.value() or None
        if t is None and h is None:
            return
        quand = self.quand.dateTime().toString("yyyy-MM-dd HH:mm:00")
        self.cave.ajouter_conditions([(self.lieu.currentData(), quand, t, h)], source="saisie")
        self.accept()


class VueConditions(QWidget):
    modifie = pyqtSignal()

    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        racine = QVBoxLayout(self)
        haut = QHBoxLayout()
        haut.addWidget(QLabel(tr("cond.lieu")))
        self.lieu = QComboBox()
        self.lieu.addItem(tr("cond.tous_lieux"), None)
        for eid, nom in _caves(cave):
            self.lieu.addItem(nom, eid)
        haut.addWidget(self.lieu, 1)
        self.b_ajouter = QPushButton(tr("cond.ajouter"))
        self.b_importer = QPushButton(tr("cond.importer"))
        self.b_supprimer = QPushButton(tr("cond.supprimer"))
        for b in (self.b_ajouter, self.b_importer, self.b_supprimer):
            haut.addWidget(b)
        racine.addLayout(haut)
        self.resume = QLabel()
        self.resume.setWordWrap(True)
        racine.addWidget(self.resume)
        coupe = QSplitter(Qt.Orientation.Vertical)
        self.courbe = Courbe()
        coupe.addWidget(self.courbe)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([tr("cond.quand"), tr("cond.temperature"),
                                              tr("cond.hygrometrie"), tr("cond.source")])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        coupe.addWidget(self.table)
        racine.addWidget(coupe, 1)
        aide = QLabel(tr("cond.aide"))
        aide.setObjectName("legende")
        aide.setWordWrap(True)
        racine.addWidget(aide)
        self.lieu.currentIndexChanged.connect(lambda _i: self.rafraichir())
        self.b_ajouter.clicked.connect(self.ajouter)
        self.b_importer.clicked.connect(self.importer)
        self.b_supprimer.clicked.connect(self.supprimer)
        self.rafraichir()

    def rafraichir(self) -> None:
        eid = self.lieu.currentData()
        mesures = self.cave.conditions(eid, limite=5000)
        self.courbe.definir(mesures)
        self.table.setRowCount(min(len(mesures), 500))
        for r, m in enumerate(mesures[:500]):
            quand = date_affichee(m["date_heure"]) + " " + m["date_heure"][11:16]
            for c, val in enumerate((quand, f"{nombre(m['temperature'])} °C" if m["temperature"] is not None
                                     else "", f"{nombre(m['hygrometrie'], 0)} %"
                                     if m["hygrometrie"] is not None else "", m["source"] or "")):
                it = QTableWidgetItem(val)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if c == 0:
                    it.setData(Qt.ItemDataRole.UserRole, m["id"])
                self.table.setItem(r, c, it)
        s = self.cave.resume_conditions(eid)
        if s.get("n"):
            self.resume.setText(tr("cond.resume", n=s["n"], tmin=nombre(s["tmin"]), tmax=nombre(s["tmax"]),
                                   tmoy=nombre(s["tmoy"]), hmin=nombre(s["hmin"], 0),
                                   hmax=nombre(s["hmax"], 0), hmoy=nombre(s["hmoy"], 0),
                                   debut=date_affichee(s["debut"]), fin=date_affichee(s["fin"])))
        else:
            self.resume.setText(tr("cond.aucune"))

    def ajouter(self) -> None:
        if DialogueMesure(self.cave, self.lieu.currentData(), self).exec() == QDialog.DialogCode.Accepted:
            self.rafraichir()

    def importer(self) -> None:
        chemin, _ = QFileDialog.getOpenFileName(self, tr("cond.importer"), str(Path.home()), FILTRE_CSV)
        if not chemin:
            return
        lieu = self.lieu.currentData()
        if lieu is None and _caves(self.cave):
            lieu = _caves(self.cave)[0][0]
        r = echanges.importer_conditions(self.cave, chemin, lieu)
        texte = tr("cond.rapport", lignes=r.lignes, ajoutees=r.mesures, deja=r.deja_presentes)
        if r.avertissements:
            texte += "\n\n" + "\n".join(r.avertissements[:10])
        QMessageBox.information(self, tr("cond.importer"), texte)
        self.rafraichir()

    def supprimer(self) -> None:
        rangs = self.table.selectionModel().selectedRows()
        if not rangs:
            return
        for r in rangs:
            self.cave.supprimer_condition(self.table.item(r.row(), 0).data(Qt.ItemDataRole.UserRole))
        self.rafraichir()
