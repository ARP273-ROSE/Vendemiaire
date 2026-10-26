# -*- coding: utf-8 -*-
"""Saisie et modification : un vin, ses bouteilles, une sortie de cave."""
from __future__ import annotations

from datetime import date

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QCompleter, QDateEdit, QDialog,
                             QDialogButtonBox, QDoubleSpinBox, QFormLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QSpinBox,
                             QTabWidget, QVBoxLayout, QWidget)

from .. import referentiels
from ..echanges import cepages_vers_texte, texte_vers_cepages
from ..i18n import langue, lib, tr
from ..modele import CaseOccupee


def _combo_enum(enum: str, vide: bool = True, valeur=None) -> QComboBox:
    c = QComboBox()
    if vide:
        c.addItem("", None)
    for code in referentiels.codes(enum):
        c.addItem(lib(enum, code), code)
    if valeur is not None:
        i = c.findData(valeur)
        if i < 0:                         # code importé inconnu : gardé tel quel
            c.addItem(str(valeur), valeur)
            i = c.count() - 1
        c.setCurrentIndex(i)
    return c


def _ligne(texte=None, completions: list[str] | None = None) -> QLineEdit:
    e = QLineEdit("" if texte is None else str(texte))
    if completions:
        comp = QCompleter(completions, e)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        e.setCompleter(comp)
    return e


def _reel(valeur=None, maxi=100000.0, decimales=2, suffixe="") -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(0, maxi)
    s.setDecimals(decimales)
    s.setSpecialValueText(" ")             # 0 = vide
    if suffixe:
        s.setSuffix(suffixe)
    s.setValue(float(valeur) if valeur else 0.0)
    return s


def _date(iso: str | None, vide_permis=True) -> QDateEdit:
    d = QDateEdit()
    d.setCalendarPopup(True)
    d.setDisplayFormat("dd/MM/yyyy" if langue() == "fr" else "yyyy-MM-dd")
    d.setMinimumDate(QDate(1900, 1, 1))
    if vide_permis:
        d.setSpecialValueText(" ")
    if iso:
        d.setDate(QDate.fromString(iso[:10], "yyyy-MM-dd"))
    elif vide_permis:
        d.setDate(d.minimumDate())
    else:
        d.setDate(QDate.currentDate())
    return d


def _valeur_date(d: QDateEdit) -> str | None:
    return None if d.date() == d.minimumDate() else d.date().toString("yyyy-MM-dd")


def _code(c: QComboBox):
    return c.currentData()


def casiers(cave) -> list[tuple[int, str]]:
    """Casiers (avec leur chemin complet), dans l'ordre de l'arbre."""
    resultat = []
    for e in cave.emplacements():
        if e["niveau"] == "casier":
            resultat.append((e["id"], " › ".join(cave.chemin_emplacement(e["id"]))))
    return sorted(resultat, key=lambda x: x[1].lower())


