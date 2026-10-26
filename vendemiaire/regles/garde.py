# -*- coding: utf-8 -*-
"""Fenêtre de dégustation calculée d'après le dossier (`garde.json`).

Méthode du dossier (LISEZMOI, « Calculer une fenêtre de garde ») :

1. style du vin -> fenêtres ; niveau `garde` par défaut (sinon `tous`, sinon la
   seule fenêtre du style) ; l'utilisateur peut choisir `courant` (entrée de
   gamme), `nouveau_monde`, `primeur`… quand le style les a ;
2. années après le millésime (vin sans millésime : après l'entrée en cave) :
   `pret`, `apogee_debut`, `apogee_fin`, `fin` (null = non chiffré) ;
3. ajustement millésime (`garde.millesime`) : toute la fenêtre décalée de
   0,44 an par point sur 100 au-dessus de la moyenne de la région (Wine
   Enthusiast, Wine Spectator), 1,76 an par point sur 10 (The Wine Society,
   Berry Bros.) ; marge ± 0,06 an par point sur 100 ;
4. ajustement cave (`garde.temperature_cave`) : durées divisées par
   2^((T−12)/10) — une cave à 18 °C vieillit ≈ 1,5 fois plus vite qu'une cave à
   12 °C ; marge relative ± 50 %, confiance faible ;
5. format (`garde.bouteille_format`) : magnum plus lent, demi-bouteille plus
   rapide — NON chiffré par le dossier : signalé, jamais calculé.

Le résultat garde toutes ses marges (fenêtre, millésime, cave) séparées, le
modèle (plateau ou cloche : sommet au milieu de l'apogée), la confiance, les
sources et le détail de chaque étape.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import Estimation
from . import millesimes as module_millesimes
from .jeu import JeuRegles, jeu
from .styles import Classement, classer

NIVEAUX = ("garde", "courant", "primeur", "nouveau_monde", "tous")
CLES = ("pret", "apogee_debut", "apogee_fin", "fin")
#: phases d'une bouteille par rapport à sa fenêtre (codes ; libellés dans textes.py)
PHASES = ("trop_jeune", "buvable", "apogee", "apogee_passee", "declin", "passe")


def arrondi(x: float) -> int:
    """Arrondi d'une année « à la moitié supérieure » (2034,5 -> 2035), jamais
    l'arrondi bancaire de Python."""
    return int(math.floor(x + 0.5))


def _fmt(x: float | None, langue: str) -> str:
    if x is None:
        return "—"
    t = f"{x:.2f}".rstrip("0").rstrip(".")
    return t.replace(".", ",") if langue == "fr" else t


@dataclass
class Fenetre:
    classement: Classement
    niveau: str
    regle: dict                      # fenêtre du dossier retenue
    base: int | None                 # millésime (ou année d'entrée d'un vin sans millésime)
    base_est_entree: bool
    ans: dict                        # âges ajustés (années, décimales)
    annees: dict                     # années civiles arrondies (debut, apogee_debut, apogee_fin, fin)
    pic: int | None                  # année du sommet (cloche) ; None pour un plateau
    decalage_millesime: float = 0.0
    marge_millesime: float = 0.0
    note: module_millesimes.NoteMillesime | None = None
    temperature_cave: float | None = None
    facteur_cave: float = 1.0
    formats: tuple = ()
    sources: list[str] = field(default_factory=list)
    regles_appliquees: list[str] = field(default_factory=list)
    details_fr: list[str] = field(default_factory=list)
    details_en: list[str] = field(default_factory=list)

    @property
    def modele(self) -> str:
        return self.regle["modele"]

    @property
    def confiance(self) -> str:
        return self.regle["confiance"]

    @property
    def marge_ans(self) -> float | None:
        return self.regle.get("marge_ans")

    @property
    def detail_source(self) -> str:
        return f"{self.classement.id}/{self.niveau}"

    def explication(self, langue: str = "fr") -> str:
        return self.regle["explication_fr"] if langue == "fr" else self.regle.get("explication_en") or \
            self.regle["explication_fr"]

    def estimation(self) -> Estimation:
        return Estimation(dict(self.annees, pic=self.pic, ans=self.ans), self.regle["explication_fr"],
                          self.regle.get("explication_en") or "", list(self.sources),
                          self.detail_source, self.modele, self.confiance,
                          {"ans": self.marge_ans, "millesime_ans": round(self.marge_millesime, 2),
                           "cave_relative": 0.5 if self.facteur_cave != 1.0 else None},
                          list(self.details_fr), list(self.details_en))

    def texte_pour_base(self) -> str:
        """Le « pourquoi » rangé dans fenetre_degustation.explication (français,
        comme les autres explications saisies)."""
        return " ".join([self.regle["explication_fr"]] + self.details_fr)


