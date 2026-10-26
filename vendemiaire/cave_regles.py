# -*- coding: utf-8 -*-
"""La cave et les règles du dossier « Le vin » : fenêtres calculées, alertes,
courbe d'apogée, service, bouteilles ouvertes, dégustations, « que boire ce
soir ? ». Mélangé à `modele.Cave` (classe de base) ; aucune règle ici : tout
vient de `vendemiaire.regles`.

Lire puis écrire : les calculs se font AVANT la transaction (règle des
applications de la maison : jamais de travail lent dans `ecriture()`).
"""
from __future__ import annotations

from datetime import date, timedelta

from .base import maintenant
from .regles import accords as r_accords
from .regles import conservation as r_conservation
from .regles import garde as r_garde
from .regles import service as r_service
from .regles.styles import classer

#: ordre de préférence des fenêtres : la mienne, puis celle d'un critique, puis la calculée
ORDRE_SOURCES = {"perso": 0, "critique": 1, "calcul": 2}
OCCASIONS = ("", "aperitif", "quotidien", "grande")


class CaveRegles:
    """Méthodes de `Cave` liées aux règles (voir `modele.Cave`)."""

    # ------------------------------------------------------------------ vins vus par les règles
    def _vins_pour_regles(self, ids=None) -> dict[int, dict]:
        sql = "SELECT v.*, p.nom AS producteur FROM vin v LEFT JOIN producteur p ON p.id=v.producteur_id"
        params: list = []
        if ids is not None:
            ids = list(ids)
            if not ids:
                return {}
            sql += f" WHERE v.id IN ({','.join('?' * len(ids))})"
            params = ids
        vins = {r["id"]: dict(r) for r in self.base.lire(sql, params)}
        for r in self.base.lire("SELECT vin_id, cepage FROM vin_cepage ORDER BY vin_id, rang"):
            if r["vin_id"] in vins:
                vins[r["vin_id"]].setdefault("cepages", []).append(r["cepage"])
        for v in vins.values():
            v.setdefault("cepages", [])
        return vins

    def vin_pour_regles(self, vin_id: int) -> dict | None:
        return self._vins_pour_regles([vin_id]).get(vin_id)

    def style_du_vin(self, vin_id: int):
        v = self.vin_pour_regles(vin_id)
        return classer(v) if v else None

    # ------------------------------------------------------------------ température de cave
    def _racines(self) -> dict[int, int]:
        """emplacement -> cave racine."""
        parents = {r["id"]: r["parent_id"] for r in self.emplacements()}
        racine = {}
        for e in parents:
            x, vus = e, set()
            while parents.get(x) is not None and x not in vus:
                vus.add(x)
                x = parents[x]
            racine[e] = x
        return racine

    def temperatures_caves(self, jours: int = 365) -> dict:
        """Température moyenne mesurée par cave racine (clé None : toutes les
        mesures). Les mesures de la dernière année d'abord ; à défaut, toutes."""
        racine = self._racines()
        limite = (date.today() - timedelta(days=jours)).isoformat()
        lignes = self.base.lire("SELECT emplacement_id, temperature FROM condition_cave "
                                "WHERE temperature IS NOT NULL AND date_heure >= ?", (limite,))
        if not lignes:
            lignes = self.base.lire("SELECT emplacement_id, temperature FROM condition_cave "
                                    "WHERE temperature IS NOT NULL")
        sommes: dict = {}
        for r in lignes:
            for cle in {None, racine.get(r["emplacement_id"]) if r["emplacement_id"] else None}:
                s, n = sommes.get(cle, (0.0, 0))
                sommes[cle] = (s + r["temperature"], n + 1)
        return {k: s / n for k, (s, n) in sommes.items() if n}

    def temperature_du_vin(self, vin_id: int, temperatures: dict | None = None) -> float | None:
        """Moyenne des caves où sont ses bouteilles (mesures rattachées à la
        cave), sinon moyenne de toutes les mesures, sinon None."""
        temperatures = self.temperatures_caves() if temperatures is None else temperatures
        if not temperatures:
            return None
        racine = self._racines()
        caves = {racine.get(r["emplacement_id"]) for r in self.base.lire(
            "SELECT emplacement_id FROM bouteille WHERE vin_id=? AND statut='en_cave' "
            "AND emplacement_id IS NOT NULL", (vin_id,))}
        valeurs = [temperatures[c] for c in caves if c in temperatures]
        if valeurs:
            return sum(valeurs) / len(valeurs)
        return temperatures.get(None)

    def _contexte_garde(self, vin_id: int, temperatures: dict | None = None) -> dict:
        b = self.base.lire("SELECT format, date_entree, date_achat FROM bouteille WHERE vin_id=? "
                           "AND statut IN ('en_cave','en_attente','primeur')", (vin_id,))
        annees = [int(str(x["date_entree"] or x["date_achat"])[:4]) for x in b
                  if (x["date_entree"] or x["date_achat"])]
        return {"temperature_cave": self.temperature_du_vin(vin_id, temperatures),
                "annee_entree": min(annees) if annees else None,
                "formats": tuple(sorted({x["format"] for x in b}))}

    # ------------------------------------------------------------------ fenêtres
    def fenetre_calculee(self, vin_id: int, temperatures: dict | None = None,
                         vin: dict | None = None):
        v = vin or self.vin_pour_regles(vin_id)
        if v is None:
            return None
        return r_garde.fenetre(v, **self._contexte_garde(vin_id, temperatures))

    def enregistrer_fenetres_calculees(self, vin_ids=None) -> int:
        """(Re)calcule la fenêtre de chaque vin et la range dans
        `fenetre_degustation` (source « calcul », detail_source = style/niveau) ;
        les fenêtres « perso » et « critique » ne sont jamais touchées. Calcul
        d'abord, puis une seule transaction courte."""
        vins = self._vins_pour_regles(vin_ids)
        temperatures = self.temperatures_caves()
        lignes = []
        for vid, v in vins.items():
            f = self.fenetre_calculee(vid, temperatures, v)
            if f is None or not f.base:
                lignes.append((vid, None))
                continue
            a = f.annees
            lignes.append((vid, (f.detail_source, a["debut"], a["apogee_debut"], a["apogee_fin"], a["fin"],
                                 f.modele, f.texte_pour_base())))
        t = maintenant()
        with self.base.ecriture() as c:
            for vid, l in lignes:
                c.execute("DELETE FROM fenetre_degustation WHERE vin_id=? AND source='calcul'", (vid,))
                if l is None:
                    continue
                c.execute("INSERT INTO fenetre_degustation(vin_id, source, detail_source, debut, apogee_debut, "
                          "apogee_fin, fin, modele, explication, date) VALUES(?,?,?,?,?,?,?,?,?,?)",
                          (vid, "calcul", l[0], l[1], l[2], l[3], l[4], l[5], l[6], t))
        return sum(1 for _v, l in lignes if l is not None)

    def fenetre_effective(self, vin_id: int) -> dict | None:
        """La fenêtre qui fait foi : la mienne, sinon celle d'un critique, sinon la calculée."""
        lignes = [dict(r) for r in self.fenetres(vin_id)]
        lignes.sort(key=lambda r: ORDRE_SOURCES.get(r["source"], 9))
        for r in lignes:
            if any(r[k] is not None for k in ("debut", "apogee_debut", "apogee_fin", "fin")):
                return r
        f = self.fenetre_calculee(vin_id)
        if f is not None and f.base:
            return dict(f.annees, source="calcul", detail_source=f.detail_source, modele=f.modele)
        return None

    # ------------------------------------------------------------------ état de la cave
    def etat_bouteilles(self, annee: int | None = None) -> list[dict]:
        """Une ligne par bouteille en cave : vin, style, fenêtre qui fait foi,
        phase et alerte de l'année, prix (achat ou dernière valeur)."""
        annee = annee or date.today().year
        vins = self._vins_pour_regles()
        fen: dict[int, dict] = {}
        for r in self.base.lire("SELECT * FROM fenetre_degustation"):
            r = dict(r)
            ancien = fen.get(r["vin_id"])
            if any(r[k] is not None for k in ("debut", "apogee_debut", "apogee_fin", "fin")) and (
                    ancien is None or ORDRE_SOURCES.get(r["source"], 9) < ORDRE_SOURCES.get(ancien["source"], 9)):
                fen[r["vin_id"]] = r
        styles = {vid: classer(v) for vid, v in vins.items()}
        valeurs = {(r["vin_id"], r["format"]): r["montant"] for r in self.base.lire(
            "SELECT vin_id, format, montant FROM valeur va WHERE id = (SELECT id FROM valeur v2 WHERE "
            "v2.vin_id=va.vin_id AND v2.format=va.format ORDER BY date DESC, id DESC LIMIT 1)")}
        sortie = []
        for b in self.base.lire("SELECT * FROM bouteille WHERE statut='en_cave' ORDER BY vin_id, id"):
            v = vins.get(b["vin_id"])
            if v is None:
                continue
            if b["vin_id"] not in fen:
                f = self.fenetre_calculee(b["vin_id"], vin=v)
                fen[b["vin_id"]] = (dict(f.annees, source="calcul", detail_source=f.detail_source)
                                    if f is not None and f.base else {})
            f = fen[b["vin_id"]]
            cl = styles.get(b["vin_id"])
            prix = valeurs.get((b["vin_id"], b["format"]))
            sortie.append({
                "bouteille_id": b["id"], "vin_id": b["vin_id"], "format": b["format"],
                "emplacement_id": b["emplacement_id"], "niveau": b["niveau"], "niveau_cm": b["niveau_cm"],
                "prix": prix if prix is not None else b["prix_achat"], "prix_achat": b["prix_achat"],
                "producteur": v.get("producteur"), "cuvee": v.get("cuvee"), "appellation": v.get("appellation"),
                "millesime": v.get("millesime"), "couleur": v.get("couleur"), "type": v.get("type"),
                "coup_de_coeur": v.get("coup_de_coeur"),
                "style": cl.id if cl else None,
                "source_fenetre": f.get("source"), "debut": f.get("debut"),
                "apogee_debut": f.get("apogee_debut"), "apogee_fin": f.get("apogee_fin"), "fin": f.get("fin"),
                "phase": r_garde.phase(f, annee) if f else None,
                "alerte": r_garde.alerte(f, annee) if f else None,
            })
        return sortie

    def alertes_garde(self, annee: int | None = None) -> dict[str, list[dict]]:
        """{« a_boire » | « declin » | « trop_jeune » : [bouteilles]}."""
        sortie = {"a_boire": [], "declin": [], "trop_jeune": []}
        for b in self.etat_bouteilles(annee):
            if b["alerte"] in sortie:
                sortie[b["alerte"]].append(b)
        return sortie

    def courbe_apogee(self, annee: int | None = None, annees: int = 20):
        annee = annee or date.today().year
        fen = [b for b in self.etat_bouteilles(annee) if b.get("source_fenetre")]
        return r_garde.courbe(fen, annee, annees)

    def bouchons_a_controler(self, annee: int | None = None) -> list[dict]:
        """Bouteilles en cave de plus de 15 ans (`cave.bouchon_fatigue`)."""
        annee = annee or date.today().year
        seuil = r_conservation.age_controle_bouchon()
        return [dict(r) for r in self.base.lire(
            "SELECT b.id AS bouteille_id, b.vin_id, b.niveau, b.niveau_cm, b.etat_bouchon, v.millesime "
            "FROM bouteille b JOIN vin v ON v.id=b.vin_id WHERE b.statut='en_cave' AND v.millesime IS NOT NULL "
            "AND ? - v.millesime >= ? ORDER BY v.millesime, b.id", (annee, seuil))]

    def conditions_hors_plage(self, limite: int = 500) -> list[tuple[dict, list]]:
        """Dernières mesures hors des plages du dossier : [(mesure, [(règle, sens)])]."""
        sortie = []
        for m in self.conditions(limite=limite):
            a = r_conservation.hors_plage(m["temperature"], m["hygrometrie"])
            if a:
                sortie.append((dict(m), a))
        return sortie

    # ------------------------------------------------------------------ service
    def service_du_vin(self, vin_id: int, annee: int | None = None, piece_c: float | None = None,
                       cave_c: float | None = None):
        v = self.vin_pour_regles(vin_id)
        if v is None:
            return None
        if cave_c is None:
            cave_c = self.temperature_du_vin(vin_id)
        return r_service.service(v, annee or date.today().year, cave_c, piece_c)

    # ------------------------------------------------------------------ bouteilles ouvertes
    def entamer(self, bid: int, mode: str = "bouchon", reste_cl: float | None = None,
                jour: str | None = None, **details) -> int:
        """Ouvre une bouteille sans la finir : sortie « bue » au livre de cave et
        fiche « bouteille ouverte » avec la date limite du dossier (haut de la
        fourchette de jours, selon le style et le mode)."""
        jour = jour or date.today().isoformat()
        b = self.bouteille(bid)
        if b is None:
            raise KeyError(bid)
        v = self.vin_pour_regles(b["vin_id"])
        e = r_conservation.bouteille_ouverte(v, mode, date.fromisoformat(jour)) if v else None
        a_finir = e.valeur["a_finir_entre"][1] if e and e.valeur.get("a_finir_entre") else None
        if b["statut"] == "en_cave":
            self.sortir(bid, "sortie_bue", jour, **details)
        with self.base.ecriture() as c:
            return c.execute("INSERT INTO bouteille_ouverte(bouteille_id, ouverte_le, reste_cl, conservation, "
                             "a_finir_avant) VALUES(?,?,?,?,?)",
                             (bid, jour, reste_cl, mode, a_finir)).lastrowid

    def bouteilles_ouvertes(self, avec_finies: bool = False) -> list[dict]:
        sql = ("SELECT o.*, b.vin_id FROM bouteille_ouverte o JOIN bouteille b ON b.id=o.bouteille_id")
        if not avec_finies:
            sql += " WHERE o.finie_le IS NULL"
        return [dict(r) for r in self.base.lire(sql + " ORDER BY o.a_finir_avant IS NULL, o.a_finir_avant")]

    def finir_ouverte(self, oid: int, jour: str | None = None) -> None:
        with self.base.ecriture() as c:
            c.execute("UPDATE bouteille_ouverte SET finie_le=? WHERE id=?",
                      (jour or date.today().isoformat(), oid))

    # ------------------------------------------------------------------ dégustations
    def enregistrer_degustation(self, d: dict, did: int | None = None) -> int:
        champs = ("vin_id", "bouteille_id", "seance_id", "date", "robe", "nez", "bouche", "finale",
                  "aromes", "note", "echelle", "commentaire", "privee", "aveugle")
        valeurs = {k: d.get(k) for k in champs if k in d}
        valeurs.setdefault("date", date.today().isoformat())
        with self.base.ecriture() as c:
            if did is None:
                cols = list(valeurs)
                return c.execute(f"INSERT INTO degustation({','.join(cols)}) VALUES({','.join('?' * len(cols))})",
                                 list(valeurs.values())).lastrowid
            c.execute(f"UPDATE degustation SET {', '.join(f'{k}=?' for k in valeurs)} WHERE id=?",
                      list(valeurs.values()) + [did])
            return did

    def degustations(self, vin_id: int):
        return self.base.lire("SELECT * FROM degustation WHERE vin_id=? ORDER BY date DESC, id DESC", (vin_id,))

    def supprimer_degustation(self, did: int) -> None:
        with self.base.ecriture() as c:
            c.execute("DELETE FROM degustation WHERE id=?", (did,))

    # ------------------------------------------------------------------ que boire ce soir ?
    def que_boire(self, plat: str = "", budget: float | None = None, couleur: str = "",
                  occasion: str = "", annee: int | None = None, avec_trop_jeunes: bool = False) -> dict:
        """Bouteilles proposées pour ce soir, une ligne par vin : d'abord celles en
        déclin, puis « à boire cette année », à l'apogée, buvables ; les trop
        jeunes sont écartées (sauf demande). Filtres : plat (recherche tolérante
        dans les accords du dossier), budget (prix d'achat ou dernière valeur),
        couleur, occasion (apéritif = accords « Apéritif » ; quotidien = les moins
        chères d'abord à urgence égale ; grande occasion = coups de cœur et les
        plus chères d'abord)."""
        etat = self.etat_bouteilles(annee)
        plats, difficiles = [], []
        if occasion == "aperitif" and not plat:
            plats = [p for p in r_accords.plats() if p.id == "aperitif"]
        elif plat:
            plats = r_accords.chercher_plats(plat)
            difficiles = r_accords.difficiles(plat)
        styles = set()
        for p in plats[:1]:
            styles.update(p.styles)
        par_vin: dict[int, dict] = {}
        for b in etat:
            if couleur and b["couleur"] != couleur:
                continue
            if budget and (b["prix"] is None or b["prix"] > budget):
                continue
            if (plat or occasion == "aperitif") and b["style"] not in styles:
                continue
            if b["phase"] == "trop_jeune" and not avec_trop_jeunes:
                continue
            g = par_vin.setdefault(b["vin_id"], dict(b, n=0, bouteilles=[]))
            g["n"] += 1
            g["bouteilles"].append(b["bouteille_id"])
        lignes = [r_accords.Proposition(g, plats[:1]) for g in par_vin.values()]

        def cle(p):
            b = p.bouteille
            prix = b.get("prix") if b.get("prix") is not None else 1e9
            if occasion == "quotidien":
                second = prix
            elif occasion == "grande":
                second = (-(b.get("coup_de_coeur") or 0), -prix if prix < 1e9 else 0)
            else:
                second = b.get("apogee_fin") or 9999
            return (p.rang, second)
        lignes.sort(key=cle)
        return {"plats": plats, "difficiles": difficiles, "propositions": lignes}
