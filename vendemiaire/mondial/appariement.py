# -*- coding: utf-8 -*-
"""Appariement d'un vin de la cave à une base mondiale : candidats classés,
score EXPLIQUÉ, et jamais d'écriture sans confirmation.

Règles reprises de MusicOthèque (mesurées sur de vrais morceaux) :

* le score fourni par une source (rang plein texte, pertinence) ne prouve
  rien : on calcule le nôtre, sur des formes normalisées, critère par critère ;
* on dit POURQUOI : chaque critère donne une ligne d'explication, affichée à
  l'utilisateur et gardée avec l'identifiant confirmé ;
* mieux vaut une case vide qu'une case fausse : sous le seuil, aucun candidat
  n'est proposé d'office ; si deux candidats se valent (écart < 0,05), on
  RENONCE à choisir et l'utilisateur tranche ;
* rien n'est écrit sans confirmation ; la complétion passe par
  `Cave.completer_vin` (champs vides et non manuels seulement, COALESCE,
  journal de ce qui a été rempli et d'où).
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from ..base import normaliser

SEUIL = 0.45            # en dessous : pas de candidat proposé d'office
ECART_AMBIGU = 0.05     # deux candidats à moins de 0,05 : on renonce à choisir

POIDS = {"producteur": 0.45, "cuvee": 0.20, "appellation": 0.15, "couleur": 0.10,
         "pays": 0.05, "millesime": 0.05}


@dataclass
class Raison:
    """Une ligne d'explication : clé de texte (textes.py) et ses valeurs."""
    cle: str
    valeurs: dict = field(default_factory=dict)
    signe: int = 0          # +1 favorable, 0 neutre, -1 défavorable


@dataclass
class Candidat:
    source: str                     # lwin, wikidata, off
    identifiant: str
    libelle: str
    score: float
    raisons: list[Raison]
    donnees: dict                   # ce que la source peut apporter (CHAMPS_VIN + producteur)
    brut: dict = field(default_factory=dict)
    url: str = ""


@dataclass
class Decision:
    candidats: list[Candidat]
    choisi: Candidat | None         # préselection (jamais une écriture)
    motif: str                      # « sur », « ambigu », « faible », « aucun »


# ---------------------------------------------------------------- mesures
def _mot_proche(x: str, y: str) -> bool:
    """Deux mots qui ne diffèrent que d'une lettre ou deux (« marnie » et
    « marnier », une faute de frappe, l'OCR) : mots de 5 lettres au moins."""
    return (len(x) >= 5 and len(y) >= 5 and abs(len(x) - len(y)) <= 2
            and difflib.SequenceMatcher(None, x, y).ratio() >= 0.85)


def _communs(ma: set, mb: set) -> float:
    """Nombre de mots communs ; un mot presque identique compte pour 0,9."""
    n = float(len(ma & mb))
    reste_b = mb - ma
    for x in ma - mb:
        y = next((y for y in reste_b if _mot_proche(x, y)), None)
        if y is not None:
            n += 0.9
            reste_b = reste_b - {y}
    return n


