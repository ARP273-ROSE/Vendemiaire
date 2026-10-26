# -*- coding: utf-8 -*-
"""Partage de la cave en LECTURE SEULE : une page HTML autonome (un seul
fichier, photos incluses en vignettes, aucun script, aucun service en ligne)
et son PDF.

Ce qui part et ce qui reste : par défaut, ni prix, ni valeurs, ni
emplacements, ni notes privées (`degustation.privee`) — on les ajoute
explicitement. Ordre : celui de la carte des vins (couleur › pays › région ›
appellation › producteur › millésime)."""
from __future__ import annotations

import base64
from datetime import date
from html import escape
from pathlib import Path

from ..i18n import tr_en
from . import carte as mod_carte
from . import geo


def html(cave, langue: str = "fr", titre: str = "", prix: bool = False, photos: bool = True,
         emplacements: bool = False, notes: bool = True, vin_ids=None, images: dict | None = None) -> str:
    k = mod_carte.construire(cave, {"langue": langue, "accords_auto": False, "cartes": False}, vin_ids)
    e = escape
    titre = titre or tr_en(langue, "partage.titre")
    valeurs = {}
    if prix:
        for r in cave.base.lire("SELECT vin_id, format, montant, date, source FROM valeur ORDER BY date, id"):
            valeurs[(r["vin_id"], r["format"])] = dict(r)
    achats = {}
    if prix:
        for r in cave.base.lire("SELECT vin_id, format, AVG(prix_achat) p FROM bouteille WHERE statut='en_cave' "
                                "AND prix_achat IS NOT NULL GROUP BY vin_id, format"):
            achats[(r["vin_id"], r["format"])] = r["p"]
    publiques = {}
    if notes:
        for r in cave.base.lire("SELECT vin_id, note, echelle, commentaire FROM degustation WHERE privee=0 "
                                "ORDER BY date DESC"):
            publiques.setdefault(r["vin_id"], []).append(dict(r))
    lieux = {}
    if emplacements:
        for r in cave.base.lire("SELECT vin_id, emplacement_id, COUNT(*) n FROM bouteille WHERE statut='en_cave' "
                                "GROUP BY vin_id, emplacement_id"):
            lieux.setdefault(r["vin_id"], []).append(
                (" › ".join(cave.chemin_emplacement(r["emplacement_id"])) or "—", r["n"]))
    h = [f"<!DOCTYPE html><html lang='{langue}'><head><meta charset='utf-8'><meta name='viewport' "
         f"content='width=device-width, initial-scale=1'><title>{e(titre)}</title><style>"
         "body{font-family:Georgia,'EB Garamond',serif;color:#2A1A14;background:#FFFCF5;max-width:820px;margin:20px auto;padding:0 16px}"
         "h1{color:#5E1427;text-align:center;font-weight:normal} h2{color:#5E1427;border-bottom:1px solid #C99A3B;font-weight:normal}"
         "h3{color:#8E2A3D;margin:12px 0 4px 0} table{width:100%;border-collapse:collapse} td{padding:3px 4px;vertical-align:top;"
         "border-bottom:1px solid #EFE6D2} .doux{color:#7D7064;font-size:90%} img{border-radius:3px}</style></head><body>",
         f"<h1>{e(titre)}</h1><p class='doux' style='text-align:center'>"
         f"{e(tr_en(langue, 'partage.sous_titre', n=k.bouteilles, date=mod_carte.date_texte(date.today().isoformat(), langue)))}</p>"]
    for s in k.sections + k.demi + k.grands:
        h.append(f"<h2>{e(mod_carte.titre_section(k, s.cle))}</h2>")
        for p in s.pays:
            for r in p.regions:
                h.append(f"<h3>{e(' — '.join(x for x in (geo.nom_pays(p.nom, langue), mod_carte.nom_region(r.nom, langue)) if x))}</h3><table>")
                for a in r.appellations:
                    for g in a.groupes:
                        for l in g.lignes:
                            vignette = ""
                            if photos:
                                chemin = cave.image_principale(l.vin_id)
                                if chemin is not None:
                                    vignette = _img(chemin, l.vin_id, images)
                            infos = [a.nom] if a.nom else []
                            if l.format != "bouteille":
                                infos.append(mod_carte.libelle_format(l.format, langue))
                            f = cave.fenetre_effective(l.vin_id)
                            if f and (f.get("debut") or f.get("fin")):
                                infos.append(tr_en(langue, "partage.fenetre", debut=f.get("debut") or "…",
                                                   fin=f.get("fin") or "…"))
                            detail = []
                            if prix:
                                v = valeurs.get((l.vin_id, l.format))
                                if (l.vin_id, l.format) in achats:
                                    detail.append(tr_en(langue, "partage.achat",
                                                        prix=mod_carte.prix_texte(round(achats[(l.vin_id, l.format)], 2), langue)))
                                if v:
                                    detail.append(tr_en(langue, "partage.valeur", prix=mod_carte.prix_texte(v["montant"], langue),
                                                        date=mod_carte.date_texte(v["date"], langue), source=v["source"]))
                            for lieu, n in lieux.get(l.vin_id, []):
                                detail.append(f"{lieu} ({n})")
                            for d in publiques.get(l.vin_id, [])[:2]:
                                note = f"{d['note']:g}/{d['echelle']}" if d.get("note") is not None else ""
                                detail.append(" ".join(x for x in (note, d.get("commentaire") or "") if x))
                            h.append(f"<tr><td width='64'>{vignette}</td><td><b>{e(l.producteur or '—')}</b>"
                                     + (f", <i>{e(l.cuvee)}</i>" if l.cuvee else "")
                                     + f"<br><span class='doux'>{e(' · '.join(infos))}</span>"
                                     + "".join(f"<br><span class='doux'>{e(x)}</span>" for x in detail)
                                     + f"</td><td align='right'>{mod_carte._millesime(l, k)}</td>"
                                     f"<td align='right'>{e(tr_en(langue, 'partage.bouteilles', n=l.n))}</td></tr>")
                h.append("</table>")
    h.append(f"<p class='doux'>{e(tr_en(langue, 'partage.pied'))}</p></body></html>")
    return "\n".join(h)


def _img(chemin: Path, vin_id: int, images: dict | None) -> str:
    try:
        from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, Qt
        from PyQt6.QtGui import QImage
        img = QImage(str(chemin))
        if img.isNull():
            return ""
        img = img.scaled(120, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        if images is not None:
            images[f"v{vin_id}"] = img
            return f"<img src='v{vin_id}' width='60'>"
        tampon = QByteArray()
        b = QBuffer(tampon)
        b.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(b, "JPEG", 78)
        return f"<img src='data:image/jpeg;base64,{base64.b64encode(bytes(tampon)).decode('ascii')}' width='60'>"
    except Exception:
        return ""


def ecrire_html(cave, chemin, **options) -> None:
    Path(chemin).write_text(html(cave, **options), encoding="utf-8")


def ecrire_pdf(cave, chemin, **options) -> None:
    from .qt_pdf import html_vers_pdf
    images: dict = {}
    page = html(cave, images=images, **options)
    html_vers_pdf(page, chemin, images)
