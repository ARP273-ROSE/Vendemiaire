# -*- coding: utf-8 -*-
"""Séances de dégustation : verticale (un vin sur plusieurs millésimes),
horizontale (plusieurs vins d'un même millésime), à l'aveugle (on note AVANT de
révéler), ou libre.

À l'aveugle, les vins reçoivent un ordre tiré au hasard et une lettre (A, B,
C…) ; tant que la séance n'est pas révélée, l'interface ne montre que les
lettres. Une fois révélée, les notes prises à l'aveugle sont FIGÉES (on ne
peut plus les modifier ni en ajouter) : c'est ce qui donne son sens à
l'exercice."""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date

from .base import maintenant

TYPES = ("verticale", "horizontale", "aveugle", "libre")


class SeanceRevelee(RuntimeError):
    """Note à l'aveugle demandée après la révélation."""


@dataclass
class VinSeance:
    id: int
    vin_id: int
    bouteille_id: int | None
    ordre: int
    etiquette: str
    nom: str
    millesime: int | None
    degustation: dict | None


def creer(cave, type_: str, titre: str = "", jour: str | None = None, notes: str = "") -> int:
    if type_ not in TYPES:
        raise ValueError(type_)
    with cave.base.ecriture() as c:
        return c.execute("INSERT INTO seance(type, titre, date, notes) VALUES(?,?,?,?)",
                         (type_, titre or None, jour or date.today().isoformat(), notes or None)).lastrowid


def modifier(cave, sid: int, titre: str, jour: str, notes: str = "") -> None:
    with cave.base.ecriture() as c:
        c.execute("UPDATE seance SET titre=?, date=?, notes=? WHERE id=?", (titre or None, jour, notes or None, sid))


def supprimer(cave, sid: int) -> None:
    """Supprime la séance ; ses dégustations restent dans les fiches des vins."""
    with cave.base.ecriture() as c:
        c.execute("DELETE FROM seance WHERE id=?", (sid,))


def seance(cave, sid: int) -> dict | None:
    r = cave.base.un("SELECT * FROM seance WHERE id=?", (sid,))
    return dict(r) if r else None


def seances(cave) -> list[dict]:
    return [dict(r) for r in cave.base.lire(
        "SELECT s.*, (SELECT COUNT(*) FROM seance_vin sv WHERE sv.seance_id=s.id) AS n "
        "FROM seance s ORDER BY s.date DESC, s.id DESC")]


def cachee(s: dict) -> bool:
    """Les vins sont-ils encore cachés ?"""
    return s["type"] == "aveugle" and not s.get("revelee_le")


def ajouter_vin(cave, sid: int, vin_id: int, bouteille_id: int | None = None) -> int:
    s = seance(cave, sid)
    if s["type"] == "aveugle" and s.get("revelee_le"):
        raise SeanceRevelee("séance déjà révélée")
    with cave.base.ecriture() as c:
        n = c.execute("SELECT COUNT(*) FROM seance_vin WHERE seance_id=?", (sid,)).fetchone()[0]
        return c.execute("INSERT INTO seance_vin(seance_id, vin_id, bouteille_id, ordre, etiquette) "
                         "VALUES(?,?,?,?,?)", (sid, vin_id, bouteille_id, n, _lettre(n))).lastrowid


def retirer_vin(cave, svid: int) -> None:
    with cave.base.ecriture() as c:
        c.execute("DELETE FROM seance_vin WHERE id=?", (svid,))