class BlocBouteilles(QWidget):
    """Attributs communs d'un lot de bouteilles à ajouter."""

    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        f = QFormLayout(self)
        self.nombre = QSpinBox()
        self.nombre.setRange(0, 600)
        self.nombre.setValue(6)
        self.format = _combo_enum("format", vide=False, valeur="bouteille")
        self.statut = QComboBox()
        for code in ("en_cave", "primeur", "en_attente"):
            self.statut.addItem(lib("statut", code), code)
        self.prix = _reel(suffixe=" €")
        self.lieu = _ligne(completions=[r[0] for r in cave.base.lire(
            "SELECT DISTINCT lieu_achat FROM bouteille WHERE lieu_achat IS NOT NULL")])
        self.date_achat = _date(date.today().isoformat())
        self.livraison = _date(None)
        self.caisse = _combo_enum("caisse")
        self.provenance = _ligne()
        self.casier = QComboBox()
        self.casier.addItem(tr("saisie.sans_emplacement"), None)
        for eid, chemin in casiers(cave):
            self.casier.addItem(chemin, eid)
        self.placer = QCheckBox(tr("saisie.placer_libres"))
        self.placer.setChecked(True)
        f.addRow(tr("saisie.nombre"), self.nombre)
        f.addRow(tr("saisie.format"), self.format)
        f.addRow(tr("saisie.statut"), self.statut)
        f.addRow(tr("saisie.prix"), self.prix)
        f.addRow(tr("saisie.lieu_achat"), self.lieu)
        f.addRow(tr("saisie.date_achat"), self.date_achat)
        f.addRow(tr("saisie.livraison"), self.livraison)
        f.addRow(tr("saisie.caisse"), self.caisse)
        f.addRow(tr("saisie.provenance"), self.provenance)
        f.addRow(tr("saisie.emplacement"), self.casier)
        f.addRow("", self.placer)

    def attributs(self) -> dict:
        a = {"format": _code(self.format), "statut": _code(self.statut),
             "prix_achat": self.prix.value() or None, "lieu_achat": self.lieu.text().strip() or None,
             "date_achat": _valeur_date(self.date_achat),
             "date_livraison_prevue": _valeur_date(self.livraison),
             "caisse": _code(self.caisse), "provenance": self.provenance.text().strip() or None}
        if a["caisse"] == "cbo" and self.nombre.value() in (6, 12):
            a["caisse_complete"] = 1
        return {k: v for k, v in a.items() if v is not None}

    def enregistrer(self, vin_id: int) -> list[int]:
        n = self.nombre.value()
        if not n:
            return []
        a = self.attributs()
        casier = self.casier.currentData()
        positions = None
        if casier and a["statut"] == "en_cave":
            a["emplacement_id"] = casier
            if self.placer.isChecked():
                libres = self.cave.cases_libres(casier)
                positions = [(casier, r, c) for r, c in libres[:n]]
        return self.cave.ajouter_bouteilles(vin_id, n, a, positions,
                                            date_mouvement=a.get("date_achat"))


