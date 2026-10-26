# -*- coding: utf-8 -*-
"""Affichage des règles du dossier « Le vin » : le pourquoi, la confiance, les
sources, les conventions du dossier, l'échelle illustrée des niveaux.

Tout résultat d'une règle s'affiche avec son explication et ses sources ; une
règle de source « DOSSIER » est signalée comme convention modifiable.
"""
from __future__ import annotations

import html
from datetime import date

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QSizePolicy, QTextBrowser, QVBoxLayout,
                             QWidget)

from .. import style
from ..i18n import langue, lib, nombre, tr
from ..regles import service as r_service
from ..regles.anglais import en
from ..regles.jeu import jeu

e = html.escape


def sources_html(ids) -> str:
    """Liste des sources (titre complet) en petit."""
    j = jeu()
    lignes = []
    for s in ids or []:
        titre = j.source(s).get("titre", s)
        lignes.append(f"<li><b>{e(s)}</b> — {e(titre)}</li>")
    return f"<ul style='margin:0 0 0 12px; font-size:small'>{''.join(lignes)}</ul>" if lignes else ""


def confiance_html(est) -> str:
    morceaux = []
    if getattr(est, "confiance", None):
        morceaux.append(e(lib("confiance", est.confiance)))
    if getattr(est, "convention", False):
        morceaux.append(f"<i>{e(tr('regles.convention'))}</i>")
    return " · ".join(morceaux)


def estimation_html(est, titre: str | None = None, sources: bool = True) -> str:
    """Bloc HTML : titre, explication, détail du calcul, confiance, sources."""
    lg = langue()
    morceaux = []
    if titre:
        morceaux.append(f"<p style='margin:6px 0 2px 0'><b>{e(titre)}</b></p>")
    if est.explication(lg):
        morceaux.append(f"<p style='margin:0'>{e(est.explication(lg))}</p>")
    for d in est.details(lg):
        morceaux.append(f"<p style='margin:0 0 0 10px'>• {e(d)}</p>")
    c = confiance_html(est)
    if c:
        morceaux.append(f"<p style='margin:2px 0; color:{style.GRIS}'>{c}</p>")
    if sources and est.sources:
        morceaux.append(sources_html(est.sources))
    return "".join(morceaux)


class DialoguePourquoi(QDialog):
    """Le « pourquoi » d'un résultat, avec toutes ses sources."""

    def __init__(self, titre: str, contenu_html: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titre)
        self.resize(720, 560)
        l = QVBoxLayout(self)
        self.texte = QTextBrowser()
        self.texte.setOpenExternalLinks(True)
        self.texte.setHtml(contenu_html)
        l.addWidget(self.texte)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        b.button(QDialogButtonBox.StandardButton.Close).setText(tr("regles.fermer"))
        b.rejected.connect(self.reject)
        l.addWidget(b)


# ---------------------------------------------------------------------------- textes du service
def texte_temperature(s) -> str:
    v = s.temperature.valeur
    m = s.temperature.marge.get("c")
    return tr("regles.temperature_val", tmin=nombre(v["min_c"]), tmax=nombre(v["max_c"]),
              marge=nombre(m) if m is not None else "?", verser=nombre(s.a_verser_c))


def texte_sortie(s) -> str:
    v = s.sortie.valeur
    cave, piece = nombre(v["cave_c"]), nombre(v["piece_c"])
    if v["action"] == "sortir":
        return tr("regles.sortir", duree=r_service.duree(v["minutes"], langue()), cave=cave, piece=piece,
                  cible=nombre(v["cible_c"]))
    if v["action"] == "rafraichir":
        return tr("regles.rafraichir", frigo=r_service.duree(v["frigo_min"], langue()),
                  seau=r_service.duree(v["seau_min"], langue()), cave=cave, cible=nombre(v["cible_c"]))
    if v["action"] == "piece_trop_froide":
        return tr("regles.piece_froide", piece=piece, cible=nombre(v["cible_c"]))
    return tr("regles.deja_a_temperature", cave=cave)


def texte_ouverte(est) -> str:
    v = est.valeur
    lieu = v.get("lieu") or ""
    lieu = lieu if langue() == "fr" else en(lieu)
    if v.get("jours"):
        a, b = v["jours"]
        return tr("regles.ouverte_jours", a=a, b=b, mode=lib("conservation_ouverte", v["mode"]), lieu=lieu)
    texte = v.get("texte") or ""
    return tr("regles.ouverte_texte", texte=texte if langue() == "fr" else en(texte),
              mode=lib("conservation_ouverte", v["mode"]), lieu=lieu)


