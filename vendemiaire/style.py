# -*- coding: utf-8 -*-
"""Apparence FIGÉE de Vendémiaire / Fixed look.

Style Qt « Fusion », palette COMPLÈTE (trois groupes, état désactivé compris),
polices embarquées (Source Sans 3 pour le texte, Cormorant Garamond pour les
titres) et feuille de style aux couleurs du logo : bordeaux, or, crème.
Rien ne dépend du thème clair/sombre du système ni de ses polices ; seule la
mise à l'échelle de l'écran reste celle du système.
"""
from __future__ import annotations

from pathlib import Path

POLICES = Path(__file__).resolve().parent / "polices"
FAMILLE = "Source Sans 3"
FAMILLE_TITRES = "Cormorant Garamond"

BORDEAUX = "#5E1427"
BORDEAUX_CLAIR = "#8E2A3D"
OR = "#C99A3B"
OR_CLAIR = "#F3D58A"
CREME = "#F7F1E3"       # fond des fenêtres
CARTE = "#FFFCF5"       # champs, listes
LIGNE = "#EFE6D2"       # lignes alternées, barres
BOUTON = "#EADFC6"
ENCRE = "#2A1A14"       # texte
GRIS = "#7D7064"        # texte secondaire, désactivé
BORD = "#CDBB98"

#: couleurs des vins sur le plan de cave et dans les pochettes
TEINTES_VIN = {
    "rouge": "#7A1730", "blanc": "#E4CF7A", "rose": "#E79AA6", "orange": "#D98A3D",
    None: "#9C8F80",
}

COULEURS = {
    "fenetre": CREME, "texte": ENCRE, "base": CARTE, "base_alt": LIGNE,
    "bouton": BOUTON, "texte_bouton": ENCRE, "selection": BORDEAUX,
    "texte_selection": "#FFFFFF", "lien": BORDEAUX_CLAIR, "infobulle": "#FFFBEF",
    "texte_infobulle": ENCRE, "desactive": GRIS, "clair": "#FFFFFF",
    "moyen": BORD, "sombre": "#8C7A5E",
}

FEUILLE = f"""
QMainWindow::separator {{ background: {BORD}; width: 3px; height: 3px; }}
QGroupBox {{ border: 1px solid {BORD}; border-radius: 6px; margin-top: 14px; padding-top: 6px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px;
    color: {BORDEAUX}; font-weight: 600; }}
QPushButton {{ background: {BOUTON}; border: 1px solid {BORD}; border-radius: 5px; padding: 4px 12px; }}
QPushButton:hover {{ background: #F2E8D2; border-color: {OR}; }}
QPushButton:pressed, QPushButton:checked {{ background: {OR_CLAIR}; }}
QPushButton:disabled {{ color: {GRIS}; background: {LIGNE}; }}
QPushButton#principal {{ background: {BORDEAUX}; color: #FFFFFF; border-color: {BORDEAUX}; }}
QPushButton#principal:hover {{ background: {BORDEAUX_CLAIR}; }}
QToolTip {{ background: #FFFBEF; color: {ENCRE}; border: 1px solid {OR}; padding: 4px; }}
QMenuBar {{ background: {BORDEAUX}; color: #FFFFFF; }}
QMenuBar::item {{ background: transparent; padding: 4px 10px; }}
QMenuBar::item:selected {{ background: {BORDEAUX_CLAIR}; }}
QMenu {{ background: {CARTE}; border: 1px solid {BORD}; }}
QMenu::item:selected {{ background: {BORDEAUX}; color: #FFFFFF; }}
QMenu::separator {{ height: 1px; background: {BORD}; margin: 4px 8px; }}
QTabWidget::pane {{ border: 1px solid {BORD}; border-top: 2px solid {OR}; }}
QTabBar::tab {{ background: {LIGNE}; border: 1px solid {BORD}; border-bottom: 0;
    padding: 6px 16px; margin-right: 2px; border-top-left-radius: 5px; border-top-right-radius: 5px; }}
QTabBar::tab:selected {{ background: {BORDEAUX}; color: #FFFFFF; border-color: {BORDEAUX}; }}
QHeaderView::section {{ background: {LIGNE}; border: 0; border-right: 1px solid {BORD};
    border-bottom: 1px solid {BORD}; padding: 3px 6px; font-weight: 600; }}
QStatusBar {{ background: {LIGNE}; border-top: 1px solid {BORD}; }}
QLabel#titre {{ font-family: "{FAMILLE_TITRES}"; font-size: 20pt; font-weight: 600; color: {BORDEAUX}; }}
QLabel#sous_titre {{ color: {GRIS}; }}
QFrame#tuile {{ background: {CARTE}; border: 1px solid {BORD}; border-radius: 8px; }}
QLabel#chiffre {{ font-size: 22pt; font-weight: 600; color: {BORDEAUX}; }}
QLabel#legende {{ color: {GRIS}; }}
"""


def appliquer(app) -> str | None:
    """Impose le style figé ; renvoie la famille de police retenue."""
    try:
        import interface_kit
    except ImportError:                      # copie sans le kit : style minimal
        app.setStyle("Fusion")
        app.setStyleSheet(FEUILLE)
        return None
    return interface_kit.appliquer_style(
        app, COULEURS, polices=POLICES, famille=FAMILLE, taille=10,
        feuille=FEUILLE, sombre=False)


def style_de_base(app) -> str:
    """Nom du style Qt sous la feuille de style (la feuille l'enveloppe)."""
    feuille = app.styleSheet()
    if not feuille:
        return app.style().name().lower()
    app.setStyleSheet("")
    try:
        return app.style().name().lower()
    finally:
        app.setStyleSheet(feuille)
