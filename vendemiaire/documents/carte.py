# -*- coding: utf-8 -*-
"""Carte des vins « de grand restaurant », générée depuis la cave.

Règles (cahier des charges, enquête du 26/10 : vinography.com, musthavemenus,
écoles hôtelières…) :

* ordre classique : effervescents → blancs → (orange) → rosés → rouges → vins
  doux et liquoreux → vins mutés ; dans chaque couleur, pays (France d'abord en
  option) › région › appellation, puis producteur et millésime ; JAMAIS trié
  par prix ;
* une ligne : BIN, producteur/domaine, cuvée, millésime, format, prix
  (facultatif), éventuellement degré, cépages et une ligne d'accord ;
* verticales regroupées (un même vin sur plusieurs millésimes) ;
* à part : « au verre / à la carafe », demi-bouteilles, grands formats ;
  coups de cœur mis en avant, « dernière bouteille » signalée ;
* extras : page de garde (logo, nom du lieu, date), mot d'accueil, petites
  cartes des régions, menu du soir (vin suggéré par plat, d'après les accords du
  dossier « Le vin »), index des producteurs.

Mise à jour d'un clic : une carte enregistrée (`carte`, `carte_vin`) garde sa
sélection et ses options ; la régénérer relit la cave (une bouteille bue
disparaît). Trois rendus du même contenu : LaTeX (trois modèles), HTML (aperçu,
partage), PDF par Qt (repli sans LaTeX).
"""
from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from datetime import date
from html import escape
from pathlib import Path

from .. import i18n, logo, referentiels
from ..base import maintenant
from ..i18n import tr_en
from ..mondial.lwin import REGIONS as _REGIONS_LWIN
from ..regles import accords as r_accords
from . import geo
from .latex import echapper

MODELES = ("classique", "moderne", "bistrot")
FORMATS_PAGE = ("a4", "a5", "simple")
#: ordre classique des sections
SECTIONS = ("effervescent", "blanc", "orange", "rose", "rouge", "doux", "mute", "autre")
OPTIONS_DEFAUT = {
    "modele": "classique", "format": "a4", "langue": "fr", "titre": "", "lieu": "", "date": "",
    "mot": "", "prix": False, "france_dabord": True, "cartes": True, "index": True,
    "accords_auto": True, "degre": False, "cepages": False, "menu": [],
}
#: régions : nom de la cave (français) -> anglais
REGIONS_EN = {fr: en for en, fr in _REGIONS_LWIN.items()}
REGIONS_EN.update({"Californie": "California", "Moselle": "Mosel", "Vallée du Rhône": "Rhône Valley",
                   "Val de Loire": "Loire Valley", "Sud-Ouest": "South West France", "Toscane": "Tuscany",
                   "Piémont": "Piedmont", "Vénétie": "Veneto", "Rhône": "Rhône", "Loire": "Loire",
                   "Bourgogne": "Burgundy", "Rhône nord": "Northern Rhône", "Rhône sud": "Southern Rhône",
                   "Côte de Nuits": "Côte de Nuits", "Côte de Beaune": "Côte de Beaune",
                   "Australie-Méridionale": "South Australia", "Le Cap": "Cape Town", "Tasmanie": "Tasmania",
                   "Kakhétie": "Kakheti", "Sicile": "Sicily", "Pouilles": "Apulia", "Santorin": "Santorini",
                   "Chili central": "Central Chile", "Graves et Sauternes": "Graves and Sauternes"})


def nom_region(nom: str | None, langue: str) -> str:
    if not nom:
        return ""
    return REGIONS_EN.get(nom, nom) if langue == "en" else nom


# ============================================================================ contenu
@dataclass
class Ligne:
    vin_id: int
    format: str
    n: int                                   # bouteilles disponibles dans ce format
    bin: str = ""
    bin_auto: bool = False
    producteur: str = ""
    cuvee: str = ""
    appellation: str = ""
    region: str = ""
    pays: str = ""
    millesime: int | None = None
    couleur: str = ""
    type: str = ""
    degre: float | None = None
    cepages: list = field(default_factory=list)
    prix: float | None = None
    prix_verre: float | None = None
    accord: str = ""
    coup_de_coeur: bool = False
    style: str | None = None
    phase: str | None = None
    alerte: str | None = None

    @property
    def cle(self) -> str:
        return f"l{self.vin_id}{self.format}"

    @property
    def derniere(self) -> bool:
        return self.n == 1


@dataclass
class Groupe:
    """Un vin d'un producteur (une ligne) ou une verticale (plusieurs millésimes)."""
    producteur: str
    cuvee: str
    lignes: list[Ligne]

    @property
    def verticale(self) -> bool:
        return len({l.millesime for l in self.lignes}) > 1


@dataclass
class Appellation:
    nom: str
    groupes: list[Groupe]


@dataclass
class Region:
    nom: str
    appellations: list[Appellation]


@dataclass
class Pays:
    nom: str
    regions: list[Region]


@dataclass
class Section:
    cle: str
    pays: list[Pays]

    def lignes(self) -> list[Ligne]:
        return [l for p in self.pays for r in p.regions for a in r.appellations for g in a.groupes
                for l in g.lignes]


@dataclass
class Accord:
    plat: str
    regle: object | None             # accords.Plat reconnu, ou None
    ligne: Ligne | None
    autre: Ligne | None = None


@dataclass
class Carte:
    options: dict
    sections: list[Section]
    au_verre: list[Ligne]
    demi: list[Section]
    grands: list[Section]
    coups_de_coeur: list[Ligne]
    menu: list[Accord]
    producteurs: dict[str, list[Ligne]]
    regions_par_pays: dict[str, list[dict]]
    bouteilles: int

    @property
    def langue(self) -> str:
        return self.options.get("langue", "fr")

    def toutes_les_lignes(self) -> list[Ligne]:
        return [l for s in self.sections + self.demi + self.grands for l in s.lignes()]

    def vide(self) -> bool:
        return not self.toutes_les_lignes()


