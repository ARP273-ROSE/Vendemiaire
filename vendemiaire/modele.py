# -*- coding: utf-8 -*-
"""Opérations sur la cave : vins, bouteilles, emplacements, livre de cave.

Toutes les écritures passent par `Base.ecriture()` (transaction courte). Les
préparations lentes — lire un fichier, calculer une empreinte d'image — se font
AVANT d'ouvrir la transaction.

Règle d'or des données (reprise de MusicOthèque) : **une saisie manuelle n'est
jamais écrasée par une donnée importée**. `enregistrer_vin(..., origine='manuel')`
écrit ce que l'utilisateur a saisi et le marque dans `origine_champ` ;
`completer_vin(...)` (imports, bases mondiales) ne remplit QUE les champs vides
qui ne sont pas d'origine manuelle, et note chaque remplissage dans
`journal_enrichissement`.
"""
from __future__ import annotations

import hashlib
import shutil
import uuid
from datetime import date
from pathlib import Path
from typing import Iterable

from .base import Base, maintenant, normaliser
from .cave_regles import CaveRegles
from .referentiels import SORTIE_VERS_STATUT, STATUTS_A_VENIR

#: champs de la table vin modifiables par la saisie et les imports
CHAMPS_VIN = ("cuvee", "appellation", "region", "sous_region", "pays", "classement",
              "couleur", "type", "millesime", "non_millesime", "degre", "lwin", "ean",
              "seuil_reassort", "coup_de_coeur", "notes", "style", "niveau_garde")
#: champs de la table bouteille modifiables
CHAMPS_BOUTEILLE = ("format", "statut", "emplacement_id", "rangee", "colonne", "prix_achat",
                    "devise", "lieu_achat", "date_achat", "date_entree",
                    "date_livraison_prevue", "date_sortie", "niveau", "niveau_cm",
                    "etat_etiquette", "etat_capsule", "etat_bouchon", "caisse",
                    "caisse_complete", "caisse_ref", "provenance", "historique_stockage",
                    "facture", "bin", "notes")


class CaseOccupee(ValueError):
    """La case de destination porte déjà une bouteille."""