def niveaux_du_style(style_id: str, regles: JeuRegles | None = None) -> list[str]:
    regles = regles or jeu()
    return [f["niveau"] for f in regles.garde["styles"].get(style_id, [])]


def choisir_niveau(style_id: str, voulu: str | None, regles: JeuRegles | None = None) -> str | None:
    dispo = niveaux_du_style(style_id, regles)
    if not dispo:
        return None
    if voulu in dispo:
        return voulu
    for n in ("garde", "tous"):
        if n in dispo:
            return n
    return dispo[0]


def facteur_vitesse(temperature: float, reference: float = 12.0) -> float:
    """2^((T−12)/10) : formule du dossier (`garde.temperature_cave`)."""
    return 2 ** ((temperature - reference) / 10)


def fenetre(vin: dict, temperature_cave: float | None = None, annee_entree: int | None = None,
            formats=(), regles: JeuRegles | None = None,
            ajuster_millesime: bool = True) -> Fenetre | None:
    """Fenêtre calculée pour un vin (dict : couleur, type, appellation, cuvée,
    région, cépages, millésime, non_millesime, style, niveau_garde).

    `temperature_cave` : température moyenne MESURÉE de la cave (None = pas de
    mesure : aucun ajustement, la fenêtre suppose une cave à 12 °C)."""
    regles = regles or jeu()
    cl = classer(vin, regles)
    if cl is None:
        return None
    niveau = choisir_niveau(cl.id, vin.get("niveau_garde"), regles)
    if niveau is None:
        return None
    regle = next(f for f in regles.garde["styles"][cl.id] if f["niveau"] == niveau)
    ajust = {a["id"]: a for a in regles.garde.get("ajustements") or []}
    fr, en = [], []
    sources = list(regle["sources"])
    appliquees = [f"garde/{cl.id}/{niveau}"]
    fa = regle["fenetre_ans"]
    ans = {k: (float(fa[k]) if fa[k] is not None else None) for k in CLES}
    fr.append(f"Style « {cl.nom('fr')} », niveau « {niveau} » : prêt à {_fmt(ans['pret'], 'fr')} an(s), "
              f"apogée {_fmt(ans['apogee_debut'], 'fr')}–{_fmt(ans['apogee_fin'], 'fr')} ans, fin "
              f"{_fmt(ans['fin'], 'fr')} ans (± {_fmt(regle.get('marge_ans'), 'fr')} an), modèle "
              f"« {regle['modele']} », confiance {regle['confiance']}.")
    en.append(f"Style \"{cl.nom('en')}\", level \"{niveau}\": ready at {_fmt(ans['pret'], 'en')} y, peak "
              f"{_fmt(ans['apogee_debut'], 'en')}–{_fmt(ans['apogee_fin'], 'en')} y, end "
              f"{_fmt(ans['fin'], 'en')} y (± {_fmt(regle.get('marge_ans'), 'en')} y), "
              f"\"{regle['modele']}\" model, {regle['confiance']} confidence.")

    # base : millésime, ou entrée en cave pour un vin sans millésime
    base, base_entree = vin.get("millesime"), False
    if not base:
        base, base_entree = annee_entree, True
        if base:
            fr.append(f"Sans millésime : âges comptés depuis l'entrée en cave ({base}).")
            en.append(f"Non-vintage: ages counted from the date it entered the cellar ({base}).")

    # ajustement millésime
    decalage, marge_mil, note = 0.0, 0.0, None
    am = ajust.get("garde.millesime")
    if ajuster_millesime and am and vin.get("millesime"):
        note = module_millesimes.note(vin, regles)
        if note is not None:
            if note.echelle == 100:
                pente, marge_pente = am["valeur"]["ans_par_point_100"], am["marge"].get("ans_par_point_100", 0)
            else:
                pente, marge_pente = am["valeur"]["ans_par_point_10"], None
            ecart = note.note - note.moyenne
            decalage = pente * ecart
            marge_mil = abs(ecart) * marge_pente if marge_pente is not None else 0.0
            for k in CLES:
                if ans[k] is not None:
                    ans[k] = ans[k] + decalage
            sources += [s for s in am["sources"] if s not in sources]
            appliquees.append(am["id"])
            m_fr = f" ± {_fmt(round(marge_mil, 2), 'fr')} an" if marge_pente is not None else ""
            m_en = f" ± {_fmt(round(marge_mil, 2), 'en')} y" if marge_pente is not None else ""
            fr.append(f"Millésime {vin['millesime']} ({note.region_nom}) : {_fmt(note.note, 'fr')}/{note.echelle} "
                      f"chez {note.source_nom}, moyenne de la région {_fmt(round(note.moyenne, 2), 'fr')} "
                      f"sur {note.n_annees} millésimes → fenêtre décalée de {_fmt(round(decalage, 2), 'fr')} an "
                      f"({_fmt(pente, 'fr')} an par point){m_fr}.")
            en.append(f"Vintage {vin['millesime']} ({note.region_nom}): {_fmt(note.note, 'en')}/{note.echelle} "
                      f"from {note.source_nom}, regional mean {_fmt(round(note.moyenne, 2), 'en')} over "
                      f"{note.n_annees} vintages → window shifted by {_fmt(round(decalage, 2), 'en')} y "
                      f"({_fmt(pente, 'en')} y per point){m_en}.")
        else:
            fr.append("Millésime absent des tableaux du dossier pour cette région : fenêtre d'un millésime moyen.")
            en.append("Vintage not in the dossier's charts for this region: average-vintage window.")

    # ajustement cave
    facteur = 1.0
    at = ajust.get("garde.temperature_cave")
    if at and temperature_cave is not None:
        reference = float(at["valeur"].get("reference_c", 12))
        facteur = facteur_vitesse(float(temperature_cave), reference)
        for k in CLES:
            if ans[k] is not None:
                ans[k] = ans[k] / facteur
        sources += [s for s in at["sources"] if s not in sources]
        appliquees.append(at["id"])
        fr.append(f"Cave mesurée à {_fmt(round(temperature_cave, 1), 'fr')} °C : vieillissement "
                  f"×{_fmt(round(facteur, 2), 'fr')} par rapport à 12 °C (2^((T−12)/10)), durées divisées "
                  f"d'autant ; marge ± 50 %, confiance faible.")
        en.append(f"Cellar measured at {_fmt(round(temperature_cave, 1), 'en')} °C: ageing "
                  f"×{_fmt(round(facteur, 2), 'en')} compared with 12 °C (2^((T−12)/10)), durations divided "
                  f"accordingly; margin ± 50 %, low confidence.")
    elif at:
        fr.append("Aucune température de cave mesurée : la fenêtre suppose une cave à 12 °C.")
        en.append("No measured cellar temperature: the window assumes a 12 °C cellar.")

    # format : signalé, non chiffré
    af = ajust.get("garde.bouteille_format")
    formats = tuple(sorted(set(formats or ())))
    grands = [f for f in formats if f in ("magnum", "marie_jeanne", "double_magnum", "rehoboam",
                                          "jeroboam_bdx", "mathusalem", "salmanazar", "balthazar",
                                          "nabuchodonosor", "salomon", "souverain", "primat", "melchisedech")]
    petits = [f for f in formats if f in ("piccolo", "demi", "pot", "cinquante")]
    if af and (grands or petits):
        appliquees.append(af["id"])
        sources += [s for s in af["sources"] if s not in sources]
        if grands:
            fr.append("Grand format en cave : il vieillit plus lentement (non chiffré par le dossier : "
                      "fenêtre inchangée, convention).")
            en.append("Large format in the cellar: it ages more slowly (not quantified by the dossier: "
                      "window unchanged, convention).")
        if petits:
            fr.append("Demi-bouteille ou petit format en cave : il vieillit plus vite (non chiffré par le "
                      "dossier : fenêtre inchangée, convention).")
            en.append("Half bottle or small format in the cellar: it ages faster (not quantified by the "
                      "dossier: window unchanged, convention).")

    for k in CLES:                                  # un âge négatif n'a pas de sens
        if ans[k] is not None and ans[k] < 0:
            ans[k] = 0.0
    annees = {"debut": None, "apogee_debut": None, "apogee_fin": None, "fin": None}
    pic = None
    if base:
        for k, cle in zip(CLES, ("debut", "apogee_debut", "apogee_fin", "fin")):
            annees[cle] = None if ans[k] is None else arrondi(base + ans[k])
        if regle["modele"] == "cloche" and ans["apogee_debut"] is not None and ans["apogee_fin"] is not None:
            pic = arrondi(base + (ans["apogee_debut"] + ans["apogee_fin"]) / 2)
    return Fenetre(cl, niveau, regle, int(base) if base else None, base_entree, ans, annees, pic,
                   decalage, marge_mil, note, temperature_cave, facteur, formats, sources, appliquees, fr, en)


