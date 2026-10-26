# -*- coding: utf-8 -*-
"""Liste d'achats et alertes de prix.

* LISTE D'ACHATS : générée par les seuils de réassort (« garder au moins N
  bouteilles de ce vin » : il en manque seuil − en cave), complétée au choix par
  les envies non satisfaites. Pour chaque ligne : combien acheter, dernier prix
  payé et où, prix maximal de l'envie. Imprimable (PDF) et exportable (CSV).
* ALERTES DE PRIX sur la liste d'envies, SANS aspirateur de sites : on relève
  soi-même un prix vu (marchand, salon, catalogue, avec sa date et sa source),
  ou on importe un fichier CSV de prix relevés. Une envie est en alerte quand
  le prix relevé le plus bas encore récent est au plus son prix maximal — ou
  quand la dernière valeur saisie du vin lié l'est. Les relevés anciens (plus de
  `JOURS_VALIDITE` jours) ne déclenchent plus d'alerte (un prix d'il y a un an
  ne dit plus rien du marché).
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from .base import maintenant, normaliser

JOURS_VALIDITE = 90


# ============================================================================ liste d'achats
@dataclass
class LigneAchat:
    origine: str                    # « reassort » ou « envie »
    libelle: str
    a_acheter: int | None
    en_cave: int = 0
    seuil: int | None = None
    dernier_prix: float | None = None
    lieu: str | None = None
    prix_max: float | None = None
    priorite: int | None = None
    vin_id: int | None = None
    envie_id: int | None = None
    alerte_prix: float | None = None   # prix relevé sous le prix maximal


def liste_achats(cave, avec_envies: bool = True, priorite_max: int = 3) -> list[LigneAchat]:
    """Réassort d'abord (le plus gros manque en tête), puis les envies par
    priorité. Une envie liée à un vin déjà en réassort n'est pas répétée."""
    b = cave.base
    lignes: list[LigneAchat] = []
    for r in b.lire("""
            SELECT v.id, v.seuil_reassort AS seuil,
                   (SELECT COUNT(*) FROM bouteille bo WHERE bo.vin_id=v.id AND bo.statut='en_cave') AS n,
                   (SELECT bo.prix_achat FROM bouteille bo WHERE bo.vin_id=v.id AND bo.prix_achat IS NOT NULL
                     ORDER BY bo.date_entree DESC, bo.id DESC LIMIT 1) AS prix,
                   (SELECT bo.lieu_achat FROM bouteille bo WHERE bo.vin_id=v.id AND bo.lieu_achat IS NOT NULL
                     AND bo.lieu_achat<>'' ORDER BY bo.date_entree DESC, bo.id DESC LIMIT 1) AS lieu
            FROM vin v WHERE v.seuil_reassort IS NOT NULL AND v.seuil_reassort > 0"""):
        if r["n"] < r["seuil"]:
            lignes.append(LigneAchat("reassort", cave.nom_vin(r["id"]), r["seuil"] - r["n"], r["n"],
                                     r["seuil"], r["prix"], r["lieu"], vin_id=r["id"]))
    lignes.sort(key=lambda l: (-(l.a_acheter or 0), l.libelle.lower()))
    if avec_envies:
        deja = {l.vin_id for l in lignes}
        alertes = {a["envie_id"]: a["prix"] for a in alertes_prix(cave)}
        for e in cave.envies(False):
            if e["vin_id"] and e["vin_id"] in deja or (e["priorite"] or 2) > priorite_max:
                continue
            libelle = " · ".join(str(x) for x in (e["producteur"], e["cuvee"], e["appellation"],
                                                  e["millesime"]) if x)
            if e["vin_id"] and not libelle:
                libelle = cave.nom_vin(e["vin_id"])
            lignes.append(LigneAchat("envie", libelle, e["quantite"], e.get("en_cave") or 0,
                                     prix_max=e["prix_max"], priorite=e["priorite"], vin_id=e["vin_id"],
                                     envie_id=e["id"], alerte_prix=alertes.get(e["id"])))
    return lignes