def ressemblance(a: str | None, b: str | None) -> float:
    """0..1 entre deux noms : mots communs (Jaccard), inclusion d'un nom dans
    l'autre, et ressemblance de lettres (fautes de frappe, OCR).

    L'inclusion est prudente (mesuré sur une vraie cave et le vrai fichier LWIN,
    1.0.2) : un nom d'UN seul mot contenu dans un autre (« Le Clos » dans « Clos
    Marnié ») ne prouve presque rien, et chaque mot en trop de l'autre côté
    (« Hospices de Morvan » / « Hospices de Morvan (Maison Arnolet) ») retire un
    peu : le nom exact passe devant le nom augmenté."""
    na, nb = normaliser(a), normaliser(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ma, mb = set(na.split()), set(nb.split())
    commun = _communs(ma, mb)
    jaccard = commun / (len(ma) + len(mb) - commun)
    inclusion = 0.0
    if commun:
        petit, grand = min(len(ma), len(mb)), max(len(ma), len(mb))
        inclusion = min(1.0, commun / petit) * (0.9 - 0.1 * (grand - petit) / grand)
        if petit < 2:
            inclusion *= 0.7
    lettres = difflib.SequenceMatcher(None, na, nb).ratio() * 0.95
    return min(1.0, max(jaccard, inclusion, lettres if lettres >= 0.75 else 0.0))


def couverture(mots_cherches: str | None, texte: str | None) -> float:
    """Part des mots de `mots_cherches` présents dans `texte` (texte d'étiquette)."""
    m = set(normaliser(mots_cherches).split())
    if not m:
        return 0.0
    t = set(normaliser(texte).split())
    trouves = sum(1 for x in m if x in t or (len(x) >= 5 and any(
        difflib.SequenceMatcher(None, x, y).ratio() >= 0.85 for y in t if abs(len(y) - len(x)) <= 2)))
    return trouves / len(m)


def _pct(x: float) -> int:
    return int(round(100 * x))


# ---------------------------------------------------------------- LWIN
def score_lwin(requete: dict, ligne: dict) -> tuple[float, list[Raison]]:
    """Score d'une ligne LWIN pour une requête {producteur, cuvee, appellation,
    region, pays, couleur, type, millesime, texte}. `texte` (lu sur l'étiquette)
    sert quand les champs structurés manquent."""
    raisons: list[Raison] = []
    total = 0.0
    prod_lwin = " ".join(x for x in (ligne.get("titre_producteur"), ligne.get("producteur")) if x)
    texte = requete.get("texte") or ""

    # producteur
    contradiction_producteur = False
    if requete.get("producteur"):
        s = ressemblance(requete["producteur"], prod_lwin)
        raisons.append(Raison("appariement.r_producteur", {"pct": _pct(s), "nom": prod_lwin},
                              1 if s >= 0.8 else (-1 if s < 0.5 else 0)))
        contradiction_producteur = s < 0.5
    elif texte:
        s = couverture(prod_lwin, texte)
        raisons.append(Raison("appariement.r_producteur_texte", {"pct": _pct(s), "nom": prod_lwin},
                              1 if s >= 0.8 else (-1 if s < 0.5 else 0)))
    else:
        s = 0.0
    total += POIDS["producteur"] * s

    # cuvée : LWIN range le climat ou le lieu-dit dans SITE (et PARCEL), le nom de cuvée
    # dans WINE ; « Blanc » / « Rouge » seuls ne sont pas une cuvée (vrai fichier, 1.0.2)
    vin_lwin = cuvee_lwin(ligne, requete.get("appellation"))
    distinct = normaliser(vin_lwin) not in ("", normaliser(prod_lwin))
    cuvee_req = "" if _sans_cuvee(requete.get("cuvee")) else (requete.get("cuvee") or "")
    contradiction_cuvee = False
    if cuvee_req and distinct:
        s = max(ressemblance(cuvee_req, x) for x in _formes_cuvee(ligne, vin_lwin))
        raisons.append(Raison("appariement.r_cuvee", {"pct": _pct(s), "nom": vin_lwin},
                              1 if s >= 0.8 else (-1 if s < 0.5 else 0)))
        contradiction_cuvee = s < 0.5
    elif cuvee_req and not distinct:
        s = 0.4
        raisons.append(Raison("appariement.r_cuvee_absente_lwin", {"nom": cuvee_req}, -1))
    elif distinct and texte:
        s = couverture(vin_lwin, texte)
        raisons.append(Raison("appariement.r_cuvee_texte", {"pct": _pct(s), "nom": vin_lwin},
                              1 if s >= 0.8 else -1))
    elif distinct:
        s = 0.3
        raisons.append(Raison("appariement.r_cuvee_inconnue", {"nom": vin_lwin}, -1))
    else:
        s = 1.0
        raisons.append(Raison("appariement.r_grand_vin", {}, 1))
    total += POIDS["cuvee"] * s

    # appellation (sous-région, site ou région de LWIN)
    lieux = [x for x in (ligne.get("site"), ligne.get("sous_region"), ligne.get("region")) if x]
    if requete.get("appellation") and lieux:
        s, lieu = max((ressemblance(requete["appellation"], x), x) for x in lieux)
        raisons.append(Raison("appariement.r_appellation", {"pct": _pct(s), "nom": lieu},
                              1 if s >= 0.8 else (-1 if s < 0.5 else 0)))
    elif texte and lieux:
        s, lieu = max((couverture(x, texte), x) for x in lieux)
        raisons.append(Raison("appariement.r_appellation_texte", {"pct": _pct(s), "nom": lieu},
                              1 if s >= 0.8 else 0))
    else:
        s = 0.5
    total += POIDS["appellation"] * s

    # couleur : une contradiction pèse lourd (un blanc n'est pas un rouge)
    contradiction = False
    if requete.get("couleur") and ligne.get("couleur"):
        if requete["couleur"] == ligne["couleur"]:
            s = 1.0
            raisons.append(Raison("appariement.r_couleur_ok", {"code": ligne["couleur"]}, 1))
        else:
            s = 0.0
            contradiction = True
            raisons.append(Raison("appariement.r_couleur_non", {"code": ligne["couleur"]}, -1))
    else:
        s = 0.5
    total += POIDS["couleur"] * s

    # pays
    if requete.get("pays") and ligne.get("pays"):
        s = 1.0 if normaliser(requete["pays"]) == normaliser(ligne["pays"]) else 0.0
        if not s:
            raisons.append(Raison("appariement.r_pays_non", {"nom": ligne["pays"]}, -1))
    else:
        s = 0.5
    total += POIDS["pays"] * s

    # millésime dans la période de production connue
    m = requete.get("millesime")
    debut, fin = ligne.get("premier_millesime"), ligne.get("dernier_millesime")
    if m and (debut or fin):
        dedans = (not debut or m >= debut) and (not fin or m <= fin)
        s = 1.0 if dedans else 0.0
        raisons.append(Raison("appariement.r_millesime_ok" if dedans else "appariement.r_millesime_non",
                              {"m": m, "debut": debut or "…", "fin": fin or "…"},
                              1 if dedans else -1))
    else:
        s = 0.5
    total += POIDS["millesime"] * s

    if (ligne.get("type") == "autre"):
        total *= 0.5
        raisons.append(Raison("appariement.r_pas_un_vin", {}, -1))
    if contradiction:
        total *= 0.6
    # un autre domaine ou un autre climat n'est pas le même vin, même si tout le
    # reste concorde (« Les Fournelles » n'est pas « Les Valtières ») : sous le seuil
    if contradiction_producteur:
        total *= 0.5
        raisons.append(Raison("appariement.r_autre_producteur", {}, -1))
    if contradiction_cuvee:
        total *= 0.5
        raisons.append(Raison("appariement.r_autre_cuvee", {}, -1))
    return round(min(1.0, total), 3), raisons


#: une « cuvée » qui n'est qu'une couleur ne distingue rien (LWIN écrit « Blanc »)
_COULEURS_SEULES = {"blanc", "rouge", "rose", "white", "red", "blanche", "bianco", "rosso",
                    "tinto", "blanco"}


def _sans_cuvee(nom: str | None) -> bool:
    n = normaliser(nom)
    return not n or n in _COULEURS_SEULES


def cuvee_lwin(ligne: dict, appellation: str | None = None) -> str:
    """Ce qui distingue ce vin LWIN parmi ceux du producteur : WINE, sinon le
    climat ou le lieu-dit (SITE, PARCEL) — sauf quand SITE n'est que
    l'appellation (« Chablis 1er Cru », « Hautes Cotes de Nuits »)."""
    vin = "" if _sans_cuvee(ligne.get("vin")) else (ligne.get("vin") or "")
    if vin:
        return vin
    site = ligne.get("site") or ""
    if site and _site_est_appellation(site, ligne, appellation):
        site = ""
    return " ".join(x for x in (site, ligne.get("parcelle")) if x)


def _site_est_appellation(site: str, ligne: dict, appellation: str | None) -> bool:
    ns = set(normaliser(site).split())
    for lieu in (ligne.get("sous_region"), appellation):
        nl = set(normaliser(lieu).split())
        if nl and nl <= ns:                       # « Chablis » dans « Chablis 1er Cru »
            return True
    return bool(appellation) and ressemblance(site, appellation) >= 0.8


def _formes_cuvee(ligne: dict, vin_lwin: str) -> list[str]:
    """Formes comparées à la cuvée cherchée : la cuvée LWIN, et climat + cuvée
    (« Porusot Cuvée Jehan Humblot »)."""
    formes = [vin_lwin]
    site = ligne.get("site")
    if site and ligne.get("vin") and not _sans_cuvee(ligne.get("vin")):
        formes.append(f"{site} {vin_lwin}")
    return formes


def candidats_lwin(refs, requete: dict, limite: int = 8, appellation_officielle=None) -> list[Candidat]:
    from .lwin import donnees_pour_vin, PAGE_LWIN
    texte = " ".join(str(requete.get(k) or "") for k in ("producteur", "cuvee", "appellation",
                                                          "texte"))
    lignes = refs.rechercher_lwin(texte, limite=80)
    sortie = []
    for l in lignes:
        score, raisons = score_lwin(requete, l)
        nom = l.get("nom") or " ".join(x for x in (l.get("titre_producteur"), l.get("producteur"),
                                                   l.get("vin")) if x)
        sortie.append(Candidat("lwin", l["lwin"], nom, score, raisons,
                               donnees_pour_vin(l, appellation_officielle), brut=l, url=PAGE_LWIN))
    sortie.sort(key=lambda c: c.score, reverse=True)
    return sortie[:limite]


# ---------------------------------------------------------------- décision
#: raisons qui interdisent la préselection, même avec un bon score : le domaine ou
#: la cuvée ne concordent pas nettement, la cuvée cherchée n'est pas dans la base
#: (le vin générique du domaine n'est PAS le climat cherché), ou l'inverse
_NETTES = ("appariement.r_producteur", "appariement.r_cuvee")
_BLOQUANTES = ("appariement.r_cuvee_absente_lwin", "appariement.r_cuvee_inconnue",
               "appariement.r_autre_producteur", "appariement.r_autre_cuvee",
               "appariement.r_couleur_non")


def certain(c: Candidat) -> bool:
    """Le candidat peut-il être présélectionné ? (en plus du score et de l'écart)"""
    for r in c.raisons:
        if r.cle in _BLOQUANTES or (r.cle in _NETTES and r.signe < 1):
            return False
    return True


def decider(candidats: list[Candidat]) -> Decision:
    """Préselection prudente : jamais deux candidats qui se valent, jamais sous
    le seuil, jamais un candidat dont le domaine ou la cuvée ne concordent pas
    nettement (mesuré en 1.0.2 sur une vraie cave : le village générique d'un
    domaine passait pour son premier cru)."""
    candidats = sorted(candidats, key=lambda c: c.score, reverse=True)
    if not candidats:
        return Decision([], None, "aucun")
    meilleur = candidats[0]
    if meilleur.score < SEUIL:
        return Decision(candidats, None, "faible")
    if len(candidats) > 1 and meilleur.score - candidats[1].score < ECART_AMBIGU:
        return Decision(candidats, None, "ambigu")
    if not certain(meilleur):
        return Decision(candidats, None, "faible")
    return Decision(candidats, meilleur, "sur")


def requete_depuis_vin(cave, vin_id: int) -> dict:
    v = cave.vin(vin_id)
    if v is None:
        return {}
    return {"producteur": v["producteur"], "cuvee": v["cuvee"], "appellation": v["appellation"],
            "region": v["region"], "pays": v["pays"], "couleur": v["couleur"], "type": v["type"],
            "millesime": v["millesime"]}


def explication_texte(raisons: list[Raison], tr) -> str:
    """Explication lisible (dans la langue de l'interface), une raison par ligne."""
    from ..i18n import lib
    lignes = []
    for r in raisons:
        valeurs = dict(r.valeurs)
        if "code" in valeurs:
            valeurs["code"] = lib("couleur", valeurs["code"])
        signe = {1: "+", 0: "·", -1: "−"}[r.signe]
        lignes.append(f"{signe} {tr(r.cle, **valeurs)}")
    return "\n".join(lignes)


# ---------------------------------------------------------------- confirmation
ETATS = ("remplira", "deja", "manuel", "identique")


def apercu(cave, vin_id: int, donnees: dict) -> list[tuple[str, object, object, str]]:
    """Pour chaque champ qu'une source propose : (champ, valeur proposée, valeur
    actuelle, état). État : « remplira » (vide et pas manuel), « identique »,
    « manuel » (saisi ou vidé par l'utilisateur : intouchable), « deja »
    (rempli, on ne remplace pas)."""
    from ..modele import CHAMPS_VIN
    v = cave.vin(vin_id)
    origines = cave.origines(vin_id)
    sortie = []
    for champ, propose in donnees.items():
        if champ not in CHAMPS_VIN and champ not in ("producteur", "cepages"):
            continue
        if champ == "cepages":
            actuel = ", ".join(c for c, _ in cave.cepages(vin_id)) or None
        else:
            actuel = v[champ] if v is not None else None
        if origines.get(champ) == "manuel":
            etat = "manuel" if normaliser(str(actuel or "")) != normaliser(str(propose)) \
                else "identique"
        elif actuel not in (None, ""):
            etat = "identique" if normaliser(str(actuel)) == normaliser(str(propose)) else "deja"
        else:
            etat = "remplira"
        sortie.append((champ, propose, actuel, etat))
    return sortie


def confirmer(cave, vin_id: int, candidat: Candidat, champs: list[str], explication: str) -> list[str]:
    """L'utilisateur a confirmé : on remplit les champs choisis (vides et non
    manuels seulement) et on garde l'identifiant, son score et son pourquoi."""
    donnees = {k: v for k, v in candidat.donnees.items() if k in champs}
    detail = f"{candidat.source}:{candidat.identifiant} ({candidat.libelle})"
    # une seule transaction : champs remplis, journal et identifiant, tout ou rien
    return cave.completer_vin(vin_id, donnees, candidat.source, detail, identifiant={
        "source": candidat.source, "valeur": candidat.identifiant, "score": candidat.score,
        "explication": explication})


def jeton_millesime(texte: str) -> int | None:
    """Premier millésime plausible d'un texte (1900 à l'an prochain)."""
    from datetime import date
    for m in re.finditer(r"(?<!\d)(19\d\d|20\d\d)(?!\d)", texte or ""):
        a = int(m.group(1))
        if 1900 <= a <= date.today().year + 1:
            return a
    return None
