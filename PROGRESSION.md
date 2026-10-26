# Vendémiaire — progression

Point d'entrée pour reprendre le travail. Cahier des charges (copie neutre) :
[docs/cahier_des_charges.md](docs/cahier_des_charges.md). Journal des versions : [JOURNAL.md](JOURNAL.md).

## État courant (26/10/2026)

- **Phase 1 livrée** dans le code, version `0.1.0`, **non publiée** (aucun tag : publier est une décision
  de l'utilisateur, voir « Décisions » plus bas).
- 64 essais (`tests/`), tous verts sous Xvfb (Python 3.11 local, et Python 3.12 dans un conteneur neuf
  qui rejoue la CI sur un clone propre).
- CI `tests.yml` à chaque poussée sur `main` : **bloquée par GitHub** tant que le dépôt est privé
  (« recent account payments have failed or your spending limit needs to be increased » : pas de
  minutes Actions pour les dépôts privés). Elle tournera dès que le dépôt sera public.
- Paquet Linux du kit construit en local (`build_unix.py --version 0.1.0`) : élagage Qt, vérification
  d'import, **vérification de la mise à jour : ok**, `--check` du paquet : « interface OK »
  (archive de MAJ 1,3 Mo, paquet 73 Mo).
- Captures réelles de l'interface : `docs/captures/{fr,en}-*.png` (`outils/captures.py`).
- Prochaine étape : **phase 2** (bases mondiales LWIN / Wikidata / Open Food Facts, photos d'étiquette,
  OCR). Les phases 3 et 4 attendent le dossier « Le vin » (règles sourcées).

## Les phases

| Phase | Contenu | État |
|---|---|---|
| **1 — socle et cave** | kit standard, logo/icônes, base SQLite versionnée pour tout le cahier, liste, fiche, saisie, plan des casiers (glisser-déposer, lot), livre de cave, tableau de bord simple, CSV, import CellarTracker, sauvegardes, démonstration, essais, CI | ✅ 26/10/2026 |
| **2 — bases mondiales et étiquettes** | copie locale LWIN (CC, XLSX) et recherche hors ligne, Wikidata (SPARQL, CC0) pour domaines/appellations/cépages, Open Food Facts (EAN, ODbL), registres d'appellations (eAmbrosia/GIview, INAO), appariement avec candidats + score expliqué + confirmation, photos d'étiquette (recadrage, perspective, « déroulage »), images libres (OFF, Commons) avec crédit/licence, OCR local, code-barres par webcam, mur d'étiquettes, import Vivino/Excel | ⏳ |
| **3 — d'après le dossier « Le vin »** | fenêtre calculée (modèles cloche/plateau, pourquoi, sources), alertes « à boire / en déclin / trop jeune », courbe d'apogée de la cave, service (température, carafe, verre, sortie de cave, fiche « ce soir »), conservation (conseils, bouchons fatigués), signification des niveaux selon l'âge, bouteille ouverte (jours de garde), accords dans les deux sens, conversion des notes /100 ↔ /20 ↔ étoiles, « que boire ce soir ? » | ⏳ attend le dossier |
| **4 — documents et statistiques** | carte des vins LaTeX « de grand restaurant » (modèles classique/moderne/bistrot, livret A5/A4, aperçu HTML, bilingue), rapport d'assurance/inventaire PDF (format maison), statistiques et graphiques complets, étiquettes de casier à code QR, partage en lecture seule (HTML/PDF), conditions de cave (courbes, alertes, import CSV / Home Assistant), inventaire de contrôle | ⏳ |
| **5 — publication** | manuel PDF LaTeX FR+EN (format maison, captures réelles), polissage, README, première version publiée (dépôt de distribution public, MAJ auto testée en réel) | ⏳ |

## Chaque fonction du cahier des charges : où elle est faite

| Fonction (cahier) | Phase | État / où |
|---|---|---|
| Vins : domaine, cuvée, appellation, région, pays, couleur/type, cépages %, millésime, degré | 1 | ✅ `vin`, `vin_cepage`, `producteur` ; saisie `ui/saisie.py` |
| Contenances de la piccolo au melchisédech | 1 | ✅ `referentiels.FORMATS` (20 formats) |
| Bouteilles individuelles : emplacement, prix, lieu, date d'entrée, bouchon, niveau | 1 | ✅ `bouteille` ; `DialogueBouteille` |
| Statuts en cave / en attente / primeur / bue / offerte / vendue / cassée / bouchonnée | 1 | ✅ ; réception d'un primeur : `Cave.recevoir` |
| Suivi des primeurs (livraison prévue, relance) | 1 / 4 | ✅ date prévue + alerte du tableau de bord ; relance active en 4 |
| Plusieurs caves, emplacements cave › meuble › casier › rangée › colonne | 1 | ✅ `emplacement` + `bouteille.rangee/colonne` |
| Plan visuel, glisser-déposer, déplacement en lot, historique des déplacements | 1 | ✅ `ui/plan.py`, `deplacement` (lot) |
| Vue 3D simple de la cave | 4 | ⏳ si faisable |
| Livre de cave : entrées/sorties, occasion, convives, plat, note, commentaire | 1 | ✅ `mouvement`, `ui/livre.py`, `DialogueSortie` |
| Photos dans le livre de cave | 2 | 🧱 `image.mouvement_id` prêt |
| Grille de dégustation robe/nez/bouche/finale, roue des arômes, /20 ou /100 | 3 | 🧱 table `degustation` prête |
| Dégustations verticales, horizontales, à l'aveugle | 3 | 🧱 table `seance` prête |
| Fenêtres de dégustation à 3 sources (mienne, critiques, calculée) + pourquoi | 1 / 3 | ✅ stockage + affichage des 3 sources ; **calcul en 3** (`vendemiaire/regles`) |
| Alertes à boire / en déclin / trop jeune ; courbe d'apogée | 3 | ⏳ (le tableau de bord l'annonce) |
| Servir : température, carafe, verre, sortie de cave, fiche « ce soir » | 3 | ⏳ `regles.service` |
| Accords mets-vins dans les deux sens, expliqués | 3 | ⏳ `regles.accords_pour_vin`, `regles.vins_pour_plat` |
| Conservation : conseils, bouchons fatigués, température de cave | 3 / 4 | 🧱 `condition_cave` prête |
| Notes des critiques avec échelle | 1 | ✅ `note_critique` (+ fourchette « 94–96 ») |
| Conversion /100 ↔ /20 ↔ étoiles | 3 | ⏳ `regles.convertir_note` (règle sourcée) |
| Valeur : prix d'achat, valeur datée et sourcée, total, plus/moins-value | 1 / 4 | ✅ `valeur`, total au tableau de bord ; évolution et plus-value en 4 |
| Statistiques par région, couleur, millésime, cépage, prix ; graphiques | 1 / 4 | ✅ répartitions simples ; complet en 4 |
| Rythme de consommation vs achats, « combien à boire par an pendant 20 ans » | 4 / 3 | ⏳ (entrées/sorties sur 12 mois déjà affichées) |
| Liste d'envies, cave idéale, alertes de prix | 1 / 4 | 🧱 table `envie` prête ; écran en 4 |
| Seuil de réassort et liste d'achats générée | 1 / 4 | ✅ seuil + alerte ; liste générée en 4 |
| Inventaire de contrôle (compter un casier, écarts) | 4 | 🧱 table `inventaire` prête |
| Bouteille ouverte (reste, jours de garde selon le mode) | 3 | 🧱 table `bouteille_ouverte` prête ; durée en 3 |
| Niveau (ullage) bordelais et bourguignon, illustré, signification selon l'âge | 1 / 3 | ✅ vocabulaire + cm ; signification et illustration en 3 |
| État étiquette / capsule / bouchon, caisse bois d'origine, caisse complète, photos | 1 / 2 | ✅ champs ; photos en 2 |
| Provenance, historique de stockage, facture | 1 | ✅ |
| Rapport d'assurance / d'inventaire en PDF | 4 | ⏳ |
| Carte des vins imprimable « grand restaurant » (LaTeX) | 4 | ⏳ (champ `bouteille.bin` prêt) |
| Import/export CSV, import CellarTracker | 1 | ✅ `echanges.py`, [docs/import_cellartracker.md](docs/import_cellartracker.md) |
| Import Vivino / Excel | 2 | ⏳ |
| Export complet (aucune donnée prisonnière) | 1 | ✅ JSON de toutes les tables |
| Sauvegardes automatiques | 1 | ✅ `sauvegarde.py` |
| Saisie rapide : complétion appellations, cépages, domaines | 1 / 2 | ✅ complétion sur la cave ; base de référence en 2 |
| Identifiant mondial LWIN, Wikidata, Open Food Facts, registres d'appellations | 2 | 🧱 `vin.lwin`, `vin.ean`, `identifiant_externe` (score, explication, confirmé) |
| Appariement : normalisation, candidats + score, confirmation, COALESCE, journal | 1 / 2 | ✅ `normaliser`, `completer_vin`, `origine_champ`, `journal_enrichissement` ; candidats en 2 |
| Photo d'étiquette = « pochette » partout | 1 / 2 | ✅ pochette (photo ou étiquette dessinée) dans liste et fiche ; recadrage, OCR, galerie en 2 |
| Images libres avec crédit et licence ; pas d'images protégées automatiques | 2 | 🧱 `image.credit/licence/url_source/origine` |
| Lecture code-barres webcam, impression d'étiquettes QR de casier | 2 / 4 | 🧱 `bouteille.code_interne` (unique) |
| Partage en lecture seule (HTML/PDF) | 4 | ⏳ |
| Conditions de cave : saisie/import T° et hygrométrie, courbes, alertes | 4 | 🧱 `condition_cave` |
| « Que boire ce soir ? » | 3 | ⏳ |
| Lien avec le dossier « Le vin » (encadrés sur les bouteilles de la cave) | 1 | ✅ vues `v_dossier_vin`, `v_dossier_livre` + `python -m vendemiaire.export_dossier` ([contrat](docs/export_dossier.md)) |
| Base accessible depuis un NAS, un seul écrivain | 1 | ✅ menu « Dossier des données… », verrou dans le dossier des données, lecteurs en `mode=ro` |
| Standard : kit, MAJ auto, rapports (poste = machine), bilingue testé, style figé, vrai explorateur, icône/logo | 1 | ✅ |
| Manuel PDF LaTeX FR+EN | 5 | ⏳ (le menu Aide l'ouvrira : `docs/manuel-{fr,en}.pdf`) |

✅ fait · 🧱 structure de données prête, écran ou calcul à venir · ⏳ à faire

## Architecture

```
run.py                     point d'entrée (--demo, --lang, --donnees, --check, --version)
kit.json                   tout ce qui varie pour le kit commun (ne jamais modifier les fichiers du kit à la main)
reporting.py updater.py build_package.py build_unix.py installer.iss interface_kit.py   kit commun (identiques au gabarit)
kit_aide.py                menu Aide du kit (manuel, MAJ, signaler, accord), module applicatif commun
vendemiaire/
  base.py                  SQLite : schéma v3, migrations numérotées, un seul écrivain, lecture seule
  modele.py                Cave : vins, bouteilles, emplacements, déplacements, livre, critiques, valeurs, images, statistiques
  referentiels.py          codes stockés + libellés FR/EN (formats, statuts, niveaux, états, mouvements…)
  echanges.py              CSV aller-retour, JSON complet, import CellarTracker
  export_dossier.py        export stable pour le dossier « Le vin » (lecture seule)
  sauvegarde.py            copies cohérentes (API backup de SQLite), rotation, restauration
  chemins.py               dossier des données (profil, ou partage choisi), jamais le dossier de l'appli
  regles/                  INTERFACE des règles d'œnologie (phase 3) — vide en phase 1
  demo.py                  cave de démonstration générée (producteurs inventés)
  i18n.py textes.py        bilinguisme : tr(clé), lib(enum, code), montants et dates selon la langue
  style.py logo.py         style figé (Fusion, palette bordeaux/or/crème, polices embarquées), icônes
  ui/                      fenetre, liste, fiche, saisie, plan, livre, tableau, pochette
branding/logo.svg          SEULE source du logo ; docs/logo_* en dérivent
outils/                    rendre_logo.js (PNG via resvg), captures.py (captures réelles)
```

### Base de données (schéma v3)

Tables : `producteur`, `vin`, `vin_cepage`, `identifiant_externe`, `emplacement`, `bouteille`,
`deplacement`, `seance`, `degustation`, `mouvement`, `note_critique`, `fenetre_degustation`, `valeur`,
`envie`, `bouteille_ouverte`, `condition_cave`, `inventaire`, `image`, `origine_champ`,
`journal_enrichissement`, `meta`. Vues : `v_dossier_vin`, `v_dossier_livre`.

- v1 = schéma complet ; v2 = formes normalisées des noms (`nom_normalise`, `cuvee_normalisee`) ;
  v3 = vues du dossier « Le vin ». **Une migration publiée ne se modifie jamais** (empreintes dans
  `tests/test_migrations.py`) : en ajouter une à `MIGRATIONS`.
- Chaque migration dans sa propre transaction ; une base plus récente que l'application est refusée ;
  sauvegarde « avant-migration » au démarrage.
- **Un seul écrivain** : verrou d'instance `vendemiaire.verrou` (QLockFile) DANS le dossier des données,
  donc sur le partage s'il y est ; `Base.ecrivain_disponible()` teste le verrou SQLite en 4 s au plus.
  Journal `DELETE`, jamais WAL (le `-shm` n'existe pas sur SMB).
- **Lire puis écrire** : `with base.ecriture() as c:` (BEGIN IMMEDIATE, court, rien de lent dedans :
  l'empreinte d'une image se calcule avant). Verrou équitable (file FIFO) entre fils.
- **Jamais d'écrasement d'une saisie manuelle** : `enregistrer_vin(..., origine='manuel')` marque dans
  `origine_champ` les champs remplis ou vidés par l'utilisateur ; `completer_vin()` (imports, bases
  mondiales) ne remplit que les champs vides non manuels, en `COALESCE(NULLIF(col,''), ?)`, et note
  chaque remplissage dans `journal_enrichissement`.

### Lien avec le dossier « Le vin »

- Lecture : vues `v_dossier_vin` / `v_dossier_livre`, ou `python -m vendemiaire.export_dossier <cave.db>
  <sortie.json> [--sorties-seulement]` (format `vendemiaire-dossier`, version 1). Contrat :
  [docs/export_dossier.md](docs/export_dossier.md) — colonnes ajoutées en fin seulement, jamais retirées.
- Emplacement partagé : menu **Fichier › Dossier des données…** (retenu dans `emplacement.json` du
  profil ; variable `VENDEMIAIRE_DONNEES` prioritaire). Le dossier contient `cave.db`, `images/`,
  `sauvegardes/`, `vendemiaire.verrou`. Le dossier LaTeX lit de préférence une copie ou la dernière
  sauvegarde, en `mode=ro`.
- Phase 3 : les règles (apogée, service, accords, niveaux) viendront des parties du dossier, avec leurs
  sources, comme DONNÉES versionnées lues par un fournisseur inscrit dans `vendemiaire.regles`
  (contrat `FournisseurRegles` : chaque réponse porte explication FR/EN, sources, identifiant de règle).

## Chaîne de travail

```bash
python -m pip install -r requirements.txt pytest       # PyQt6
xvfb-run -a -s "-screen 0 1920x1080x24" python -m pytest -q tests/
xvfb-run -a -s "-screen 0 1920x1080x24" python outils/captures.py     # docs/captures/
node outils/rendre_logo.js && python -m vendemiaire.logo --assembler    # après toute retouche du logo
python run.py --demo                                                    # essayer à la main
```

- Reposer le kit après une évolution du gabarit : `python <kit>/poser_le_kit.py . --multiplateforme
  --confidentialite` (garde `kit.json` ; `tests/test_kit.py` vérifie l'identité octet par octet).
- Publier (décision de l'utilisateur) : bump `VERSION` + section `## X.Y.Z` de `JOURNAL.md`, tag `vX.Y.Z`
  → `release.yml` du kit (Windows, macOS, Linux). Essai sans rien publier :
  `gh workflow run release.yml -f version=X.Y.Z -f essai=true`.

## Pièges payés (phase 1)

- 🔴 Marquer « manuel » **tous** les champs d'une saisie (le dialogue les envoie tous, même vides)
  aurait interdit à jamais aux imports de compléter quoi que ce soit après une seule modification.
  Règle retenue : manuel = rempli par l'utilisateur, ou vidé par lui alors qu'il était rempli.
- 🔴 CellarTracker écrit **`Unknown`** dans les champs non renseignés (Designation, SubRegion…) :
  pris pour une cuvée, il créait un second vin au lieu de compléter le premier. Et le millésime
  **`1001`** signifie « non millésimé ».
- 🔴 `QHeaderView.restoreState()` remet aussi les drapeaux (colonnes déplaçables…) : les poser APRÈS
  (essai `test_colonnes_retenues_et_deplacables`).
- 🔴 Reconstruire les menus au changement de langue : `menuBar().clear()` retire les actions mais
  **garde les QMenu** (enfants de la barre) — il faut les détruire, sinon ils s'accumulent (et
  l'essai « pas de français dans l'anglais » les voyait encore).
- `executescript()` valide la transaction en cours : une migration en plusieurs instructions est
  découpée (`sqlite3.complete_statement`) pour rester tout-ou-rien.
- Arbre des emplacements construit en plusieurs passes : l'ordre des enfants sortait inversé ;
  construction récursive triée par `ordre`.
- `nombre(100, 0)` donnait « 1 » (zéros retirés d'un entier) — « Pinot noir 1 % ».
- Les sauvegardes de la fenêtre partaient dans le dossier du PROFIL même quand une autre base était
  ouverte (démonstration, captures) : elles vivent désormais à côté de la base ouverte.
- Le greffon Qt `xcb` exige `libxcb-cursor0` (absent de bien des images Linux) : message « no Qt
  platform plugin could be initialized ».
- Locale Qt : sans `QLocale.setDefault`, les champs numériques affichent « 134.93 » dans l'interface
  française.

## Reste à faire (prochaine reprise : phase 2)

1. Télécharger la base LWIN (licence CC, XLSX) → table locale `ref_lwin` (migration v4) + recherche
   hors ligne ; mise à jour périodique ; afficher la licence.
2. Appariement (règles de MusicOthèque) : candidats, score **expliqué** (calculé soi-même, pas celui de
   la source), renoncement si deux candidats se valent, **confirmation** avant `completer_vin`.
3. Wikidata (SPARQL) : producteurs, appellations, cépages ; Open Food Facts par EAN ; registres
   d'appellations (eAmbrosia/GIview, INAO).
4. Photos : recadrage/perspective, vignettes en cache disque, mur d'étiquettes, OCR local (choisir un
   moteur libre hors ligne), webcam/code-barres en option.
5. Écrans encore absents mais dont les tables existent : liste d'envies, notes des critiques et valeurs
   (saisie dans la fiche), conditions de cave, inventaire de contrôle.
6. Phase 5 : manuel PDF LaTeX FR/EN (le menu Aide cherche `docs/manuel-{fr,en}.pdf`), puis
   ajouter les manuels à `copies` de `kit.json` et au `--check`.

## Décisions pour l'utilisateur

- **CI** : rien ne tourne sur GitHub tant que le dépôt est privé (pas de minutes Actions). Rendre le dépôt
  public, ou régler la facturation Actions, ou garder les essais locaux.

- **Publier ?** Le dépôt est privé : la mise à jour automatique ne peut rien trouver tant que
  `depot_distribution` (kit.json) n'est pas public. Choix : rendre ce dépôt public (le garde-fou de
  confidentialité passe), ou créer un dépôt public de distribution (`--depot-de-construction`).
- **Emplacement de la base** : profil local (défaut) ou lecteur réseau partagé (menu Fichier › Dossier
  des données…) pour que le dossier « Le vin » la lise.
- Formats : les noms au-delà du magnum varient selon les régions (bordelais / champenois) ; la liste
  actuelle est à valider avec le dossier « Le vin ».
- CellarTracker : valider l'import sur un vrai export (colonnes documentées dans
  [docs/import_cellartracker.md](docs/import_cellartracker.md)).