# ---------------------------------------------------------------------------- phases et alertes
def phase(f: dict, annee: int) -> str | None:
    """Où en est un vin l'année `annee` d'après une fenêtre (dict debut,
    apogee_debut, apogee_fin, fin — années civiles, éventuellement None)."""
    debut, a1, a2, fin = (f.get(k) for k in ("debut", "apogee_debut", "apogee_fin", "fin"))
    if debut is None and a1 is None and a2 is None and fin is None:
        return None
    if fin is not None and annee > fin:
        return "passe"
    if debut is not None and annee < debut:
        return "trop_jeune"
    if a1 is not None and annee < a1:
        return "buvable"
    if a2 is None or annee <= a2:
        return "apogee" if (a1 is not None or a2 is not None) else "buvable"
    return "declin" if fin is not None else "apogee_passee"


def alerte(f: dict, annee: int) -> str | None:
    """« trop_jeune », « a_boire » (dernière année d'apogée, ou fin de fenêtre
    cette année), « declin » (après l'apogée, ou au-delà de la fin) ou None."""
    p = phase(f, annee)
    if p == "trop_jeune":
        return "trop_jeune"
    if p in ("declin", "passe"):
        return "declin"
    if p == "apogee" and f.get("apogee_fin") == annee:
        return "a_boire"
    if f.get("fin") == annee:
        return "a_boire"
    return None