def options_completes(options: dict | None) -> dict:
    o = dict(OPTIONS_DEFAUT)
    o.update({k: v for k, v in (options or {}).items() if v is not None})
    if o["modele"] not in MODELES:
        o["modele"] = "classique"
    if o["format"] not in FORMATS_PAGE:
        o["format"] = "a4"
    if not o.get("date"):
        o["date"] = date.today().isoformat()
    return o


def section_de(couleur: str | None, type_: str | None) -> str:
    if type_ == "effervescent":
        return "effervescent"
    if type_ in ("doux", "mute"):
        return type_
    if couleur in ("blanc", "orange", "rose", "rouge"):
        return couleur
    return "autre"


def famille_format(code: str) -> str:
    f = referentiels.FORMATS_PAR_CODE.get(code)
    litres = f.litres if f else 0.75
    if litres <= 0.5:
        return "demi"
    if litres >= 1.5:
        return "grand"
    return "normal"


def construire(cave, options: dict | None = None, vin_ids=None, carte_vins: dict | None = None) -> Carte:
    """Contenu de la carte. `vin_ids` : sélection (None = tous les vins en
    cave) ; `carte_vins` : {vin_id: {au_verre, prix, prix_verre, accord}}."""
    o = options_completes(options)
    lg = o["langue"]
    carte_vins = carte_vins or {}
    etat = {}
    try:
        for b in cave.etat_bouteilles():
            etat.setdefault(b["vin_id"], b)
    except Exception:                              # règles indisponibles : la carte se fait quand même
        etat = {}
    vins = cave._vins_pour_regles(vin_ids)
    cep = {}
    for r in cave.base.lire("SELECT vin_id, cepage FROM vin_cepage ORDER BY vin_id, rang"):
        cep.setdefault(r["vin_id"], []).append(r["cepage"])
    stock = cave.base.lire(
        "SELECT vin_id, format, COUNT(*) n, MIN(NULLIF(TRIM(bin), '')) bin FROM bouteille "
        "WHERE statut='en_cave' GROUP BY vin_id, format")
    lignes: list[Ligne] = []
    for s in stock:
        v = vins.get(s["vin_id"])
        if v is None:
            continue
        cv = carte_vins.get(s["vin_id"]) or {}
        e = etat.get(s["vin_id"]) or {}
        lignes.append(Ligne(
            vin_id=v["id"], format=s["format"] or "bouteille", n=s["n"], bin=s["bin"] or "",
            producteur=v.get("producteur") or "", cuvee=v.get("cuvee") or "",
            appellation=v.get("appellation") or "", region=v.get("region") or "", pays=v.get("pays") or "",
            millesime=v.get("millesime"), couleur=v.get("couleur") or "", type=v.get("type") or "tranquille",
            degre=v.get("degre"), cepages=cep.get(v["id"], []),
            # le prix saisi est celui de la BOUTEILLE : jamais recopié sur une demie ou un magnum
            prix=cv.get("prix") if o["prix"] and famille_format(s["format"] or "bouteille") == "normal" else None,
            prix_verre=cv.get("prix_verre") if o["prix"] else None,
            accord=cv.get("accord") or "", coup_de_coeur=bool(v.get("coup_de_coeur")),
            style=e.get("style"), phase=e.get("phase"), alerte=e.get("alerte")))
    if o["accords_auto"]:
        for l in lignes:
            if not l.accord and l.style:
                plats = r_accords.plats_pour_style(l.style)[:2]
                if plats:
                    l.accord = tr_en(lg, "carte.avec", plats=", ".join(p.nom(lg).lower() if i else p.nom(lg)
                                                                        for i, p in enumerate(plats)))

    def trier_pays(nom):
        n = geo.nom_pays(nom, lg) or "~"
        return (0 if (o["france_dabord"] and nom == "France") else 1, n.lower())

    def ranger(sous: list[Ligne]) -> list[Section]:
        sorties = []
        for cle in SECTIONS:
            ls = [l for l in sous if section_de(l.couleur, l.type) == cle]
            if not ls:
                continue
            pays = []
            for nom_p in sorted({l.pays for l in ls}, key=trier_pays):
                lp = [l for l in ls if l.pays == nom_p]
                regions = []
                for nom_r in sorted({l.region for l in lp}, key=lambda r: (not r, nom_region(r, lg).lower())):
                    lr = [l for l in lp if l.region == nom_r]
                    apps = []
                    for nom_a in sorted({l.appellation for l in lr}, key=lambda a: (not a, a.lower())):
                        la = sorted((l for l in lr if l.appellation == nom_a),
                                    key=lambda l: (l.producteur.lower(), l.cuvee.lower(), l.millesime or 0,
                                                   referentiels.FORMATS_PAR_CODE.get(l.format).litres
                                                   if referentiels.FORMATS_PAR_CODE.get(l.format) else 0.75))
                        groupes: list[Groupe] = []
                        for l in la:
                            if groupes and (groupes[-1].producteur, groupes[-1].cuvee) == (l.producteur, l.cuvee):
                                groupes[-1].lignes.append(l)
                            else:
                                groupes.append(Groupe(l.producteur, l.cuvee, [l]))
                        apps.append(Appellation(nom_a, groupes))
                    regions.append(Region(nom_r, apps))
                pays.append(Pays(nom_p, regions))
            sorties.append(Section(cle, pays))
        return sorties

    normales = [l for l in lignes if famille_format(l.format) == "normal"]
    sections = ranger(normales)
    demi = ranger([l for l in lignes if famille_format(l.format) == "demi"])
    grands = ranger([l for l in lignes if famille_format(l.format) == "grand"])
    # BIN : celui des bouteilles, sinon un numéro par section (101, 102… pour les effervescents)
    pris = {l.bin for l in lignes if l.bin}
    for bloc, base_num in ((sections, 0), (demi, 800), (grands, 900)):
        for s in bloc:
            numero = base_num + (SECTIONS.index(s.cle) + 1) * 100 if not base_num else base_num
            for l in s.lignes():
                if l.bin:
                    continue
                numero += 1
                while str(numero) in pris:
                    numero += 1
                l.bin, l.bin_auto = str(numero), True
                pris.add(l.bin)
    au_verre = [l for s in sections for l in s.lignes() if (carte_vins.get(l.vin_id) or {}).get("au_verre")]
    vus, coups = set(), []
    for s in sections + demi + grands:
        for l in s.lignes():
            if l.coup_de_coeur and l.vin_id not in vus:
                vus.add(l.vin_id)
                coups.append(l)
    producteurs: dict[str, list[Ligne]] = {}
    for s in sections + demi + grands:
        for l in s.lignes():
            if l.producteur:
                producteurs.setdefault(l.producteur, []).append(l)
    regions_par_pays: dict[str, list[dict]] = {}
    for l in lignes:
        r = geo.region_geo(l.pays, l.region, l.appellation)
        if r is not None:
            liste = regions_par_pays.setdefault(geo.pays_geo(l.pays)[0], [])
            if r not in liste:
                liste.append(r)
    menu = []
    toutes = [l for s in sections + demi + grands for l in s.lignes()]
    for plat in [p.strip() for p in o.get("menu") or [] if p and p.strip()]:
        trouves = r_accords.chercher_plats(plat)
        regle = trouves[0] if trouves else None
        choix = []
        if regle is not None:
            props = r_accords.vins_pour_plat(regle, [dict(style=l.style, phase=l.phase, alerte=l.alerte, ligne=l)
                                                      for l in toutes if l.style])
            props.sort(key=lambda p: (p.rang, not p.bouteille["ligne"].coup_de_coeur))
            choix = [p.bouteille["ligne"] for p in props]
            uniques = []
            for c in choix:
                if c.vin_id not in {u.vin_id for u in uniques}:
                    uniques.append(c)
            choix = uniques
        menu.append(Accord(plat, regle, choix[0] if choix else None, choix[1] if len(choix) > 1 else None))
    return Carte(o, sections, au_verre, demi, grands, coups, menu, dict(sorted(
        producteurs.items(), key=lambda kv: kv[0].lower())), regions_par_pays, sum(l.n for l in lignes))