def texte_fenetre(f) -> str:
    """« 2026 → apogée 2033-2041 (pic 2037) → 2048 »."""
    a = f.annees if hasattr(f, "annees") else f
    morceaux = []
    if a.get("debut") is not None:
        morceaux.append(tr("regles.f_des", annee=a["debut"]))
    if a.get("apogee_debut") is not None or a.get("apogee_fin") is not None:
        morceaux.append(tr("regles.f_apogee", a=a.get("apogee_debut") or "?", b=a.get("apogee_fin") or "?"))
    pic = getattr(f, "pic", None)
    if pic:
        morceaux.append(tr("regles.f_pic", annee=pic))
    if a.get("fin") is not None:
        morceaux.append(tr("regles.f_jusqu", annee=a["fin"]))
    else:
        morceaux.append(tr("regles.f_sans_fin"))
    return " · ".join(morceaux)


def age_du_vin(millesime) -> int | None:
    return date.today().year - int(millesime) if millesime else None


# ---------------------------------------------------------------------------- niveaux illustrés
#: position schématique des niveaux bordelais sur le col (0 = haut du goulot, 1 = bas d'épaule)
POSITIONS = {"IN": 0.10, "BN": 0.24, "VTS": 0.36, "TS": 0.46, "HS": 0.58, "MS": 0.72, "LS": 0.86, "BLS": 0.97}