def _vide(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


class Cave(CaveRegles):
    def __init__(self, base: Base, dossier_images: Path | None = None):
        self.base = base
        self.dossier_images = Path(dossier_images) if dossier_images else \
            base.chemin.parent / "images"
        self._references = None

    @property
    def references(self):
        """Base de référence (LWIN, registres d'appellations), fichier à côté de
        la cave ; créée et garnie des registres embarqués au premier usage."""
        if self._references is None:
            from .mondial.appellations import charger_embarques
            from .references import References
            self._references = References(self.base.chemin.parent / "references.db")
            try:
                charger_embarques(self._references)
            except Exception:                           # registre illisible : la cave marche sans
                import logging
                logging.getLogger(__name__).exception("registres d'appellations embarqués")
        return self._references

    @property
    def dossier_vignettes(self) -> Path:
        return self.base.chemin.parent / "vignettes"

    def fermer_references(self) -> None:
        if self._references is not None:
            self._references.fermer()

    def bouteille_par_code(self, code: str):
        return self.base.un("SELECT * FROM bouteille WHERE code_interne=?", ((code or "").strip(),))

    # =====================================================================
    # Producteurs et vins
    # =====================================================================
    def _producteur(self, c, nom: str | None, pays=None, region=None) -> int | None:
        if _vide(nom):
            return None
        nom = nom.strip()
        norm = normaliser(nom)
        ligne = c.execute("SELECT id FROM producteur WHERE nom_normalise=? ORDER BY id LIMIT 1",
                          (norm,)).fetchone()
        if ligne:
            return ligne[0]
        t = maintenant()
        return c.execute(
            "INSERT INTO producteur(nom, nom_normalise, pays, region, cree_le, modifie_le) "
            "VALUES(?,?,?,?,?,?)", (nom, norm, pays, region, t, t)).lastrowid

    def _marquer(self, c, table: str, ligne_id: int, champs: Iterable[str], origine: str):
        t = maintenant()
        for champ in champs:
            c.execute("INSERT INTO origine_champ(table_nom, ligne_id, champ, origine, date) "
                      "VALUES(?,?,?,?,?) ON CONFLICT(table_nom, ligne_id, champ) DO UPDATE "
                      "SET origine=excluded.origine, date=excluded.date",
                      (table, ligne_id, champ, origine, t))

    def enregistrer_vin(self, donnees: dict, vin_id: int | None = None,
                        origine: str = "manuel") -> int:
        """Crée ou modifie un vin avec ce que l'utilisateur a saisi.

        `donnees` : champs de CHAMPS_VIN, plus « producteur » (nom) et
        « cepages » (liste de (cépage, pourcentage)). Seules les clés présentes
        sont écrites ; une clé présente et vide EFFACE le champ (choix de
        l'utilisateur).

        Marquage « manuel » (que les imports ne toucheront plus) : un champ
        rempli, ou un champ que l'utilisateur a VIDÉ alors qu'il était rempli.
        Un champ laissé vide reste ouvert aux imports et aux bases mondiales."""
        champs = {k: donnees[k] for k in CHAMPS_VIN if k in donnees}
        for k, v in list(champs.items()):
            if isinstance(v, str):
                champs[k] = v.strip() or None
        t = maintenant()
        avant = dict(self.vin(vin_id)) if vin_id is not None else {}
        avant_cepages = self.cepages(vin_id) if vin_id is not None else []
        with self.base.ecriture() as c:
            if "producteur" in donnees:
                champs["producteur_id"] = self._producteur(
                    c, donnees.get("producteur"), donnees.get("pays"), donnees.get("region"))
            if "cuvee" in champs:
                champs["cuvee_normalisee"] = normaliser(champs["cuvee"])
            if vin_id is None:
                champs.setdefault("type", "tranquille")
                cols = list(champs) + ["cree_le", "modifie_le"]
                vals = list(champs.values()) + [t, t]
                vin_id = c.execute(
                    f"INSERT INTO vin({','.join(cols)}) VALUES({','.join('?' * len(cols))})",
                    vals).lastrowid
            elif champs:
                sets = ", ".join(f"{k}=?" for k in champs)
                c.execute(f"UPDATE vin SET {sets}, modifie_le=? WHERE id=?",
                          list(champs.values()) + [t, vin_id])
            if "cepages" in donnees:
                c.execute("DELETE FROM vin_cepage WHERE vin_id=?", (vin_id,))
                for rang, (cep, pct) in enumerate(donnees["cepages"] or [], 1):
                    if not _vide(cep):
                        c.execute("INSERT INTO vin_cepage(vin_id, rang, cepage, pourcentage) "
                                  "VALUES(?,?,?,?)", (vin_id, rang, cep.strip(), pct))
            def _saisi(nouveau, ancien) -> bool:
                return not _vide(nouveau) or not _vide(ancien)
            marques = [k for k in champs if k not in ("cuvee_normalisee", "producteur_id")
                       and _saisi(champs[k], avant.get(k))]
            if "cepages" in donnees and (donnees["cepages"] or avant_cepages):
                marques.append("cepages")
            if "producteur" in donnees and _saisi(donnees.get("producteur"), avant.get("producteur")):
                marques.append("producteur")
            self._marquer(c, "vin", vin_id, marques, origine)
        return vin_id

    def completer_vin(self, vin_id: int, donnees: dict, source: str,
                      detail: str = "") -> list[str]:
        """Remplit les champs VIDES d'un vin depuis une source externe.

        Jamais un champ déjà rempli, jamais un champ d'origine manuelle (même
        vidé par l'utilisateur : il a choisi qu'il soit vide). Renvoie la liste
        des champs remplis, consignés dans journal_enrichissement."""
        actuel = self.base.un("SELECT * FROM vin WHERE id=?", (vin_id,))
        if actuel is None:
            raise KeyError(vin_id)
        manuels = {r[0] for r in self.base.lire(
            "SELECT champ FROM origine_champ WHERE table_nom='vin' AND ligne_id=? "
            "AND origine='manuel'", (vin_id,))}
        a_remplir = {}
        for k in CHAMPS_VIN:
            if k in donnees and not _vide(donnees[k]) and k not in manuels \
                    and _vide(actuel[k]):
                a_remplir[k] = donnees[k].strip() if isinstance(donnees[k], str) else donnees[k]
        nb_cep = self.base.valeur("SELECT COUNT(*) FROM vin_cepage WHERE vin_id=?", (vin_id,))
        cepages = donnees.get("cepages") if (not nb_cep and "cepages" not in manuels) else None
        producteur = (donnees.get("producteur") if actuel["producteur_id"] is None
                      and "producteur" not in manuels else None)
        if not (a_remplir or cepages or not _vide(producteur)):
            return []
        t = maintenant()
        remplis = list(a_remplir)
        with self.base.ecriture() as c:
            if a_remplir:
                # COALESCE(NULLIF(col,'')…) : même si une autre écriture a
                # rempli le champ entre la lecture et l'écriture, on ne l'écrase pas
                sets = ", ".join(f"{k}=COALESCE(NULLIF({k}, ''), ?)" for k in a_remplir)
                c.execute(f"UPDATE vin SET {sets}, modifie_le=? WHERE id=?",
                          list(a_remplir.values()) + [t, vin_id])
                if "cuvee" in a_remplir:
                    c.execute("UPDATE vin SET cuvee_normalisee=? WHERE id=?",
                              (normaliser(a_remplir["cuvee"]), vin_id))
            if not _vide(producteur):
                c.execute("UPDATE vin SET producteur_id=? WHERE id=? AND producteur_id IS NULL",
                          (self._producteur(c, producteur), vin_id))
                remplis.append("producteur")
            if cepages:
                for rang, (cep, pct) in enumerate(cepages, 1):
                    c.execute("INSERT OR IGNORE INTO vin_cepage(vin_id, rang, cepage, pourcentage) "
                              "VALUES(?,?,?,?)", (vin_id, rang, cep, pct))
                remplis.append("cepages")
            self._marquer(c, "vin", vin_id, remplis, source)
            for k in remplis:
                v = a_remplir.get(k, producteur if k == "producteur" else cepages)
                c.execute("INSERT INTO journal_enrichissement(date, table_nom, ligne_id, champ, "
                          "valeur, source, detail) VALUES(?,?,?,?,?,?,?)",
                          (t, "vin", vin_id, k, str(v), source, detail))
        return remplis

    def trouver_vin(self, producteur: str | None, cuvee: str | None,
                    millesime: int | None, appellation: str | None = None) -> int | None:
        """Vin déjà connu (comparaison sur les formes normalisées) ?"""
        lignes = self.base.lire(
            "SELECT v.id, v.appellation FROM vin v LEFT JOIN producteur p ON p.id=v.producteur_id "
            "WHERE COALESCE(p.nom_normalise,'')=? AND COALESCE(v.cuvee_normalisee,'')=? "
            "AND COALESCE(v.millesime, 0)=?",
            (normaliser(producteur), normaliser(cuvee), int(millesime or 0)))
        if not lignes:
            return None
        if appellation:
            for l in lignes:
                if normaliser(l["appellation"]) == normaliser(appellation):
                    return l["id"]
            if len(lignes) > 1:
                return None
            if lignes[0]["appellation"] and normaliser(lignes[0]["appellation"]) != normaliser(appellation):
                return None
        return lignes[0]["id"]

    def supprimer_vin(self, vin_id: int) -> None:
        """Supprime un vin et ses bouteilles. Le livre de cave garde ses lignes
        (vin_id mis à NULL), avec le nom recopié dans le commentaire."""
        nom = self.nom_vin(vin_id)
        with self.base.ecriture() as c:
            c.execute("UPDATE mouvement SET commentaire=COALESCE(commentaire || ' — ', '') || ? "
                      "WHERE vin_id=?", (nom, vin_id))
            c.execute("DELETE FROM bouteille WHERE vin_id=?", (vin_id,))
            c.execute("DELETE FROM origine_champ WHERE table_nom='vin' AND ligne_id=?", (vin_id,))
            c.execute("DELETE FROM vin WHERE id=?", (vin_id,))

    # -- lecture ---------------------------------------------------------------
    def vin(self, vin_id: int):
        return self.base.un(
            "SELECT v.*, p.nom AS producteur FROM vin v "
            "LEFT JOIN producteur p ON p.id=v.producteur_id WHERE v.id=?", (vin_id,))

    def nom_vin(self, vin_id: int) -> str:
        v = self.vin(vin_id)
        if v is None:
            return ""
        morceaux = [v["producteur"], v["cuvee"], v["appellation"],
                    str(v["millesime"]) if v["millesime"] else None]
        return " · ".join(m for m in morceaux if m)

    def cepages(self, vin_id: int) -> list[tuple[str, float | None]]:
        return [(r["cepage"], r["pourcentage"]) for r in self.base.lire(
            "SELECT cepage, pourcentage FROM vin_cepage WHERE vin_id=? ORDER BY rang", (vin_id,))]

    def origines(self, vin_id: int) -> dict[str, str]:
        return {r["champ"]: r["origine"] for r in self.base.lire(
            "SELECT champ, origine FROM origine_champ WHERE table_nom='vin' AND ligne_id=?",
            (vin_id,))}

    def liste_vins(self, texte: str = "", couleur: str = "", pays: str = "",
                   statut: str = "presents") -> list[dict]:
        """Une ligne par vin : quantités, prix, valeur, emplacements.

        statut : « presents » (au moins une bouteille en cave ou à venir),
        « tous », ou un code de statut de bouteille."""
        sql = """
        SELECT v.id, p.nom AS producteur, v.cuvee, v.appellation, v.region, v.pays,
               v.couleur, v.type, v.millesime, v.non_millesime, v.degre, v.lwin,
               v.seuil_reassort, v.coup_de_coeur, v.classement,
               SUM(b.statut='en_cave') AS en_cave,
               SUM(b.statut IN ('en_attente','primeur')) AS a_venir,
               COUNT(b.id) AS total,
               AVG(b.prix_achat) AS prix_moyen,
               SUM(CASE WHEN b.statut='en_cave' THEN b.prix_achat END) AS prix_total,
               (SELECT montant FROM valeur va WHERE va.vin_id=v.id AND va.format='bouteille'
                ORDER BY va.date DESC, va.id DESC LIMIT 1) AS valeur_unitaire,
               GROUP_CONCAT(DISTINCT b.format) AS formats,
               (SELECT GROUP_CONCAT(cepage, ', ') FROM
                  (SELECT cepage FROM vin_cepage vc WHERE vc.vin_id=v.id ORDER BY rang)) AS cepages
        FROM vin v
        LEFT JOIN producteur p ON p.id=v.producteur_id
        LEFT JOIN bouteille b ON b.vin_id=v.id
        WHERE 1=1
        """
        params: list = []
        if couleur:
            sql += " AND v.couleur=?"
            params.append(couleur)
        if pays:
            sql += " AND v.pays=?"
            params.append(pays)
        sql += " GROUP BY v.id"
        if statut == "presents":
            sql += " HAVING en_cave > 0 OR a_venir > 0"
        elif statut and statut != "tous":
            sql += " HAVING SUM(b.statut=?) > 0"
            params.append(statut)
        sql += " ORDER BY p.nom COLLATE NOCASE, v.cuvee COLLATE NOCASE, v.millesime"
        lignes = [dict(r) for r in self.base.lire(sql, params)]
        if texte:
            mots = normaliser(texte).split()
            def _cle(r):
                return normaliser(" ".join(str(r[k] or "") for k in (
                    "producteur", "cuvee", "appellation", "region", "pays", "millesime",
                    "cepages", "classement")))
            lignes = [r for r in lignes if all(m in _cle(r) for m in mots)]
        return lignes

    def valeurs_distinctes(self, champ: str) -> list[str]:
        """Pour les listes de complétion et les filtres (champ de CHAMPS_VIN)."""
        if champ == "producteur":
            return [r[0] for r in self.base.lire(
                "SELECT nom FROM producteur ORDER BY nom COLLATE NOCASE")]
        if champ == "cepage":
            return [r[0] for r in self.base.lire(
                "SELECT DISTINCT cepage FROM vin_cepage ORDER BY cepage COLLATE NOCASE")]
        if champ not in CHAMPS_VIN:
            raise ValueError(champ)
        return [r[0] for r in self.base.lire(
            f"SELECT DISTINCT {champ} FROM vin WHERE {champ} IS NOT NULL AND {champ} <> '' "
            f"ORDER BY {champ} COLLATE NOCASE")]

    # =====================================================================
    # Bouteilles
    # =====================================================================
    def ajouter_bouteilles(self, vin_id: int, nombre: int = 1, attributs: dict | None = None,
                           positions: list[tuple[int, int, int]] | None = None,
                           mouvement: str | None = "entree_achat",
                           date_mouvement: str | None = None) -> list[int]:
        """Ajoute `nombre` bouteilles d'un vin. `positions` : (casier, rangée,
        colonne) pour chacune (facultatif). Une bouteille en cave fait une
        ligne « entrée » dans le livre de cave ; une bouteille en primeur ou en
        attente n'y entre qu'à sa réception (`recevoir`)."""
        attributs = {k: v for k, v in (attributs or {}).items() if k in CHAMPS_BOUTEILLE}
        attributs.setdefault("statut", "en_cave")
        attributs.setdefault("format", "bouteille")
        jour = date_mouvement or attributs.get("date_entree") or date.today().isoformat()
        if attributs["statut"] == "en_cave":
            attributs.setdefault("date_entree", jour)
        positions = list(positions or [])
        t = maintenant()
        ids = []
        with self.base.ecriture() as c:
            for i in range(nombre):
                a = dict(attributs)
                if i < len(positions) and positions[i]:
                    a["emplacement_id"], a["rangee"], a["colonne"] = positions[i]
                    self._verifier_case_libre(c, a["emplacement_id"], a["rangee"], a["colonne"])
                a["code_interne"] = "V" + uuid.uuid4().hex[:10].upper()
                cols = list(a) + ["vin_id", "cree_le", "modifie_le"]
                vals = list(a.values()) + [vin_id, t, t]
                bid = c.execute(
                    f"INSERT INTO bouteille({','.join(cols)}) VALUES({','.join('?' * len(cols))})",
                    vals).lastrowid
                ids.append(bid)
                if a.get("emplacement_id"):
                    c.execute("INSERT INTO deplacement(bouteille_id, date, vers_emplacement, "
                              "vers_rangee, vers_colonne, motif) VALUES(?,?,?,?,?,?)",
                              (bid, t, a["emplacement_id"], a.get("rangee"), a.get("colonne"),
                               "entree"))
            if mouvement and attributs["statut"] == "en_cave":
                for bid in ids:
                    c.execute("INSERT INTO mouvement(date, type, vin_id, bouteille_id, quantite, "
                              "prix, lieu, cree_le) VALUES(?,?,?,?,1,?,?,?)",
                              (jour, mouvement, vin_id, bid, attributs.get("prix_achat"),
                               attributs.get("lieu_achat"), t))
        return ids

    def _verifier_case_libre(self, c, casier, rangee, colonne, sauf: Iterable[int] = ()):
        if casier is None or rangee is None or colonne is None:
            return
        dims = c.execute("SELECT rangees, colonnes FROM emplacement WHERE id=?",
                         (casier,)).fetchone()
        if dims is None:
            raise ValueError(f"emplacement {casier} inconnu")
        if dims[0] and dims[1] and not (1 <= rangee <= dims[0] and 1 <= colonne <= dims[1]):
            raise ValueError(f"case {rangee},{colonne} hors du casier {dims[0]}×{dims[1]}")
        sauf = list(sauf)
        sql = ("SELECT id FROM bouteille WHERE emplacement_id=? AND rangee=? AND colonne=? "
               "AND statut='en_cave'")
        if sauf:
            sql += f" AND id NOT IN ({','.join('?' * len(sauf))})"
        if c.execute(sql, (casier, rangee, colonne, *sauf)).fetchone():
            raise CaseOccupee(f"case {rangee},{colonne} occupée")

    def modifier_bouteille(self, bid: int, attributs: dict) -> None:
        attributs = {k: v for k, v in attributs.items()
                     if k in CHAMPS_BOUTEILLE and k not in ("emplacement_id", "rangee", "colonne")}
        if not attributs:
            return
        sets = ", ".join(f"{k}=?" for k in attributs)
        with self.base.ecriture() as c:
            c.execute(f"UPDATE bouteille SET {sets}, modifie_le=? WHERE id=?",
                      list(attributs.values()) + [maintenant(), bid])
            self._marquer(c, "bouteille", bid, attributs, "manuel")

    def bouteille(self, bid: int):
        return self.base.un("SELECT * FROM bouteille WHERE id=?", (bid,))

    def bouteilles(self, vin_id: int, presentes_seulement: bool = False):
        sql = "SELECT * FROM bouteille WHERE vin_id=?"
        if presentes_seulement:
            sql += " AND statut IN ('en_cave','en_attente','primeur')"
        return self.base.lire(sql + " ORDER BY statut<>'en_cave', id", (vin_id,))

    def deplacer(self, mouvements: list[tuple[int, int | None, int | None, int | None]],
                 motif: str = "") -> str:
        """Déplace une ou plusieurs bouteilles (déplacement en lot), tout ou rien.

        `mouvements` : (bouteille, casier, rangée, colonne). Les échanges de
        cases à l'intérieur du lot sont permis (A va chez B, B chez A). Chaque
        déplacement est consigné avec le même identifiant de lot."""
        lot = uuid.uuid4().hex[:12]
        t = maintenant()
        ids = [m[0] for m in mouvements]
        with self.base.ecriture() as c:
            avant = {r["id"]: r for r in c.execute(
                f"SELECT id, emplacement_id, rangee, colonne, statut FROM bouteille "
                f"WHERE id IN ({','.join('?' * len(ids))})", ids).fetchall()}
            # libérer d'abord toutes les cases du lot, puis poser : les échanges
            # ne heurtent pas l'index d'unicité des cases
            for bid in ids:
                c.execute("UPDATE bouteille SET rangee=NULL, colonne=NULL WHERE id=?", (bid,))
            destinations = set()
            for bid, casier, rangee, colonne in mouvements:
                if bid not in avant:
                    raise KeyError(bid)
                if rangee is not None and (casier, rangee, colonne) in destinations:
                    raise CaseOccupee(f"deux bouteilles vers la case {rangee},{colonne}")
                destinations.add((casier, rangee, colonne))
                self._verifier_case_libre(c, casier, rangee, colonne, sauf=ids)
                c.execute("UPDATE bouteille SET emplacement_id=?, rangee=?, colonne=?, "
                          "modifie_le=? WHERE id=?", (casier, rangee, colonne, t, bid))
                a = avant[bid]
                c.execute("INSERT INTO deplacement(bouteille_id, date, de_emplacement, de_rangee, "
                          "de_colonne, vers_emplacement, vers_rangee, vers_colonne, lot, motif) "
                          "VALUES(?,?,?,?,?,?,?,?,?,?)",
                          (bid, t, a["emplacement_id"], a["rangee"], a["colonne"], casier,
                           rangee, colonne, lot, motif))
        return lot

    def historique_deplacements(self, bid: int):
        return self.base.lire("SELECT * FROM deplacement WHERE bouteille_id=? ORDER BY id", (bid,))

    def sortir(self, bid: int, type_mouvement: str = "sortie_bue", date_sortie: str | None = None,
               **details) -> int:
        """Sort une bouteille de la cave (bue, offerte, vendue, cassée,
        bouchonnée) et l'inscrit au livre de cave avec occasion, convives,
        plat, note, échelle, commentaire, prix."""
        if type_mouvement not in SORTIE_VERS_STATUT:
            raise ValueError(type_mouvement)
        jour = date_sortie or date.today().isoformat()
        b = self.bouteille(bid)
        if b is None:
            raise KeyError(bid)
        if b["statut"] != "en_cave":
            raise ValueError(f"bouteille {bid} : statut {b['statut']}, pas en cave")
        champs = {k: details.get(k) for k in ("occasion", "convives", "plat", "lieu", "note",
                                               "echelle", "commentaire", "prix")}
        with self.base.ecriture() as c:
            c.execute("UPDATE bouteille SET statut=?, date_sortie=?, modifie_le=? WHERE id=?",
                      (SORTIE_VERS_STATUT[type_mouvement], jour, maintenant(), bid))
            return c.execute(
                "INSERT INTO mouvement(date, type, vin_id, bouteille_id, quantite, prix, occasion, "
                "convives, plat, lieu, note, echelle, commentaire, cree_le) "
                "VALUES(?,?,?,?,1,?,?,?,?,?,?,?,?,?)",
                (jour, type_mouvement, b["vin_id"], bid, champs["prix"], champs["occasion"],
                 champs["convives"], champs["plat"], champs["lieu"], champs["note"],
                 champs["echelle"], champs["commentaire"], maintenant())).lastrowid

    def recevoir(self, bid: int, date_reception: str | None = None,
                 position: tuple[int, int, int] | None = None) -> None:
        """Une bouteille en primeur ou en attente arrive en cave."""
        b = self.bouteille(bid)
        if b is None or b["statut"] not in STATUTS_A_VENIR:
            raise ValueError(f"bouteille {bid} : rien à recevoir")
        jour = date_reception or date.today().isoformat()
        with self.base.ecriture() as c:
            if position:
                self._verifier_case_libre(c, *position)
                c.execute("UPDATE bouteille SET emplacement_id=?, rangee=?, colonne=? WHERE id=?",
                          (*position, bid))
            c.execute("UPDATE bouteille SET statut='en_cave', date_entree=?, modifie_le=? "
                      "WHERE id=?", (jour, maintenant(), bid))
            c.execute("INSERT INTO mouvement(date, type, vin_id, bouteille_id, quantite, prix, "
                      "cree_le) VALUES(?,?,?,?,1,?,?)",
                      (jour, "entree_primeur" if b["statut"] == "primeur" else "entree_achat",
                       b["vin_id"], bid, b["prix_achat"], maintenant()))

    # =====================================================================
    # Livre de cave
    # =====================================================================
    def mouvements(self, limite: int | None = None, type_prefixe: str = "", texte: str = ""):
        sql = ("SELECT m.*, p.nom AS producteur, v.cuvee, v.appellation, v.millesime, v.couleur "
               "FROM mouvement m LEFT JOIN vin v ON v.id=m.vin_id "
               "LEFT JOIN producteur p ON p.id=v.producteur_id WHERE 1=1")
        params: list = []
        if type_prefixe:
            sql += " AND m.type LIKE ?"
            params.append(type_prefixe + "%")
        sql += " ORDER BY m.date DESC, m.id DESC"
        if limite and not texte:
            sql += f" LIMIT {int(limite)}"
        lignes = [dict(r) for r in self.base.lire(sql, params)]
        if texte:
            mots = normaliser(texte).split()
            lignes = [r for r in lignes if all(m in normaliser(" ".join(str(r[k] or "") for k in (
                "producteur", "cuvee", "appellation", "millesime", "occasion", "convives", "plat",
                "commentaire"))) for m in mots)]
            if limite:
                lignes = lignes[:limite]
        return lignes

    # -- photos du livre de cave (le plat, la tablée, la bouteille ouverte…)
    def ajouter_photo_mouvement(self, mid: int, fichier: str | Path) -> int:
        """Photo rattachée à une ligne du livre de cave (et au vin, pour sa
        galerie) ; jamais « principale » : la pochette du vin reste son étiquette."""
        vin_id = self.base.valeur("SELECT vin_id FROM mouvement WHERE id=?", (mid,))
        return self.ajouter_image(fichier, vin_id=vin_id, type_image="moment", principale=False,
                                  mouvement_id=mid)

    def photos_mouvement(self, mid: int) -> list[dict]:
        return [dict(r) for r in self.base.lire(
            "SELECT * FROM image WHERE mouvement_id=? ORDER BY id", (mid,))]

    def nombre_photos_mouvements(self) -> dict[int, int]:
        return {r[0]: r[1] for r in self.base.lire(
            "SELECT mouvement_id, COUNT(*) FROM image WHERE mouvement_id IS NOT NULL GROUP BY mouvement_id")}

    def modifier_mouvement(self, mid: int, champs: dict) -> None:
        permis = {k: v for k, v in champs.items() if k in (
            "date", "occasion", "convives", "plat", "lieu", "note", "echelle", "commentaire", "prix")}
        if permis:
            with self.base.ecriture() as c:
                c.execute(f"UPDATE mouvement SET {', '.join(f'{k}=?' for k in permis)} WHERE id=?",
                          list(permis.values()) + [mid])

    # =====================================================================
    # Emplacements
    # =====================================================================
    def creer_emplacement(self, nom: str, niveau: str, parent_id: int | None = None,
                          rangees: int | None = None, colonnes: int | None = None) -> int:
        with self.base.ecriture() as c:
            ordre = c.execute("SELECT COALESCE(MAX(ordre), 0) + 1 FROM emplacement WHERE "
                              "parent_id IS ?", (parent_id,)).fetchone()[0]
            return c.execute("INSERT INTO emplacement(parent_id, niveau, nom, rangees, colonnes, "
                             "ordre) VALUES(?,?,?,?,?,?)",
                             (parent_id, niveau, nom, rangees, colonnes, ordre)).lastrowid

    def renommer_emplacement(self, eid: int, nom: str) -> None:
        with self.base.ecriture() as c:
            c.execute("UPDATE emplacement SET nom=? WHERE id=?", (nom, eid))

    def emplacements(self):
        return self.base.lire("SELECT * FROM emplacement ORDER BY parent_id IS NOT NULL, ordre, id")

    def emplacement(self, eid: int):
        return self.base.un("SELECT * FROM emplacement WHERE id=?", (eid,))

    def chemin_emplacement(self, eid: int | None) -> list[str]:
        noms = []
        vus = set()
        while eid is not None and eid not in vus:
            vus.add(eid)
            e = self.emplacement(eid)
            if e is None:
                break
            noms.append(e["nom"])
            eid = e["parent_id"]
        return list(reversed(noms))

    def contenu_casier(self, casier_id: int):
        """Bouteilles présentes dans un casier, avec de quoi les dessiner."""
        return self.base.lire(
            "SELECT b.id, b.rangee, b.colonne, b.format, b.vin_id, v.couleur, v.type, v.millesime, "
            "v.cuvee, v.appellation, p.nom AS producteur FROM bouteille b JOIN vin v ON v.id=b.vin_id "
            "LEFT JOIN producteur p ON p.id=v.producteur_id "
            "WHERE b.emplacement_id=? AND b.statut='en_cave' ORDER BY b.rangee, b.colonne",
            (casier_id,))

    def cases_libres(self, casier_id: int) -> list[tuple[int, int]]:
        e = self.emplacement(casier_id)
        if e is None or not e["rangees"] or not e["colonnes"]:
            return []
        prises = {(r["rangee"], r["colonne"]) for r in self.contenu_casier(casier_id)}
        return [(r, c) for r in range(1, e["rangees"] + 1) for c in range(1, e["colonnes"] + 1)
                if (r, c) not in prises]

    # =====================================================================
    # Critiques, fenêtres, valeurs, images
    # =====================================================================
    def ajouter_note_critique(self, vin_id: int, critique: str, note: float | None,
                              echelle: str, note_max: float | None = None, texte: str = "",
                              date_note: str | None = None, source: str = "") -> int:
        with self.base.ecriture() as c:
            return c.execute(
                "INSERT INTO note_critique(vin_id, critique, note, note_max, echelle, texte, date, "
                "source) VALUES(?,?,?,?,?,?,?,?)",
                (vin_id, critique, note, note_max, echelle, texte or None, date_note,
                 source or None)).lastrowid

    def notes_critiques(self, vin_id: int):
        return self.base.lire("SELECT * FROM note_critique WHERE vin_id=? ORDER BY date DESC, id",
                              (vin_id,))

    def definir_fenetre(self, vin_id: int, source: str, debut: int | None, fin: int | None,
                        apogee_debut: int | None = None, apogee_fin: int | None = None,
                        detail_source: str = "", modele: str | None = None,
                        explication: str | None = None) -> None:
        with self.base.ecriture() as c:
            c.execute(
                "INSERT INTO fenetre_degustation(vin_id, source, detail_source, debut, apogee_debut, "
                "apogee_fin, fin, modele, explication, date) VALUES(?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(vin_id, source, detail_source) DO UPDATE SET debut=excluded.debut, "
                "apogee_debut=excluded.apogee_debut, apogee_fin=excluded.apogee_fin, "
                "fin=excluded.fin, modele=excluded.modele, explication=excluded.explication, "
                "date=excluded.date",
                (vin_id, source, detail_source, debut, apogee_debut, apogee_fin, fin, modele,
                 explication, maintenant()))

    def fenetres(self, vin_id: int):
        return self.base.lire("SELECT * FROM fenetre_degustation WHERE vin_id=? ORDER BY "
                              "CASE source WHEN 'perso' THEN 0 WHEN 'critique' THEN 1 ELSE 2 END",
                              (vin_id,))

    def ajouter_valeur(self, vin_id: int, montant: float, source: str,
                       date_valeur: str | None = None, format_code: str = "bouteille",
                       devise: str = "EUR", url: str | None = None) -> int:
        with self.base.ecriture() as c:
            return c.execute("INSERT INTO valeur(vin_id, format, montant, devise, date, source, url) "
                             "VALUES(?,?,?,?,?,?,?)",
                             (vin_id, format_code, montant, devise,
                              date_valeur or date.today().isoformat(), source, url)).lastrowid

    def valeurs(self, vin_id: int):
        return self.base.lire("SELECT * FROM valeur WHERE vin_id=? ORDER BY date DESC, id DESC",
                              (vin_id,))

    def _copier_image(self, source: Path) -> tuple[str, str, int | None, int | None]:
        """Copie une image dans le dossier des données (nom = empreinte) : (relatif,
        empreinte, largeur, hauteur). Hors transaction : c'est lent."""
        h = hashlib.sha256(source.read_bytes()).hexdigest()
        cible = self.dossier_images / h[:2] / f"{h}{source.suffix.lower() or '.jpg'}"
        cible.parent.mkdir(parents=True, exist_ok=True)
        if not cible.exists():
            shutil.copy2(source, cible)
        largeur = hauteur = None
        try:
            from PyQt6.QtGui import QImageReader
            taille = QImageReader(str(cible)).size()
            if taille.isValid():
                largeur, hauteur = taille.width(), taille.height()
        except Exception:
            pass
        return cible.relative_to(self.dossier_images).as_posix(), h, largeur, hauteur

    def ajouter_image(self, fichier: str | Path, vin_id: int | None = None,
                      bouteille_id: int | None = None, type_image: str = "etiquette",
                      origine: str = "perso", credit: str | None = None,
                      licence: str | None = None, url_source: str | None = None,
                      principale: bool = True, original: str | Path | None = None,
                      retouche: str | None = None, texte_ocr: str | None = None,
                      mouvement_id: int | None = None) -> int:
        """Copie l'image (et la photo d'origine si `fichier` en est la version
        redressée) dans le dossier des données puis l'inscrit. Copies et
        empreintes AVANT la transaction."""
        relatif, h, largeur, hauteur = self._copier_image(Path(fichier))
        rel_original = self._copier_image(Path(original))[0] if original else None
        with self.base.ecriture() as c:
            if principale and vin_id is not None:
                c.execute("UPDATE image SET principale=0 WHERE vin_id=? AND type=?",
                          (vin_id, type_image))
            return c.execute(
                "INSERT INTO image(vin_id, bouteille_id, mouvement_id, type, fichier, sha256, largeur, "
                "hauteur, origine, credit, licence, url_source, principale, cree_le, "
                "fichier_original, retouche, texte_ocr) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (vin_id, bouteille_id, mouvement_id, type_image, relatif, h, largeur, hauteur,
                 origine, credit, licence, url_source, 1 if principale else 0, maintenant(),
                 rel_original, retouche, texte_ocr)).lastrowid

    def retoucher_image(self, image_id: int, fichier: str | Path, retouche: str | None,
                        texte_ocr: str | None = None) -> None:
        """Nouvelle version redressée d'une image ; la photo d'origine est gardée
        (elle devient `fichier_original` si elle ne l'était pas déjà)."""
        avant = self.base.un("SELECT * FROM image WHERE id=?", (image_id,))
        if avant is None:
            raise KeyError(image_id)
        relatif, h, largeur, hauteur = self._copier_image(Path(fichier))
        with self.base.ecriture() as c:
            c.execute("UPDATE image SET fichier=?, sha256=?, largeur=?, hauteur=?, retouche=?, "
                      "texte_ocr=COALESCE(?, texte_ocr), "
                      "fichier_original=COALESCE(fichier_original, ?) WHERE id=?",
                      (relatif, h, largeur, hauteur, retouche, texte_ocr, avant["fichier"], image_id))
        self._nettoyer_fichier(avant["fichier"])

    def noter_texte_image(self, image_id: int, texte: str) -> None:
        with self.base.ecriture() as c:
            c.execute("UPDATE image SET texte_ocr=? WHERE id=?", (texte, image_id))

    def images(self, vin_id: int):
        return self.base.lire("SELECT * FROM image WHERE vin_id=? ORDER BY type<>'etiquette', "
                              "principale DESC, id", (vin_id,))

    def image(self, image_id: int):
        return self.base.un("SELECT * FROM image WHERE id=?", (image_id,))

    def chemin_image(self, relatif: str | None) -> Path | None:
        if not relatif:
            return None
        p = self.dossier_images / relatif
        return p if p.exists() else None

    def definir_principale(self, image_id: int) -> None:
        im = self.image(image_id)
        if im is None:
            return
        with self.base.ecriture() as c:
            c.execute("UPDATE image SET principale=0 WHERE vin_id=? AND type=?",
                      (im["vin_id"], im["type"]))
            c.execute("UPDATE image SET principale=1 WHERE id=?", (image_id,))

    def changer_type_image(self, image_id: int, type_image: str) -> None:
        with self.base.ecriture() as c:
            c.execute("UPDATE image SET type=?, principale=0 WHERE id=?", (type_image, image_id))

    def supprimer_image(self, image_id: int) -> None:
        im = self.image(image_id)
        if im is None:
            return
        with self.base.ecriture() as c:
            c.execute("DELETE FROM image WHERE id=?", (image_id,))
        for f in (im["fichier"], im["fichier_original"]):
            self._nettoyer_fichier(f)

    def _nettoyer_fichier(self, relatif: str | None) -> None:
        """Efface un fichier d'image que plus aucune ligne ne cite."""
        if not relatif:
            return
        if self.base.valeur("SELECT COUNT(*) FROM image WHERE fichier=? OR fichier_original=?",
                            (relatif, relatif)):
            return
        try:
            (self.dossier_images / relatif).unlink(missing_ok=True)
        except OSError:
            pass

    def mur(self, texte: str = "", statut: str = "presents") -> list[dict]:
        """Le « mur d'étiquettes » : une case par vin, avec sa pochette."""
        vins = self.liste_vins(texte=texte, statut=statut)
        photos = {r["vin_id"]: r["fichier"] for r in self.base.lire(
            "SELECT vin_id, fichier FROM image WHERE type='etiquette' AND vin_id IS NOT NULL "
            "ORDER BY principale, id")}             # la dernière lue gagne : principale, puis la plus récente
        for v in vins:
            v["photo"] = self.chemin_image(photos.get(v["id"]))
        return vins

    def image_principale(self, vin_id: int) -> Path | None:
        r = self.base.un("SELECT fichier FROM image WHERE vin_id=? AND type='etiquette' "
                         "ORDER BY principale DESC, id DESC LIMIT 1", (vin_id,))
        if r is None:
            return None
        p = self.dossier_images / r["fichier"]
        return p if p.exists() else None

    # =====================================================================
    # Bases mondiales : identifiants confirmés, fiches, journal
    # =====================================================================
    def retenir_identifiant(self, vin_id: int, source: str, valeur: str, score: float | None,
                            explication: str | None, confirme: bool = True) -> None:
        """Un vin n'a qu'un identifiant par source : le nouveau remplace l'ancien."""
        with self.base.ecriture() as c:
            c.execute("DELETE FROM identifiant_externe WHERE vin_id=? AND source=?", (vin_id, source))
            c.execute("INSERT INTO identifiant_externe(vin_id, source, valeur, confirme, score, "
                      "explication, date) VALUES(?,?,?,?,?,?,?)",
                      (vin_id, source, str(valeur), 1 if confirme else 0, score, explication,
                       maintenant()))

    def identifiants(self, vin_id: int):
        return self.base.lire("SELECT * FROM identifiant_externe WHERE vin_id=? ORDER BY source",
                              (vin_id,))

    def journal(self, vin_id: int):
        """Ce qui a été rempli automatiquement pour ce vin (et son producteur), et d'où."""
        pid = self.base.valeur("SELECT producteur_id FROM vin WHERE id=?", (vin_id,))
        return self.base.lire(
            "SELECT * FROM journal_enrichissement WHERE (table_nom='vin' AND ligne_id=?) "
            "OR (table_nom='producteur' AND ligne_id=?) ORDER BY id DESC", (vin_id, pid or -1))

    def producteur(self, pid: int):
        return self.base.un("SELECT * FROM producteur WHERE id=?", (pid,))

    def completer_producteur(self, pid: int, donnees: dict, source: str, detail: str = "") -> list[str]:
        """Même règle que completer_vin : champs vides et non manuels seulement."""
        actuel = self.producteur(pid)
        if actuel is None:
            raise KeyError(pid)
        manuels = {r[0] for r in self.base.lire(
            "SELECT champ FROM origine_champ WHERE table_nom='producteur' AND ligne_id=? "
            "AND origine='manuel'", (pid,))}
        a_remplir = {k: v for k, v in donnees.items()
                     if k in ("pays", "region", "adresse", "site_web") and not _vide(v)
                     and k not in manuels and _vide(actuel[k])}
        if not a_remplir:
            return []
        t = maintenant()
        with self.base.ecriture() as c:
            sets = ", ".join(f"{k}=COALESCE(NULLIF({k}, ''), ?)" for k in a_remplir)
            c.execute(f"UPDATE producteur SET {sets}, modifie_le=? WHERE id=?",
                      list(a_remplir.values()) + [t, pid])
            self._marquer(c, "producteur", pid, a_remplir, source)
            for k, v in a_remplir.items():
                c.execute("INSERT INTO journal_enrichissement(date, table_nom, ligne_id, champ, "
                          "valeur, source, detail) VALUES(?,?,?,?,?,?,?)",
                          (t, "producteur", pid, k, str(v), source, detail))
        return list(a_remplir)

    def enregistrer_fiche(self, source: str, identifiant: str, objet: str, donnees: dict,
                          nom: str | None = None, producteur_id: int | None = None,
                          vin_id: int | None = None, licence: str | None = None,
                          url: str | None = None) -> int:
        """Fiche d'une base mondiale (confirmée) rattachée à un producteur ou un vin.
        Une seule fiche par (source, objet, rattachement) : la nouvelle remplace l'ancienne."""
        import json
        with self.base.ecriture() as c:
            c.execute("DELETE FROM fiche_externe WHERE source=? AND objet=? AND "
                      "COALESCE(producteur_id,0)=? AND COALESCE(vin_id,0)=?",
                      (source, objet, producteur_id or 0, vin_id or 0))
            return c.execute(
                "INSERT INTO fiche_externe(source, identifiant, objet, producteur_id, vin_id, nom, "
                "donnees, licence, url, date) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (source, identifiant, objet, producteur_id, vin_id, nom,
                 json.dumps(donnees, ensure_ascii=False), licence, url, maintenant())).lastrowid

    def fiches(self, vin_id: int) -> list[dict]:
        """Fiches du vin et de son producteur (JSON décodé)."""
        import json
        pid = self.base.valeur("SELECT producteur_id FROM vin WHERE id=?", (vin_id,))
        sortie = []
        for r in self.base.lire("SELECT * FROM fiche_externe WHERE vin_id=? OR producteur_id=? "
                                "ORDER BY objet, source", (vin_id, pid or -1)):
            d = dict(r)
            try:
                d["donnees"] = json.loads(d["donnees"])
            except ValueError:
                d["donnees"] = {}
            sortie.append(d)
        return sortie

    # =====================================================================
    # Critiques et valeurs (modifier, supprimer)
    # =====================================================================
    def modifier_note_critique(self, nid: int, critique: str, note: float | None, echelle: str,
                               note_max: float | None = None, texte: str = "",
                               date_note: str | None = None, source: str = "") -> None:
        with self.base.ecriture() as c:
            c.execute("UPDATE note_critique SET critique=?, note=?, note_max=?, echelle=?, texte=?, "
                      "date=?, source=? WHERE id=?",
                      (critique, note, note_max, echelle, texte or None, date_note, source or None,
                       nid))

    def supprimer_note_critique(self, nid: int) -> None:
        with self.base.ecriture() as c:
            c.execute("DELETE FROM note_critique WHERE id=?", (nid,))

    def supprimer_valeur(self, valeur_id: int) -> None:
        with self.base.ecriture() as c:
            c.execute("DELETE FROM valeur WHERE id=?", (valeur_id,))

    def ajouter_valeur_complete(self, vin_id: int, montant: float, source: str, date_valeur: str,
                                format_code: str = "bouteille", devise: str = "EUR",
                                url: str | None = None, note: str | None = None) -> int:
        with self.base.ecriture() as c:
            return c.execute("INSERT INTO valeur(vin_id, format, montant, devise, date, source, url, "
                             "note) VALUES(?,?,?,?,?,?,?,?)",
                             (vin_id, format_code, montant, devise, date_valeur, source,
                              url or None, note or None)).lastrowid

    # =====================================================================
    # Liste d'envies
    # =====================================================================
    CHAMPS_ENVIE = ("vin_id", "producteur", "cuvee", "appellation", "millesime", "quantite",
                    "prix_max", "priorite", "notes")

    def ajouter_envie(self, donnees: dict) -> int:
        d = {k: (donnees[k].strip() or None if isinstance(donnees[k], str) else donnees[k])
             for k in self.CHAMPS_ENVIE if k in donnees}
        cols = list(d) + ["cree_le"]
        with self.base.ecriture() as c:
            return c.execute(f"INSERT INTO envie({','.join(cols)}) VALUES({','.join('?' * len(cols))})",
                             list(d.values()) + [maintenant()]).lastrowid

    def modifier_envie(self, eid: int, donnees: dict) -> None:
        d = {k: (donnees[k].strip() or None if isinstance(donnees[k], str) else donnees[k])
             for k in self.CHAMPS_ENVIE if k in donnees}
        if d:
            with self.base.ecriture() as c:
                c.execute(f"UPDATE envie SET {', '.join(f'{k}=?' for k in d)} WHERE id=?",
                          list(d.values()) + [eid])

    def supprimer_envie(self, eid: int) -> None:
        with self.base.ecriture() as c:
            c.execute("DELETE FROM envie WHERE id=?", (eid,))

    def satisfaire_envie(self, eid: int, jour: str | None = None) -> None:
        with self.base.ecriture() as c:
            c.execute("UPDATE envie SET satisfaite_le=? WHERE id=?",
                      (jour or date.today().isoformat(), eid))

    def envies(self, avec_satisfaites: bool = False) -> list[dict]:
        sql = ("SELECT e.*, (SELECT COUNT(*) FROM bouteille b WHERE b.vin_id=e.vin_id "
               "AND b.statut='en_cave') AS en_cave FROM envie e")
        if not avec_satisfaites:
            sql += " WHERE e.satisfaite_le IS NULL"
        return [dict(r) for r in self.base.lire(sql + " ORDER BY e.satisfaite_le IS NOT NULL, "
                                                "e.priorite, e.id")]

    # =====================================================================
    # Conditions de cave (température, hygrométrie)
    # =====================================================================
    def ajouter_conditions(self, mesures: Iterable[tuple], source: str = "saisie") -> int:
        """`mesures` : (emplacement, date_heure ISO, température, hygrométrie). Une
        mesure déjà présente (même lieu, même instant) n'est pas doublée."""
        mesures = list(mesures)
        n = 0
        with self.base.ecriture() as c:
            for eid, quand, temp, hygro in mesures:
                if c.execute("SELECT 1 FROM condition_cave WHERE emplacement_id IS ? AND date_heure=?",
                             (eid, quand)).fetchone():
                    continue
                c.execute("INSERT INTO condition_cave(emplacement_id, date_heure, temperature, "
                          "hygrometrie, source) VALUES(?,?,?,?,?)", (eid, quand, temp, hygro, source))
                n += 1
        return n

    def conditions(self, emplacement_id: int | None = None, limite: int | None = None):
        sql = "SELECT * FROM condition_cave"
        params: list = []
        if emplacement_id is not None:
            sql += " WHERE emplacement_id=?"
            params.append(emplacement_id)
        sql += " ORDER BY date_heure DESC"
        if limite:
            sql += f" LIMIT {int(limite)}"
        return self.base.lire(sql, params)

    def resume_conditions(self, emplacement_id: int | None = None) -> dict:
        where, params = ("WHERE emplacement_id=?", [emplacement_id]) if emplacement_id else ("", [])
        r = self.base.un(f"SELECT COUNT(*) n, MIN(temperature) tmin, MAX(temperature) tmax, "
                         f"AVG(temperature) tmoy, MIN(hygrometrie) hmin, MAX(hygrometrie) hmax, "
                         f"AVG(hygrometrie) hmoy, MIN(date_heure) debut, MAX(date_heure) fin "
                         f"FROM condition_cave {where}", params)
        return dict(r) if r else {}

    def supprimer_condition(self, cid: int) -> None:
        with self.base.ecriture() as c:
            c.execute("DELETE FROM condition_cave WHERE id=?", (cid,))

    # =====================================================================
    # Inventaire de contrôle
    # =====================================================================
    def attendues(self, casier_id: int) -> list[dict]:
        """Bouteilles que la base place dans ce casier (ou ce meuble, cette cave)."""
        ids = self._descendants(casier_id)
        return [dict(r) for r in self.base.lire(
            f"SELECT b.id, b.code_interne, b.rangee, b.colonne, b.emplacement_id, b.format, b.vin_id "
            f"FROM bouteille b WHERE b.statut='en_cave' AND b.emplacement_id IN "
            f"({','.join('?' * len(ids))}) ORDER BY b.emplacement_id, b.rangee, b.colonne, b.id", ids)]

    def _descendants(self, eid: int) -> list[int]:
        tous = {r["id"]: r["parent_id"] for r in self.emplacements()}
        sortie, file = [], [eid]
        while file:
            e = file.pop()
            sortie.append(e)
            file += [k for k, p in tous.items() if p == e]
        return sortie

    def enregistrer_inventaire(self, casier_id: int, trouvees: Iterable[int],
                               en_trop: Iterable[str] = (), jour: str | None = None) -> dict:
        """Compte d'un casier : attendues, trouvées, manquantes, en trop. Rien
        n'est modifié dans la cave : l'utilisateur décide ensuite (`marquer_manquantes`)."""
        import json
        attendues = {b["id"] for b in self.attendues(casier_id)}
        trouvees = set(trouvees)
        ecarts = {"manquantes": sorted(attendues - trouvees),
                  "ailleurs": sorted(trouvees - attendues),
                  "en_trop": [x for x in en_trop if x]}
        with self.base.ecriture() as c:
            c.execute("INSERT INTO inventaire(emplacement_id, date, attendu, compte, ecarts) "
                      "VALUES(?,?,?,?,?)", (casier_id, jour or date.today().isoformat(),
                                            len(attendues), len(trouvees) + len(ecarts["en_trop"]),
                                            json.dumps(ecarts)))
        return ecarts

    def inventaires(self, casier_id: int | None = None):
        sql = "SELECT * FROM inventaire"
        params = []
        if casier_id is not None:
            sql += " WHERE emplacement_id=?"
            params.append(casier_id)
        return self.base.lire(sql + " ORDER BY date DESC, id DESC", params)

    def marquer_manquantes(self, bouteilles: Iterable[int], jour: str | None = None) -> int:
        """Bouteilles introuvables : sortie « écart d'inventaire » au livre de cave."""
        n = 0
        for bid in bouteilles:
            b = self.bouteille(bid)
            if b is not None and b["statut"] == "en_cave":
                self.sortir(bid, "sortie_inventaire", jour)
                n += 1
        return n

    # =====================================================================
    # Tableau de bord
    # =====================================================================
    def statistiques(self) -> dict:
        b = self.base
        s = {
            "bouteilles": b.valeur("SELECT COUNT(*) FROM bouteille WHERE statut='en_cave'") or 0,
            "a_venir": b.valeur("SELECT COUNT(*) FROM bouteille WHERE statut IN "
                                "('en_attente','primeur')") or 0,
            "vins": b.valeur("SELECT COUNT(DISTINCT vin_id) FROM bouteille WHERE statut='en_cave'") or 0,
            "litres": 0.0,
            "prix_total": b.valeur("SELECT SUM(prix_achat) FROM bouteille WHERE statut='en_cave'") or 0.0,
        }
        from .referentiels import FORMATS_PAR_CODE
        for r in b.lire("SELECT format, COUNT(*) n FROM bouteille WHERE statut='en_cave' "
                        "GROUP BY format"):
            f = FORMATS_PAR_CODE.get(r["format"])
            s["litres"] += (f.litres if f else 0.75) * r["n"]
        # valeur estimée : dernière valeur connue du vin (format bouteille, au
        # prorata pour les autres formats), sinon le prix d'achat
        s["valeur_estimee"] = b.valeur("""
            SELECT SUM(COALESCE((SELECT montant FROM valeur va WHERE va.vin_id=bo.vin_id
                                 AND va.format=bo.format ORDER BY va.date DESC, va.id DESC LIMIT 1),
                                bo.prix_achat, 0))
            FROM bouteille bo WHERE bo.statut='en_cave'""") or 0.0
        groupe = lambda col: [(r[0], r[1]) for r in b.lire(  # noqa: E731
            f"SELECT {col} AS k, COUNT(*) n FROM bouteille bo JOIN vin v ON v.id=bo.vin_id "
            f"WHERE bo.statut='en_cave' GROUP BY k ORDER BY n DESC")]
        s["par_couleur"] = groupe("v.couleur")
        s["par_pays"] = groupe("v.pays")
        s["par_region"] = groupe("v.region")
        s["par_decennie"] = sorted(groupe("(v.millesime / 10) * 10"),
                                   key=lambda x: (x[0] is None, x[0] or 0))
        s["entrees_12_mois"] = b.valeur(
            "SELECT COUNT(*) FROM mouvement WHERE type LIKE 'entree%' AND date >= date('now','-12 months')") or 0
        s["sorties_12_mois"] = b.valeur(
            "SELECT COUNT(*) FROM mouvement WHERE type LIKE 'sortie%' AND date >= date('now','-12 months')") or 0
        s["primeurs"] = [dict(r) for r in b.lire(
            "SELECT bo.vin_id, COUNT(*) n, MIN(bo.date_livraison_prevue) AS livraison "
            "FROM bouteille bo WHERE bo.statut IN ('en_attente','primeur') "
            "GROUP BY bo.vin_id ORDER BY livraison")]
        s["reassort"] = [dict(r) for r in b.lire(
            "SELECT v.id AS vin_id, v.seuil_reassort AS seuil, "
            "(SELECT COUNT(*) FROM bouteille bo WHERE bo.vin_id=v.id AND bo.statut='en_cave') AS n "
            "FROM vin v WHERE v.seuil_reassort IS NOT NULL AND v.seuil_reassort > 0 "
            "AND (SELECT COUNT(*) FROM bouteille bo WHERE bo.vin_id=v.id AND bo.statut='en_cave') "
            "< v.seuil_reassort")]
        s["derniers"] = self.mouvements(limite=8)
        return s
