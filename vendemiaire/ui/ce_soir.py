# -*- coding: utf-8 -*-
"""« Que boire ce soir ? », fiche « ce soir » imprimable, bouteille entamée.

Les propositions viennent des règles du dossier « Le vin » (accords, fenêtres)
appliquées à LA cave : les bouteilles en déclin ou à boire cette année
d'abord, puis à l'apogée, puis buvables ; les trop jeunes sont écartées.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from PyQt6.QtCore import Qt, QTime, pyqtSignal
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QCompleter, QDialog,
                             QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
                             QTextBrowser, QTimeEdit, QVBoxLayout, QWidget)

from .. import referentiels
from ..i18n import argent, langue, lib, tr
from ..regles import accords as r_accords
from ..regles import conservation as r_conservation
from ..regles import service as r_service
from . import regles_ui


FILTRE_HTML = "HTML (*.html)"
FILTRE_PDF = "PDF (*.pdf)"
UNITE_CL = " cl"


def _cellule(texte) -> QTableWidgetItem:
    it = QTableWidgetItem("" if texte is None else str(texte))
    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return it


# ---------------------------------------------------------------------------- fiche « ce soir »
def entree_ce_soir(cave, vin_id: int, heure: QTime | None = None, piece_c: float | None = None,
                   plat: str = "") -> dict:
    """Une section de la fiche « ce soir » (textes déjà dans la langue)."""
    lg = langue()
    v = cave.vin_pour_regles(vin_id)
    s = cave.service_du_vin(vin_id, piece_c=piece_c)
    lignes, pourquoi, sources = [], [], []
    b = cave.base.un("SELECT * FROM bouteille WHERE vin_id=? AND statut='en_cave' ORDER BY id LIMIT 1",
                     (vin_id,))
    if b is not None and b["emplacement_id"]:
        ou = " › ".join(cave.chemin_emplacement(b["emplacement_id"]))
        if b["rangee"] and b["colonne"]:
            ou += " " + tr("plan.case", r=b["rangee"], c=b["colonne"])
        lignes.append((tr("cesoir.ou"), ou))
    if s is not None:
        lignes.append((tr("regles.temperature"), regles_ui.texte_temperature(s)))
        sortie = regles_ui.texte_sortie(s)
        if heure is not None and s.sortie.valeur["action"] == "sortir" and s.sortie.valeur["minutes"]:
            quand = datetime.combine(date.today(), heure.toPyTime()) - timedelta(
                minutes=s.sortie.valeur["minutes"])
            sortie = tr("cesoir.sortir_a", heure=quand.strftime("%H:%M")) + " — " + sortie
        lignes.append((tr("regles.sortie"), sortie))
        if s.carafes:
            lignes.append((tr("regles.carafe"), r_service.texte_carafe(s.carafes[0], lg)))
        if s.verres:
            lignes.append((tr("regles.verre"), r_service.texte_verre(s.verres[0], lg)))
        pourquoi.append(s.temperature.explication(lg))
        if s.carafes:
            pourquoi.append(s.carafes[0].explication(lg))
        sources += s.temperature.sources + (s.carafes[0].sources if s.carafes else [])
    cl = s.classement if s else None
    trouves = [p for p in r_accords.chercher_plats(plat) if cl and cl.id in p.styles] if plat else []
    if trouves:
        lignes.append((tr("regles.accords"), f"{trouves[0].nom(lg)} — {trouves[0].pourquoi(lg)}"))
        sources += trouves[0].regle["sources"]
    elif cl:
        plats = r_accords.plats_pour_style(cl.id)
        if plats:
            lignes.append((tr("regles.accords"), " ; ".join(p.nom(lg) for p in plats[:6])))
    if v:
        o = r_conservation.bouteille_ouverte(v, "bouchon")
        if o:
            lignes.append((tr("regles.ouverte"), regles_ui.texte_ouverte(o)))
    eff = cave.fenetre_effective(vin_id)
    if eff:
        lignes.append((tr("cesoir.fenetre"), regles_ui.texte_fenetre(eff)))
    nom = cave.nom_vin(vin_id)
    details = " · ".join(x for x in ((cl.nom(lg) if cl else ""),) if x)
    vus = []
    for x in sources:
        if x not in vus:
            vus.append(x)
    return {"nom": nom, "details": details, "lignes": lignes, "pourquoi": [p for p in pourquoi if p],
            "sources": [tr("cesoir.sources", liste=", ".join(vus))] if vus else []}


def html_ce_soir(cave, vin_ids: list[int], heure: QTime | None, piece_c: float | None, plat: str = "",
                 occasion: str = "") -> str:
    entrees = [entree_ce_soir(cave, vid, heure, piece_c, plat) for vid in vin_ids]
    sous = [date.today().strftime("%d/%m/%Y") if langue() == "fr" else date.today().isoformat()]
    if plat:
        sous.append(plat)
    if occasion:
        sous.append(lib("occasion", occasion))
    if heure is not None:
        sous.append(tr("cesoir.service_a", heure=heure.toString("HH:mm")))
    from ..regles.jeu import jeu
    pied = tr("cesoir.pied", date=jeu().date_audit or "?", n=jeu().nombre_regles())
    return r_service.fiche_ce_soir_html(entrees, langue(), tr("cesoir.titre_fiche"), " · ".join(sous), pied)


def ecrire_pdf(html: str, chemin: str | Path) -> None:
    """PDF A4 de la fiche (rendu Qt du même HTML). Pas de `setPageSize` en pixels
    du QPdfWriter : le texte en sortait minuscule (corrigé en phase 4)."""
    from ..documents.qt_pdf import html_vers_pdf
    html_vers_pdf(html, chemin)


class DialogueFicheCeSoir(QDialog):
    def __init__(self, cave, vin_ids: list[int], plat: str = "", occasion: str = "", parent=None):
        super().__init__(parent)
        self.cave, self.vin_ids, self.plat, self.occasion = cave, list(vin_ids), plat, occasion
        self.setWindowTitle(tr("cesoir.titre_fiche"))
        self.resize(820, 760)
        l = QVBoxLayout(self)
        f = QHBoxLayout()
        f.addWidget(QLabel(tr("cesoir.heure")))
        self.heure = QTimeEdit(QTime(20, 0))
        self.heure.setDisplayFormat("HH:mm")
        f.addWidget(self.heure)
        f.addWidget(QLabel(tr("cesoir.piece")))
        self.piece = QDoubleSpinBox()
        self.piece.setRange(10, 30)
        self.piece.setDecimals(1)
        self.piece.setSuffix(" °C")
        from ..regles.jeu import jeu
        self.piece.setValue(float(jeu().service["sortie_de_cave"]["valeur"]["piece_c"]))
        f.addWidget(self.piece)
        f.addStretch(1)
        l.addLayout(f)
        self.apercu = QTextBrowser()
        l.addWidget(self.apercu, 1)
        b = QHBoxLayout()
        self.b_html = QPushButton(tr("cesoir.enregistrer_html"))
        self.b_pdf = QPushButton(tr("cesoir.enregistrer_pdf"))
        self.b_pdf.setObjectName("principal")
        fermer = QPushButton(tr("regles.fermer"))
        for x in (self.b_html, self.b_pdf):
            b.addWidget(x)
        b.addStretch(1)
        b.addWidget(fermer)
        l.addLayout(b)
        self.heure.timeChanged.connect(lambda _t: self.rafraichir())
        self.piece.valueChanged.connect(lambda _v: self.rafraichir())
        self.b_html.clicked.connect(self.enregistrer_html)
        self.b_pdf.clicked.connect(self.enregistrer_pdf)
        fermer.clicked.connect(self.accept)
        self.rafraichir()

    def html(self) -> str:
        return html_ce_soir(self.cave, self.vin_ids, self.heure.time(), self.piece.value(), self.plat,
                            self.occasion)

    def rafraichir(self) -> None:
        self.apercu.setHtml(self.html())

    def enregistrer_html(self, chemin: str | None = None) -> str | None:
        if not chemin:
            chemin, _ = QFileDialog.getSaveFileName(self, tr("cesoir.enregistrer_html"),
                                                    str(Path.home() / "ce-soir.html"), FILTRE_HTML)
        if chemin:
            Path(chemin).write_text(self.html(), encoding="utf-8")
        return chemin or None

    def enregistrer_pdf(self, chemin: str | None = None) -> str | None:
        if not chemin:
            chemin, _ = QFileDialog.getSaveFileName(self, tr("cesoir.enregistrer_pdf"),
                                                    str(Path.home() / "ce-soir.pdf"), FILTRE_PDF)
        if chemin:
            ecrire_pdf(self.html(), chemin)
        return chemin or None


# ---------------------------------------------------------------------------- bouteille entamée
class DialogueEntamer(QDialog):
    """Ouvrir une bouteille sans la finir : combien de jours elle se garde
    (dossier, selon le style et le mode), inscrite au livre de cave."""

    def __init__(self, cave, bouteille_id: int, parent=None):
        super().__init__(parent)
        self.cave, self.bid = cave, bouteille_id
        b = cave.bouteille(bouteille_id)
        self.vin = cave.vin_pour_regles(b["vin_id"])
        self.setWindowTitle(tr("ouv.titre", vin=cave.nom_vin(b["vin_id"])))
        self.resize(560, 360)
        l = QVBoxLayout(self)
        f = QFormLayout()
        self.mode = QComboBox()
        for code in ("bouchon", "vide", "gaz", "coravin"):
            self.mode.addItem(lib("conservation_ouverte", code), code)
        self.reste = QDoubleSpinBox()
        self.reste.setRange(0, 300)
        self.reste.setDecimals(0)
        self.reste.setSuffix(UNITE_CL)
        self.reste.setValue(40)
        self.plat = QLineEdit()
        f.addRow(tr("ouv.mode"), self.mode)
        f.addRow(tr("ouv.reste"), self.reste)
        f.addRow(tr("sortie.plat"), self.plat)
        l.addLayout(f)
        self.conseil = QLabel()
        self.conseil.setWordWrap(True)
        self.conseil.setTextFormat(Qt.TextFormat.RichText)
        l.addWidget(self.conseil, 1)
        boutons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        boutons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("ouv.valider"))
        boutons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("bouton.annuler"))
        boutons.accepted.connect(self.accepter)
        boutons.rejected.connect(self.reject)
        l.addWidget(boutons)
        self.mode.currentIndexChanged.connect(lambda _i: self.rafraichir())
        self.ouverte_id = None
        self.rafraichir()

    def rafraichir(self) -> None:
        e = r_conservation.bouteille_ouverte(self.vin, self.mode.currentData(), date.today()) \
            if self.vin else None
        if e is None:
            self.conseil.setText(tr("regles.non_classe"))
            return
        texte = f"<p><b>{regles_ui.e(regles_ui.texte_ouverte(e))}</b></p>"
        if e.valeur.get("a_finir_entre"):
            a, b = e.valeur["a_finir_entre"]
            from ..i18n import date_affichee
            texte += f"<p>{regles_ui.e(tr('ouv.a_finir', a=date_affichee(a), b=date_affichee(b)))}</p>"
        self.conseil.setText(texte + regles_ui.estimation_html(e))

    def accepter(self) -> None:
        self.ouverte_id = self.cave.entamer(self.bid, self.mode.currentData(), self.reste.value() or None,
                                            plat=self.plat.text().strip() or None)
        self.accept()


# ---------------------------------------------------------------------------- « que boire ce soir ? »
class VueCeSoir(QWidget):
    vin_choisi = pyqtSignal(int)
    modifie = pyqtSignal()

    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        lg = langue()
        racine = QVBoxLayout(self)
        filtres = QHBoxLayout()
        self.plat = QLineEdit()
        self.plat.setPlaceholderText(tr("cesoir.plat_aide"))
        noms = [p.nom(lg) for p in r_accords.plats()]
        comp = QCompleter(noms, self.plat)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        self.plat.setCompleter(comp)
        self.budget = QDoubleSpinBox()
        self.budget.setRange(0, 100000)
        self.budget.setDecimals(0)
        self.budget.setSpecialValueText(tr("cesoir.sans_budget"))
        self.budget.setSuffix(" €")
        self.couleur = QComboBox()
        self.couleur.addItem(tr("cesoir.toutes_couleurs"), "")
        for code in referentiels.codes("couleur"):
            self.couleur.addItem(lib("couleur", code), code)
        self.occasion = QComboBox()
        self.occasion.addItem(tr("cesoir.toute_occasion"), "")
        for code in referentiels.codes("occasion"):
            self.occasion.addItem(lib("occasion", code), code)
        self.jeunes = QCheckBox(tr("cesoir.avec_jeunes"))
        for etiquette, w in ((tr("cesoir.plat"), self.plat), (tr("cesoir.budget"), self.budget),
                             (tr("cesoir.couleur"), self.couleur), (tr("cesoir.occasion"), self.occasion)):
            filtres.addWidget(QLabel(etiquette))
            filtres.addWidget(w, 2 if w is self.plat else 0)
        filtres.addWidget(self.jeunes)
        racine.addLayout(filtres)
        coupe = QSplitter(Qt.Orientation.Vertical)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([tr("cesoir.c_vin"), tr("cesoir.c_n"), tr("cesoir.c_etat"),
                                              tr("cesoir.c_fenetre"), tr("cesoir.c_prix"), tr("cesoir.c_style"),
                                              tr("cesoir.c_source")])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        coupe.addWidget(self.table)
        self.explication = QTextBrowser()
        self.explication.setOpenExternalLinks(True)
        coupe.addWidget(self.explication)
        coupe.setSizes([420, 220])
        racine.addWidget(coupe, 1)
        bas = QHBoxLayout()
        self.b_fiche = QPushButton(tr("cesoir.fiche"))
        self.b_fiche.setObjectName("principal")
        self.b_voir = QPushButton(tr("cesoir.voir"))
        bas.addWidget(self.b_fiche)
        bas.addWidget(self.b_voir)
        bas.addStretch(1)
        self.total = QLabel()
        self.total.setObjectName("legende")
        bas.addWidget(self.total)
        racine.addLayout(bas)
        self.plat.textChanged.connect(lambda _t: self.rafraichir())
        self.budget.valueChanged.connect(lambda _v: self.rafraichir())
        self.couleur.currentIndexChanged.connect(lambda _i: self.rafraichir())
        self.occasion.currentIndexChanged.connect(lambda _i: self.rafraichir())
        self.jeunes.toggled.connect(lambda _b: self.rafraichir())
        self.table.itemDoubleClicked.connect(lambda _i: self._voir())
        self.b_voir.clicked.connect(self._voir)
        self.b_fiche.clicked.connect(self.fiche)
        self.resultat: dict = {}
        self.rafraichir()

    def vins_choisis(self) -> list[int]:
        rangs = sorted({i.row() for i in self.table.selectedIndexes()})
        if not rangs and self.table.rowCount():
            rangs = [0]
        return [self.table.item(r, 0).data(Qt.ItemDataRole.UserRole) for r in rangs]

    def _voir(self) -> None:
        v = self.vins_choisis()
        if v:
            self.vin_choisi.emit(v[0])

    def fiche(self) -> None:
        v = self.vins_choisis()
        if v:
            DialogueFicheCeSoir(self.cave, v, self.plat.text().strip(), self.occasion.currentData(), self).exec()

    def rafraichir(self) -> None:
        lg = langue()
        r = self.cave.que_boire(self.plat.text().strip(), self.budget.value() or None,
                                self.couleur.currentData(), self.occasion.currentData(),
                                avec_trop_jeunes=self.jeunes.isChecked())
        self.resultat = r
        props = r["propositions"]
        self.table.setRowCount(len(props))
        for i, p in enumerate(props):
            b = p.bouteille
            nom = " · ".join(str(x) for x in (b["producteur"], b["cuvee"], b["appellation"], b["millesime"]) if x)
            etat = lib("alerte", b["alerte"]) if b.get("alerte") in ("a_boire", "declin") else \
                lib("phase", b.get("phase"))
            fen = regles_ui.texte_fenetre(b) if b.get("source_fenetre") else ""
            from ..regles.jeu import jeu
            st = jeu().styles_par_id.get(b.get("style"))
            cellules = (nom, b["n"], etat, fen, argent(b["prix"]) if b.get("prix") is not None else "",
                        (st["nom_fr"] if lg == "fr" else st["nom_en"]) if st else "",
                        lib("source_fenetre", b.get("source_fenetre")))
            for c, val in enumerate(cellules):
                it = _cellule(val)
                if c == 0:
                    it.setData(Qt.ItemDataRole.UserRole, b["vin_id"])
                self.table.setItem(i, c, it)
        self.table.resizeColumnsToContents()
        self.b_fiche.setEnabled(bool(props))
        self.b_voir.setEnabled(bool(props))
        self.total.setText(tr("cesoir.total", n=len(props), b=sum(p.bouteille["n"] for p in props)))
        morceaux = []
        texte = self.plat.text().strip()
        if r["plats"]:
            p = r["plats"][0]
            morceaux.append(regles_ui.estimation_html(p.estimation(), tr("cesoir.plat_trouve", plat=p.nom(lg))))
            if len(r["plats"]) > 1:
                morceaux.append(f"<p>{regles_ui.e(tr('cesoir.autres_plats', liste=' ; '.join(x.nom(lg) for x in r['plats'][1:4])))}</p>")
        elif texte:
            morceaux.append(f"<p>{regles_ui.e(tr('cesoir.plat_inconnu', plat=texte))}</p>")
        for d in r["difficiles"]:
            morceaux.append(f"<p><b>{regles_ui.e(tr('cesoir.difficile', plat=d.nom(lg)))}</b> "
                            f"{regles_ui.e(d.pourquoi(lg))}</p>" + regles_ui.sources_html(d.regle["sources"]))
        morceaux.append(f"<p style='color:gray'>{regles_ui.e(tr('cesoir.methode'))}</p>")
        self.explication.setHtml("".join(morceaux))