def html_liste(lignes: list[LigneAchat], titre: str, textes: dict, montant) -> str:
    """Page HTML imprimable (aperçu et PDF par Qt). `textes` : libellés déjà
    traduits ; `montant` : mise en forme d'un prix dans la langue."""
    from html import escape as e
    h = ["<html><head><meta charset='utf-8'><style>",
         "body{font-family:'Source Sans 3',sans-serif;font-size:10.5pt;color:#2A1A14}",
         "h1{font-family:'Cormorant Garamond',serif;color:#5E1427;font-size:20pt;margin:0}",
         "h2{color:#1C6DB4;font-size:12pt;margin-top:16px;border-bottom:1px solid #CDBB98}",
         "td,th{padding:3px 6px;border-bottom:1px solid #EFE6D2;vertical-align:top}",
         "th{text-align:left;color:#7D7064;font-weight:600}",
         ".case{width:14px}.n{text-align:right}.doux{color:#7D7064}",
         "</style></head><body>",
         f"<h1>{e(titre)}</h1><p class='doux'>{e(textes['date'])}</p>"]
    for origine, cle in (("reassort", "reassort"), ("envie", "envies")):
        groupe = [l for l in lignes if l.origine == origine]
        if not groupe:
            continue
        h.append(f"<h2>{e(textes[cle])}</h2><table width='100%' cellspacing='0'><tr>"
                 f"<th class='case'></th><th>{e(textes['vin'])}</th><th class='n'>{e(textes['quantite'])}</th>"
                 f"<th>{e(textes['detail'])}</th></tr>")
        for l in groupe:
            if origine == "reassort":
                detail = textes["detail_reassort"].format(n=l.en_cave, seuil=l.seuil)
                if l.dernier_prix is not None:
                    detail += " · " + textes["dernier_prix"].format(prix=montant(l.dernier_prix))
                if l.lieu:
                    detail += " · " + l.lieu
            else:
                morceaux = []
                if l.prix_max:
                    morceaux.append(textes["prix_max"].format(prix=montant(l.prix_max)))
                if l.alerte_prix is not None:
                    morceaux.append(textes["alerte"].format(prix=montant(l.alerte_prix)))
                detail = " · ".join(morceaux)
            h.append(f"<tr><td class='case'>&#9744;</td><td>{e(l.libelle)}</td>"
                     f"<td class='n'>{'' if l.a_acheter is None else l.a_acheter}</td>"
                     f"<td class='doux'>{e(detail)}</td></tr>")
        h.append("</table>")
    if not lignes:
        h.append(f"<p>{e(textes['vide'])}</p>")
    h.append("</body></html>")
    return "\n".join(h)


def exporter_csv(lignes: list[LigneAchat], chemin) -> int:
    with open(chemin, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["origine", "vin", "a_acheter", "en_cave", "seuil", "dernier_prix", "lieu",
                    "prix_max", "priorite", "prix_releve_sous_le_max"])
        for l in lignes:
            w.writerow([l.origine, l.libelle, l.a_acheter, l.en_cave, l.seuil, l.dernier_prix, l.lieu,
                        l.prix_max, l.priorite, l.alerte_prix])
    return len(lignes)


# ============================================================================ prix relevés
def ajouter_prix(cave, envie_id: int, montant: float, source: str, jour: str | None = None,
                 url: str | None = None, note: str | None = None, devise: str = "EUR") -> int:
    """Un prix vu pour une envie. La source (marchand, salon…) est obligatoire :
    un prix sans source ne prouve rien."""
    if not (source or "").strip():
        raise ValueError("source obligatoire")
    if montant is None or montant < 0:
        raise ValueError("montant invalide")
    with cave.base.ecriture() as c:
        return c.execute("INSERT INTO prix_observe(envie_id, montant, devise, date, source, url, note, cree_le) "
                         "VALUES(?,?,?,?,?,?,?,?)",
                         (envie_id, float(montant), devise, jour or date.today().isoformat(), source.strip(),
                          (url or "").strip() or None, (note or "").strip() or None, maintenant())).lastrowid


def prix_releves(cave, envie_id: int) -> list[dict]:
    return [dict(r) for r in cave.base.lire(
        "SELECT * FROM prix_observe WHERE envie_id=? ORDER BY date DESC, id DESC", (envie_id,))]


def supprimer_prix(cave, prix_id: int) -> None:
    with cave.base.ecriture() as c:
        c.execute("DELETE FROM prix_observe WHERE id=?", (prix_id,))


def meilleurs_prix(cave, jours: int = JOURS_VALIDITE) -> dict[int, dict]:
    """{envie_id: relevé le moins cher parmi les relevés récents}."""
    limite = (date.today() - timedelta(days=jours)).isoformat()
    sortie: dict[int, dict] = {}
    for r in cave.base.lire("SELECT * FROM prix_observe WHERE date >= ? ORDER BY montant, date DESC",
                            (limite,)):
        sortie.setdefault(r["envie_id"], dict(r))
    return sortie