class IllustrationNiveaux(QWidget):
    """Échelle illustrée : le col d'une bouteille bordelaise et les huit niveaux
    des ventes aux enchères ; le niveau choisi est mis en évidence (positions
    schématiques, comme la figure du dossier)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.code: str | None = None
        self.setMinimumSize(300, 230)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def definir(self, code: str | None) -> None:
        self.code = code
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        h = self.height() - 10
        x0, haut = 20.0, 5.0
        col, corps = 26.0, 70.0
        # silhouette : goulot, épaule, corps
        chemin = QPainterPath()
        chemin.moveTo(x0 + (corps - col) / 2, haut)
        chemin.lineTo(x0 + (corps - col) / 2, haut + h * 0.40)
        chemin.cubicTo(x0 + (corps - col) / 2, haut + h * 0.62, x0, haut + h * 0.66, x0, haut + h * 0.86)
        chemin.lineTo(x0, haut + h)
        chemin.lineTo(x0 + corps, haut + h)
        chemin.lineTo(x0 + corps, haut + h * 0.86)
        chemin.cubicTo(x0 + corps, haut + h * 0.66, x0 + (corps + col) / 2, haut + h * 0.62,
                       x0 + (corps + col) / 2, haut + h * 0.40)
        chemin.lineTo(x0 + (corps + col) / 2, haut)
        if self.code in POSITIONS:
            y = haut + POSITIONS[self.code] * h * 0.9
            p.save()
            p.setClipPath(chemin)
            p.fillRect(QRectF(x0 - 2, y, corps + 4, h), QColor(style.BORDEAUX))
            p.restore()
        p.setPen(QPen(QColor(style.ENCRE), 1.5))
        p.drawPath(chemin)
        police = QFont(style.FAMILLE)
        police.setPixelSize(11)
        p.setFont(police)
        for code, pos in POSITIONS.items():
            y = haut + pos * h * 0.9
            choisi = code == self.code
            p.setPen(QPen(QColor(style.BORDEAUX if choisi else style.GRIS), 2 if choisi else 1))
            p.drawLine(int(x0 + corps + 4), int(y), int(x0 + corps + 18), int(y))
            police.setBold(choisi)
            p.setFont(police)
            p.setPen(QColor(style.ENCRE))
            p.drawText(QRectF(x0 + corps + 22, y - 8, self.width() - corps - 46, 16),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       f"{code} — {lib('niveau', code)}")
        p.end()


# ---------------------------------------------------------------------------- panneau de la fiche
def _lien(cle: str) -> str:
    return f" <a href='pourquoi:{cle}'>{e(tr('regles.pourquoi'))}</a>"


def panneau_html(cave, vin_id: int) -> str:
    """Ce que les règles du dossier disent de ce vin : style, fenêtre, service,
    bouteille ouverte, accords, bouchon ; chaque bloc a son lien « pourquoi ? »."""
    from ..regles import accords as r_accords
    from ..regles import conservation as r_conservation
    lg = langue()
    v = cave.vin_pour_regles(vin_id)
    f = cave.fenetre_calculee(vin_id)
    if v is None or f is None:
        return f"<p>{e(tr('regles.non_classe'))}</p>"
    cl = f.classement
    lignes = []
    raison = cl.raisons(lg)[-1] if cl.raisons(lg) else ""
    style_txt = e(cl.nom(lg)) + (f" <i>({e(tr('regles.style_impose'))})</i>" if cl.impose else "")
    lignes.append((tr("regles.style"), f"{style_txt} — <span style='color:{style.GRIS}'>{e(raison)}</span>"
                   + _lien("style")))
    if f.base:
        fen = e(texte_fenetre(f)) + f" — {e(lib('niveau_garde', f.niveau))}, {e(f.modele)}, " \
              f"± {e(nombre(f.marge_ans))} {e(tr('regles.ans'))}"
    else:
        fen = e(tr("regles.sans_base"))
    lignes.append((tr("regles.fenetre_calculee"), fen + _lien("fenetre")))
    eff = cave.fenetre_effective(vin_id)
    if eff:
        from ..regles import garde as r_garde
        ph = r_garde.phase(eff, date.today().year)
        al = r_garde.alerte(eff, date.today().year)
        lignes.append((tr("regles.aujourdhui"), (e(lib("phase", ph)) if ph else "") +
                       (f" — <b>{e(lib('alerte', al))}</b>" if al else "") +
                       f" <span style='color:{style.GRIS}'>({e(lib('source_fenetre', eff['source']))})</span>"))
    s = cave.service_du_vin(vin_id)
    if s:
        lignes.append((tr("regles.temperature"), e(texte_temperature(s)) + _lien("service")))
        lignes.append((tr("regles.sortie"), e(texte_sortie(s))))
        if s.carafes:
            lignes.append((tr("regles.carafe"), e(r_service.texte_carafe(s.carafes[0], lg))))
        if s.verres:
            lignes.append((tr("regles.verre"), e(r_service.texte_verre(s.verres[0], lg))))
    o = r_conservation.bouteille_ouverte(v, "bouchon")
    if o:
        lignes.append((tr("regles.ouverte"), e(texte_ouverte(o))))
    plats = r_accords.plats_pour_style(cl.id)
    if plats:
        lignes.append((tr("regles.accords"), e(" ; ".join(p.nom(lg) for p in plats)) + _lien("accords")))
    age = age_du_vin(v.get("millesime"))
    if age is not None and age >= r_conservation.age_controle_bouchon():
        lignes.append((tr("regles.bouchon"), e(tr("regles.bouchon_controle", age=age))))
    corps = "".join(f"<tr><td style='padding:2px 8px 2px 0; color:{style.BORDEAUX}'><b>{e(a)}</b></td>"
                    f"<td style='padding:2px 0'>{b}</td></tr>" for a, b in lignes)
    return f"<table>{corps}</table>"


def pourquoi_html(cave, vin_id: int, sujet: str) -> str:
    """Le détail d'un bloc du panneau, avec toutes ses sources."""
    from ..regles import accords as r_accords
    lg = langue()
    f = cave.fenetre_calculee(vin_id)
    if f is None:
        return ""
    cl = f.classement
    if sujet == "style":
        morceaux = [f"<h3>{e(cl.nom(lg))}</h3>"] + [f"<p>• {e(r)}</p>" for r in cl.raisons(lg)]
        if cl.impose and cl.automatique:
            nom = cl.automatique["nom_fr"] if lg == "fr" else cl.automatique["nom_en"]
            morceaux.append(f"<p>{e(tr('regles.style_auto', nom=nom))}</p>")
        ex = cl.style.get("exemples", "")
        morceaux.append(f"<p><i>{e(tr('regles.exemples'))}</i> {e(ex if lg == 'fr' else en(ex))}</p>")
        morceaux.append(f"<p style='color:{style.GRIS}'>{e(tr('regles.methode_style'))}</p>")
        return "".join(morceaux)
    if sujet == "fenetre":
        est = f.estimation()
        tete = f"<h3>{e(texte_fenetre(f)) if f.base else e(tr('regles.sans_base'))}</h3>"
        marges = [tr("regles.marge_fenetre", m=nombre(f.marge_ans) if f.marge_ans is not None else "?")]
        if f.note:
            marges.append(tr("regles.marge_millesime", m=nombre(round(f.marge_millesime, 2), 2)))
        if f.facteur_cave != 1.0:
            marges.append(tr("regles.marge_cave"))
        return tete + estimation_html(est) + f"<p><b>{e(tr('regles.marges'))}</b> {e(' ; '.join(marges))}</p>"
    if sujet == "service":
        s = cave.service_du_vin(vin_id)
        if s is None:
            return ""
        morceaux = [estimation_html(s.temperature, texte_temperature(s))]
        for a in s.ajustements:
            morceaux.append(estimation_html(a, None))
        morceaux.append(estimation_html(s.sortie, texte_sortie(s)))
        for c in s.carafes:
            morceaux.append(estimation_html(c, r_service.texte_carafe(c, lg)))
        for v_ in s.verres:
            morceaux.append(estimation_html(v_, r_service.texte_verre(v_, lg)))
        return "".join(morceaux)
    if sujet == "accords":
        morceaux = []
        for p in r_accords.plats_pour_style(cl.id):
            morceaux.append(estimation_html(p.estimation(), p.nom(lg)))
            preuves = p.regle.get("preuves_corpus") or []
            if preuves:
                morceaux.append("<ul style='font-size:small'>" + "".join(
                    f"<li>« {e(x['phrase'][:300])} » — <a href='{e(x['url'])}'>{e(x['article'])}</a></li>"
                    for x in preuves[:3]) + "</ul>")
        return "".join(morceaux)
    return ""


