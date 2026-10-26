# -*- coding: utf-8 -*-
"""Fiche d'un vin : pochette, identité, fenêtres de dégustation, critiques,
valeurs, et la liste de ses bouteilles avec leurs actions."""
from __future__ import annotations

from datetime import date

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QAbstractItemView, QDialog, QFormLayout, QGroupBox, QHBoxLayout,
                             QLabel, QMessageBox, QPushButton, QScrollArea, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from .. import referentiels, regles
from ..i18n import argent, date_affichee, langue, lib, nombre, tr
from .photos import fichiers_images
from .pochette import pochette


class _Pochette(QLabel):
    """La pochette de la fiche : une photo glissée dessus devient la photo du vin."""
    photo_deposee = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, ev):
        if fichiers_images(ev.mimeData()):
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        f = fichiers_images(ev.mimeData())
        if f:
            self.photo_deposee.emit(f[0])
            ev.acceptProposedAction()


def _cellule(texte) -> QTableWidgetItem:
    it = QTableWidgetItem("" if texte is None else str(texte))
    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return it


class FicheVin(QScrollArea):
    modifier = pyqtSignal(int)
    ajouter_bouteilles = pyqtSignal(int)
    choisir_photo = pyqtSignal(int)
    sortir = pyqtSignal(int)
    modifier_bouteille = pyqtSignal(int)
    recevoir = pyqtSignal(int)
    voir_plan = pyqtSignal(int)
    identifier = pyqtSignal(int)
    photos = pyqtSignal(int)
    envie = pyqtSignal(int)
    photo_deposee = pyqtSignal(object)        # (vin_id, chemin)
    modifie = pyqtSignal(int)

    def __init__(self, cave, parent=None):
        super().__init__(parent)
        self.cave = cave
        self.vin_id: int | None = None
        self.setWidgetResizable(True)
        corps = QWidget()
        self.setWidget(corps)
        racine = QVBoxLayout(corps)

        haut = QHBoxLayout()
        self.image = _Pochette()
        self.image.setFixedSize(150, 200)
        self.image.setToolTip(tr("fiche.deposer_photo"))
        self.image.photo_deposee.connect(lambda f: self.vin_id and self.photo_deposee.emit((self.vin_id, f)))
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        haut.addWidget(self.image)
        identite = QVBoxLayout()
        self.titre = QLabel()
        self.titre.setObjectName("titre")
        self.titre.setWordWrap(True)
        self.sous_titre = QLabel()
        self.sous_titre.setObjectName("sous_titre")
        self.sous_titre.setWordWrap(True)
        identite.addWidget(self.titre)
        identite.addWidget(self.sous_titre)
        self.formulaire = QFormLayout()
        identite.addLayout(self.formulaire)
        identite.addStretch(1)
        boutons = QHBoxLayout()
        self.b_modifier = QPushButton(tr("fiche.modifier"))
        self.b_photo = QPushButton(tr("fiche.photo"))
        self.b_photos = QPushButton(tr("fiche.photos"))
        self.b_identifier = QPushButton(tr("fiche.identifier"))
        self.b_envie = QPushButton(tr("fiche.envie"))
        self.b_envie.setToolTip(tr("fiche.envie_aide"))
        for b in (self.b_modifier, self.b_identifier, self.b_envie):
            boutons.addWidget(b)
        boutons.addStretch(1)
        identite.addLayout(boutons)
        boutons2 = QHBoxLayout()
        for b in (self.b_photo, self.b_photos):
            boutons2.addWidget(b)
        boutons2.addStretch(1)
        identite.addLayout(boutons2)
        haut.addLayout(identite, 1)
        racine.addLayout(haut)

        self.g_fenetres = QGroupBox(tr("fiche.fenetres"))
        lf = QVBoxLayout(self.g_fenetres)
        self.t_fenetres = self._table(["fiche.f_source", "fiche.f_debut", "fiche.f_apogee",
                                       "fiche.f_fin", "fiche.f_pourquoi"])
        self.calcul = QLabel()
        self.calcul.setWordWrap(True)
        self.calcul.setObjectName("legende")
        lf.addWidget(self.t_fenetres)
        lf.addWidget(self.calcul)
        racine.addWidget(self.g_fenetres)

        self.g_critiques = QGroupBox(tr("fiche.critiques"))
        lc = QVBoxLayout(self.g_critiques)
        self.t_critiques = self._table(["fiche.c_critique", "fiche.c_note", "fiche.c_equivalence",
                                        "fiche.c_date", "fiche.c_source"])
        lc.addWidget(self.t_critiques)
        bc = QHBoxLayout()
        self.b_critique_ajouter = QPushButton(tr("fiche.critique_ajouter"))
        self.b_critique_modifier = QPushButton(tr("fiche.critique_modifier"))
        self.b_critique_supprimer = QPushButton(tr("fiche.critique_supprimer"))
        for b in (self.b_critique_ajouter, self.b_critique_modifier, self.b_critique_supprimer):
            bc.addWidget(b)
        bc.addStretch(1)
        lc.addLayout(bc)
        racine.addWidget(self.g_critiques)

        self.g_valeurs = QGroupBox(tr("fiche.valeurs"))
        lv = QVBoxLayout(self.g_valeurs)
        self.t_valeurs = self._table(["fiche.v_date", "fiche.v_montant", "fiche.v_format",
                                      "fiche.v_source"])
        lv.addWidget(self.t_valeurs)
        bv = QHBoxLayout()
        self.b_valeur_ajouter = QPushButton(tr("fiche.valeur_ajouter"))
        self.b_valeur_supprimer = QPushButton(tr("fiche.valeur_supprimer"))
        bv.addWidget(self.b_valeur_ajouter)
        bv.addWidget(self.b_valeur_supprimer)
        bv.addStretch(1)
        lv.addLayout(bv)
        racine.addWidget(self.g_valeurs)

        self.g_bouteilles = QGroupBox(tr("fiche.bouteilles"))
        lb = QVBoxLayout(self.g_bouteilles)
        self.t_bouteilles = self._table(["fiche.b_statut", "fiche.b_format", "fiche.b_emplacement",
                                         "fiche.b_prix", "fiche.b_entree", "fiche.b_niveau",
                                         "fiche.b_etat"])
        self.t_bouteilles.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        lb.addWidget(self.t_bouteilles)
        actions = QHBoxLayout()
        self.b_ajouter = QPushButton(tr("fiche.ajouter_bouteilles"))
        self.b_sortir = QPushButton(tr("fiche.sortir"))
        self.b_sortir.setObjectName("principal")
        self.b_modif_b = QPushButton(tr("fiche.modifier_bouteille"))
        self.b_recevoir = QPushButton(tr("fiche.recevoir"))
        self.b_plan = QPushButton(tr("fiche.voir_plan"))
        for b in (self.b_ajouter, self.b_sortir, self.b_modif_b, self.b_recevoir, self.b_plan):
            actions.addWidget(b)
        actions.addStretch(1)
        lb.addLayout(actions)
        racine.addWidget(self.g_bouteilles)
        self.valeurs = QLabel()
        self.valeurs.setWordWrap(True)
        racine.addWidget(self.valeurs)

        self.g_references = QGroupBox(tr("fiche.references"))
        lr = QVBoxLayout(self.g_references)
        haut_ref = QHBoxLayout()
        self.image_domaine = QLabel()
        self.image_domaine.setFixedSize(200, 140)
        self.image_domaine.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.references = QLabel()
        self.references.setWordWrap(True)
        self.references.setOpenExternalLinks(True)
        self.references.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        haut_ref.addWidget(self.references, 1)
        haut_ref.addWidget(self.image_domaine)
        lr.addLayout(haut_ref)
        self.t_journal = self._table(["fiche.j_date", "fiche.j_champ", "fiche.j_valeur", "fiche.j_source"])
        lr.addWidget(self.t_journal)
        racine.addWidget(self.g_references)
        racine.addStretch(1)

        self.b_modifier.clicked.connect(lambda: self.vin_id and self.modifier.emit(self.vin_id))
        self.b_photo.clicked.connect(lambda: self.vin_id and self.choisir_photo.emit(self.vin_id))
        self.b_photos.clicked.connect(lambda: self.vin_id and self.photos.emit(self.vin_id))
        self.b_identifier.clicked.connect(lambda: self.vin_id and self.identifier.emit(self.vin_id))
        self.b_envie.clicked.connect(lambda: self.vin_id and self.envie.emit(self.vin_id))
        self.b_critique_ajouter.clicked.connect(self.ajouter_critique)
        self.b_critique_modifier.clicked.connect(self.modifier_critique)
        self.b_critique_supprimer.clicked.connect(self.supprimer_critique)
        self.t_critiques.itemDoubleClicked.connect(lambda _i: self.modifier_critique())
        self.b_valeur_ajouter.clicked.connect(self.ajouter_valeur)
        self.b_valeur_supprimer.clicked.connect(self.supprimer_valeur)
        self.b_ajouter.clicked.connect(lambda: self.vin_id and self.ajouter_bouteilles.emit(self.vin_id))
        self.b_sortir.clicked.connect(lambda: self._sur_bouteille(self.sortir))
        self.b_modif_b.clicked.connect(lambda: self._sur_bouteille(self.modifier_bouteille))
        self.b_recevoir.clicked.connect(lambda: self._sur_bouteille(self.recevoir))
        self.b_plan.clicked.connect(lambda: self._sur_bouteille(self.voir_plan))
        self.t_bouteilles.itemSelectionChanged.connect(self._etat_boutons)
        self.afficher(None)

    def _table(self, entetes: list[str]) -> QTableWidget:
        t = QTableWidget(0, len(entetes))
        t.setHorizontalHeaderLabels([tr(e) for e in entetes])
        t.verticalHeader().setVisible(False)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.horizontalHeader().setStretchLastSection(True)
        t.setAlternatingRowColors(True)
        t.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._ajuster(t)
        return t

    @staticmethod
    def _ajuster(t: QTableWidget, maxi: int = 6) -> None:
        """Hauteur à la mesure du contenu (au plus `maxi` lignes visibles)."""
        n = min(maxi, t.rowCount())
        corps = sum(t.rowHeight(i) for i in range(n)) if n else t.verticalHeader().defaultSectionSize()
        barre = t.horizontalScrollBar().sizeHint().height()
        h = t.horizontalHeader().sizeHint().height() + corps + barre
        t.setFixedHeight(h + 2 * t.frameWidth() + 2)

    def bouteille_choisie(self) -> int | None:
        lignes = self.t_bouteilles.selectionModel().selectedRows()
        if not lignes:
            return None
        return self.t_bouteilles.item(lignes[0].row(), 0).data(Qt.ItemDataRole.UserRole)

    def _sur_bouteille(self, signal) -> None:
        bid = self.bouteille_choisie()
        if bid is not None:
            signal.emit(bid)

    def _etat_boutons(self) -> None:
        bid = self.bouteille_choisie()
        b = self.cave.bouteille(bid) if bid else None
        statut = b["statut"] if b else None
        self.b_sortir.setEnabled(statut == "en_cave")
        self.b_modif_b.setEnabled(b is not None)
        self.b_recevoir.setEnabled(statut in ("primeur", "en_attente"))
        self.b_plan.setEnabled(bool(b and b["emplacement_id"]))

    def afficher(self, vin_id: int | None) -> None:
        self.vin_id = vin_id
        v = self.cave.vin(vin_id) if vin_id else None
        for w in (self.b_modifier, self.b_photo, self.b_photos, self.b_identifier, self.b_envie,
                  self.b_ajouter, self.g_fenetres, self.g_critiques, self.g_valeurs, self.g_bouteilles,
                  self.g_references):
            w.setEnabled(v is not None)
        while self.formulaire.rowCount():
            self.formulaire.removeRow(0)
        if v is None:
            self.titre.setText(tr("fiche.aucun"))
            self.sous_titre.setText(tr("fiche.aucun_aide"))
            self.image.clear()
            for t in (self.t_fenetres, self.t_critiques, self.t_bouteilles, self.t_valeurs,
                      self.t_journal):
                t.setRowCount(0)
            self.valeurs.clear()
            self.references.clear()
            self.image_domaine.clear()
            self.calcul.clear()
            self._etat_boutons()
            return
        d = dict(v)
        self.image.setPixmap(pochette(d, 150, 200, self.cave.image_principale(vin_id),
                                      self.cave.dossier_vignettes))
        mil = str(v["millesime"]) if v["millesime"] else (tr("vin.nm") if v["non_millesime"] else "")
        self.titre.setText(" ".join(x for x in (v["producteur"], mil) if x))
        self.sous_titre.setText(" · ".join(x for x in (v["cuvee"], v["appellation"],
                                                        v["classement"]) if x))
        cepages = ", ".join(f"{c} {nombre(p, 0)} %" if p is not None else c
                            for c, p in self.cave.cepages(vin_id))
        lignes = [
            ("vin.region", " › ".join(x for x in (v["pays"], v["region"], v["sous_region"]) if x)),
            ("vin.couleur_type", " · ".join(x for x in (lib("couleur", v["couleur"]),
                                                         lib("type", v["type"])) if x)),
            ("vin.cepages", cepages),
            ("vin.degre", f"{nombre(v['degre'])} %" if v["degre"] else ""),
            ("vin.lwin", v["lwin"] or ""),
            ("vin.seuil", str(v["seuil_reassort"]) if v["seuil_reassort"] else ""),
            ("vin.notes", v["notes"] or ""),
        ]
        for cle, valeur in lignes:
            if valeur:
                etiquette = QLabel(valeur)
                etiquette.setWordWrap(True)
                self.formulaire.addRow(tr(cle), etiquette)

        # fenêtres de dégustation : la mienne, critiques, calculée (phase 3)
        fen = self.cave.fenetres(vin_id)
        self.t_fenetres.setRowCount(len(fen))
        for r, f in enumerate(fen):
            source = lib("source_fenetre", f["source"])
            if f["detail_source"]:
                source += f" ({f['detail_source']})"
            apogee = "–".join(str(x) for x in (f["apogee_debut"], f["apogee_fin"]) if x)
            for c, val in enumerate((source, f["debut"], apogee, f["fin"], f["explication"])):
                self.t_fenetres.setItem(r, c, _cellule(val))
        if not regles.disponibles("fenetre_degustation"):
            self.calcul.setText(tr("fiche.regles_a_venir"))
        else:
            self.calcul.clear()

        from .critiques import equivalence
        notes = self.cave.notes_critiques(vin_id)
        self.t_critiques.setRowCount(len(notes))
        for r, n in enumerate(notes):
            note = nombre(n["note"])
            if n["note_max"]:
                note += f"–{nombre(n['note_max'])}"
            note += " " + lib("echelle", n["echelle"])
            equiv = equivalence(n["note"], n["echelle"]).split("\n")[0] if n["note"] else ""
            nom = referentiels.CRITIQUES.get(n["critique"], (n["critique"],))[0]
            for c, val in enumerate((nom, note, equiv, date_affichee(n["date"]), n["source"] or "")):
                it = _cellule(val)
                if c == 0:
                    it.setData(Qt.ItemDataRole.UserRole, n["id"])
                self.t_critiques.setItem(r, c, it)
        self.t_critiques.resizeColumnsToContents()
        self.b_critique_modifier.setEnabled(bool(notes))
        self.b_critique_supprimer.setEnabled(bool(notes))

        valeurs = self.cave.valeurs(vin_id)
        self.t_valeurs.setRowCount(len(valeurs))
        for r, dv in enumerate(valeurs):
            source = dv["source"] + (f" — {dv['url']}" if dv["url"] else "")
            for c, val in enumerate((date_affichee(dv["date"]), argent(dv["montant"], dv["devise"]),
                                     lib("format", dv["format"]), source)):
                it = _cellule(val)
                if c == 0:
                    it.setData(Qt.ItemDataRole.UserRole, dv["id"])
                self.t_valeurs.setItem(r, c, it)
        self.t_valeurs.resizeColumnsToContents()
        self.b_valeur_supprimer.setEnabled(bool(valeurs))
        self._afficher_references(vin_id)

        bouteilles = self.cave.bouteilles(vin_id)
        self.t_bouteilles.setRowCount(len(bouteilles))
        for r, b in enumerate(bouteilles):
            present = b["statut"] == "en_cave"
            chemin = " › ".join(self.cave.chemin_emplacement(b["emplacement_id"])) if present else ""
            if present and b["rangee"] and b["colonne"]:
                chemin += " " + tr("plan.case", r=b["rangee"], c=b["colonne"])
            etats = ", ".join(x for x in (lib("etat_etiquette", b["etat_etiquette"]),
                                           lib("caisse", b["caisse"]) if b["caisse"] not in
                                           (None, "aucune") else "") if x)
            date_ref = b["date_entree"] if b["statut"] == "en_cave" else (
                b["date_livraison_prevue"] if b["statut"] in ("primeur", "en_attente")
                else b["date_sortie"])
            cellules = (lib("statut", b["statut"]), lib("format", b["format"]), chemin,
                        argent(b["prix_achat"], b["devise"]), date_affichee(date_ref),
                        lib("niveau", b["niveau"]) or (f"{nombre(b['niveau_cm'])} cm"
                                                        if b["niveau_cm"] else ""), etats)
            for c, val in enumerate(cellules):
                it = _cellule(val)
                if c == 0:
                    it.setData(Qt.ItemDataRole.UserRole, b["id"])
                self.t_bouteilles.setItem(r, c, it)
        self.t_bouteilles.resizeColumnsToContents()
        for t in (self.t_fenetres, self.t_critiques, self.t_bouteilles, self.t_valeurs, self.t_journal):
            self._ajuster(t, 8 if t is self.t_bouteilles else 4)
        if bouteilles:
            premiere = next((r for r, b in enumerate(bouteilles) if b["statut"] == "en_cave"), 0)
            self.t_bouteilles.selectRow(premiere)
        valeurs = self.cave.valeurs(vin_id)
        if valeurs:
            dv = valeurs[0]
            self.valeurs.setText(tr("fiche.valeur", montant=argent(dv["montant"], dv["devise"]),
                                    date=date_affichee(dv["date"]), source=dv["source"]))
        else:
            self.valeurs.setText("")
        age = date.today().year - v["millesime"] if v["millesime"] else None
        self.g_bouteilles.setTitle(tr("fiche.bouteilles_age", n=len(bouteilles), age=age)
                                   if age is not None else tr("fiche.bouteilles"))
        self._etat_boutons()

    # ------------------------------------------------------------------ références
    def _afficher_references(self, vin_id: int) -> None:
        morceaux = []
        for i in self.cave.identifiants(vin_id):
            ligne = tr("fiche.identifiant", source=i["source"], valeur=i["valeur"],
                       score=int(round((i["score"] or 0) * 100)), date=date_affichee(i["date"]))
            if i["source"] == "lwin":
                from ..mondial.lwin import lwin11
                v = self.cave.vin(vin_id)
                l11 = lwin11(i["valeur"], v["millesime"], bool(v["non_millesime"]))
                if l11:
                    ligne += f" · LWIN-11 {l11}"
            morceaux.append(ligne)
        self.image_domaine.clear()
        for f in self.cave.fiches(vin_id):
            d = f["donnees"]
            details = [f"<b>{d.get('nom') or f['nom'] or ''}</b>"]
            if d.get("description"):
                details.append(d["description"])
            if d.get("fondation"):
                details.append(tr("ident.fondation", annee=d["fondation"]))
            if d.get("coordonnees"):
                lat, lon = d["coordonnees"]
                details.append(tr("ident.coordonnees", lat=f"{lat:.4f}", lon=f"{lon:.4f}"))
            if d.get("proprietaires"):
                details.append(tr("ident.proprietaires", noms=", ".join(d["proprietaires"][:4])))
            liens = []
            wp = d.get("wikipedia_fr" if langue() == "fr" else "wikipedia_en") or d.get("wikipedia_en")
            if wp:
                liens.append(f'<a href="{wp}">Wikipedia</a>')
            if f["url"]:
                liens.append(f'<a href="{f["url"]}">{f["source"].capitalize()}</a>')
            if d.get("site"):
                liens.append(f'<a href="{d["site"]}">{tr("ident.site_web")}</a>')
            credit = d.get("image_credit") or {}
            if credit.get("image_fichier"):
                chemin = self.cave.chemin_image(credit["image_fichier"])
                if chemin:
                    pm = QPixmap(str(chemin))
                    if not pm.isNull():
                        self.image_domaine.setPixmap(pm.scaled(
                            200, 140, Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation))
                details.append(tr("fiche.credit_image", auteur=credit.get("auteur") or "?",
                                  licence=credit.get("licence") or "?", page=credit.get("page") or ""))
            details.append(" · ".join(liens) + " · " + tr("fiche.licence_fiche", licence=f["licence"] or "?"))
            morceaux.append("<br>".join(details))
        self.references.setText("<br><br>".join(morceaux) if morceaux else tr("fiche.references_aucune"))
        journal = self.cave.journal(vin_id)
        self.t_journal.setRowCount(len(journal))
        for r, j in enumerate(journal):
            source = j["source"] + (f" ({j['detail']})" if j["detail"] else "")
            for c, val in enumerate((date_affichee(j["date"]), j["champ"], j["valeur"], source)):
                self.t_journal.setItem(r, c, _cellule(val))
        self.t_journal.resizeColumnsToContents()

    # ------------------------------------------------------------------ critiques et valeurs
    def _id_choisi(self, table) -> int | None:
        rangs = table.selectionModel().selectedRows()
        if not rangs:
            return None
        return table.item(rangs[0].row(), 0).data(Qt.ItemDataRole.UserRole)

    def ajouter_critique(self) -> None:
        from .critiques import DialogueCritique
        if self.vin_id and DialogueCritique(self.cave, self.vin_id, None, self).exec() \
                == QDialog.DialogCode.Accepted:
            self.modifie.emit(self.vin_id)

    def modifier_critique(self) -> None:
        from .critiques import DialogueCritique
        nid = self._id_choisi(self.t_critiques)
        note = next((dict(n) for n in self.cave.notes_critiques(self.vin_id) if n["id"] == nid), None) \
            if nid else None
        if note and DialogueCritique(self.cave, self.vin_id, note, self).exec() \
                == QDialog.DialogCode.Accepted:
            self.modifie.emit(self.vin_id)

    def supprimer_critique(self) -> None:
        nid = self._id_choisi(self.t_critiques)
        if nid and QMessageBox.question(self, tr("fiche.critiques"), tr("fiche.supprimer_q")) \
                == QMessageBox.StandardButton.Yes:
            self.cave.supprimer_note_critique(nid)
            self.modifie.emit(self.vin_id)

    def ajouter_valeur(self) -> None:
        from .critiques import DialogueValeur
        if self.vin_id and DialogueValeur(self.cave, self.vin_id, self).exec() \
                == QDialog.DialogCode.Accepted:
            self.modifie.emit(self.vin_id)

    def supprimer_valeur(self) -> None:
        vid = self._id_choisi(self.t_valeurs)
        if vid and QMessageBox.question(self, tr("fiche.valeurs"), tr("fiche.supprimer_q")) \
                == QMessageBox.StandardButton.Yes:
            self.cave.supprimer_valeur(vid)
            self.modifie.emit(self.vin_id)