def attribuer_bins(cave, carte: Carte) -> int:
    """Inscrit dans la cave les numéros BIN attribués automatiquement (toutes les
    bouteilles du vin dans ce format qui n'en ont pas)."""
    n = 0
    with cave.base.ecriture() as c:
        for l in carte.toutes_les_lignes():
            if l.bin_auto:
                n += c.execute("UPDATE bouteille SET bin=? WHERE vin_id=? AND format=? AND statut='en_cave' "
                               "AND (bin IS NULL OR TRIM(bin)='')", (l.bin, l.vin_id, l.format)).rowcount
                l.bin_auto = False
    return n


# ============================================================================ cartes enregistrées
def enregistrer(cave, nom: str, options: dict, vins: dict | None, carte_id: int | None = None) -> int:
    """`vins` : None = toute la cave ; sinon {vin_id: {au_verre, prix, prix_verre, accord}}."""
    o = json.dumps(options_completes(options), ensure_ascii=False)
    with cave.base.ecriture() as c:
        if carte_id is None:
            carte_id = c.execute("INSERT INTO carte(nom, options, toute_la_cave, cree_le, modifie_le) "
                                 "VALUES(?,?,?,?,?)", (nom, o, 1 if vins is None else 0, maintenant(),
                                                       maintenant())).lastrowid
        else:
            c.execute("UPDATE carte SET nom=?, options=?, toute_la_cave=?, modifie_le=? WHERE id=?",
                      (nom, o, 1 if vins is None else 0, maintenant(), carte_id))
            c.execute("DELETE FROM carte_vin WHERE carte_id=?", (carte_id,))
        for vid, d in (vins or {}).items():
            c.execute("INSERT INTO carte_vin(carte_id, vin_id, au_verre, prix, prix_verre, accord) "
                      "VALUES(?,?,?,?,?,?)", (carte_id, vid, 1 if d.get("au_verre") else 0, d.get("prix"),
                                              d.get("prix_verre"), d.get("accord") or None))
    return carte_id


def cartes(cave) -> list[dict]:
    return [dict(r) for r in cave.base.lire("SELECT * FROM carte ORDER BY modifie_le DESC, id DESC")]


def lire(cave, carte_id: int) -> tuple[dict, dict, dict | None]:
    """(ligne carte, options, vins ou None pour toute la cave)."""
    r = dict(cave.base.un("SELECT * FROM carte WHERE id=?", (carte_id,)))
    vins = {x["vin_id"]: dict(x) for x in cave.base.lire("SELECT * FROM carte_vin WHERE carte_id=?", (carte_id,))}
    return r, options_completes(json.loads(r["options"] or "{}")), (None if r["toute_la_cave"] else vins)


def supprimer(cave, carte_id: int) -> None:
    with cave.base.ecriture() as c:
        c.execute("DELETE FROM carte WHERE id=?", (carte_id,))


def construire_enregistree(cave, carte_id: int) -> Carte:
    _r, o, vins = lire(cave, carte_id)
    if vins is None:
        # toute la cave : les réglages par vin (au verre, prix) restent ceux de la table
        reglages = {x["vin_id"]: dict(x) for x in cave.base.lire(
            "SELECT * FROM carte_vin WHERE carte_id=?", (carte_id,))}
        return construire(cave, o, None, reglages)
    return construire(cave, o, list(vins), vins)


def noter_pdf(cave, carte_id: int, chemin: str) -> None:
    with cave.base.ecriture() as c:
        c.execute("UPDATE carte SET dernier_pdf=?, modifie_le=? WHERE id=?", (str(chemin), maintenant(), carte_id))


# ============================================================================ textes communs
def _t(carte: Carte, cle: str, **kw) -> str:
    return tr_en(carte.langue, cle, **kw)


def titre_section(carte: Carte, cle: str) -> str:
    return _t(carte, f"carte.s_{cle}")


def libelle_format(code: str, langue: str) -> str:
    f = referentiels.FORMATS_PAR_CODE.get(code)
    if f is None:
        return code
    nom = f.fr if langue == "fr" else f.en
    return nom.split(" (")[0]


def prix_texte(montant, langue: str) -> str:
    if montant is None:
        return ""
    ancienne = i18n.langue()
    i18n.definir_langue(langue)
    try:
        return i18n.argent(montant)
    finally:
        i18n.definir_langue(ancienne)


