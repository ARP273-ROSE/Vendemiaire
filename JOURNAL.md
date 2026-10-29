# Vendémiaire — journal

## 1.0.4 — 2026-10-29 — recherches en ligne sous Windows

- **« Mettre à jour en ligne » (registres INAO / eAmbrosia) et les autres recherches en ligne** passent par la
  cascade de certificats du kit : magasin du système, puis les racines de `certifi` si le système refuse
  une chaîne valide. Sous Windows, data.gouv.fr échouait avec « certificate has expired » alors que son
  certificat était valide.
- `certifi` fait désormais partie des dépendances embarquées (sans lui, le repli n'avait aucune racine).

## 1.0.3 — 2026-10-29 — garde-fous de l'import de tableau

- **Le fichier LWIN de Liv-ex est refusé dans « Fichier › Importer un tableau »** : importé là avec « 1
  bouteille par ligne », chacun de ses vins devenait une bouteille en cave (plus de 100 000). Il est reconnu
  à ses en-têtes (`LWIN` avec `DISPLAY_NAME` ou `PRODUCER_NAME`) et l'appli propose d'ouvrir **Références ›
  Bases de référence**, où il se charge comme base de référence.
- **Confirmation au-delà de 300 bouteilles** : tout import de tableau qui en ajouterait davantage l'annonce
  et demande confirmation (réponse par défaut : non). La sauvegarde « avant-import » reste faite.
- Pour revenir en arrière après un import non voulu : **Fichier › Restaurer une sauvegarde…** et choisir la
  sauvegarde `avant-import` de la date voulue.

## 1.0.2 — 2026-10-28 — identifier toute la cave d'un coup

- **Références › Identifier toute la cave…** (et bouton dans l'onglet Cave) : les candidats de chaque vin
  sans identifiant LWIN (au choix, aussi ceux déjà identifiés) sont calculés en tâche de fond, avec barre de
  progression et annulation, sans rien écrire : copie locale de LWIN avec les registres d'appellations, et
  Wikidata pour les domaines sans candidat si les recherches en ligne sont permises. Un **récapitulatif
  unique** montre une ligne par vin (meilleur candidat, score, raison en bref, deuxième candidat s'il est
  proche) : décisions **sûres cochées d'avance**, douteuses signalées et non cochées, vins sans candidat à
  part ; double-clic = écran d'identification habituel. **Valider la sélection** confirme chaque vin coché
  dans sa propre transaction, sans jamais remplacer une saisie à la main, puis affiche le journal de ce qui
  a été rempli et d'où.
- **Appariement LWIN au format réel du fichier** (mesuré sur une vraie cave) : le climat ou lieu-dit d'un vin
  de Bourgogne est lu dans la colonne `SITE` (il était pris pour l'appellation, et tous les climats d'un
  domaine se valaient) ; « Blanc » ou « Rouge » à la place d'une cuvée ne comptent plus comme cuvée ; un
  domaine écrit dans l'autre ordre (« Domaine de la Source (Paul Verdier) » / « Domaine Paul Verdier
  (Source) ») et un mot à une lettre près (« Clos Marnié » / « Le Clos Marnier ») sont reconnus ; le nom exact
  passe devant le nom augmenté d'un éleveur.
- **Moins de faux positifs** : un autre domaine ou un autre climat divise le score par deux, et un candidat
  n'est plus présélectionné quand le domaine ou la cuvée ne concordent pas nettement, ni quand la cuvée
  cherchée est absente de la base (le village générique d'un domaine n'est pas son premier cru).
- Confirmation d'un identifiant : champs remplis, journal et identifiant dans **une seule transaction**.
- Manuel FR et EN : nouvelle section et captures ; essais du lot (sûres et douteuses, non-écrasement,
  annulation, écran sous Xvfb).

## 1.0.1 — 2026-10-28 — import LWIN validé sur le vrai fichier de Liv-ex

- **Import LWIN** testé sur le vrai fichier téléchargé chez Liv-ex (212 208 vins, environ 25 s) : les cases
  vides y sont écrites « NA » ; elles entraient jusqu'ici dans les noms et la recherche (« NA Schieferkopf »).
  Elles sont maintenant lues comme vides. Les dates de mise à jour, données en numéro de série Excel,
  sont converties en vraies dates.
- Essai ajouté sur le format réel du fichier.

## 1.0.0 — 2026-10-27 — phase 5 : première version publiable

- **Outils embarqués sur les trois systèmes** (kit commun, clé `outils` de `kit.json`) : **Tesseract**
  (conda-forge, modèles `fra` et `eng` de tessdata_fast) pour lire les étiquettes, **Tectonic** (MIT) avec un
  **cache de paquets LaTeX pré-rempli** (cartes des vins, rapport d'assurance, manuel) : PDF soignés **hors
  ligne** ; le cache est recopié dans le profil, jamais écrit dans le dossier d'installation. Essai réel à la
  construction (code QR écrit puis relu, étiquette lue, document compilé sans réseau).
- **Manuel PDF** français et anglais (format maison, 41 et 40 pages, captures réelles de la cave de
  démonstration), régénéré par chaque construction des paquets, ouvert par **Aide › Manuel** (F1).
- **Livre de cave** : photos du moment (le plat, la tablée…) rangées avec chaque ligne.
- **Liste d'achats** (Documents, Ctrl+Maj+L) générée par les seuils de réassort et, au choix, les envies ;
  PDF imprimable et CSV.
- **Alertes de prix** sur la liste d'envies, sans aspirateur : prix vus saisis (source et date obligatoires)
  ou importés (CSV) ; alerte quand un prix récent (90 jours) est au plus le prix maximal (schéma v7 :
  `prix_observe`).
- **Accessibilité au clavier** : Ctrl+1…0 pour les onglets, raccourcis des actions principales, plan des
  casiers au clavier (flèches, Ctrl+flèches, Entrée), focus toujours visible.
- **Grande cave** : 20 000 bouteilles s'ouvrent en ≈ 2 s ; plus aucun gel au-delà de 0,6 s (état de la cave
  mis en cache, fenêtres recalculées seulement si elles changent, onglets rafraîchis à leur ouverture).
- **Cave de démonstration** depuis le menu Aide (autre fenêtre, données séparées).
- **Règles** resynchronisées : porto ruby/LBV → « muté jeune et fruité », tawny/colheita → « muté
  oxydatif », muscat de Rivesaltes → « muté jeune et fruité » (corrigé dans le dossier « Le vin », 69 sources).

## 0.4.0 — 2026-10-26 — phase 4 : documents et statistiques (non publiée)

- **Carte des vins** « de grand restaurant » (`documents/carte.py`, Documents › Carte des vins) : ordre
  classique, BIN, verticales, au verre, demies et grands formats, coups de cœur, menu du soir (accords du
  dossier), petites cartes des régions (Natural Earth, domaine public), index des producteurs ; modèles
  classique, moderne, bistrot ; A4, A5, carte simple ; FR/EN ; cartes enregistrées régénérées d'un clic
  (tables `carte`, `carte_vin`, schéma v6). PDF par LaTeX (Tectonic, XeLaTeX, LuaLaTeX, pdfLaTeX), repli Qt.
- **Rapport d'assurance / d'inventaire** (format maison) : valeur datée et sourcée, niveau et son sens,
  état, caisse, provenance, photo.
- **Statistiques** (onglet) : répartitions, valeur dans le temps, entrées/sorties, rythme, apogée par couleur.
- **Codes QR** (segno) et **lecture à l'image** (zxing-cpp) : planche d'étiquettes de casier, scanner pour
  sortir une bouteille.
- **Imports** Excel (XLSX lu sans dépendance) et Vivino (correspondance proposée, à vérifier sur un vrai
  export) ; **partage** en lecture seule HTML/PDF.
- **Séances de dégustation** (onglet) : verticale, horizontale, à l'aveugle (notes figées après la
  révélation ; table `seance_vin`, `seance.revelee_le`).