class DialogueVin(QDialog):
    """Création (vin + premières bouteilles) ou modification d'un vin."""

    def __init__(self, cave, vin_id: int | None = None, parent=None):
        super().__init__(parent)
        self.cave = cave
        self.vin_id = vin_id
        v = cave.vin(vin_id) if vin_id else None
        self.setWindowTitle(tr("saisie.titre_modifier") if v else tr("saisie.titre_nouveau"))
        self.resize(620, 640)
        racine = QVBoxLayout(self)
        onglets = QTabWidget()
        racine.addWidget(onglets)

        page = QWidget()
        f = QFormLayout(page)
        g = (lambda k: v[k] if v is not None else None)
        dist = cave.valeurs_distinctes
        self.producteur = _ligne(g("producteur"), dist("producteur"))
        self.cuvee = _ligne(g("cuvee"))
        officielles = cave.references.noms_appellations()
        self.appellation = _ligne(g("appellation"),
                                  sorted(set(dist("appellation")) | set(officielles), key=str.lower))
        self.appellation_officielle = QLabel()
        self.appellation_officielle.setObjectName("legende")
        self.appellation_officielle.setWordWrap(True)
        self.appellation_officielle.linkActivated.connect(self._corriger_appellation)
        self.appellation.editingFinished.connect(self._verifier_appellation)
        self._verifier_appellation()
        self.region = _ligne(g("region"), dist("region"))
        self.sous_region = _ligne(g("sous_region"), dist("sous_region"))
        self.pays = _ligne(g("pays"), dist("pays"))
        self.classement = _ligne(g("classement"), dist("classement"))
        self.couleur = _combo_enum("couleur", valeur=g("couleur"))
        self.type = _combo_enum("type", vide=False, valeur=g("type") or "tranquille")
        self.millesime = QSpinBox()
        self.millesime.setRange(1799, 2200)
        self.millesime.setSpecialValueText(" ")
        self.millesime.setValue(g("millesime") or 1799)
        self.non_millesime = QCheckBox(tr("saisie.non_millesime"))
        self.non_millesime.setChecked(bool(g("non_millesime")))
        ligne_mil = QHBoxLayout()
        ligne_mil.addWidget(self.millesime)
        ligne_mil.addWidget(self.non_millesime)
        self.degre = _reel(g("degre"), 30, 1, " %")
        self.cepages = _ligne(cepages_vers_texte(cave.cepages(vin_id)) if vin_id else "",
                              dist("cepage"))
        self.cepages.setPlaceholderText(tr("saisie.cepages_aide"))
        self.lwin = _ligne(g("lwin"))
        self.ean = _ligne(g("ean"))
        self.seuil = QSpinBox()
        self.seuil.setRange(0, 999)
        self.seuil.setSpecialValueText(" ")
        self.seuil.setValue(g("seuil_reassort") or 0)
        self.coeur = QCheckBox(tr("saisie.coup_de_coeur"))
        self.coeur.setChecked(bool(g("coup_de_coeur")))
        self.notes = QPlainTextEdit(g("notes") or "")
        self.notes.setMaximumHeight(80)
        # style et niveau de garde du dossier « Le vin » : automatiques sauf choix
        from ..regles.jeu import jeu
        self.style = QComboBox()
        self.style.addItem(tr("saisie.style_auto"), None)
        for s in jeu().styles:
            self.style.addItem(s["nom_fr"] if langue() == "fr" else s["nom_en"], s["id"])
        self.style.setCurrentIndex(max(0, self.style.findData(g("style"))))
        self.style.setToolTip(tr("saisie.style_aide"))
        self.niveau_garde = QComboBox()
        self.niveau_garde.addItem(tr("saisie.niveau_garde_auto"), None)
        for code in referentiels.codes("niveau_garde"):
            self.niveau_garde.addItem(lib("niveau_garde", code), code)
        self.niveau_garde.setCurrentIndex(max(0, self.niveau_garde.findData(g("niveau_garde"))))
        self.niveau_garde.setToolTip(tr("saisie.niveau_garde_aide"))
        for cle, w in (("vin.producteur", self.producteur), ("vin.cuvee", self.cuvee),
                       ("vin.appellation", self.appellation), ("", self.appellation_officielle),
                       ("vin.region_seule", self.region),
                       ("vin.sous_region", self.sous_region), ("vin.pays", self.pays),
                       ("vin.classement", self.classement), ("vin.couleur", self.couleur),
                       ("vin.type", self.type)):
            f.addRow(tr(cle) if cle else "", w)
        f.addRow(tr("vin.millesime"), ligne_mil)
        for cle, w in (("vin.degre", self.degre), ("vin.cepages", self.cepages),
                       ("vin.lwin", self.lwin), ("vin.ean", self.ean),
                       ("vin.seuil", self.seuil), ("", self.coeur), ("vin.style", self.style),
                       ("vin.niveau_garde", self.niveau_garde), ("vin.notes", self.notes)):
            f.addRow(tr(cle) if cle else "", w)
        onglets.addTab(page, tr("saisie.onglet_vin"))

        self.bloc = None
        if v is None:
            self.bloc = BlocBouteilles(cave)
            onglets.addTab(self.bloc, tr("saisie.onglet_bouteilles"))
        boutons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        boutons.button(QDialogButtonBox.StandardButton.Save).setText(tr("bouton.enregistrer"))
        boutons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("bouton.annuler"))
        boutons.accepted.connect(self.accepter)
        boutons.rejected.connect(self.reject)
        racine.addWidget(boutons)

    def _verifier_appellation(self) -> None:
        """Orthographe officielle (registres INAO / eAmbrosia) proposée, jamais imposée."""
        texte = self.appellation.text().strip()
        off = self.cave.references.appellation_officielle(texte) if texte else None
        if off and off["nom"] != texte:
            self._officielle = off["nom"]
            self.appellation_officielle.setText(tr("saisie.appellation_officielle", nom=off["nom"],
                                                   signe=off["signe"] or "", registre=off["registre"]))
        elif off:
            self._officielle = None
            self.appellation_officielle.setText(tr("saisie.appellation_reconnue", signe=off["signe"] or "",
                                                   registre=off["registre"]))
        else:
            self._officielle = None
            self.appellation_officielle.setText("")

    def _corriger_appellation(self, _lien: str) -> None:
        if getattr(self, "_officielle", None):
            self.appellation.setText(self._officielle)
            self._verifier_appellation()

    def donnees(self) -> dict:
        mil = self.millesime.value()
        return {
            "producteur": self.producteur.text(), "cuvee": self.cuvee.text(),
            "appellation": self.appellation.text(), "region": self.region.text(),
            "sous_region": self.sous_region.text(), "pays": self.pays.text(),
            "classement": self.classement.text(), "couleur": _code(self.couleur),
            "type": _code(self.type),
            "millesime": None if (mil == self.millesime.minimum() or self.non_millesime.isChecked())
            else mil,
            "non_millesime": 1 if self.non_millesime.isChecked() else 0,
            "degre": self.degre.value() or None,
            "cepages": texte_vers_cepages(self.cepages.text()),
            "lwin": self.lwin.text(), "ean": self.ean.text(),
            "seuil_reassort": self.seuil.value() or None,
            "coup_de_coeur": 1 if self.coeur.isChecked() else 0,
            "notes": self.notes.toPlainText(),
            "style": self.style.currentData() or "",
            "niveau_garde": self.niveau_garde.currentData() or "",
        }

    def accepter(self) -> None:
        d = self.donnees()
        if not (d["producteur"].strip() or d["cuvee"].strip() or d["appellation"].strip()):
            QMessageBox.warning(self, self.windowTitle(), tr("saisie.erreur_nom"))
            return
        total = sum(p or 0 for _c, p in d["cepages"])
        if total > 100.5:
            QMessageBox.warning(self, self.windowTitle(), tr("saisie.erreur_cepages", total=total))
            return
        self.vin_id = self.cave.enregistrer_vin(d, self.vin_id, origine="manuel")
        if self.bloc is not None:
            self.bloc.enregistrer(self.vin_id)
        self.accept()


