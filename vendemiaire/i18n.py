# -*- coding: utf-8 -*-
"""Bilinguisme FR / EN. Tout texte affiché passe par `tr(clé)` (ou `lib()` pour
les codes des référentiels). La langue est celle du système au premier
lancement, puis celle choisie dans le menu Langue (retenue).

Un test (tests/test_i18n_textes.py) attrape tout texte passé en dur à un
widget, toute clé manquante et tout français dans la partie anglaise.
"""
from __future__ import annotations

from . import referentiels
from .textes import T

LANGUES = {"fr": "Français", "en": "English"}
_langue = "fr"


def langue() -> str:
    return _langue


def definir_langue(lg: str) -> None:
    global _langue
    _langue = lg if lg in LANGUES else "en"


def tr(cle: str, **valeurs) -> str:
    jeu = T.get(cle)
    if jeu is None:
        return f"<{cle}>"
    texte = jeu.get(_langue) or jeu["en"]
    return texte.format(**valeurs) if valeurs else texte


def lib(enum: str, code) -> str:
    """Libellé d'un code de référentiel (statut, couleur, format…)."""
    return referentiels.libelle(enum, code, _langue)


def detect_language(langues_ui=None) -> str:
    """« fr » si la première langue d'interface du système est le français."""
    if langues_ui is None:
        import locale
        try:
            loc = locale.getlocale()[0] or ""
        except Exception:
            loc = ""
        langues_ui = [loc]
    for l in langues_ui:
        l = (l or "").lower()
        if l.startswith("fr") or l.startswith("french"):
            return "fr"
        if l:
            return "en"
    return "en"


def cles_manquantes() -> list[str]:
    return [k for k, v in T.items() if not v.get("fr") or not v.get("en")]


def argent(montant, devise: str = "EUR") -> str:
    """Montant dans la présentation de la langue : « 1 234,50 € » / « €1,234.50 »."""
    if montant is None or montant == "":
        return ""
    try:
        m = float(montant)
    except (TypeError, ValueError):
        return str(montant)
    symbole = {"EUR": "€", "USD": "$", "GBP": "£", "CHF": "CHF"}.get(devise or "EUR", devise)
    if _langue == "fr":
        texte = f"{m:,.2f}".replace(",", " ").replace(".", ",")
        if texte.endswith(",00"):
            texte = texte[:-3]
        return f"{texte} {symbole}"
    texte = f"{m:,.2f}"
    if texte.endswith(".00"):
        texte = texte[:-3]
    return f"{symbole}{texte}" if len(symbole) == 1 else f"{texte} {symbole}"


def nombre(v, decimales: int = 1) -> str:
    if v is None or v == "":
        return ""
    texte = f"{float(v):.{decimales}f}"
    if "." in texte:
        texte = texte.rstrip("0").rstrip(".")
    return texte.replace(".", ",") if _langue == "fr" else texte


def date_affichee(iso: str | None) -> str:
    """« 2026-10-26 » -> « 26/10/2026 » (fr) ou « 2026-10-26 » (en, ISO)."""
    if not iso:
        return ""
    iso = str(iso)[:10]
    if _langue == "fr" and len(iso) == 10 and iso[4] == "-":
        return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"
    return iso
