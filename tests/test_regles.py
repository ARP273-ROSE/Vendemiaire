# -*- coding: utf-8 -*-
"""Règles du dossier « Le vin » : copie fidèle, jeu valide, et les cinq vins de
référence du dossier (muscadet, Nuits-Saint-Georges, Léoville Las Cases, Dom
Pérignon, Petrus) donnent exactement les valeurs de ses tableaux
(`gen/regles_*.tex`, générés depuis les mêmes JSON).

Les valeurs attendues ci-dessous sont recopiées des tableaux du dossier ; quand
le dossier est présent à côté du dépôt, un essai de plus relit ses tableaux
générés et compare TOUTES les fenêtres et températures."""
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from vendemiaire.regles import accords, conservation, degustation, garde, niveaux, service  # noqa: E402
from vendemiaire.regles.anglais import TRADUCTIONS, en  # noqa: E402
from vendemiaire.regles.jeu import DONNEES, JeuRegles, ReglesInvalides, jeu  # noqa: E402
from vendemiaire.regles.styles import classer  # noqa: E402

DOSSIER = Path(os.environ.get("VENDEMIAIRE_DOSSIER_VIN") or RACINE.parent / "_docs" / "Vin")

#: les cinq vins de la question, tels qu'on les saisirait dans Vendémiaire
MUSCADET = dict(couleur="blanc", type="tranquille", appellation="Muscadet Sèvre et Maine",
                region="Val de Loire", pays="France", cepages=["Melon de Bourgogne"], millesime=2023)
NSG = dict(couleur="rouge", type="tranquille", appellation="Nuits-Saint-Georges", region="Bourgogne",
           pays="France", cepages=["Pinot noir"], millesime=2019)
LEOVILLE = dict(couleur="rouge", type="tranquille", appellation="Saint-Julien", region="Bordeaux",
                pays="France", cuvee="Grand vin de Léoville du Marquis de Las Cases",
                cepages=["Cabernet sauvignon", "Merlot", "Cabernet franc"], millesime=2021)
DOM_PERIGNON = dict(couleur="blanc", type="effervescent", appellation="Champagne", region="Champagne",
                    pays="France", cuvee="Dom Pérignon", cepages=["Chardonnay", "Pinot noir"], millesime=2015)
PETRUS = dict(couleur="rouge", type="tranquille", appellation="Pomerol", region="Bordeaux", pays="France",
              cepages=["Merlot"], millesime=2021)


# ---------------------------------------------------------------------------- copie et validité
def test_copie_conforme_au_manifeste():
    m = json.loads((DONNEES / "MANIFESTE.json").read_text(encoding="utf-8"))
    assert m["date_audit"] == "2026-10-26"
    assert len(m["fichiers"]) == 14
    for nom, info in m["fichiers"].items():
        assert hashlib.sha256((DONNEES / nom).read_bytes()).hexdigest() == info["sha256"], nom


