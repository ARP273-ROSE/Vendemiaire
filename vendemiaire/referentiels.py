# -*- coding: utf-8 -*-
"""Référentiels fixes : formats de bouteille, statuts, couleurs, niveaux…

Chaque valeur a un CODE (stocké dans la base, jamais traduit) et un libellé
dans chaque langue de l'interface. Ajouter une valeur ici suffit : la base
n'impose pas de liste fermée (un code inconnu reste affiché tel quel), ce qui
permet d'importer sans perte une donnée que l'application ne connaît pas
encore.

Ce module ne contient AUCUNE règle d'œnologie (apogée, signification d'un
niveau selon l'âge, service, accords) : elles viendront du dossier « Le vin »,
avec leurs sources, par l'interface `vendemiaire.regles`.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Format:
    code: str
    litres: float
    fr: str
    en: str


#: de la piccolo au melchisédech ; contenances usuelles (les noms au-delà du
#: magnum varient selon les régions : bordelais et champenois diffèrent)
FORMATS: tuple[Format, ...] = (
    Format("piccolo", 0.1875, "Piccolo (quart)", "Piccolo (quarter bottle)"),
    Format("demi", 0.375, "Demi-bouteille (fillette)", "Half bottle"),
    Format("pot", 0.46, "Pot lyonnais", "Lyonnais pot"),
    Format("cinquante", 0.5, "Bouteille de 50 cl", "50 cl bottle"),
    Format("clavelin", 0.62, "Clavelin", "Clavelin"),
    Format("bouteille", 0.75, "Bouteille", "Bottle"),
    Format("litre", 1.0, "Litre", "Litre"),
    Format("magnum", 1.5, "Magnum", "Magnum"),
    Format("marie_jeanne", 2.25, "Marie-Jeanne", "Marie-Jeanne"),
    Format("double_magnum", 3.0, "Double magnum (jéroboam)", "Double magnum (Jeroboam)"),
    Format("rehoboam", 4.5, "Réhoboam", "Rehoboam"),
    Format("jeroboam_bdx", 5.0, "Jéroboam bordelais", "Bordeaux Jeroboam"),
    Format("mathusalem", 6.0, "Mathusalem (impériale)", "Methuselah (Imperial)"),
    Format("salmanazar", 9.0, "Salmanazar", "Salmanazar"),
    Format("balthazar", 12.0, "Balthazar", "Balthazar"),
    Format("nabuchodonosor", 15.0, "Nabuchodonosor", "Nebuchadnezzar"),
    Format("salomon", 18.0, "Salomon (melchior)", "Solomon (Melchior)"),
    Format("souverain", 26.25, "Souverain", "Sovereign"),
    Format("primat", 27.0, "Primat (goliath)", "Primat (Goliath)"),
    Format("melchisedech", 30.0, "Melchisédech (midas)", "Melchizedek (Midas)"),
)
FORMATS_PAR_CODE = {f.code: f for f in FORMATS}

#: énumérations simples : code -> (français, anglais)
ENUMS: dict[str, dict[str, tuple[str, str]]] = {
    "statut": {
        "en_cave": ("En cave", "In cellar"),
        "en_attente": ("En attente de livraison", "Awaiting delivery"),
        "primeur": ("Achetée en primeur", "Bought en primeur (futures)"),
        "bue": ("Bue", "Drunk"),
        "offerte": ("Offerte", "Given away"),
        "vendue": ("Vendue", "Sold"),
        "cassee": ("Cassée", "Broken"),
        "bouchonnee": ("Bouchonnée", "Corked"),
        "manquante": ("Manquante (inventaire)", "Missing (stock-take)"),
    },
    "couleur": {
        "rouge": ("Rouge", "Red"),
        "blanc": ("Blanc", "White"),
        "rose": ("Rosé", "Rosé"),
        "orange": ("Orange", "Orange"),
    },
    "type": {
        "tranquille": ("Tranquille", "Still"),
        "effervescent": ("Effervescent", "Sparkling"),
        "doux": ("Moelleux ou liquoreux", "Sweet"),
        "mute": ("Muté (porto, xérès…)", "Fortified (port, sherry...)"),
        "autre": ("Autre", "Other"),
    },
    # Niveau du vin, échelle des ventes aux enchères (bouteille bordelaise).
    # La SIGNIFICATION d'un niveau selon l'âge du vin viendra du dossier
    # « Le vin » (phase 3) ; ici, seulement le vocabulaire.
    "niveau": {
        "IN": ("Dans le goulot", "Into neck"),
        "BN": ("Base du goulot", "Base of neck"),
        "VTS": ("Très haut d'épaule", "Very top shoulder"),
        "TS": ("Haut d'épaule", "Top shoulder"),
        "HS": ("Haute épaule", "High shoulder"),
        "MS": ("Mi-épaule", "Mid shoulder"),
        "LS": ("Bas d'épaule", "Low shoulder"),
        "BLS": ("Sous le bas d'épaule", "Below low shoulder"),
    },
    "etat_etiquette": {
        "parfaite": ("Parfaite", "Perfect"),
        "legere": ("Légèrement abîmée", "Slightly damaged"),
        "tachee": ("Tachée", "Stained"),
        "dechiree": ("Déchirée", "Torn"),
        "decollee": ("Décollée", "Loose"),
        "absente": ("Absente", "Missing"),
    },
    "etat_capsule": {
        "intacte": ("Intacte", "Intact"),
        "coupee": ("Coupée", "Cut"),
        "corrodee": ("Corrodée", "Corroded"),
        "abimee": ("Abîmée", "Damaged"),
        "fuite": ("Traces de fuite", "Signs of leakage"),
        "absente": ("Absente", "Missing"),
    },
    "etat_bouchon": {
        "normal": ("Normal", "Normal"),
        "enfonce": ("Enfoncé", "Depressed"),
        "sorti": ("Remonté", "Raised"),
        "suintant": ("Suintant", "Seeping"),
    },
    "caisse": {
        "aucune": ("Aucune", "None"),
        "cbo": ("Caisse bois d'origine (CBO)", "Original wooden case (OWC)"),
        "carton_origine": ("Carton d'origine", "Original carton"),
        "carton": ("Carton", "Carton"),
        "coffret": ("Coffret", "Gift box"),
    },
    "mouvement": {
        "entree_achat": ("Entrée : achat", "In: purchase"),
        "entree_cadeau": ("Entrée : cadeau reçu", "In: gift received"),
        "entree_primeur": ("Entrée : primeur livré", "In: futures delivered"),
        "entree_inventaire": ("Entrée : écart d'inventaire", "In: stock-take difference"),
        "sortie_bue": ("Sortie : bue", "Out: drunk"),
        "sortie_offerte": ("Sortie : offerte", "Out: given away"),
        "sortie_vendue": ("Sortie : vendue", "Out: sold"),
        "sortie_cassee": ("Sortie : cassée", "Out: broken"),
        "sortie_bouchonnee": ("Sortie : bouchonnée", "Out: corked"),
        "sortie_inventaire": ("Sortie : écart d'inventaire", "Out: stock-take difference"),
    },
    "echelle": {
        "20": ("sur 20", "out of 20"),
        "100": ("sur 100", "out of 100"),
        "5": ("étoiles (sur 5)", "stars (out of 5)"),
        "3": ("étoiles (sur 3)", "stars (out of 3)"),
    },
    "niveau_emplacement": {
        "cave": ("Cave", "Cellar"),
        "meuble": ("Meuble", "Unit"),
        "casier": ("Casier", "Rack"),
    },
    "image": {
        "etiquette": ("Étiquette", "Label"),
        "contre_etiquette": ("Contre-étiquette", "Back label"),
        "capsule": ("Capsule", "Capsule"),
        "caisse": ("Caisse", "Case"),
        "bouteille": ("Bouteille", "Bottle"),
        "facture": ("Facture", "Invoice"),
        "autre": ("Autre", "Other"),
    },
    "source_fenetre": {
        "perso": ("La mienne", "Mine"),
        "critique": ("Critique", "Critic"),
        "calcul": ("Calculée par Vendémiaire", "Computed by Vendémiaire"),
    },
    "conservation_ouverte": {
        "bouchon": ("Rebouchée", "Recorked"),
        "gaz": ("Gaz inerte", "Inert gas"),
        "coravin": ("Coravin", "Coravin"),
        "vide": ("Pompe à vide", "Vacuum pump"),
    },
}

#: critiques et guides usuels : code -> (nom, échelle par défaut)
CRITIQUES: dict[str, tuple[str, str]] = {
    "RP": ("Robert Parker / Wine Advocate", "100"),
    "WS": ("Wine Spectator", "100"),
    "DEC": ("Decanter", "100"),
    "JS": ("James Suckling", "100"),
    "VIN": ("Vinous", "100"),
    "JR": ("Jancis Robinson", "20"),
    "BD": ("Bettane+Desseauve", "20"),
    "RVF": ("La Revue du vin de France", "20"),
    "GH": ("Guide Hachette", "3"),
}

#: statuts qui comptent comme « en cave » / « à venir » / « sortie »
STATUTS_EN_CAVE = ("en_cave",)
STATUTS_A_VENIR = ("en_attente", "primeur")
STATUTS_SORTIS = ("bue", "offerte", "vendue", "cassee", "bouchonnee", "manquante")

#: type de mouvement de sortie -> statut de la bouteille
SORTIE_VERS_STATUT = {
    "sortie_bue": "bue",
    "sortie_offerte": "offerte",
    "sortie_vendue": "vendue",
    "sortie_cassee": "cassee",
    "sortie_bouchonnee": "bouchonnee",
    "sortie_inventaire": "manquante",
}


def libelle(enum: str, code: str | None, langue: str) -> str:
    """Libellé d'un code dans la langue voulue ; un code inconnu reste lisible."""
    if code is None or code == "":
        return ""
    if enum == "format":
        f = FORMATS_PAR_CODE.get(code)
        return (f.fr if langue == "fr" else f.en) if f else code
    paire = ENUMS.get(enum, {}).get(code)
    if not paire:
        return code
    return paire[0] if langue == "fr" else paire[1]


def codes(enum: str) -> list[str]:
    if enum == "format":
        return [f.code for f in FORMATS]
    return list(ENUMS[enum])