def date_texte(iso: str, langue: str) -> str:
    try:
        d = date.fromisoformat(iso[:10])
    except ValueError:
        return iso
    if langue == "fr":
        mois = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
                "octobre", "novembre", "décembre")[d.month - 1]
        return f"{d.day}{'er' if d.day == 1 else ''} {mois} {d.year}"
    mois = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
            "November", "December")[d.month - 1]
    return f"{mois} {d.day}, {d.year}"


def _millesime(l: Ligne, carte: Carte) -> str:
    return str(l.millesime) if l.millesime else _t(carte, "carte.nv")


def _details(l: Ligne, carte: Carte, avec_format: bool) -> list[str]:
    d = []
    if avec_format and l.format != "bouteille":
        d.append(libelle_format(l.format, carte.langue))
    if carte.options.get("degre") and l.degre:
        d.append(f"{l.degre:g} %".replace(".", "," if carte.langue == "fr" else "."))
    if carte.options.get("cepages") and l.cepages:
        d.append(", ".join(l.cepages))
    return d


# ============================================================================ LaTeX
COULEURS = {
    "classique": {"titre": "5E1427", "accent": "C99A3B", "texte": "2A1A14", "doux": "7D7064",
                  "carte": "F3EAD7", "carteTrait": "8E2A3D", "cartePoint": "5E1427", "fond": None},
    "moderne": {"titre": "1F1F1F", "accent": "8E2A3D", "texte": "1F1F1F", "doux": "6B6B6B",
                "carte": "ECECEC", "carteTrait": "6B6B6B", "cartePoint": "8E2A3D", "fond": None},
    "bistrot": {"titre": "F7F1E3", "accent": "B5382B", "texte": "2B2622", "doux": "6A5D50",
                "carte": "E4D3AE", "carteTrait": "2F3A36", "cartePoint": "B5382B", "fond": "F1E6CF",
                "ardoise": "2F3A36"},
}


def _preambule(carte: Carte, moteur_unicode: bool) -> str:
    o = carte.options
    m, fmt, lg = o["modele"], o["format"], carte.langue
    c = COULEURS[m]
    papier = "a5paper" if fmt == "a5" else "a4paper"
    corps = "10pt" if fmt in ("a5", "simple") else "11pt"
    marges = ("top=16mm,bottom=18mm,left=15mm,right=15mm" if fmt == "a5" else
              "top=14mm,bottom=16mm,left=14mm,right=14mm" if fmt == "simple" else
              "top=22mm,bottom=24mm,left=26mm,right=26mm")
    p = [rf"\documentclass[{corps}]{{article}}",
         rf"\usepackage[{papier},{marges}]{{geometry}}"]
    if not moteur_unicode:
        p += [r"\usepackage[T1]{fontenc}", r"\usepackage[utf8]{inputenc}", r"\usepackage{eurosym}"]
    else:
        p += [r"\usepackage{fontspec}", r"\providecommand{\euro}{€}"]
    p.append(rf"\usepackage[{'french' if lg == 'fr' else 'british'}]{{babel}}")
    if m == "classique":
        p.append(r"\usepackage{ebgaramond}")
    elif m == "moderne":
        p.append(r"\usepackage[default]{sourcesanspro}")
    else:
        p += [r"\usepackage{librebaskerville}", r"\usepackage{josefin}"]
    p += [r"\usepackage{xcolor}", r"\usepackage{graphicx}", r"\usepackage{tikz}", r"\usepackage{multicol}",
          r"\usepackage{fontawesome5}", r"\usepackage{needspace}", r"\usepackage{fancyhdr}",
          r"\usepackage{refcount}", r"\usepackage[hidelinks]{hyperref}",
          r"\makeatletter\newcommand{\pagesuniques}[1]{\def\pu@prec{}\def\pu@sep{}\@for\pu@l:=#1\do{"
          r"\edef\pu@p{\getpagerefnumber{\pu@l}}\ifx\pu@p\pu@prec\else\pu@sep\pu@p\def\pu@sep{, }"
          r"\let\pu@prec\pu@p\fi}}\makeatother"]
    for nom, val in c.items():
        if val:
            p.append(rf"\definecolor{{{nom}}}{{HTML}}{{{val}}}")
    p.append(r"\colorlet{rubrique}{" + ("ardoise" if m == "bistrot" else "titre") + "}")
    if c.get("fond"):
        p.append(r"\pagecolor{fond}")
    p += [r"\color{texte}", r"\setlength{\parindent}{0pt}", r"\setlength{\parskip}{0pt}",
          r"\pagestyle{fancy}\fancyhf{}\renewcommand{\headrulewidth}{0pt}",
          r"\fancyfoot[C]{\footnotesize\color{doux}" + echapper(o.get("titre") or _t(carte, "carte.titre_defaut"))
          + r" \quad\textperiodcentered\quad \thepage}"]
    # titres
    if m == "classique":
        p += [r"\newcommand{\Section}[1]{\clearpage\vspace*{4mm}{\centering{\color{accent}\rule{0.18\linewidth}{0.6pt}}\\[3mm]"
              r"{\Huge\scshape\color{titre}#1}\\[2mm]{\color{accent}\rule{0.18\linewidth}{0.6pt}}\par}\vspace{7mm}}",
              r"\newcommand{\Pays}[1]{\Needspace{6\baselineskip}\vspace{4mm}{\centering\Large\scshape\color{titre}#1\par}\vspace{2mm}}",
              r"\newcommand{\Region}[1]{\Needspace{5\baselineskip}\vspace{3mm}{\centering\large\itshape\color{accent}#1\par}\vspace{1.5mm}}",
              r"\newcommand{\Appellation}[1]{\Needspace{4\baselineskip}\vspace{2.5mm}{\scshape\color{titre}#1}\par\vspace{0.8mm}}"]
    elif m == "moderne":
        p += [r"\newcommand{\Section}[1]{\clearpage{\color{accent}\rule{\linewidth}{1.2pt}}\par\vspace{2mm}"
              r"{\fontsize{24}{28}\selectfont\bfseries\color{titre}\MakeUppercase{#1}}\par\vspace{6mm}}",
              r"\newcommand{\Pays}[1]{\Needspace{6\baselineskip}\vspace{4mm}{\large\bfseries\color{titre}\MakeUppercase{#1}}\par\vspace{1mm}{\color{doux}\rule{\linewidth}{0.3pt}}\par\vspace{1.5mm}}",
              r"\newcommand{\Region}[1]{\Needspace{5\baselineskip}\vspace{2.5mm}{\bfseries\color{accent}#1}\par\vspace{1mm}}",
              r"\newcommand{\Appellation}[1]{\Needspace{4\baselineskip}\vspace{1.8mm}{\small\color{doux}\MakeUppercase{#1}}\par\vspace{0.5mm}}"]
    else:
        p += [r"\newcommand{\Section}[1]{\clearpage\noindent\colorbox{ardoise}{\parbox{\dimexpr\linewidth-2\fboxsep}{\centering\vspace{2mm}"
              r"{\sffamily\fontsize{26}{30}\selectfont\bfseries\color{titre}\MakeUppercase{#1}}\vspace{2mm}}}\par\vspace{6mm}}",
              r"\newcommand{\Pays}[1]{\Needspace{6\baselineskip}\vspace{4mm}{\sffamily\Large\bfseries\color{ardoise}\MakeUppercase{#1}}\par\vspace{1mm}}",
              r"\newcommand{\Region}[1]{\Needspace{5\baselineskip}\vspace{2.5mm}{\sffamily\large\color{accent}#1}\par\vspace{1mm}}",
              r"\newcommand{\Appellation}[1]{\Needspace{4\baselineskip}\vspace{1.8mm}{\sffamily\bfseries\color{ardoise}#1}\par\vspace{0.5mm}}"]
    # une ligne : #1 BIN, #2 producteur, #3 cuvée et détails, #4 millésime, #5 prix, #6 accord, #7 marques
    p += [r"\newcommand{\Bin}[1]{\makebox[2.6em][l]{\footnotesize\color{doux}#1}}",
          r"\newcommand{\Vin}[7]{\Needspace{2\baselineskip}\noindent\Bin{#1}#7{\producteur{#2}}\ifx&#3&\else, {\itshape #3}\fi"
          r"\ {\color{doux}\dotfill}\ #4\ifx&#5&\else\hspace{1.2em}\makebox[3.6em][r]{#5}\fi\par"
          r"\ifx&#6&\else{\leftskip=2.6em\footnotesize\itshape\color{doux}#6\par}\fi\vspace{0.9mm}}",
          r"\newcommand{\Verticale}[4]{\Needspace{3\baselineskip}\noindent\hspace*{2.6em}#4{\producteur{#1}}\ifx&#2&\else, {\itshape #2}\fi"
          r"\ {\footnotesize\color{doux}(" + echapper(_t(carte, "carte.verticale")) + r")}\par"
          r"\ifx&#3&\else{\leftskip=2.6em\footnotesize\itshape\color{doux}#3\par}\fi\vspace{0.3mm}}",
          r"\newcommand{\Millesime}[3]{\noindent\Bin{#1}\hspace*{1.2em}#2\ifx&#3&\par\else\ {\color{doux}\dotfill}"
          r"\ \makebox[3.6em][r]{#3}\par\fi\vspace{0.4mm}}",
          r"\newcommand{\coeur}{{\color{accent}\faHeart}\ }",
          r"\newcommand{\derniere}{{\footnotesize\color{accent}\faWineBottle}\ }",
          r"\newcommand{\producteur}[1]{" + (r"\textsc{#1}" if m == "classique" else
                                              r"\textbf{#1}" if m == "moderne" else r"{\bfseries #1}") + "}"]
    return "\n".join(p)