def alertes_prix(cave, jours: int = JOURS_VALIDITE) -> list[dict]:
    """Envies non satisfaites dont un prix récent est au plus le prix maximal :
    [{envie_id, libelle, prix, prix_max, source, date, origine}] — origine
    « releve » (prix vu) ou « valeur » (dernière valeur saisie du vin lié)."""
    meilleurs = meilleurs_prix(cave, jours)
    limite = (date.today() - timedelta(days=jours)).isoformat()
    sortie = []
    for e in cave.envies(False):
        if not e["prix_max"]:
            continue
        candidats = []
        m = meilleurs.get(e["id"])
        if m and m["montant"] <= e["prix_max"]:
            candidats.append(("releve", m["montant"], m["source"], m["date"]))
        if e["vin_id"]:
            v = cave.base.un("SELECT montant, source, date FROM valeur WHERE vin_id=? AND format='bouteille' "
                             "ORDER BY date DESC, id DESC LIMIT 1", (e["vin_id"],))
            if v and v["date"] >= limite and v["montant"] <= e["prix_max"]:
                candidats.append(("valeur", v["montant"], v["source"], v["date"]))
        if candidats:
            origine, prix, source, jour = min(candidats, key=lambda c: c[1])
            libelle = " · ".join(str(x) for x in (e["producteur"], e["cuvee"], e["appellation"],
                                                  e["millesime"]) if x) or cave.nom_vin(e["vin_id"] or 0)
            sortie.append({"envie_id": e["id"], "libelle": libelle, "prix": prix, "prix_max": e["prix_max"],
                           "source": source, "date": jour, "origine": origine})
    return sortie


@dataclass
class ResultatImportPrix:
    importes: int = 0
    non_rapproches: list[str] = field(default_factory=list)
    erreurs: list[str] = field(default_factory=list)


#: en-têtes reconnus (normalisés) → champ
ENTETES = {"envie": "envie", "id": "envie", "producteur": "producteur", "domaine": "producteur",
           "producer": "producteur", "winery": "producteur", "cuvee": "cuvee", "wine": "cuvee", "vin": "cuvee",
           "appellation": "appellation", "millesime": "millesime", "vintage": "millesime", "annee": "millesime",
           "prix": "prix", "price": "prix", "montant": "prix", "date": "date", "source": "source",
           "marchand": "source", "merchant": "source", "shop": "source", "url": "url", "lien": "url",
           "note": "note", "devise": "devise", "currency": "devise"}


def _cle(*morceaux) -> str:
    return " ".join(normaliser(str(m)) for m in morceaux if m not in (None, ""))


def importer_prix_csv(cave, chemin) -> ResultatImportPrix:
    """Importe des prix relevés (CSV : envie ou producteur/cuvée/appellation/millésime, prix, date,
    source, url). Rapprochement : identifiant d'envie, sinon producteur + cuvée (+ millésime si
    les deux le donnent). Une ligne sans source prend le nom du fichier : rien n'est inventé."""
    from .echanges import _reel, lire_texte
    texte = lire_texte(chemin)
    try:
        dialecte = csv.Sniffer().sniff(texte[:8192], delimiters=";,\t")
    except csv.Error:
        dialecte = csv.excel
        dialecte.delimiter = ";" if texte[:8192].count(";") > texte[:8192].count(",") else ","
    lignes = list(csv.DictReader(io.StringIO(texte), dialect=dialecte))
    envies = cave.envies(False)
    par_id = {e["id"]: e for e in envies}
    res = ResultatImportPrix()
    a_ecrire = []
    for i, brute in enumerate(lignes, 2):
        l = {}
        for k, v in brute.items():
            champ = ENTETES.get(normaliser(k or "").replace(" ", ""))
            if champ and v not in (None, ""):
                l[champ] = v.strip()
        prix = _reel(l.get("prix"))
        if prix is None:
            res.erreurs.append(f"ligne {i} : prix illisible")
            continue
        cible = None
        if l.get("envie") and str(l["envie"]).isdigit():
            cible = par_id.get(int(l["envie"]))
        if cible is None:
            cle_ligne = _cle(l.get("producteur"), l.get("cuvee"))
            for e in envies:
                if cle_ligne and cle_ligne == _cle(e["producteur"], e["cuvee"]) and (
                        not l.get("millesime") or not e["millesime"] or str(e["millesime"]) == l["millesime"]):
                    cible = e
                    break
        if cible is None:
            res.non_rapproches.append(f"ligne {i} : " + " · ".join(
                x for x in (l.get("producteur"), l.get("cuvee"), l.get("millesime")) if x))
            continue
        jour = (l.get("date") or "")[:10] or date.today().isoformat()
        a_ecrire.append((cible["id"], prix, l.get("devise") or "EUR", jour,
                         l.get("source") or Path(chemin).name, l.get("url"), l.get("note")))
    if a_ecrire:
        with cave.base.ecriture() as c:
            for envie_id, prix, devise, jour, source, url, note in a_ecrire:
                c.execute("INSERT INTO prix_observe(envie_id, montant, devise, date, source, url, note, cree_le) "
                          "VALUES(?,?,?,?,?,?,?,?)", (envie_id, prix, devise, jour, source, url, note,
                                                      maintenant()))
        res.importes = len(a_ecrire)
    return res