- Règles du dossier resynchronisées : champagne sans millésime → « effervescent sans année », banyuls
  rimage / VDN grenat → « muté jeune et fruité » ; rattachement des millésimes lu dans le dossier
  (`rattachement_millesimes.json`) ; 66 sources.

## 0.3.0 — 2026-10-26 — phase 3 : règles du dossier « Le vin » (non publiée)

- **Moteur de règles** `vendemiaire/regles/` : les 194 règles et 62 sources du
  dossier « Le vin » (`data/regles/*.json`) copiées octet pour octet avec leur
  empreinte et la date d'audit (`MANIFESTE.json`, `outils/synchroniser_regles.py
  --verifier`) ; jeu vérifié au chargement (empreintes, identifiants, sources,
  styles) ; chaque résultat porte son explication, ses sources, sa confiance
  et le signalement des conventions du dossier.
- **Style** d'un vin (28 familles, méthode du dossier), imposable à la main ;
  **niveau de garde** (garde, courant, primeur, Nouveau Monde) au choix.
- **Fenêtre calculée** : prêt, apogée, fin, pic (modèle cloche), ajustée au
  millésime (0,44 an par point sur 100, 1,76 sur 10, moyenne de la région dans
  le même tableau) et à la température MESURÉE de la cave (2^((T−12)/10)),
  marges séparées ; format signalé sans chiffre inventé ; rangée dans la base
  (source « calcul ») sans jamais toucher la vôtre ni celles des critiques.
- **Alertes** « à boire cette année », « en déclin », « trop jeune » et
  **courbe d'apogée** de la cave au tableau de bord.
- **Servir** : température (vieux vin, plafond), heure de sortie de cave (loi de
  Newton du dossier, à la minute près), carafe, verre ; **fiche « ce soir »**
  en HTML et en PDF.
- **Conserver** : plages de la cave et mesures hors plage, bouchons à contrôler
  (plus de 15 ans), **bouteille entamée** (jours selon le style et le mode).
- **Niveaux** : sens selon l'âge (bordelais et bourguignon), échelle illustrée.
- **Accords** dans les deux sens, recherche de plat tolérante, accords
  difficiles signalés ; onglet **« Ce soir »** (plat, budget, couleur,
  occasion ; urgences d'abord).
- **Dégustation** avec la roue des arômes ; **diagnostic** des défauts.
- Libellés anglais des règles (`regles/anglais.py`) sans changer une valeur.
- Schéma v5 (`vin.style`, `vin.niveau_garde`).

## 0.2.0 — 2026-10-26 — phase 2 : bases mondiales et étiquettes (non publiée)

- Copie locale de **LWIN** (Liv-ex, CC BY 4.0) : import du fichier XLSX/CSV
  (lecteur sans dépendance, tout ou rien, dans un fil de fond), recherche
  plein texte hors ligne (FTS5), lien direct et mise à jour tous les 30 jours
  en option. Base de référence séparée (`references.db`).
- **Registres d'appellations** INAO et eAmbrosia embarqués (et mis à jour en
  ligne sur demande) : complétion et orthographe officielle à la saisie.
- **Wikidata** (domaines, appellations, cépages ; image Commons avec auteur et
  licence) et **Open Food Facts** (code-barres) : client identifié, une
  requête par seconde, accord de l'utilisateur.
- **Appariement** : candidats classés, score expliqué critère par critère,
  renoncement si deux candidats se valent, confirmation champ par champ,
  jamais d'écrasement d'une saisie manuelle, journal de ce qui a été rempli.
- **Photos d'étiquette** : recadrage et redressement automatiques, déroulage,
  original gardé, vignettes en cache, mur d'étiquettes, webcam, OCR local
  (Tesseract) et identification d'une bouteille d'après sa photo.
- Liste d'envies, notes des critiques (conversion d'après la table Decanter
  du dossier « Le vin »), valeurs datées et sourcées, conditions de cave
  (saisie, import CSV / Home Assistant, courbe), inventaire de contrôle.
- Schéma v4 (photos retouchées, fiches externes, statut « manquante »).

## 0.1.0 — 2026-10-26 — phase 1 : socle et cave (non publiée)

- Kit commun posé (`poser_le_kit.py --multiplateforme --confidentialite`) :
  rapports d'incident, mise à jour automatique, installeur Windows, paquets
  macOS et Linux, garde-fou de confidentialité.
- Base SQLite versionnée (v3) : vins, cépages, producteurs, identifiants
  externes, bouteilles individuelles (formats de la piccolo au melchisédech,
  statuts, niveau, état, caisse, provenance), caves › meubles › casiers et
  historique des déplacements, livre de cave, dégustations, notes des
  critiques, fenêtres de dégustation à plusieurs sources, valeurs datées,
  liste d'envies, bouteilles ouvertes, conditions de cave, images avec crédit
  et licence, origine de chaque champ, journal d'enrichissement ; vues stables
  pour le dossier « Le vin ».
- Interface : tableau de bord, liste de la cave (filtres, recherche, colonnes
  retenues, pochettes), fiche du vin, saisie d'un vin et de ses bouteilles,
  sortie au livre de cave, plan des casiers (glisser-déposer, échange,
  déplacement en lot), livre de cave.
- Import/export CSV sans perte, import CellarTracker, export JSON complet,
  export pour le dossier « Le vin », sauvegardes automatiques.
- Bilingue français / anglais, style figé aux couleurs du logo.
