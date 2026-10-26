# -*- coding: utf-8 -*-
"""Préambule « format maison » des PDF LaTeX : article 11 pt, Latin Modern,
titres sans empattement colorés (sections bleu ciel #1C6DB4, sous-sections
rouge #B5382B), encadrés tcolorbox, icônes fontawesome5, titlesec + needspace
contre les titres orphelins, fancyhdr, page de garde. Compatible pdfLaTeX,
XeLaTeX, LuaLaTeX et Tectonic."""
from __future__ import annotations

from .latex import echapper


def preambule(titre_court: str, langue: str = "fr", unicode: bool = True, paysage: bool = False) -> str:
    p = [r"\documentclass[11pt,a4paper]{article}"]
    if unicode:
        p += [r"\usepackage{fontspec}", r"\providecommand{\euro}{€}"]
    else:
        p += [r"\usepackage[T1]{fontenc}", r"\usepackage[utf8]{inputenc}", r"\usepackage{lmodern}",
              r"\usepackage{eurosym}"]
    p += [rf"\usepackage[{'french' if langue == 'fr' else 'british'}]{{babel}}",
          r"\usepackage[a4paper,margin=18mm,headheight=24pt" + (",landscape" if paysage else "") + "]{geometry}",
          r"\usepackage{graphicx}", r"\usepackage[table]{xcolor}", r"\usepackage[most]{tcolorbox}",
          r"\usepackage{booktabs}", r"\usepackage{tabularx}", r"\usepackage{longtable}", r"\usepackage{xltabular}",
          r"\usepackage{array}", r"\usepackage[nobottomtitles*]{titlesec}", r"\usepackage{needspace}",
          r"\usepackage{fancyhdr}", r"\usepackage{fontawesome5}", r"\usepackage{etoolbox}",
          r"\usepackage[hidelinks]{hyperref}",
          r"\definecolor{sky}{HTML}{1C6DB4}", r"\definecolor{skyl}{HTML}{E6F0F8}",
          r"\definecolor{alert}{HTML}{B5382B}", r"\definecolor{alertl}{HTML}{FBE8EA}",
          r"\definecolor{summit}{HTML}{6B7A8F}", r"\definecolor{night}{HTML}{1B2A4A}",
          r"\definecolor{ink}{HTML}{1F2430}", r"\definecolor{or}{HTML}{B8860B}", r"\definecolor{orl}{HTML}{FBF3DC}",
          r"\AtBeginDocument{\color{ink}}",
          r"\titleformat{\section}{\Large\bfseries\sffamily\color{sky}}{}{0em}{}[{\vspace{1pt}\color{sky!35}\titlerule[1.1pt]}]",
          r"\titlespacing*{\section}{0pt}{14pt}{7pt}",
          r"\titleformat{\subsection}{\large\bfseries\sffamily\color{alert}}{}{0em}{}",
          r"\titlespacing*{\subsection}{0pt}{10pt}{4pt}",
          r"\pretocmd{\section}{\Needspace{10\baselineskip}}{}{}",
          r"\pretocmd{\subsection}{\Needspace{9\baselineskip}}{}{}",
          r"\widowpenalty=10000 \clubpenalty=10000 \raggedbottom",
          r"\setlength{\parindent}{0pt}\setlength{\parskip}{3pt}",
          r"\pagestyle{fancy}\fancyhf{}\renewcommand{\headrulewidth}{0.4pt}",
          r"\fancyhead[L]{\sffamily\small\color{night}\textbf{" + echapper(titre_court.upper()) + "}}",
          r"\fancyhead[R]{\sffamily\small\color{summit}VEND\'EMIAIRE}",
          r"\fancyfoot[C]{\sffamily\small\color{summit}\thepage}",
          r"\newtcolorbox{cadrebox}[1]{enhanced,unbreakable,colback=skyl,colframe=sky,coltitle=white,"
          r"fonttitle=\bfseries\sffamily\small,boxrule=0.9pt,arc=2.5pt,title={\faClipboardList~~#1}}",
          r"\newtcolorbox{warnbox}[1]{enhanced,breakable,colback=alertl,colframe=alert,coltitle=white,"
          r"fonttitle=\bfseries\sffamily\small,boxrule=0.9pt,arc=2.5pt,title={\faExclamationTriangle~~#1}}",
          r"\BeforeBeginEnvironment{cadrebox}{\par\Needspace{9\baselineskip}}"]
    return "\n".join(p)


def page_de_garde(titre: str, sous_titre: str, date_txt: str, logo: bool = True) -> str:
    t = [r"\begin{titlepage}\centering\vspace*{30mm}"]
    if logo:
        t.append(r"\includegraphics[width=42mm]{logo.png}\\[12mm]")
    t += [r"{\sffamily\bfseries\fontsize{28}{34}\selectfont\color{night} " + echapper(titre) + r"\par}\vspace{6mm}",
          r"{\sffamily\Large\color{sky} " + echapper(sous_titre) + r"\par}\vspace{14mm}",
          r"{\large\color{summit} " + echapper(date_txt) + r"\par}", r"\vfill",
          r"{\small\color{summit} Vend\'emiaire\par}", r"\end{titlepage}"]
    return "\n".join(t)