@pytest.mark.skipif(not (DOSSIER / "data" / "regles").is_dir(), reason="dossier « Le vin » absent (CI)")
def test_copie_identique_au_dossier():
    r = subprocess.run([sys.executable, str(RACINE / "outils" / "synchroniser_regles.py"), "--verifier",
                        "--dossier", str(DOSSIER)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_jeu_valide_194_regles_62_sources():
    j = jeu()
    assert j.nombre_regles() == 194
    assert len(j.sources) == 62
    assert len(j.styles) == 28
    assert j.date_audit == "2026-10-26"


def test_copie_retouchee_refusee(tmp_path):
    copie = tmp_path / "donnees"
    shutil.copytree(DONNEES, copie)
    p = copie / "service.json"
    p.write_text(p.read_text(encoding="utf-8").replace('"min_c": 16', '"min_c": 15', 1), encoding="utf-8")
    with pytest.raises(ReglesInvalides) as e:
        JeuRegles(copie)
    assert "service.json" in str(e.value)


def test_regle_incoherente_refusee(tmp_path):
    """Une source inconnue est refusée même si le manifeste a été refait."""
    copie = tmp_path / "donnees"
    shutil.copytree(DONNEES, copie)
    p = copie / "service.json"
    p.write_text(p.read_text(encoding="utf-8").replace('"WSET_TEMP"', '"SOURCE_INVENTEE"', 1), encoding="utf-8")
    with pytest.raises(ReglesInvalides) as e:
        JeuRegles(copie, verifier_empreintes=False)
    assert "SOURCE_INVENTEE" in str(e.value)


# ---------------------------------------------------------------------------- les cinq vins
@pytest.mark.parametrize("vin,style", [(MUSCADET, "blanc_frais"), (NSG, "rouge_pinot_garde"),
                                        (LEOVILLE, "rouge_bordeaux"), (DOM_PERIGNON, "eff_millesime"),
                                        (PETRUS, "rouge_bordeaux")])
def test_cinq_vins_styles(vin, style):
    c = classer(vin)
    assert c.id == style
    assert c.raisons("fr") and c.raisons("en")


#: tableau « Le tableau des fenêtres, style par style » (gen/regles_garde.tex) :
#: (prêt, apogée début, apogée fin, fin, marge, modèle) pour un millésime moyen
FENETRES = {
    "blanc_frais": (0, 0, 2, 4, 1, "plateau"),                 # Muscadet
    "rouge_pinot_garde": (6, 12, 19, 25, 5, "cloche"),         # Nuits-Saint-Georges
    "rouge_bordeaux": (5, 12, 20, 27, 6, "plateau"),           # Léoville Las Cases, Petrus
    "eff_millesime": (8, 15, 21, 28, 5, "plateau"),            # Dom Pérignon
}


@pytest.mark.parametrize("vin", [MUSCADET, NSG, LEOVILLE, DOM_PERIGNON, PETRUS])
def test_cinq_vins_fenetre_millesime_moyen(vin):
    f = garde.fenetre(vin, ajuster_millesime=False)
    pret, a1, a2, fin, marge, modele = FENETRES[f.classement.id]
    assert f.niveau == "garde"
    assert (f.ans["pret"], f.ans["apogee_debut"], f.ans["apogee_fin"], f.ans["fin"]) == (pret, a1, a2, fin)
    assert f.marge_ans == marge and f.modele == modele
    m = vin["millesime"]
    assert f.annees == {"debut": m + pret, "apogee_debut": m + a1, "apogee_fin": m + a2, "fin": m + fin}
    assert f.pic == (m + math.floor((a1 + a2) / 2 + 0.5) if modele == "cloche" else None)
    assert f.sources and f.confiance == "moyenne"


def test_ajustement_millesime_0_44_an_par_point():
    """Léoville Las Cases 2010 : 98/100 chez Wine Enthusiast (Bordeaux rive gauche) ;
    décalage = 0,44 × (98 − moyenne de la région dans ce tableau), marge ± 0,06/point."""
    v = dict(LEOVILLE, millesime=2010)
    f = garde.fenetre(v)
    n = f.note
    assert n.region == "bx_gauche" and n.source == "WE" and n.note == 98 and n.echelle == 100
    region = next(r for r in jeu().millesimes["regions"] if r["id"] == "bx_gauche")
    notes = [a["sources"]["WE"]["note"] for a in region["annees"] if "WE" in a["sources"]]
    assert n.moyenne == pytest.approx(sum(notes) / len(notes))
    assert f.decalage_millesime == pytest.approx(0.44 * (98 - n.moyenne))
    assert f.marge_millesime == pytest.approx(0.06 * (98 - n.moyenne))
    assert f.ans["apogee_debut"] == pytest.approx(12 + f.decalage_millesime)
    assert "garde.millesime" in f.regles_appliquees and "GARDE_CALC" in f.sources


def test_ajustement_millesime_sur_10():
    """The Wine Society (sur 10) : 1,76 an par point."""
    f = garde.fenetre(PETRUS)                       # 2021 rive droite : pas de Wine Enthusiast
    assert f.note.echelle == 10 and f.note.source == "WSO"
    assert f.decalage_millesime == pytest.approx(1.76 * (f.note.note - f.note.moyenne))


def test_cave_a_18_degres_vieillit_1_5_fois_plus_vite():
    assert garde.facteur_vitesse(18) == pytest.approx(2 ** 0.6) == pytest.approx(1.516, abs=1e-3)
    assert garde.facteur_vitesse(12) == 1
    f = garde.fenetre(LEOVILLE, temperature_cave=18, ajuster_millesime=False)
    assert f.ans["apogee_debut"] == pytest.approx(12 / 2 ** 0.6)
    assert f.ans["fin"] == pytest.approx(27 / 2 ** 0.6)
    assert "garde.temperature_cave" in f.regles_appliquees
    froide = garde.fenetre(LEOVILLE, temperature_cave=10, ajuster_millesime=False)
    assert froide.ans["fin"] > 27                     # plus froid : plus lent


def test_magnum_signale_sans_chiffre_invente():
    f = garde.fenetre(LEOVILLE, formats=("magnum",), ajuster_millesime=False)
    g = garde.fenetre(LEOVILLE, ajuster_millesime=False)
    assert f.annees == g.annees                       # le dossier ne chiffre pas
    assert "garde.bouteille_format" in f.regles_appliquees
    assert any("plus lentement" in d for d in f.details_fr)
    assert "DOSSIER" in f.sources


def test_niveau_choisi_par_l_utilisateur():
    f = garde.fenetre(dict(LEOVILLE, niveau_garde="courant"), ajuster_millesime=False)
    assert f.niveau == "courant" and (f.ans["pret"], f.ans["fin"]) == (0, 5)
    f = garde.fenetre(dict(LEOVILLE, niveau_garde="inexistant"), ajuster_millesime=False)
    assert f.niveau == "garde"


def test_style_impose_par_l_utilisateur():
    c = classer(dict(MUSCADET, style="blanc_mineral_garde"))
    assert c.id == "blanc_mineral_garde" and c.impose and c.automatique["id"] == "blanc_frais"


def test_vin_sans_millesime_compte_depuis_l_entree():
    v = dict(DOM_PERIGNON, cuvee="Brut", millesime=None, non_millesime=1)
    f = garde.fenetre(v, annee_entree=2024)
    assert f.base == 2024 and f.base_est_entree


# ---------------------------------------------------------------------------- service
#: tableau des températures (gen/regles_temperature.tex) : (min, max, marge)
TEMPERATURES = {"blanc_frais": (8, 10, 2), "rouge_pinot_garde": (14, 16, 2), "rouge_bordeaux": (16, 18, 1),
                "eff_millesime": (10, 12, 2)}


@pytest.mark.parametrize("vin", [MUSCADET, NSG, LEOVILLE, DOM_PERIGNON, PETRUS])
def test_cinq_vins_service(vin):
    s = service.service(vin, 2026)
    tmin, tmax, marge = TEMPERATURES[s.classement.id]
    assert s.temperature.valeur == {"min_c": tmin, "max_c": tmax}
    assert s.temperature.marge == {"c": marge}
    assert s.a_verser_c == tmin
    carafes = [c.regle for c in s.carafes]
    verres = [v.regle for v in s.verres]
    assert carafes[-1] == "carafe.reduction" and verres[-1] == "verre.universel"
    attendu = {"blanc_frais": ([], []), "rouge_pinot_garde": (["carafe.pinot_leger"], ["verre.rouge_ample"]),
               "rouge_bordeaux": (["carafe.rouge_tannique_jeune"], ["verre.rouge_structure"]),
               "eff_millesime": (["carafe.effervescent"], ["verre.effervescent"])}[s.classement.id]
    assert carafes[:-1] == attendu[0] and verres[:-1] == attendu[1]


def test_sortie_de_cave_redonne_le_tableau():
    """Loi de Newton du dossier : les durées publiées (cave 12 °C, pièce 20 °C,
    réfrigérateur 4 °C, seau d'eau glacée) à la minute près."""
    v = jeu().service["sortie_de_cave"]["valeur"]
    for cible, minutes in v["minutes_pour_atteindre"].items():
        assert service.sortie_de_cave(float(cible)).valeur["minutes"] == minutes
    for cible, d in v["refroidir_minutes"].items():
        depuis_cave = service.sortie_de_cave(float(cible)).valeur
        depuis_20 = service.sortie_de_cave(float(cible), cave_c=20).valeur
        assert (depuis_cave["frigo_min"], depuis_cave["seau_min"]) == (d["frigo_depuis_cave_min"],
                                                                     d["seau_depuis_cave_min"])
        assert (depuis_20["frigo_min"], depuis_20["seau_min"]) == (d["frigo_depuis_20C_min"],
                                                                 d["seau_depuis_20C_min"])


def test_leoville_sortir_1h45_avant():
    s = service.service(LEOVILLE, 2026, cave_c=12, piece_c=20)
    assert s.sortie.valeur["action"] == "sortir" and s.sortie.valeur["minutes"] == 107
    assert service.duree(107, "fr") == "1 h 47"


def test_vieux_bordeaux_plus_chaud_mais_plafonne_et_decante():
    s = service.service(dict(LEOVILLE, millesime=2005), 2026)
    assert s.temperature.valeur == {"min_c": 17, "max_c": 18}
    regles = [a.regle for a in s.ajustements]
    assert "temp.ajust.vieux_vin" in regles and "temp.plafond" in regles
    assert [c.regle for c in s.carafes][0] == "carafe.vieux_rouge_depot"


def test_dom_perignon_a_rafraichir():
    s = service.service(DOM_PERIGNON, 2026, cave_c=12)
    assert s.sortie.valeur["action"] == "rafraichir"
    assert (s.sortie.valeur["frigo_min"], s.sortie.valeur["seau_min"]) == (45, 7)


# ---------------------------------------------------------------------------- conservation, niveaux
@pytest.mark.parametrize("vin,jours", [(MUSCADET, [2, 7]), (NSG, [3, 5]), (LEOVILLE, [3, 5]),
                                       (DOM_PERIGNON, [1, 3]), (PETRUS, [3, 5])])
def test_cinq_vins_bouteille_ouverte(vin, jours):
    e = conservation.bouteille_ouverte(vin, "bouchon", date(2026, 10, 26))
    assert e.valeur["jours"] == jours
    assert e.valeur["a_finir_entre"][1] == date.fromordinal(date(2026, 10, 26).toordinal() + jours[1]).isoformat()
    gaz = conservation.bouteille_ouverte(vin, "gaz")
    assert gaz.valeur["jours"][1] > jours[1]
    assert conservation.bouteille_ouverte(vin, "coravin").valeur["texte"]


def test_conditions_hors_plage():
    assert conservation.hors_plage(12, 65) == []
    assert conservation.hors_plage(18, 65) == [("cave.temperature", "haut")]
    assert conservation.hors_plage(9, 40) == [("cave.temperature", "bas"), ("cave.hygrometrie", "bas")]
    assert conservation.age_controle_bouchon() == 15


@pytest.mark.parametrize("code,age,verdict", [("IN", 2, "excellent"), ("TS", 10, "bas_pour_age"),
                                              ("TS", 20, "normal"), ("TS", 40, "excellent"),
                                              ("MS", 20, "bas_pour_age"), ("MS", 45, "normal"),
                                              ("LS", 50, "risque"), ("BLS", 5, "risque")])
def test_niveaux_bordelais_selon_l_age(code, age, verdict):
    e = niveaux.sens_niveau(code, age)
    assert e.valeur["verdict"] == verdict and e.sources
    assert e.explication_en != e.explication_fr


@pytest.mark.parametrize("cm,age,verdict", [(1.5, 3, "excellent"), (3, 5, "bas_pour_age"), (3, 15, "normal"),
                                            (6, 55, "normal"), (9, 60, "hors_echelle")])
def test_niveaux_bourguignons(cm, age, verdict):
    assert niveaux.sens_niveau(None, age, cm).valeur["verdict"] == verdict


# ---------------------------------------------------------------------------- accords
#: tableau inverse « J'ouvre ce vin, que servir ? » (gen/regles_accords_vins.tex)
ACCORDS = {
    "rouge_bordeaux": ["viande_rouge_grillee", "agneau", "gibier", "canard_foie"],
    "eff_millesime": ["crustaces", "foie_gras"],
    "rouge_pinot_garde": ["volaille", "plats_mijotes", "gibier", "porc", "champignons", "pate_molle_lavee"],
    "blanc_frais": ["huitres", "poisson_grille", "sushi", "charcuterie", "fondue", "epice_asie", "chevre",
                    "aperitif"],
}


@pytest.mark.parametrize("vin", [MUSCADET, NSG, LEOVILLE, DOM_PERIGNON, PETRUS])
def test_cinq_vins_accords(vin):
    st = classer(vin).id
    plats = accords.plats_pour_style(st)
    assert [p.id for p in plats] == ACCORDS[st]
    assert all(p.pourquoi("fr") and p.pourquoi("en") != p.pourquoi("fr") for p in plats)


def test_muscadet_et_huitres_atteste():
    p = accords.chercher_plats("huîtres")[0]
    assert p.id == "huitres" and "blanc_frais" in p.styles
    assert any("Muscadet" in x["phrase"] for x in p.regle["preuves_corpus"])


@pytest.mark.parametrize("texte,plat", [("huitre", "huitres"), ("HUÎTRES", "huitres"), ("côte de boeuf",
                                        "viande_rouge_grillee"), ("pizza", "pates_tomate"), ("lamb", "agneau"),
                                        ("choclat", "chocolat"), ("poulet aux morilles", "volaille_creme"),
                                        ("boeuf bourguignon", "plats_mijotes"), ("roquefort", "pate_persillee")])
def test_recherche_de_plat_tolerante(texte, plat):
    assert accords.chercher_plats(texte)[0].id == plat


def test_accord_difficile_signale():
    assert [d.regle["id"] for d in accords.difficiles("artichauts")] == ["imp.artichaut"]
    assert accords.chercher_plats("zzzz") == []


# ---------------------------------------------------------------------------- dégustation
def test_diagnostic_des_defauts():
    assert accords and degustation.diagnostic("carton mouillé")[0][0]["id"] == "tca"
    assert degustation.diagnostic("vinegar")[0][0]["id"] == "acidite_volatile"
    assert len(degustation.diagnostic("")) == len(jeu().defauts)


def test_roue_des_aromes_code_et_relit():
    choix = [("P.FNR", "cassis"), ("S.BOI", "vanille"), ("T.BTR", None)]
    texte = degustation.coder(choix)
    assert texte == "P.FNR:cassis;S.BOI:vanille;T.BTR"
    assert degustation.decoder(texte) == choix
    assert degustation.libelle_arome("P.FNR", "cassis", "en") == "blackcurrant (Black fruit)"


# ---------------------------------------------------------------------------- phases, courbe
def test_phases_et_alertes():
    f = {"debut": 2026, "apogee_debut": 2033, "apogee_fin": 2041, "fin": 2048}
    assert garde.phase(f, 2025) == "trop_jeune" and garde.alerte(f, 2025) == "trop_jeune"
    assert garde.phase(f, 2030) == "buvable" and garde.alerte(f, 2030) is None
    assert garde.phase(f, 2035) == "apogee"
    assert garde.alerte(f, 2041) == "a_boire"
    assert garde.phase(f, 2045) == "declin" and garde.alerte(f, 2045) == "declin"
    assert garde.phase(f, 2050) == "passe" and garde.alerte(f, 2050) == "declin"


def test_courbe_repartit_chaque_bouteille():
    fen = [{"apogee_debut": 2026, "apogee_fin": 2029}, {"apogee_debut": 2010, "apogee_fin": 2015},
           {"debut": 2028, "fin": 2030}]
    c = garde.courbe(fen, 2026, 10)
    assert math.isclose(sum(b for _y, b, _n in c), 3)
    assert c[0][1] == pytest.approx(1 + 0.25)           # passée -> cette année ; 1/4 de la première
    assert c[0][2] == 1 and c[2][2] == 2


# ---------------------------------------------------------------------------- anglais
def _textes_affiches():
    j = jeu()
    t = [s["exemples"] for s in j.styles]
    for p in j.accords["plats"]:
        t += [p["plat_fr"], p["pourquoi_fr"], p["exemples_fr"]]
    for d in j.accords["accords_difficiles"]:
        t += [d["fr"], d["pourquoi_fr"]]
    for d in j.defauts:
        t += [d[k] for k in ("nom_fr", "molecule", "seuil", "perception_fr", "cause_fr", "que_faire_fr")]
    for n in j.niveaux["bordelaise"] + j.niveaux["bourguignonne_cm"]:
        t.append(n["explication_fr"])
        if n.get("risque"):
            t.append(n["risque"])
    for r in j.ouverte["regles"]:
        t += [r["valeur"]["lieu"], r["valeur"]["coravin"]]
    for v in j.service["verre"]:
        t += [x for k, x in v["valeur"].items() if isinstance(x, str)]
    for f in j.aromes["familles"]:
        t += f["descripteurs"] + [f["cercle"]]
    t.append(j.aromes["explication_fr"])
    for r in j.conservation["cave"]:
        t += [x for x in r["valeur"].values() if isinstance(x, str)]
    return t


def test_traductions_completes():
    manquantes = sorted({x for x in _textes_affiches() if x not in TRADUCTIONS})
    assert not manquantes, manquantes


def test_traductions_sans_francais():
    import re
    francais = re.compile(r"[éèàçêôûùîïœ«»]")
    admis = ("Vendémiaire", "Cuvée", "cuvée", "Rosé", "rosé", "rosés", "Côte", "Côtes", "Château", "Pérignon",
             "Rhône", "Émilion", "Estèphe", "Léognan", "Médoc", "Mâcon", "Savennières", "Spätlese", "Jurançon",
             "Ximénez", "albariño", "Crépy", "Époisses", "Comté", "Gruyère", "crémant", "Sélection",
             "aszú", "Beaumes", "Guerrouane", "gaïacol", "µg", "°C", "Chignin", "—", "crémants",
             "qvevri", "Rôtie", "supérieur", "Fumé", "jacquère")
    fautes = []
    for fr, en_ in TRADUCTIONS.items():
        nu = en_
        for mot in admis:
            nu = nu.replace(mot, "")
        if francais.search(nu):
            fautes.append(en_)
    assert not fautes, fautes
    assert en("texte inconnu") == "texte inconnu"


# ---------------------------------------------------------------------------- tous les tableaux du dossier
def _nb(x):
    return str(x) if not isinstance(x, float) else f"{x:.0f}"


@pytest.mark.skipif(not (DOSSIER / "gen" / "regles_garde.tex").exists(), reason="dossier « Le vin » absent (CI)")
def test_toutes_les_fenetres_identiques_au_tableau_du_dossier():
    """Pour CHAQUE style et niveau, la fenêtre que Vendémiaire calcule (millésime
    moyen, cave à 12 °C) est la ligne du tableau généré du dossier."""
    tex = (DOSSIER / "gen" / "regles_garde.tex").read_text(encoding="utf-8")
    niv = {"courant": "courant", "garde": "de garde", "primeur": "primeur", "nouveau_monde": "Nouveau Monde",
           "tous": ""}
    j = jeu()
    for st in j.styles:
        crit = st["criteres"]
        vin = {"couleur": crit["couleur"][0], "type": crit["type"][0], "style": st["id"], "millesime": 2000}
        for regle in j.garde["styles"][st["id"]]:
            f = garde.fenetre(dict(vin, niveau_garde=regle["niveau"]), ajuster_millesime=False)
            a = f.ans
            nom = st["nom_fr"] + (f" ({niv[regle['niveau']]})" if niv[regle["niveau"]] else "")
            ap = "--" if a["apogee_debut"] is None else \
                f"{_nb(a['apogee_debut'])}-{_nb(a['apogee_fin']) if a['apogee_fin'] is not None else '?'}"
            fin = "?" if a["fin"] is None else _nb(a["fin"])
            ligne = f"{nom} & {_nb(a['pret'])} & {ap} & {fin}"
            assert ligne in tex, ligne


@pytest.mark.skipif(not (DOSSIER / "gen" / "regles_temperature.tex").exists(), reason="dossier absent (CI)")
def test_toutes_les_temperatures_identiques_au_tableau_du_dossier():
    tex = (DOSSIER / "gen" / "regles_temperature.tex").read_text(encoding="utf-8")
    j = jeu()
    for st in j.styles:
        crit = st["criteres"]
        s = service.service({"couleur": crit["couleur"][0], "type": crit["type"][0], "style": st["id"]}, 2026)
        v = s.temperature.valeur
        assert f"\\textbf{{{int(v['min_c'])}-{int(v['max_c'])}}}" in tex, st["id"]


@pytest.mark.skipif(not (DOSSIER / "gen" / "regles_accords_vins.tex").exists(), reason="dossier absent (CI)")
def test_tous_les_accords_identiques_au_tableau_du_dossier():
    tex = (DOSSIER / "gen" / "regles_accords_vins.tex").read_text(encoding="utf-8")
    for st in jeu().styles:
        plats = accords.plats_pour_style(st["id"])
        if plats:
            ligne = f"\\textbf{{{st['nom_fr']}}} & {' ; '.join(p.nom('fr') for p in plats)} \\\\"
            assert ligne in tex, ligne