def _lettre(i: int) -> str:
    lettres = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return lettres[i] if i < 26 else lettres[i // 26 - 1] + lettres[i % 26]


def melanger(cave, sid: int, graine: int | None = None) -> None:
    """À l'aveugle : nouvel ordre de service tiré au hasard, lettres A, B, C… dans cet ordre."""
    ids = [r["id"] for r in cave.base.lire("SELECT id FROM seance_vin WHERE seance_id=?", (sid,))]
    random.Random(graine).shuffle(ids)
    with cave.base.ecriture() as c:
        for i, svid in enumerate(ids):
            c.execute("UPDATE seance_vin SET ordre=?, etiquette=? WHERE id=?", (i, _lettre(i), svid))


def vins(cave, sid: int) -> list[VinSeance]:
    notes = {r["vin_id"]: dict(r) for r in cave.base.lire(
        "SELECT * FROM degustation WHERE seance_id=? ORDER BY id", (sid,))}
    sortie = []
    for r in cave.base.lire("SELECT sv.*, v.millesime FROM seance_vin sv JOIN vin v ON v.id=sv.vin_id "
                            "WHERE sv.seance_id=? ORDER BY sv.ordre, sv.id", (sid,)):
        sortie.append(VinSeance(r["id"], r["vin_id"], r["bouteille_id"], r["ordre"], r["etiquette"] or "",
                                cave.nom_vin(r["vin_id"]), r["millesime"], notes.get(r["vin_id"])))
    return sortie


def noter(cave, sid: int, vin_id: int, d: dict) -> int:
    """Enregistre (ou remplace) la note de ce vin dans la séance. À l'aveugle,
    refusé après la révélation."""
    s = seance(cave, sid)
    if s["type"] == "aveugle" and s.get("revelee_le"):
        raise SeanceRevelee("séance révélée : les notes à l'aveugle sont figées")
    ancien = cave.base.un("SELECT id FROM degustation WHERE seance_id=? AND vin_id=?", (sid, vin_id))
    sv = cave.base.un("SELECT bouteille_id FROM seance_vin WHERE seance_id=? AND vin_id=?", (sid, vin_id))
    donnees = dict(d, vin_id=vin_id, seance_id=sid, aveugle=1 if s["type"] == "aveugle" else int(d.get("aveugle") or 0),
                   date=d.get("date") or s["date"] or date.today().isoformat())
    if sv and sv["bouteille_id"] and not donnees.get("bouteille_id"):
        donnees["bouteille_id"] = sv["bouteille_id"]
    return cave.enregistrer_degustation(donnees, ancien["id"] if ancien else None)


def reveler(cave, sid: int) -> None:
    with cave.base.ecriture() as c:
        c.execute("UPDATE seance SET revelee_le=? WHERE id=? AND revelee_le IS NULL", (maintenant(), sid))


def suggestions(cave, type_: str, vin_id: int) -> list[int]:
    """Vins de la cave (avec au moins une bouteille) qui vont avec `vin_id` :
    verticale = même producteur, même cuvée, autres millésimes ; horizontale =
    même millésime, même appellation (sinon même région)."""
    v = cave.base.un("SELECT * FROM vin WHERE id=?", (vin_id,))
    if v is None:
        return []
    present = "EXISTS (SELECT 1 FROM bouteille b WHERE b.vin_id=vin.id AND b.statut='en_cave')"
    if type_ == "verticale":
        r = cave.base.lire(f"SELECT id FROM vin WHERE id<>? AND producteur_id IS ? AND COALESCE(cuvee,'')=? "
                           f"AND COALESCE(appellation,'')=? AND {present} ORDER BY millesime",
                           (vin_id, v["producteur_id"], v["cuvee"] or "", v["appellation"] or ""))
        return [x["id"] for x in r]
    if type_ == "horizontale" and v["millesime"]:
        r = cave.base.lire(f"SELECT id FROM vin WHERE id<>? AND millesime=? AND COALESCE(appellation,'')=? "
                           f"AND {present}", (vin_id, v["millesime"], v["appellation"] or ""))
        ids = [x["id"] for x in r]
        if not ids and v["region"]:
            ids = [x["id"] for x in cave.base.lire(
                f"SELECT id FROM vin WHERE id<>? AND millesime=? AND region=? AND couleur IS ? AND {present}",
                (vin_id, v["millesime"], v["region"], v["couleur"]))]
        return ids
    return []