def _ligne_tex(l: Ligne, carte: Carte, avec_format: bool = True) -> str:
    details = _details(l, carte, avec_format)
    cuvee = ", ".join(x for x in [l.cuvee] + details if x)
    marques = (r"\coeur" if l.coup_de_coeur else "") + (r"\derniere" if l.derniere else "")
    return (rf"\Vin{{{echapper(l.bin)}}}{{{echapper(l.producteur or '—')}}}{{{echapper(cuvee)}}}"
            rf"{{{_millesime(l, carte)}}}{{{echapper(prix_texte(l.prix, carte.langue))}}}"
            rf"{{{echapper(l.accord)}}}{{{marques}}}\label{{{l.cle}}}")


def _groupe_tex(g: Groupe, carte: Carte, avec_format: bool = True) -> list[str]:
    if not g.verticale:
        return [_ligne_tex(l, carte, avec_format) for l in g.lignes]
    accord = g.lignes[0].accord
    marques = r"\coeur" if any(l.coup_de_coeur for l in g.lignes) else ""
    t = [rf"\Verticale{{{echapper(g.producteur or '—')}}}{{{echapper(g.cuvee)}}}{{{echapper(accord)}}}{{{marques}}}"]
    for l in g.lignes:
        det = ", ".join(_details(l, carte, avec_format))
        mil = _millesime(l, carte) + ((" — " + echapper(det)) if det else "") + (r" \derniere" if l.derniere else "")
        t.append(rf"\Millesime{{{echapper(l.bin)}}}{{{mil}}}{{{echapper(prix_texte(l.prix, carte.langue))}}}"
                 rf"\label{{{l.cle}}}")
    return t


def _sections_tex(sections: list[Section], carte: Carte, titre: str | None = None,
                  avec_format: bool = True) -> list[str]:
    t = []
    if titre and sections:
        t.append(rf"\Section{{{echapper(titre)}}}")
    for s in sections:
        if titre:
            t.append(rf"\Pays{{{echapper(titre_section(carte, s.cle))}}}")
        else:
            t.append(rf"\Section{{{echapper(titre_section(carte, s.cle))}}}")
        for p in s.pays:
            if not titre:
                t.append(rf"\Pays{{{echapper(geo.nom_pays(p.nom, carte.langue) or _t(carte, 'carte.autres_pays'))}}}")
            for r in p.regions:
                if r.nom:
                    t.append(rf"\Region{{{echapper(nom_region(r.nom, carte.langue))}}}")
                for a in r.appellations:
                    if a.nom:
                        t.append(rf"\Appellation{{{echapper(a.nom)}}}")
                    for g in a.groupes:
                        t += _groupe_tex(g, carte, avec_format)
    return t


