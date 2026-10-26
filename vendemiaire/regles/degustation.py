# -*- coding: utf-8 -*-
"""Dégustation : défauts du vin (`defauts.json`) et roue des arômes
(`aromes.json`).

* Diagnostic : l'utilisateur décrit ce qu'il perçoit (« carton mouillé »,
  « vinaigre »…) ; on propose les défauts dont la description du dossier
  contient ces mots, avec la molécule, le seuil, la cause et que faire. Pas de
  verdict automatique : le dossier décrit, l'utilisateur juge.
* Roue des arômes : cercles (primaire, secondaire, tertiaire, défaut),
  familles (`P.FNR`…) et descripteurs. Une fiche de dégustation range les
  arômes choisis dans `degustation.aromes` sous la forme « CODE:descripteur »
  séparés par « ; » (contrat du dossier : codes séparés par « ; »).
"""
from __future__ import annotations


from .anglais import en
from .jeu import JeuRegles, jeu, normaliser


def defauts(regles: JeuRegles | None = None) -> list[dict]:
    return list((regles or jeu()).defauts)


def texte_defaut(d: dict, champ: str, langue: str) -> str:
    """champ : nom, molecule, seuil, perception, cause, que_faire."""
    cle = {"nom": "nom_fr", "perception": "perception_fr", "cause": "cause_fr",
           "que_faire": "que_faire_fr"}.get(champ, champ)
    v = d.get(cle) or ""
    return v if langue == "fr" else en(v)


def diagnostic(texte: str, regles: JeuRegles | None = None) -> list[tuple[dict, int]]:
    """Défauts dont la description (« ce qu'on sent », nom, molécule), en
    français ou en anglais, contient les mots tapés ; le plus de mots trouvés
    d'abord. Texte vide : tous les défauts, dans l'ordre du dossier."""
    mots = [m for m in normaliser(texte).split() if len(m) >= 3]
    sortie = []
    for i, d in enumerate(defauts(regles)):
        cible = normaliser(" ".join(x for c in ("nom_fr", "perception_fr", "molecule")
                                    for x in (d.get(c) or "", en(d.get(c) or ""))))
        n = sum(1 for m in mots if m in cible) if mots else 1
        if n:
            sortie.append((i, d, n))
    return [(d, n) for _i, d, n in sorted(sortie, key=lambda x: (-x[2], x[0]))]


# ---------------------------------------------------------------------------- roue des arômes
CERCLES = ("primaire", "secondaire", "tertiaire", "défaut")


def familles(regles: JeuRegles | None = None) -> list[dict]:
    return list((regles or jeu()).aromes["familles"])


def nom_famille(f: dict, langue: str) -> str:
    return f["fr"] if langue == "fr" else f["en"]


def descripteur(d: str, langue: str) -> str:
    return d if langue == "fr" else en(d)


def coder(choix: list[tuple[str, str | None]]) -> str:
    """[(code de famille, descripteur ou None)] -> « P.FNR:cassis;S.BOI »."""
    return ";".join(f"{c}:{d}" if d else c for c, d in choix)


def decoder(texte: str | None) -> list[tuple[str, str | None]]:
    sortie = []
    for morceau in (texte or "").split(";"):
        m = morceau.strip()
        if not m:
            continue
        code, _, d = m.partition(":")
        sortie.append((code.strip(), d.strip() or None))
    return sortie


def libelle_arome(code: str, d: str | None, langue: str, regles: JeuRegles | None = None) -> str:
    f = next((x for x in familles(regles) if x["code"] == code), None)
    nom = nom_famille(f, langue) if f else code
    return f"{descripteur(d, langue)} ({nom})" if d else nom