class DialogueAjoutBouteilles(QDialog):
    def __init__(self, cave, vin_id: int, parent=None):
        super().__init__(parent)
        self.cave, self.vin_id = cave, vin_id
        self.setWindowTitle(tr("saisie.titre_ajout", vin=cave.nom_vin(vin_id)))
        racine = QVBoxLayout(self)
        self.bloc = BlocBouteilles(cave)
        racine.addWidget(self.bloc)
        boutons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        boutons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("bouton.ajouter"))
        boutons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("bouton.annuler"))
        boutons.accepted.connect(self.accepter)
        boutons.rejected.connect(self.reject)
        racine.addWidget(boutons)
        self.ids: list[int] = []

    def accepter(self) -> None:
        self.ids = self.bloc.enregistrer(self.vin_id)
        self.accept()


class DialogueBouteille(QDialog):
    """Tout ce qui décrit UNE bouteille : achat, niveau, état, caisse, provenance."""

    def __init__(self, cave, bouteille_id: int, parent=None):
        super().__init__(parent)
        self.cave, self.bid = cave, bouteille_id
        b = cave.bouteille(bouteille_id)
        self.setWindowTitle(tr("saisie.titre_bouteille", vin=cave.nom_vin(b["vin_id"])))
        self.resize(560, 600)
        racine = QVBoxLayout(self)
        onglets = QTabWidget()
        racine.addWidget(onglets)

        achat = QWidget()
        fa = QFormLayout(achat)
        self.format = _combo_enum("format", vide=False, valeur=b["format"])
        # une sortie (bue, offerte…) passe par « Sortir » : elle s'inscrit au
        # livre de cave ; ici on ne passe qu'entre « en cave » et « à venir »
        self.statut = QComboBox()
        presentes = ("en_cave", "en_attente", "primeur")
        for code in (presentes if b["statut"] in presentes else (b["statut"],)):
            self.statut.addItem(lib("statut", code), code)
        self.statut.setCurrentIndex(max(0, self.statut.findData(b["statut"])))
        self.statut.setEnabled(b["statut"] in presentes)
        self.prix = _reel(b["prix_achat"], suffixe=" €")
        self.lieu = _ligne(b["lieu_achat"])
        self.date_achat = _date(b["date_achat"])
        self.date_entree = _date(b["date_entree"])
        self.livraison = _date(b["date_livraison_prevue"])
        self.facture = _ligne(b["facture"])
        self.bin = _ligne(b["bin"])
        for cle, w in (("saisie.format", self.format), ("saisie.statut", self.statut),
                       ("saisie.prix", self.prix), ("saisie.lieu_achat", self.lieu),
                       ("saisie.date_achat", self.date_achat), ("saisie.date_entree", self.date_entree),
                       ("saisie.livraison", self.livraison), ("saisie.facture", self.facture),
                       ("saisie.bin", self.bin)):
            fa.addRow(tr(cle), w)
        onglets.addTab(achat, tr("saisie.onglet_achat"))

        etat = QWidget()
        fe = QFormLayout(etat)
        self.niveau = _combo_enum("niveau", valeur=b["niveau"])
        self.niveau_cm = _reel(b["niveau_cm"], 20, 1, " cm")
        self.etiquette = _combo_enum("etat_etiquette", valeur=b["etat_etiquette"])
        self.capsule = _combo_enum("etat_capsule", valeur=b["etat_capsule"])
        self.bouchon = _combo_enum("etat_bouchon", valeur=b["etat_bouchon"])
        self.caisse = _combo_enum("caisse", valeur=b["caisse"])
        self.caisse_complete = QCheckBox(tr("saisie.caisse_complete"))
        self.caisse_complete.setChecked(bool(b["caisse_complete"]))
        self.caisse_ref = _ligne(b["caisse_ref"])
        for cle, w in (("saisie.niveau", self.niveau), ("saisie.niveau_cm", self.niveau_cm),
                       ("saisie.etiquette", self.etiquette), ("saisie.capsule", self.capsule),
                       ("saisie.bouchon", self.bouchon), ("saisie.caisse", self.caisse),
                       ("", self.caisse_complete), ("saisie.caisse_ref", self.caisse_ref)):
            fe.addRow(tr(cle) if cle else "", w)
        aide = QGroupBox(tr("saisie.niveau_aide_titre"))
        la = QHBoxLayout(aide)
        from .regles_ui import IllustrationNiveaux
        self.illustration = IllustrationNiveaux()
        la.addWidget(self.illustration)
        self.sens = QLabel()
        self.sens.setWordWrap(True)
        self.sens.setTextFormat(Qt.TextFormat.RichText)
        la.addWidget(self.sens, 1)
        fe.addRow(aide)
        v = cave.vin(b["vin_id"])
        self._millesime = v["millesime"] if v else None
        self.niveau.currentIndexChanged.connect(lambda _i: self._sens_niveau())
        self.niveau_cm.valueChanged.connect(lambda _v: self._sens_niveau())
        self._sens_niveau()
        onglets.addTab(etat, tr("saisie.onglet_etat"))

        prov = QWidget()
        fp = QFormLayout(prov)
        self.provenance = _ligne(b["provenance"])
        self.historique = QPlainTextEdit(b["historique_stockage"] or "")
        self.notes = QPlainTextEdit(b["notes"] or "")
        fp.addRow(tr("saisie.provenance"), self.provenance)
        fp.addRow(tr("saisie.historique"), self.historique)
        fp.addRow(tr("vin.notes"), self.notes)
        onglets.addTab(prov, tr("saisie.onglet_provenance"))

        boutons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        boutons.button(QDialogButtonBox.StandardButton.Save).setText(tr("bouton.enregistrer"))
        boutons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("bouton.annuler"))
        boutons.accepted.connect(self.accepter)
        boutons.rejected.connect(self.reject)
        racine.addWidget(boutons)

    def _sens_niveau(self) -> None:
        """Ce que veut dire ce niveau à l'âge du vin (niveaux.json du dossier)."""
        from html import escape
        from ..regles.niveaux import sens_niveau
        from .regles_ui import age_du_vin, sources_html
        code = _code(self.niveau)
        self.illustration.definir(code)
        age = age_du_vin(self._millesime)
        s = sens_niveau(code, age, self.niveau_cm.value() or None)
        if s is None:
            self.sens.setText(escape(tr("saisie.niveau_aide")))
            return
        tete = lib("verdict_niveau", s.valeur["verdict"])
        if age is not None:
            tete += " " + tr("saisie.niveau_age", age=age)
        self.sens.setText(f"<p><b>{escape(tete)}</b></p><p>{escape(s.explication(langue()))}</p>"
                          + sources_html(s.sources))

    def accepter(self) -> None:
        a = {
            "format": _code(self.format), "prix_achat": self.prix.value() or None,
            "lieu_achat": self.lieu.text().strip() or None,
            "date_achat": _valeur_date(self.date_achat), "date_entree": _valeur_date(self.date_entree),
            "date_livraison_prevue": _valeur_date(self.livraison),
            "facture": self.facture.text().strip() or None, "bin": self.bin.text().strip() or None,
            "niveau": _code(self.niveau), "niveau_cm": self.niveau_cm.value() or None,
            "etat_etiquette": _code(self.etiquette), "etat_capsule": _code(self.capsule),
            "etat_bouchon": _code(self.bouchon), "caisse": _code(self.caisse),
            "caisse_complete": 1 if self.caisse_complete.isChecked() else 0,
            "caisse_ref": self.caisse_ref.text().strip() or None,
            "provenance": self.provenance.text().strip() or None,
            "historique_stockage": self.historique.toPlainText().strip() or None,
            "notes": self.notes.toPlainText().strip() or None,
        }
        if self.statut.isEnabled():
            a["statut"] = _code(self.statut)
        try:
            self.cave.modifier_bouteille(self.bid, a)
        except CaseOccupee as e:
            QMessageBox.warning(self, self.windowTitle(), str(e))
            return
        self.accept()