def latex(carte: Carte, moteur_unicode: bool = True) -> tuple[str, dict]:
    """(source LaTeX, fichiers annexes {nom: chemin})."""
    o = carte.options
    m, fmt, lg = o["modele"], o["format"], carte.langue
    annexes = {}
    if logo.png(512).exists():
        annexes["logo.png"] = logo.png(512)
    t = [_preambule(carte, moteur_unicode), r"\begin{document}"]
    titre = o.get("titre") or _t(carte, "carte.titre_defaut")
    if fmt != "simple":
        # page de garde
        t += [r"\thispagestyle{empty}"]
        if m == "classique":
            t += [r"\begin{tikzpicture}[remember picture,overlay]",
                  r"\draw[accent,line width=1.2pt] ([xshift=12mm,yshift=-12mm]current page.north west) rectangle ([xshift=-12mm,yshift=12mm]current page.south east);",
                  r"\draw[accent,line width=0.4pt] ([xshift=14.5mm,yshift=-14.5mm]current page.north west) rectangle ([xshift=-14.5mm,yshift=14.5mm]current page.south east);",
                  r"\end{tikzpicture}"]
        t += [r"\vspace*{\fill}", r"\begin{center}"]
        if "logo.png" in annexes:
            t.append(r"\includegraphics[width=" + ("0.30" if fmt == "a5" else "0.28") + r"\linewidth]{logo.png}\\[10mm]")
        style_titre = {"classique": r"\fontsize{34}{40}\selectfont\scshape\color{titre}",
                       "moderne": r"\fontsize{34}{40}\selectfont\bfseries\color{titre}",
                       "bistrot": r"\sffamily\fontsize{36}{42}\selectfont\bfseries\color{ardoise}"}[m]
        t.append("{" + style_titre + " " + echapper(titre) + r"}\\[6mm]")
        if o.get("lieu"):
            t.append(r"{\Large\itshape\color{accent} " + echapper(o["lieu"]) + r"}\\[3mm]")
        t.append(r"{\large\color{doux} " + echapper(date_texte(o["date"], lg)) + r"}")
        t += [r"\end{center}", r"\vspace*{\fill}", r"\clearpage"]
        # mot d'accueil, coups de cœur, menu du soir
        if o.get("mot"):
            t += [r"\vspace*{10mm}", r"{\centering\Large\color{rubrique} " + echapper(_t(carte, "carte.mot_titre"))
                  + r"\par}\vspace{6mm}", r"{\itshape " + echapper(o["mot"]).replace("\n", r"\par ") + r"\par}",
                  r"\vspace{8mm}"]
        if carte.menu:
            t += [r"\Needspace{8\baselineskip}{\centering\Large\color{rubrique} " + echapper(_t(carte, "carte.menu_titre"))
                  + r"\par}\vspace{4mm}"]
            for a in carte.menu:
                t.append(r"{\large\color{rubrique} " + echapper(a.plat) + r"}\par")
                if a.ligne is not None:
                    l = a.ligne
                    nom = ", ".join(x for x in (l.producteur, l.cuvee, l.appellation, _millesime(l, carte)) if x)
                    t.append(r"\hspace*{1.5em}" + echapper(nom) + rf" {{\footnotesize\color{{doux}}(BIN {echapper(l.bin)}, p.~\pageref{{{l.cle}}})}}\par")
                    if a.regle is not None:
                        t.append(r"{\leftskip=1.5em\footnotesize\itshape\color{doux} " + echapper(a.regle.pourquoi(lg)) + r"\par}")
                else:
                    t.append(r"{\leftskip=1.5em\footnotesize\itshape\color{doux} " + echapper(
                        _t(carte, "carte.menu_rien" if a.regle is None else "carte.menu_aucun_vin")) + r"\par}")
                t.append(r"\vspace{2.5mm}")
        if carte.coups_de_coeur:
            t += [r"\vspace{6mm}\Needspace{6\baselineskip}{\centering\Large\color{rubrique} \coeur "
                  + echapper(_t(carte, "carte.coups_titre")) + r"\par}\vspace{3mm}"]
            for l in carte.coups_de_coeur:
                nom = ", ".join(x for x in (l.producteur, l.cuvee, l.appellation, _millesime(l, carte)) if x)
                t.append(echapper(nom) + rf" {{\footnotesize\color{{doux}}— BIN {echapper(l.bin)}, p.~\pageref{{{l.cle}}}}}\par\vspace{{1mm}}")
        # cartes des régions
        if o.get("cartes") and carte.regions_par_pays:
            t += [r"\clearpage", r"{\centering\Large\color{rubrique} " + echapper(_t(carte, "carte.regions_titre"))
                  + r"\par}\vspace{6mm}", r"\begin{center}"]
            largeur = 5.2 if fmt == "a4" else 4.6
            for pays, regions in carte.regions_par_pays.items():
                dessin = geo.tikz(pays, regions, largeur, largeur, echapper=lambda x: echapper(nom_region(x, lg)))
                if dessin:
                    t += [r"\begin{minipage}[t]{" + f"{largeur + 0.9:.1f}" + r"cm}\centering",
                          r"{\scshape\color{rubrique} " + echapper(geo.nom_pays(pays, lg)) + r"}\\[1mm]", dessin,
                          r"\end{minipage}\hspace{4mm}"]
            t += [r"\end{center}", r"\vfill{\scriptsize\color{doux} " + echapper(_t(carte, "carte.credit_cartes"))
                  + r"\par}"]
    else:
        t += [r"{\centering{\fontsize{26}{30}\selectfont\color{rubrique} " + echapper(titre) + r"}\\[2mm]"
              r"{\color{doux} " + echapper(" — ".join(x for x in (o.get("lieu"), date_texte(o["date"], lg)) if x))
              + r"}\par}\vspace{4mm}",
              r"\renewcommand{\Section}[1]{\Needspace{6\baselineskip}\vspace{4mm}{\centering\Large\color{rubrique}#1\par}\vspace{2mm}}",
              r"\begin{multicols}{2}"]
    # au verre
    if carte.au_verre:
        t.append(rf"\Section{{{echapper(_t(carte, 'carte.au_verre'))}}}")
        for l in carte.au_verre:
            nom = ", ".join(x for x in (l.cuvee, l.appellation) if x)
            t.append(rf"\Vin{{{echapper(l.bin)}}}{{{echapper(l.producteur)}}}{{{echapper(nom)}}}"
                     rf"{{{_millesime(l, carte)}}}{{{echapper(prix_texte(l.prix_verre, lg))}}}{{{echapper(l.accord)}}}{{}}")
    t += _sections_tex(carte.sections, carte)
    t += _sections_tex(carte.demi, carte, _t(carte, "carte.demi"), avec_format=False)
    t += _sections_tex(carte.grands, carte, _t(carte, "carte.grands"))
    # index des producteurs
    if o.get("index") and carte.producteurs and fmt != "simple":
        t += [rf"\Section{{{echapper(_t(carte, 'carte.index'))}}}", r"\begin{multicols}{2}\small"]
        for prod, lignes in carte.producteurs.items():
            refs = r"\pagesuniques{" + ",".join(l.cle for l in lignes) + "}"
            t.append(rf"\noindent {echapper(prod)} {{\color{{doux}}\dotfill}} {refs}\par")
        t.append(r"\end{multicols}")
    if fmt == "simple":
        t.append(r"\end{multicols}")
    t += [r"\vfill{\footnotesize\color{doux}\noindent\coeur " + echapper(_t(carte, "carte.leg_coeur"))
          + r"\quad\derniere " + echapper(_t(carte, "carte.derniere")) + r"\quad " + echapper(_t(carte, "carte.legende"))
          + r"\par}",
          r"\end{document}"]
    return "\n".join(t) + "\n", annexes


