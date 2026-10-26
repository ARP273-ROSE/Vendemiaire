# -*- coding: utf-8 -*-
"""Rapport d'assurance / d'inventaire (PDF, format maison).

Ce qu'un assureur, une maison de ventes ou un garde-meubles demande (cahier
des charges, « maisons de ventes, assureurs ») : la liste bouteille par
bouteille, la photo de l'étiquette, l'état (étiquette, capsule, bouchon), le
NIVEAU et ce qu'il signifie pour l'âge du vin (règles du dossier « Le vin »),
la caisse (CBO, complète ou non), la provenance, l'historique de stockage, la
facture, et une valeur DATÉE et SOURCÉE : la dernière valeur saisie pour le
vin dans ce format, sinon le prix d'achat (dit comme tel), sinon « non
évaluée ». Jamais de valeur inventée."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from html import escape
from pathlib import Path

from .. import referentiels
from ..i18n import tr_en
from ..regles import niveaux as r_niveaux
from .carte import date_texte, libelle_format, prix_texte
from .latex import echapper


@dataclass
class BouteilleInv:
    id: int
    format: str
    statut: str
    emplacement: str
    niveau: str | None
    niveau_cm: float | None
    sens_niveau: str               # verdict lisible
    etat_etiquette: str | None
    etat_capsule: str | None
    etat_bouchon: str | None
    caisse: str | None
    caisse_complete: int | None
    caisse_ref: str | None
    provenance: str
    historique: str
    facture: str
    prix_achat: float | None
    date_achat: str | None
    lieu_achat: str
    valeur: float | None
    valeur_date: str | None
    valeur_source: str            # « prix d'achat » ou la source saisie
    valeur_url: str
    code: str


@dataclass
class VinInv:
    id: int
    nom: str
    appellation: str
    region: str
    pays: str
    couleur: str
    millesime: int | None
    photo: Path | None
    bouteilles: list[BouteilleInv] = field(default_factory=list)

    @property
    def total(self) -> float:
        return sum(b.valeur or 0 for b in self.bouteilles)


@dataclass
class Inventaire:
    langue: str
    date: str
    vins: list[VinInv]

    @property
    def bouteilles(self) -> int:
        return sum(len(v.bouteilles) for v in self.vins)

    @property
    def total(self) -> float:
        return sum(v.total for v in self.vins)

    def compte(self, quoi: str) -> int:
        """« estimee » (valeur saisie), « achat » (prix d'achat), « aucune »."""
        n = 0
        for v in self.vins:
            for b in v.bouteilles:
                genre = "aucune" if b.valeur is None else ("achat" if b.valeur_source == "__achat__" else "estimee")
                n += genre == quoi
        return n


def construire(cave, langue: str = "fr", statuts=("en_cave",), vin_ids=None) -> Inventaire:
    lib = lambda enum, code: referentiels.libelle(enum, code, langue) if code else ""  # noqa: E731
    valeurs = {}
    for r in cave.base.lire("SELECT * FROM valeur ORDER BY date, id"):
        valeurs[(r["vin_id"], r["format"])] = dict(r)          # la dernière l'emporte
    q = f"SELECT * FROM bouteille WHERE statut IN ({','.join('?' * len(statuts))})"
    params = list(statuts)
    if vin_ids is not None:
        vin_ids = list(vin_ids) or [-1]
        q += f" AND vin_id IN ({','.join('?' * len(vin_ids))})"
        params += vin_ids
    par_vin: dict[int, list] = {}
    for b in cave.base.lire(q + " ORDER BY vin_id, id", params):
        par_vin.setdefault(b["vin_id"], []).append(dict(b))
    vins = []
    annee = date.today().year
    chemins: dict = {}
    for vid, bs in par_vin.items():
        v = cave.vin(vid)
        if v is None:
            continue
        v = dict(v)
        nom = cave.nom_vin(vid)
        vi = VinInv(vid, nom, v.get("appellation") or "", v.get("region") or "", v.get("pays") or "",
                    lib("couleur", v.get("couleur")), v.get("millesime"), cave.image_principale(vid))
        age = annee - v["millesime"] if v.get("millesime") else None
        for b in bs:
            if b["emplacement_id"] not in chemins:
                chemins[b["emplacement_id"]] = " › ".join(cave.chemin_emplacement(b["emplacement_id"]))
            emp = chemins[b["emplacement_id"]]
            if b.get("rangee"):
                emp += f" ({tr_en(langue, 'assur.case', r=b['rangee'], c=b.get('colonne') or '?')})"
            sens = ""
            try:
                e = r_niveaux.sens_niveau(b.get("niveau"), age, b.get("niveau_cm"))
                if e is not None:
                    sens = lib("verdict_niveau", e.valeur.get("verdict"))
            except Exception:
                sens = ""
            val = valeurs.get((vid, b["format"]))
            if val is not None:
                montant, d_val, src, url = val["montant"], val["date"], val["source"], val.get("url") or ""
            elif b.get("prix_achat") is not None:
                montant, d_val, src, url = b["prix_achat"], b.get("date_achat") or b.get("date_entree"), "__achat__", ""
            else:
                montant, d_val, src, url = None, None, "", ""
            vi.bouteilles.append(BouteilleInv(
                b["id"], b["format"], b["statut"], emp, b.get("niveau"), b.get("niveau_cm"), sens,
                b.get("etat_etiquette"), b.get("etat_capsule"), b.get("etat_bouchon"), b.get("caisse"),
                b.get("caisse_complete"), b.get("caisse_ref"), b.get("provenance") or "",
                b.get("historique_stockage") or "", b.get("facture") or "", b.get("prix_achat"),
                b.get("date_achat"), b.get("lieu_achat") or "", montant, d_val, src, url, b.get("code_interne") or ""))
        vins.append(vi)
    vins.sort(key=lambda v: (v.pays, v.region, v.appellation, v.nom.lower(), v.millesime or 0))
    return Inventaire(langue, date.today().isoformat(), vins)


def _source(b: BouteilleInv, lg: str) -> str:
    if b.valeur is None:
        return tr_en(lg, "assur.non_evaluee")
    src = tr_en(lg, "assur.prix_achat") if b.valeur_source == "__achat__" else b.valeur_source
    d = date_texte(b.valeur_date, lg) if b.valeur_date else tr_en(lg, "assur.date_inconnue")
    return f"{src}, {d}"


def _etat(b: BouteilleInv, lg: str) -> list[str]:
    lib = lambda enum, code: referentiels.libelle(enum, code, lg) if code else ""  # noqa: E731
    e = []
    if b.etat_etiquette:
        e.append(f"{tr_en(lg, 'assur.etiquette')} : {lib('etat_etiquette', b.etat_etiquette)}")
    if b.etat_capsule:
        e.append(f"{tr_en(lg, 'assur.capsule')} : {lib('etat_capsule', b.etat_capsule)}")
    if b.etat_bouchon:
        e.append(f"{tr_en(lg, 'assur.bouchon')} : {lib('etat_bouchon', b.etat_bouchon)}")
    return e


def _niveau(b: BouteilleInv, lg: str) -> str:
    if b.niveau:
        t = f"{b.niveau} — {referentiels.libelle('niveau', b.niveau, lg)}"
    elif b.niveau_cm:
        t = f"{b.niveau_cm:g} cm"
    else:
        return ""
    return t + (f" ({b.sens_niveau})" if b.sens_niveau else "")


def _caisse(b: BouteilleInv, lg: str) -> str:
    if not b.caisse or b.caisse == "aucune":
        return ""
    t = referentiels.libelle("caisse", b.caisse, lg)
    if b.caisse_complete is not None:
        t += ", " + tr_en(lg, "assur.complete" if b.caisse_complete else "assur.incomplete")
    if b.caisse_ref:
        t += f" [{b.caisse_ref}]"
    return t


# ---------------------------------------------------------------------------- LaTeX
def latex(inv: Inventaire, titre: str = "", unicode: bool = True) -> tuple[str, dict]:
    from .. import logo
    from . import maison
    lg = inv.langue
    titre = titre or tr_en(lg, "assur.titre")
    annexes = {}
    if logo.png(512).exists():
        annexes["logo.png"] = logo.png(512)
    t = [maison.preambule(tr_en(lg, "assur.titre_court"), lg, unicode), r"\begin{document}",
         maison.page_de_garde(titre, tr_en(lg, "assur.sous_titre"), date_texte(inv.date, lg), "logo.png" in annexes)]
    t += [r"\section{" + echapper(tr_en(lg, "assur.resume")) + "}",
          r"\begin{cadrebox}{" + echapper(tr_en(lg, "assur.chiffres")) + "}",
          r"\begin{tabularx}{\linewidth}{@{}Xr@{}}",
          echapper(tr_en(lg, "assur.n_vins")) + rf" & \textbf{{{len(inv.vins)}}} \\",
          echapper(tr_en(lg, "assur.n_bouteilles")) + rf" & \textbf{{{inv.bouteilles}}} \\",
          echapper(tr_en(lg, "assur.total")) + rf" & \textbf{{{echapper(prix_texte(round(inv.total, 2), lg))}}} \\",
          echapper(tr_en(lg, "assur.dont_estimees")) + rf" & {inv.compte('estimee')} \\",
          echapper(tr_en(lg, "assur.dont_achat")) + rf" & {inv.compte('achat')} \\",
          echapper(tr_en(lg, "assur.dont_aucune")) + rf" & {inv.compte('aucune')} \\",
          r"\end{tabularx}", r"\end{cadrebox}",
          echapper(tr_en(lg, "assur.methode")), ""]
    for v in inv.vins:
        t.append(r"\subsection{" + echapper(v.nom) + "}")
        infos = " · ".join(x for x in (v.appellation, v.region, v.pays, v.couleur) if x)
        if v.photo is not None and v.photo.suffix.lower() in (".jpg", ".jpeg", ".png"):
            nom = f"photo{v.id}{v.photo.suffix.lower()}"
            annexes[nom] = v.photo
            t.append(r"\begin{minipage}[t]{0.22\linewidth}\vspace{0pt}\includegraphics[width=\linewidth,height=42mm,keepaspectratio]{"
                     + nom + r"}\end{minipage}\hfill\begin{minipage}[t]{0.75\linewidth}\vspace{0pt}")
        else:
            t.append(r"\begin{minipage}[t]{\linewidth}")
        t.append(r"{\color{summit}" + echapper(infos) + r"}\par")
        t.append(echapper(tr_en(lg, "assur.n_bouteilles")) + f" : {len(v.bouteilles)} — "
                 + echapper(tr_en(lg, "assur.total")) + " : " + r"\textbf{" + echapper(prix_texte(round(v.total, 2), lg)) + "}")
        t.append(r"\end{minipage}\par\smallskip")
        t += [r"{\footnotesize\begin{xltabular}{\linewidth}{@{}>{\raggedright\arraybackslash}p{0.22\linewidth}"
              r">{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.17\linewidth}"
              r">{\raggedleft\arraybackslash}p{0.19\linewidth}@{}}",
              r"\toprule " + " & ".join(r"\textbf{" + echapper(tr_en(lg, k)) + "}" for k in
                                        ("assur.col_emplacement", "assur.col_etat", "assur.col_achat", "assur.col_valeur"))
              + r" \\ \midrule \endhead"]
        for b in v.bouteilles:
            emp = echapper(b.emplacement or "—") + r"\newline " + echapper(libelle_format(b.format, lg))
            if b.statut != "en_cave":
                emp += r"\newline\textit{" + echapper(referentiels.libelle("statut", b.statut, lg)) + "}"
            if b.code:
                emp += r"\newline{\color{summit}\texttt{" + echapper(b.code) + "}}"
            etat = [_niveau(b, lg)] + _etat(b, lg) + [_caisse(b, lg)]
            for cle, val in (("assur.provenance", b.provenance), ("assur.historique", b.historique),
                             ("assur.facture", b.facture)):
                if val:
                    etat.append(f"{tr_en(lg, cle)} : {val}")
            achat = " · ".join(x for x in (prix_texte(b.prix_achat, lg), date_texte(b.date_achat, lg) if b.date_achat else "",
                                           b.lieu_achat) if x)
            valeur = (r"\textbf{" + echapper(prix_texte(b.valeur, lg)) + r"}\newline " if b.valeur is not None else "") \
                + r"{\color{summit}" + echapper(_source(b, lg)) + "}"
            t.append(emp + " & " + r"\newline ".join(echapper(x) for x in etat if x) + " & " + echapper(achat or "—")
                     + " & " + valeur + r" \\ \midrule[0.2pt]")
        t.append(r"\bottomrule\end{xltabular}}")
    t += [r"\section{" + echapper(tr_en(lg, "assur.attestation")) + "}", echapper(tr_en(lg, "assur.attestation_texte")),
          r"\vspace{18mm}", r"\begin{tabularx}{\linewidth}{XX}", echapper(tr_en(lg, "assur.lieu_date")) + r" & "
          + echapper(tr_en(lg, "assur.signature")) + r" \\ \end{tabularx}", r"\end{document}"]
    return "\n".join(t) + "\n", annexes


# ---------------------------------------------------------------------------- HTML (repli et aperçu)
def html(inv: Inventaire, titre: str = "", images: dict | None = None) -> str:
    lg = inv.langue
    e = escape
    titre = titre or tr_en(lg, "assur.titre")
    h = [f"<html><head><meta charset='utf-8'><title>{e(titre)}</title><style>"
         "body{font-family:'Latin Modern Roman',Georgia,serif;color:#1F2430;max-width:900px;margin:20px auto;padding:0 16px}"
         "h1{font-family:Helvetica,Arial,sans-serif;color:#1B2A4A} h2{font-family:Helvetica,Arial,sans-serif;color:#1C6DB4;"
         "border-bottom:2px solid #9DC0E0} h3{font-family:Helvetica,Arial,sans-serif;color:#B5382B;margin-bottom:2px}"
         "table{border-collapse:collapse;width:100%;font-size:9pt} td,th{border-bottom:1px solid #ccc;padding:3px;vertical-align:top;text-align:left}"
         ".doux{color:#6B7A8F} .cadre{background:#E6F0F8;border:1px solid #1C6DB4;padding:8px}</style></head><body>",
         f"<h1>{e(titre)}</h1><p class='doux'>{e(tr_en(lg, 'assur.sous_titre'))} — {e(date_texte(inv.date, lg))}</p>",
         f"<h2>{e(tr_en(lg, 'assur.resume'))}</h2><div class='cadre'><table>"]
    for cle, val in (("assur.n_vins", len(inv.vins)), ("assur.n_bouteilles", inv.bouteilles),
                     ("assur.total", prix_texte(round(inv.total, 2), lg)), ("assur.dont_estimees", inv.compte("estimee")),
                     ("assur.dont_achat", inv.compte("achat")), ("assur.dont_aucune", inv.compte("aucune"))):
        h.append(f"<tr><td>{e(tr_en(lg, cle))}</td><td align='right'><b>{e(str(val))}</b></td></tr>")
    h.append(f"</table></div><p>{e(tr_en(lg, 'assur.methode'))}</p>")
    for v in inv.vins:
        h.append(f"<h3>{e(v.nom)}</h3>")
        photo = ""
        if v.photo is not None and images is not None:
            images[f"photo{v.id}"] = v.photo
            photo = f"<img src='photo{v.id}' width='110'>"
        h.append(f"<table><tr><td width='120'>{photo}</td><td><span class='doux'>"
                 f"{e(' · '.join(x for x in (v.appellation, v.region, v.pays, v.couleur) if x))}</span><br>"
                 f"{e(tr_en(lg, 'assur.total'))} : <b>{e(prix_texte(round(v.total, 2), lg))}</b></td></tr></table>")
        h.append("<table><tr>" + "".join(f"<th>{e(tr_en(lg, k))}</th>" for k in
                                         ("assur.col_emplacement", "assur.col_etat", "assur.col_achat", "assur.col_valeur"))
                 + "</tr>")
        for b in v.bouteilles:
            etat = [_niveau(b, lg)] + _etat(b, lg) + [_caisse(b, lg)]
            for cle, val in (("assur.provenance", b.provenance), ("assur.historique", b.historique),
                             ("assur.facture", b.facture)):
                if val:
                    etat.append(f"{tr_en(lg, cle)} : {val}")
            achat = " · ".join(x for x in (prix_texte(b.prix_achat, lg), date_texte(b.date_achat, lg) if b.date_achat else "",
                                           b.lieu_achat) if x)
            h.append(f"<tr><td>{e(b.emplacement or '—')}<br>{e(libelle_format(b.format, lg))}"
                     f"<br><span class='doux'>{e(b.code)}</span></td><td>{'<br>'.join(e(x) for x in etat if x)}</td>"
                     f"<td>{e(achat or '—')}</td><td><b>{e(prix_texte(b.valeur, lg))}</b><br>"
                     f"<span class='doux'>{e(_source(b, lg))}</span></td></tr>")
        h.append("</table>")
    h.append(f"<h2>{e(tr_en(lg, 'assur.attestation'))}</h2><p>{e(tr_en(lg, 'assur.attestation_texte'))}</p>"
             "</body></html>")
    return "\n".join(h)


def ecrire_pdf(inv: Inventaire, chemin, titre: str = "", moteur=None, forcer_qt: bool = False) -> str:
    from . import latex as mod_latex
    if not forcer_qt:
        m = moteur or mod_latex.trouver_moteur()
        if m is not None:
            src, annexes = latex(inv, titre, m.unicode)
            return mod_latex.compiler(src, chemin, annexes, moteur=m).moteur
    from .qt_pdf import html_vers_pdf
    images: dict = {}
    html_vers_pdf(html(inv, titre, images), chemin, images)
    return "qt"