# ---------------------------------------------------------------------------- les règles, en entier
def regles_html() -> str:
    """Tout ce que l'application tient du dossier : origine, audit, conseils de
    cave, échelle des niveaux, principes d'accords, accords difficiles, sources."""
    from ..regles import accords as r_accords
    from ..regles import conservation as r_conservation
    j = jeu()
    lg = langue()
    m = [f"<h2>{e(tr('regles.titre_dossier'))}</h2>",
         f"<p>{e(tr('regles.origine', n=j.nombre_regles(), s=len(j.sources), date=j.date_audit or '?'))}</p>",
         f"<p style='color:{style.GRIS}'>{e(tr('regles.conventions'))}</p>",
         f"<h3>{e(tr('regles.cave_ideale'))}</h3>"]
    for est in r_conservation.conseils():
        m.append(estimation_html(est, f"{est.regle} : {r_conservation.texte_valeur(est.regle, est.valeur, lg)}",
                                 sources=False))
    m.append(f"<h3>{e(tr('regles.echelle_niveaux'))}</h3><table>")
    for n in j.niveaux["bordelaise"]:
        m.append(f"<tr><td style='padding:2px 8px 2px 0'><b>{e(n['code'])}</b> — "
                 f"{e(n['nom_fr'] if lg == 'fr' else n['nom_en'])}</td>"
                 f"<td>{e(n['explication_fr'] if lg == 'fr' else en(n['explication_fr']))}</td></tr>")
    for n in j.niveaux["bourguignonne_cm"]:
        m.append(f"<tr><td style='padding:2px 8px 2px 0'><b>≤ {e(nombre(n['cm_max']))} cm</b></td>"
                 f"<td>{e(n['explication_fr'] if lg == 'fr' else en(n['explication_fr']))}</td></tr>")
    m.append("</table>")
    m.append(f"<h3>{e(tr('regles.principes'))}</h3>")
    for est in r_accords.principes():
        m.append(estimation_html(est, None, sources=False))
    m.append(f"<h3>{e(tr('regles.difficiles'))}</h3>")
    for d in j.accords["accords_difficiles"]:
        m.append(f"<p><b>{e(d['fr'] if lg == 'fr' else en(d['fr']))}</b> — "
                 f"{e(d['pourquoi_fr'] if lg == 'fr' else en(d['pourquoi_fr']))}</p>")
    m.append(f"<h3>{e(tr('regles.sources'))}</h3>")
    m.append(sources_html(sorted(j.sources)))
    return "".join(m)


class DialogueRegles(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("regles.titre_dossier"))
        self.resize(900, 720)
        from PyQt6.QtWidgets import QHBoxLayout
        l = QVBoxLayout(self)
        haut = QHBoxLayout()
        self.illustration = IllustrationNiveaux()
        self.illustration.setFixedWidth(320)
        self.illustration.definir("TS")
        haut.addWidget(self.illustration)
        self.texte = QTextBrowser()
        self.texte.setHtml(regles_html())
        haut.addWidget(self.texte, 1)
        l.addLayout(haut, 1)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        b.button(QDialogButtonBox.StandardButton.Close).setText(tr("regles.fermer"))
        b.rejected.connect(self.reject)
        l.addWidget(b)