class DialogueSortie(QDialog):
    """Sortir une bouteille : bue, offerte, vendue, cassée, bouchonnée — avec
    l'occasion, les convives, le plat, la note et le commentaire."""

    def __init__(self, cave, bouteille_id: int, parent=None):
        super().__init__(parent)
        self.cave, self.bid = cave, bouteille_id
        b = cave.bouteille(bouteille_id)
        self.setWindowTitle(tr("sortie.titre", vin=cave.nom_vin(b["vin_id"])))
        self.resize(520, 480)
        racine = QVBoxLayout(self)
        f = QFormLayout()
        racine.addLayout(f)
        self.type = QComboBox()
        for code in referentiels.SORTIE_VERS_STATUT:
            if code != "sortie_inventaire":          # réservé à l'inventaire de contrôle
                self.type.addItem(lib("mouvement", code), code)
        self.date = _date(date.today().isoformat(), vide_permis=False)
        self.occasion = _ligne(completions=[r[0] for r in cave.base.lire(
            "SELECT DISTINCT occasion FROM mouvement WHERE occasion IS NOT NULL")])
        self.convives = _ligne()
        self.plat = _ligne(completions=[r[0] for r in cave.base.lire(
            "SELECT DISTINCT plat FROM mouvement WHERE plat IS NOT NULL")])
        self.note = _reel(None, 100, 1)
        self.echelle = _combo_enum("echelle", vide=False, valeur="20")
        ligne_note = QHBoxLayout()
        ligne_note.addWidget(self.note)
        ligne_note.addWidget(self.echelle)
        self.prix = _reel(suffixe=" €")
        self.commentaire = QPlainTextEdit()
        self.commentaire.setPlaceholderText(tr("sortie.commentaire_aide"))
        f.addRow(tr("sortie.type"), self.type)
        f.addRow(tr("sortie.date"), self.date)
        f.addRow(tr("sortie.occasion"), self.occasion)
        f.addRow(tr("sortie.convives"), self.convives)
        f.addRow(tr("sortie.plat"), self.plat)
        f.addRow(tr("sortie.note"), ligne_note)
        f.addRow(tr("sortie.prix_vente"), self.prix)
        f.addRow(tr("sortie.commentaire"), self.commentaire)
        boutons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        boutons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("sortie.valider"))
        boutons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("bouton.annuler"))
        boutons.accepted.connect(self.accepter)
        boutons.rejected.connect(self.reject)
        racine.addWidget(boutons)
        self.mouvement_id = None

    def accepter(self) -> None:
        self.mouvement_id = self.cave.sortir(
            self.bid, _code(self.type), _valeur_date(self.date),
            occasion=self.occasion.text().strip() or None,
            convives=self.convives.text().strip() or None,
            plat=self.plat.text().strip() or None,
            note=self.note.value() or None,
            echelle=_code(self.echelle) if self.note.value() else None,
            prix=self.prix.value() or None,
            commentaire=self.commentaire.toPlainText().strip() or None)
        self.accept()