# ============================================================================ HTML
CSS = {
    "classique": {"police": "'EB Garamond', Garamond, Georgia, serif", "titre": "#5E1427", "accent": "#C99A3B",
                  "texte": "#2A1A14", "doux": "#7D7064", "fond": "#FFFCF5", "carte": "#F3EAD7"},
    "moderne": {"police": "'Source Sans 3', 'Source Sans Pro', Helvetica, Arial, sans-serif", "titre": "#1F1F1F",
                "accent": "#8E2A3D", "texte": "#1F1F1F", "doux": "#6B6B6B", "fond": "#FFFFFF", "carte": "#ECECEC"},
    "bistrot": {"police": "'Libre Baskerville', Georgia, serif", "titre": "#2F3A36", "accent": "#B5382B",
                "texte": "#2B2622", "doux": "#6A5D50", "fond": "#F1E6CF", "carte": "#E4D3AE"},
}


def _svg_data(svg_txt: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg_txt.encode("utf-8")).decode("ascii")


def html(carte: Carte, images: dict | None = None) -> str:
    """HTML autonome (aperçu, partage, repli PDF). `images` : si un dict est
    donné, les petites cartes y sont rangées ({nom: svg}) et référencées par
    leur nom (QTextDocument) au lieu d'être incluses en data: URI."""
    o = carte.options
    c = CSS[o["modele"]]
    lg = carte.langue
    titre = o.get("titre") or _t(carte, "carte.titre_defaut")
    e = escape
    h = [f"<!DOCTYPE html><html lang='{lg}'><head><meta charset='utf-8'><title>{e(titre)}</title><style>",
         f"body{{font-family:{c['police']};color:{c['texte']};background:{c['fond']};max-width:760px;margin:24px auto;padding:0 16px;}}",
         f"h1{{color:{c['titre']};text-align:center;font-size:30pt;font-weight:normal;margin:6px 0;}}",
         f"h2{{color:{c['titre']};text-align:center;font-size:20pt;font-weight:normal;border-top:1px solid {c['accent']};"
         f"border-bottom:1px solid {c['accent']};padding:6px 0;margin:28px 0 10px 0;}}",
         f"h3{{color:{c['titre']};font-size:14pt;margin:16px 0 4px 0;}}",
         f"h4{{color:{c['accent']};font-size:12pt;font-style:italic;margin:10px 0 2px 0;}}",
         f"h5{{color:{c['titre']};font-size:10.5pt;margin:8px 0 2px 0;text-transform:uppercase;font-size:9.5pt;letter-spacing:1px;}}",
         "table.l{width:100%;border-collapse:collapse;} td{padding:1px 4px;vertical-align:top;}",
         f"td.bin{{color:{c['doux']};width:38px;font-size:9pt;}} td.m{{text-align:right;width:56px;}}",
         f"td.p{{text-align:right;width:70px;}} .acc{{color:{c['doux']};font-size:9pt;font-style:italic;}}",
         f".doux{{color:{c['doux']};}} .centre{{text-align:center;}} .coeur{{color:{c['accent']};}}",
         "</style></head><body>",
         f"<h1>{e(titre)}</h1>",
         f"<p class='centre doux'>{e(' — '.join(x for x in (o.get('lieu'), date_texte(o['date'], lg)) if x))}</p>"]
    if o.get("mot"):
        h.append(f"<h2>{e(_t(carte, 'carte.mot_titre'))}</h2><p><i>{e(o['mot']).replace(chr(10), '<br>')}</i></p>")
    if carte.menu:
        h.append(f"<h2>{e(_t(carte, 'carte.menu_titre'))}</h2>")
        for a in carte.menu:
            h.append(f"<h3>{e(a.plat)}</h3>")
            if a.ligne is not None:
                l = a.ligne
                h.append(f"<p>{e(', '.join(x for x in (l.producteur, l.cuvee, l.appellation, _millesime(l, carte)) if x))}"
                         f" <span class='doux'>(BIN {e(l.bin)})</span></p>")
                if a.regle is not None:
                    h.append(f"<p class='acc'>{e(a.regle.pourquoi(lg))}</p>")
            else:
                h.append(f"<p class='acc'>{e(_t(carte, 'carte.menu_rien' if a.regle is None else 'carte.menu_aucun_vin'))}</p>")
    if carte.coups_de_coeur:
        h.append(f"<h2>&#9829; {e(_t(carte, 'carte.coups_titre'))}</h2>")
        for l in carte.coups_de_coeur:
            h.append(f"<p>{e(', '.join(x for x in (l.producteur, l.cuvee, l.appellation, _millesime(l, carte)) if x))}"
                     f" <span class='doux'>— BIN {e(l.bin)}</span></p>")
    if o.get("cartes") and carte.regions_par_pays:
        h.append(f"<h2>{e(_t(carte, 'carte.regions_titre'))}</h2><table width='100%'><tr>")
        cases = 0
        for i, (pays, regions) in enumerate(carte.regions_par_pays.items()):
            s = geo.svg(pays, [dict(r, nom=nom_region(r["nom"], lg)) for r in regions], 220, 200,
                        remplissage=c["carte"], trait=c["accent"], point=c["titre"])
            if not s:
                continue
            if images is not None:
                nom = f"carte{i}.svg"
                images[nom] = s
                src = nom
            else:
                src = _svg_data(s)
            dims = [int(float(x) * 0.85) for x in re.search(r'width="([\d.]+)" height="([\d.]+)"', s).groups()]
            if cases and cases % 3 == 0:
                h.append("</tr><tr>")
            cases += 1
            h.append(f"<td align='center' valign='top' width='33%'><b>{e(geo.nom_pays(pays, lg))}</b>"
                     f"<br><img src='{src}' alt='{e(pays)}' width='{dims[0]}' height='{dims[1]}'></td>")
        h.append("</tr></table>")
        h.append(f"<p class='doux' style='font-size:8pt'>{e(_t(carte, 'carte.credit_cartes'))}</p>")

    def ligne_html(l: Ligne, avec_format=True, millesime_seul=False, prix=None):
        details = _details(l, carte, avec_format)
        if millesime_seul:
            nom = f"&nbsp;&nbsp;&nbsp;{e(', '.join(details))}"
        else:
            nom = (("<span class='coeur'>&#9829;</span> " if l.coup_de_coeur else "") + f"<b>{e(l.producteur or '—')}</b>"
                   + (f", <i>{e(', '.join(x for x in [l.cuvee] + details if x))}</i>" if (l.cuvee or details) else ""))
        if l.derniere:
            nom += f" <span class='doux'>({e(_t(carte, 'carte.derniere'))})</span>"
        p = prix_texte(prix if prix is not None else l.prix, lg)
        r = (f"<tr><td class='bin'>{e(l.bin)}</td><td>{nom}</td><td class='m'>{_millesime(l, carte)}</td>"
             f"<td class='p'>{e(p)}</td></tr>")
        if l.accord and not millesime_seul:
            r += f"<tr><td></td><td colspan='3' class='acc'>{e(l.accord)}</td></tr>"
        return r

    def sections_html(sections, titre=None, avec_format=True):
        if titre and sections:
            h.append(f"<h2>{e(titre)}</h2>")
        for s in sections:
            h.append(f"<h3>{e(titre_section(carte, s.cle))}</h3>" if titre else f"<h2>{e(titre_section(carte, s.cle))}</h2>")
            for p in s.pays:
                if not titre:
                    h.append(f"<h3>{e(geo.nom_pays(p.nom, lg) or _t(carte, 'carte.autres_pays'))}</h3>")
                for r in p.regions:
                    if r.nom:
                        h.append(f"<h4>{e(nom_region(r.nom, lg))}</h4>")
                    for a in r.appellations:
                        if a.nom:
                            h.append(f"<h5>{e(a.nom)}</h5>")
                        h.append("<table class='l'>")
                        for g in a.groupes:
                            if g.verticale:
                                h.append(f"<tr><td></td><td colspan='3'><b>{e(g.producteur or '—')}</b>"
                                         + (f", <i>{e(g.cuvee)}</i>" if g.cuvee else "")
                                         + f" <span class='doux'>({e(_t(carte, 'carte.verticale'))})</span></td></tr>")
                                if g.lignes[0].accord:
                                    h.append(f"<tr><td></td><td colspan='3' class='acc'>{e(g.lignes[0].accord)}</td></tr>")
                                for l in g.lignes:
                                    h.append(ligne_html(l, avec_format, millesime_seul=True))
                            else:
                                for l in g.lignes:
                                    h.append(ligne_html(l, avec_format))
                        h.append("</table>")

    if carte.au_verre:
        h.append(f"<h2>{e(_t(carte, 'carte.au_verre'))}</h2><table class='l'>")
        for l in carte.au_verre:
            h.append(ligne_html(l, prix=l.prix_verre))
        h.append("</table>")
    sections_html(carte.sections)
    sections_html(carte.demi, _t(carte, "carte.demi"), avec_format=False)
    sections_html(carte.grands, _t(carte, "carte.grands"))
    if o.get("index") and carte.producteurs:
        h.append(f"<h2>{e(_t(carte, 'carte.index'))}</h2><p>")
        h.append("<br>".join(f"{e(p)} <span class='doux'>— BIN {e(', '.join(l.bin for l in ls))}</span>"
                             for p, ls in carte.producteurs.items()))
        h.append("</p>")
    h.append(f"<p class='doux' style='font-size:8.5pt;margin-top:24px'>&#9829; {e(_t(carte, 'carte.leg_coeur'))} · {e(_t(carte, 'carte.legende'))}</p>")
    h.append("</body></html>")
    return "\n".join(h)


# ============================================================================ PDF
def ecrire_pdf(carte: Carte, chemin: str | Path, moteur=None, forcer_qt: bool = False,
               garder_tex: bool = False) -> str:
    """PDF par LaTeX si un moteur existe (sinon, ou si `forcer_qt`, repli Qt).
    Renvoie le nom du moteur utilisé (« xelatex »… ou « qt »)."""
    from . import latex as mod_latex
    if not forcer_qt:
        m = moteur or mod_latex.trouver_moteur()
        if m is not None:
            source, annexes = latex(carte, m.unicode)
            r = mod_latex.compiler(source, chemin, annexes, moteur=m, garder_tex=garder_tex)
            return r.moteur
    from .qt_pdf import html_vers_pdf
    images: dict = {}
    page = html(carte, images)
    html_vers_pdf(page, chemin, images, a5=carte.options["format"] == "a5")
    return "qt"
