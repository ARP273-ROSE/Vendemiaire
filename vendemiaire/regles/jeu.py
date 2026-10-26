# -*- coding: utf-8 -*-
"""Chargement et validation du jeu de règles du dossier « Le vin ».

Les fichiers `donnees/*.json` sont des copies octet pour octet du dossier
(`outils/synchroniser_regles.py`) ; `donnees/MANIFESTE.json` garde leur
empreinte SHA-256, leur version et la date de l'audit des règles. Au
chargement on vérifie :

* que chaque fichier a l'empreinte du manifeste (une copie retouchée à la main
  est refusée : une règle se corrige dans le dossier, à un seul endroit) ;
* que chaque règle a un identifiant unique, une confiance connue, des sources
  présentes dans `sources.json`, des styles présents dans `styles.json`.

Un jeu invalide lève `ReglesInvalides` avec la liste des problèmes : on
n'affiche jamais une estimation tirée d'un jeu douteux.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

DONNEES = Path(__file__).resolve().parent / "donnees"
CONFIANCES = ("haute", "moyenne", "faible")
#: source « convention du dossier » : faute de chiffre publié, l'interface le dit
CONVENTION = "DOSSIER"
FICHIERS_REGLES = ("styles.json", "service.json", "garde.json", "conservation.json",
                   "bouteille_ouverte.json", "niveaux.json", "notes.json", "defauts.json",
                   "aromes.json", "accords.json")


class ReglesInvalides(RuntimeError):
    def __init__(self, problemes: list[str]):
        super().__init__("; ".join(problemes[:10]))
        self.problemes = problemes


def normaliser(texte) -> str:
    """Forme de comparaison du dossier : minuscules, sans accents ; traits
    d'union et apostrophes comptent comme des espaces (« Saint-Julien » =
    « saint julien »)."""
    if texte is None:
        return ""
    t = unicodedata.normalize("NFKD", str(texte))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = t.replace("œ", "oe").replace("æ", "ae")
    t = re.sub(r"[-_'’`]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _regles(objet) -> list[dict]:
    """Toutes les règles (dictionnaires portant « id » et « sources ») d'un fichier."""
    trouvees = []
    if isinstance(objet, dict):
        if "id" in objet and ("sources" in objet or "confiance" in objet):
            trouvees.append(objet)
        for v in objet.values():
            if isinstance(v, (dict, list)):
                trouvees += _regles(v)
    elif isinstance(objet, list):
        for v in objet:
            trouvees += _regles(v)
    return trouvees


