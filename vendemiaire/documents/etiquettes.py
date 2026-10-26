# -*- coding: utf-8 -*-
"""Planche d'étiquettes de casier à code QR (PDF A4, vectoriel, par Qt).

Une étiquette par bouteille : code QR du code interne, producteur, cuvée,
millésime, emplacement (casier, rangée, colonne) et le code en clair (lisible
si le QR s'abîme). Scanner l'étiquette retrouve la bouteille (Cave ›
Scanner une bouteille) pour la sortir en un geste.

Gabarits d'étiquettes autocollantes A4 courants (dimensions publiées par les
fabricants, modifiables) : 3 × 8 de 70 × 37 mm (sans marge latérale) et
3 × 7 de 63,5 × 38,1 mm."""
from __future__ import annotations

from dataclasses import dataclass

from .. import codes, referentiels


@dataclass(frozen=True)
class Gabarit:
    code: str
    colonnes: int
    rangees: int
    largeur_mm: float
    hauteur_mm: float
    marge_haut_mm: float
    marge_gauche_mm: float
    pas_x_mm: float
    pas_y_mm: float


GABARITS = {
    "3x8": Gabarit("3x8", 3, 8, 70.0, 37.0, 0.5, 0.0, 70.0, 37.0),
    "3x7": Gabarit("3x7", 3, 7, 63.5, 38.1, 15.15, 7.2, 66.0, 38.1),
}


def bouteilles_pour_etiquettes(cave, vin_id: int | None = None, casier_id: int | None = None,
                               ids: list[int] | None = None) -> list[dict]:
    q = ("SELECT b.id, b.code_interne, b.rangee, b.colonne, b.emplacement_id, b.format, b.vin_id "
         "FROM bouteille b WHERE b.statut='en_cave'")
    p: list = []
    if ids is not None:
        q += f" AND b.id IN ({','.join('?' * len(ids)) or 'NULL'})"
        p += list(ids)
    if vin_id is not None:
        q += " AND b.vin_id=?"
        p.append(vin_id)
    if casier_id is not None:
        q += " AND b.emplacement_id=?"
        p.append(casier_id)
    q += " ORDER BY b.emplacement_id, b.rangee, b.colonne, b.vin_id, b.id"
    sortie = []
    noms = {}
    for b in cave.base.lire(q, p):
        b = dict(b)
        if not b["code_interne"]:
            continue
        if b["vin_id"] not in noms:
            v = cave.vin_pour_regles(b["vin_id"]) or {}
            noms[b["vin_id"]] = v
        v = noms[b["vin_id"]]
        b["producteur"] = v.get("producteur") or ""
        b["cuvee"] = " ".join(x for x in (v.get("cuvee"), v.get("appellation")) if x)
        b["millesime"] = v.get("millesime")
        chemin = cave.chemin_emplacement(b["emplacement_id"])
        b["lieu"] = (chemin[-1] if chemin else "") + (f" · {b['rangee']}-{b['colonne']}" if b.get("rangee") else "")
        sortie.append(b)
    return sortie


def ecrire_planche(bouteilles: list[dict], chemin, gabarit: str = "3x8", langue: str = "fr",
                   depart: int = 0) -> int:
    """PDF des étiquettes ; `depart` : nombre de cases déjà utilisées sur la
    première planche (pour finir une planche entamée). Renvoie le nombre de pages."""
    from PyQt6.QtCore import QMarginsF, QRectF, Qt
    from PyQt6.QtGui import QColor, QFont, QPageLayout, QPageSize, QPainter, QPdfWriter
    g = GABARITS[gabarit]
    w = QPdfWriter(str(chemin))
    w.setResolution(600)
    w.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait,
                                QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter))
    w.setCreator("Vendémiaire")
    mm = 600 / 25.4
    p = QPainter(w)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    par_page = g.colonnes * g.rangees
    pages = 1
    case = depart
    for b in bouteilles:
        if case >= par_page:
            w.newPage()
            pages += 1
            case = 0
        col, ran = case % g.colonnes, case // g.colonnes
        x0 = (g.marge_gauche_mm + col * g.pas_x_mm) * mm
        y0 = (g.marge_haut_mm + ran * g.pas_y_mm) * mm
        L, H = g.largeur_mm * mm, g.hauteur_mm * mm
        marge = 3 * mm
        # QR : carré à gauche, marge blanche réglementaire (4 modules) comprise dans le dessin
        m = codes.matrice_qr(b["code_interne"])
        n = len(m) + 8
        cote = H - 2 * marge
        module = cote / n
        qx, qy = x0 + marge, y0 + marge
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#000000"))
        for yy, rangee in enumerate(m):
            for xx, v in enumerate(rangee):
                if v:
                    p.drawRect(QRectF(qx + (xx + 4) * module, qy + (yy + 4) * module, module + 0.5, module + 0.5))
        # texte
        tx = qx + cote + 1.5 * mm
        tl = x0 + L - marge - tx
        p.setPen(QColor("#000000"))
        lignes = [(b["producteur"], 7.5, True), (b["cuvee"], 6.5, False),
                  (str(b["millesime"] or "") + ("  " + referentiels.libelle("format", b["format"], langue)
                                                if b["format"] != "bouteille" else ""), 7.0, True),
                  (b["lieu"], 6.0, False), (b["code_interne"], 6.0, False)]
        y = qy + 0.5 * mm
        for texte, taille, gras in lignes:
            if not texte:
                continue
            f = QFont("Helvetica")
            f.setPointSizeF(taille)
            f.setBold(gras)
            if texte == b["code_interne"]:
                f.setFamily("Courier")
            p.setFont(f)
            h = p.fontMetrics().height()
            if y + h > y0 + H - marge:
                break
            p.drawText(QRectF(tx, y, tl, h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       p.fontMetrics().elidedText(texte, Qt.TextElideMode.ElideRight, int(tl)))
            y += h * 1.05
        case += 1
    p.end()
    return pages