def courbe(fenetres: list[dict], annee0: int, annees: int = 20) -> list[tuple[int, float, int]]:
    """Courbe d'apogée de la cave : pour chaque année, (année, bouteilles à boire
    cette année-là, bouteilles à leur apogée — ou dans leur fenêtre quand elle
    n'a pas d'apogée). « À boire » répartit chaque
    bouteille à parts égales sur les années d'apogée qui lui restent (toute
    entière l'année `annee0` si l'apogée est passée) : la somme vaut le nombre
    de bouteilles, d'où « combien à boire chaque année »."""
    a_boire = [0.0] * annees
    a_apogee = [0] * annees
    for f in fenetres:
        # fenêtre sans apogée (saisie « de… à… ») : la fenêtre entière en tient lieu
        a1 = f.get("apogee_debut") if f.get("apogee_debut") is not None else f.get("debut")
        a2 = f.get("apogee_fin") if f.get("apogee_fin") is not None else (
            f.get("fin") if f.get("apogee_debut") is None else None)
        if a1 is None and a2 is None:
            continue
        a1 = a1 if a1 is not None else annee0
        for i in range(annees):
            y = annee0 + i
            if a1 <= y and (a2 is None or y <= a2):
                a_apogee[i] += 1
        if a2 is None:                         # apogée sans fin chiffrée : à boire dès l'apogée
            premier = max(annee0, a1)
            if premier - annee0 < annees:
                a_boire[premier - annee0] += 1
            continue
        if a2 < annee0:
            a_boire[0] += 1
            continue
        debut = max(annee0, a1)
        n = a2 - debut + 1
        for y in range(debut, a2 + 1):
            if y - annee0 < annees:
                a_boire[y - annee0] += 1 / n
    return [(annee0 + i, a_boire[i], a_apogee[i]) for i in range(annees)]