class JeuRegles:
    """Les règles du dossier, chargées et vérifiées."""

    def __init__(self, dossier: Path = DONNEES, verifier_empreintes: bool = True):
        self.dossier = Path(dossier)
        self.manifeste = json.loads((self.dossier / "MANIFESTE.json").read_text(encoding="utf-8"))
        problemes: list[str] = []
        if verifier_empreintes:
            for nom, info in self.manifeste["fichiers"].items():
                p = self.dossier / nom
                if not p.exists():
                    problemes.append(f"{nom} : absent")
                elif hashlib.sha256(p.read_bytes()).hexdigest() != info["sha256"]:
                    problemes.append(f"{nom} : modifié depuis la copie du dossier (empreinte)")
        if problemes:
            raise ReglesInvalides(problemes)
        lire = lambda n: json.loads((self.dossier / n).read_text(encoding="utf-8"))  # noqa: E731
        self.sources: dict = lire("sources.json")["sources"]
        self.styles: list[dict] = sorted(lire("styles.json")["styles"], key=lambda s: s["priorite"])
        self.styles_par_id = {s["id"]: s for s in self.styles}
        self.service = lire("service.json")
        self.garde = lire("garde.json")
        self.conservation = lire("conservation.json")
        self.ouverte = lire("bouteille_ouverte.json")
        self.niveaux = lire("niveaux.json")
        self.notes = lire("notes.json")
        self.defauts = lire("defauts.json")["defauts"]
        self.aromes = lire("aromes.json")
        self.accords = lire("accords.json")
        self.millesimes = lire("millesimes.json")
        self.corpus = lire("accords_corpus.json")
        self.problemes = self._valider()
        if self.problemes:
            raise ReglesInvalides(self.problemes)

    # ------------------------------------------------------------------ validation
    def _valider(self) -> list[str]:
        p: list[str] = []
        vus: dict[str, str] = {}
        for nom in FICHIERS_REGLES:
            donnees = getattr(self, {"styles.json": "styles", "service.json": "service",
                                     "garde.json": "garde", "conservation.json": "conservation",
                                     "bouteille_ouverte.json": "ouverte", "niveaux.json": "niveaux",
                                     "notes.json": "notes", "defauts.json": "defauts",
                                     "aromes.json": "aromes", "accords.json": "accords"}[nom])
            for r in _regles(donnees):
                rid = r["id"]
                if rid in vus and vus[rid] != nom:
                    p.append(f"{nom} : identifiant {rid} déjà pris dans {vus[rid]}")
                vus.setdefault(rid, nom)
                if "confiance" in r and r["confiance"] not in CONFIANCES:
                    p.append(f"{nom} : {rid} : confiance inconnue {r['confiance']!r}")
                for s in r.get("sources") or []:
                    if s not in self.sources:
                        p.append(f"{nom} : {rid} : source inconnue {s}")
                for st in r.get("styles") or []:
                    if st != "*" and st not in self.styles_par_id:
                        p.append(f"{nom} : {rid} : style inconnu {st}")
        for sid, fenetres in self.garde["styles"].items():
            if sid not in self.styles_par_id:
                p.append(f"garde.json : style inconnu {sid}")
            for f in fenetres:
                if f.get("confiance") not in CONFIANCES:
                    p.append(f"garde.json : {sid}/{f.get('niveau')} : confiance inconnue")
                for s in f.get("sources") or []:
                    if s not in self.sources:
                        p.append(f"garde.json : {sid}/{f.get('niveau')} : source inconnue {s}")
                fa = f["fenetre_ans"]
                suite = [fa[k] for k in ("pret", "apogee_debut", "apogee_fin", "fin") if fa[k] is not None]
                if suite != sorted(suite):
                    p.append(f"garde.json : {sid}/{f.get('niveau')} : fenêtre dans le désordre")
        for st in self.styles:
            if not st["criteres"]["couleur"] or not st["criteres"]["type"]:
                p.append(f"styles.json : {st['id']} sans couleur ou type")
        return p

    # ------------------------------------------------------------------ accès
    @property
    def date_audit(self) -> str | None:
        return self.manifeste.get("date_audit")

    def version(self, fichier: str) -> str | None:
        return (self.manifeste["fichiers"].get(fichier) or {}).get("version")

    def source(self, sid: str) -> dict:
        return self.sources.get(sid) or {"titre": sid}

    def titres_sources(self, ids) -> list[str]:
        return [f"{s} — {self.source(s).get('titre', s)}" for s in ids or []]

    def nombre_regles(self) -> int:
        """Décompte du dossier (`scripts/regles.py`, `nombre_regles`) : températures,
        ajustements, sortie de cave, carafe, verres, fenêtres, ajustements de garde,
        cave, bouteille ouverte (+ modes), niveaux, table Decanter (+ règle),
        défauts, principes, plats, accords difficiles."""
        s, a = self.service, self.accords
        return (len(s["temperature"]) + len(s["ajustements_temperature"]) + 1 + len(s["carafe"])
                + len(s["verre"]) + sum(len(v) for v in self.garde["styles"].values())
                + len(self.garde.get("ajustements") or []) + len(self.conservation["cave"])
                + len(self.ouverte["regles"]) + 1 + len(self.niveaux["bordelaise"])
                + len(self.niveaux["bourguignonne_cm"]) + len(self.notes["decanter_100_20"]) + 1
                + len(self.defauts) + len(a["principes"]) + len(a["plats"])
                + len(a["accords_difficiles"]))


@lru_cache(maxsize=1)
def jeu() -> JeuRegles:
    """Le jeu de règles livré avec l'application (chargé une fois)."""
    return JeuRegles()
