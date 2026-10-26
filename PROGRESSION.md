# Vendémiaire — progression

Point d'entrée pour reprendre le travail. Cahier des charges (copie neutre) :
[docs/cahier_des_charges.md](docs/cahier_des_charges.md). Journal des versions : [JOURNAL.md](JOURNAL.md).

## État courant (26/10/2026, nuit)

- **Phases 1, 2 et 3 livrées** dans le code, version `0.3.0`, **non publiées** (aucun tag ni release :
  décision de l'utilisateur).
- 197 essais (`tests/`), tous verts sous Xvfb (Python 3.11 local) ; la CI (`tests.yml`, Python 3.12)
  installe aussi Tesseract. Les essais qui relisent le dossier « Le vin » (copie identique, TOUS ses
  tableaux de fenêtres, températures et accords) se sautent en CI (dossier absent) et passent en local.
- `run.py --check` : « interface OK » (vérifie aussi le jeu de règles : 194 règles, empreintes).
- Captures réelles FR/EN : `docs/captures/{fr,en}-*.png` (26 par langue : + fiche-regles, garde,
  ce-soir, fiche-ce-soir, niveaux, degustation, defauts, entamer, regles).
- Prochaine étape : **phase 4** — documents et statistiques (voir « Reste à faire »).

## Les phases

| Phase | Contenu | État |
|---|---|---|
| **1 — socle et cave** | kit standard, logo/icônes, base SQLite versionnée pour tout le cahier, liste, fiche, saisie, plan des casiers (glisser-déposer, lot), livre de cave, tableau de bord simple, CSV, import CellarTracker, sauvegardes, démonstration, essais, CI | ✅ 26/10/2026 |
| **2 — bases mondiales et étiquettes** | copie locale LWIN et recherche hors ligne, Wikidata, Open Food Facts (EAN), registres INAO + eAmbrosia, appariement (score expliqué, confirmation, journal), photos (recadrage, perspective, déroulage, original gardé, vignettes, mur, webcam), OCR local (Tesseract), envies, critiques + conversion, valeurs, conditions de cave, inventaire | ✅ 26/10/2026 (import Vivino/Excel et lecture de code-barres À L'IMAGE : reportés, voir plus bas) |
| **3 — d'après le dossier « Le vin »** | moteur de règles (194 règles copiées avec empreintes), style, fenêtre calculée (plateau/cloche, millésime, température de cave, pourquoi, sources, confiance), alertes, courbe d'apogée, service (température, sortie de cave, carafe, verre, fiche « ce soir » HTML/PDF), conservation (plages, bouchons, bouteille entamée), niveaux selon l'âge (illustrés), accords dans les deux sens, « que boire ce soir ? », dégustation (roue des arômes), diagnostic des défauts, libellés anglais | ✅ 26/10/2026 |
| **4 — documents et statistiques** | carte des vins LaTeX « de grand restaurant » (modèles classique/moderne/bistrot, livret A5/A4, aperçu HTML, bilingue), rapport d'assurance/inventaire PDF (format maison), statistiques et graphiques complets, étiquettes de casier à code QR, lecture du code-barres À L'IMAGE, imports Vivino/Excel, partage en lecture seule (HTML/PDF), séances de dégustation | ⏳ |
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
| Photos dans le livre de cave | 2 / 4 | 🧱 `image.mouvement_id` + `ajouter_image(mouvement_id=)` ; écran en 4 |
| Grille de dégustation robe/nez/bouche/finale, roue des arômes, /20 ou /100 | 3 | ✅ `ui/degustation.py` (`aromes.json`), liste dans la fiche |
| Dégustations verticales, horizontales, à l'aveugle | 3 / 4 | ✅ case « à l'aveugle » ; séances (table `seance` prête) en 4 |
| Fenêtres de dégustation à 3 sources (mienne, critiques, calculée) + pourquoi | 1 / 3 | ✅ `regles/garde.py`, `Cave.enregistrer_fenetres_calculees`, « pourquoi ? » dans la fiche |
| Alertes à boire / en déclin / trop jeune ; courbe d'apogée | 3 | ✅ `Cave.alertes_garde`, `Cave.courbe_apogee`, tableau de bord |
| Servir : température, carafe, verre, sortie de cave, fiche « ce soir » | 3 | ✅ `regles/service.py`, `ui/ce_soir.py` (HTML + PDF Qt) |
| Accords mets-vins dans les deux sens, expliqués | 3 | ✅ `regles/accords.py` (recherche tolérante, preuves du corpus) |
| Conservation : conseils, bouchons fatigués, température de cave | 3 | ✅ `regles/conservation.py` ; onglet Conditions (plages, hors plage, vitesse de vieillissement) |
| Notes des critiques avec échelle | 1 / 2 | ✅ saisie/modif/suppression `ui/critiques.py` (fourchette, source, date) |
| Conversion /100 ↔ /20 ↔ étoiles | 2 | ✅ `regles/notes.py` lit `regles/donnees/notes.json` du dossier (table Decanter ; pas de table → pas de conversion) |
| Valeur : prix d'achat, valeur datée et sourcée, total, plus/moins-value | 1 / 2 / 4 | ✅ saisie (source obligatoire) et liste dans la fiche ; évolution et plus-value en 4 |
| Statistiques par région, couleur, millésime, cépage, prix ; graphiques | 1 / 4 | ✅ répartitions simples ; complet en 4 |
| Rythme de consommation vs achats, « combien à boire par an pendant 20 ans » | 3 / 4 | ✅ courbe d'apogée sur 20 ans ; rythme vs achats en 4 |
| Liste d'envies, cave idéale, alertes de prix | 2 / 4 | ✅ onglet « Liste d'envies » (`ui/envies.py`) ; alertes de prix en 4 |
| Seuil de réassort et liste d'achats générée | 1 / 4 | ✅ seuil + alerte ; liste générée en 4 |
| Inventaire de contrôle (compter un casier, écarts) | 2 | ✅ Cave › Inventaire de contrôle (`ui/inventaire.py`) : codes lus, écarts, sortie « écart d'inventaire » sur décision |
| Bouteille ouverte (reste, jours de garde selon le mode) | 3 | ✅ `Cave.entamer` (« à finir avant »), alerte au tableau de bord |
| Niveau (ullage) bordelais et bourguignon, illustré, signification selon l'âge | 1 / 3 | ✅ `regles/niveaux.py`, `IllustrationNiveaux` (saisie de la bouteille, règles) |
| État étiquette / capsule / bouchon, caisse bois d'origine, caisse complète, photos | 1 / 2 | ✅ champs + photos (étiquette, contre-étiquette, capsule, caisse) |
| Provenance, historique de stockage, facture | 1 | ✅ |
| Rapport d'assurance / d'inventaire en PDF | 4 | ⏳ |
| Carte des vins imprimable « grand restaurant » (LaTeX) | 4 | ⏳ (champ `bouteille.bin` prêt) |
| Import/export CSV, import CellarTracker | 1 | ✅ `echanges.py`, [docs/import_cellartracker.md](docs/import_cellartracker.md) |
| Import Vivino / Excel | 4 | ⏳ reporté (pas d'export Vivino officiel documenté ; Excel → passer par le CSV) |
| Export complet (aucune donnée prisonnière) | 1 | ✅ JSON de toutes les tables |
| Sauvegardes automatiques | 1 | ✅ `sauvegarde.py` |
| Saisie rapide : complétion appellations, cépages, domaines | 1 / 2 | ✅ cave + registres officiels ; orthographe officielle proposée |
| Identifiant mondial LWIN, Wikidata, Open Food Facts, registres d'appellations | 2 | ✅ `mondial/`, `references.py`, `ui/identifier.py`, `ui/references.py` ([docs](docs/bases_mondiales.md)) |
| Appariement : normalisation, candidats + score, confirmation, COALESCE, journal | 2 | ✅ `mondial/appariement.py` ; journal visible dans la fiche |
| Photo d'étiquette = « pochette » partout | 2 | ✅ liste, fiche, mur ; recadrage/perspective/déroulage, OCR ([docs](docs/photos_et_ocr.md)) ; carte des vins en 4 |
| Images libres avec crédit et licence ; pas d'images protégées automatiques | 2 | ✅ OFF (CC BY-SA) et Commons (auteur + licence) enregistrés avec l'image |
| Lecture code-barres webcam, impression d'étiquettes QR de casier | 2 / 4 | ✅ EAN tapé, lu par l'OCR ou par une douchette (clavier) ; photo webcam ; décodage du code-barres À L'IMAGE et QR de casier en 4 |
| Partage en lecture seule (HTML/PDF) | 4 | ⏳ |
| Conditions de cave : saisie/import T° et hygrométrie, courbes, alertes | 2 / 3 | ✅ onglet + plages du dossier, mesures hors plage, alerte au tableau de bord |
| « Que boire ce soir ? » | 3 | ✅ onglet « Ce soir » (`Cave.que_boire`) |
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
  regles/                  MOTEUR des règles du dossier « Le vin » (phase 3) : jeu.py (chargement, empreintes,
                           validation), styles, garde, millesimes (+ RATTACHEMENT appellation → région), service,
                           conservation, niveaux, accords, degustation, dossier (FournisseurDossier), anglais
  cave_regles.py           Cave × règles : fenêtres calculées, alertes, courbe, entamer, dégustations, que_boire
  demo.py                  cave de démonstration générée (producteurs inventés)
  i18n.py textes.py        bilinguisme : tr(clé), lib(enum, code), montants et dates selon la langue
  style.py logo.py         style figé (Fusion, palette bordeaux/or/crème, polices embarquées), icônes
  references.py            base de RÉFÉRENCE séparée (references.db) : LWIN + FTS5, appellations, cache
  reseau.py                client HTTP poli : accord, User-Agent, 1 req/s par hôte, Retry-After, simulable
  mondial/                 lwin (XLSX en flux), wikidata, off, appellations (INAO, eAmbrosia), appariement
  images.py                détection des bords (Qt pur, OpenCV si présent), perspective, déroulage, vignettes
  ocr.py                   Tesseract (programme externe) + indices (millésime, degré, EAN, appellations)
  demo_photos.py           photos d'étiquette dessinées (libres) pour essais et captures
  donnees/                 registres d'appellations embarqués + sources.json (date, licence)
  regles/donnees/          les 13 JSON + LISEZMOI du dossier « Le vin », TELS QUELS, + MANIFESTE.json (empreintes,
                           date d'audit) — `outils/synchroniser_regles.py [--verifier]`
  ui/                      fenetre, liste, fiche, saisie, plan, livre, tableau, pochette, mur, photos,
                           identifier, references, envies, critiques, conditions, inventaire, travail,
                           regles_ui (pourquoi, sources, échelle des niveaux), ce_soir, degustation
branding/logo.svg          SEULE source du logo ; docs/logo_* en dérivent
outils/                    rendre_logo.js (PNG via resvg), captures.py (captures réelles)
```

### Base de données (schéma v5)

Tables : `producteur`, `vin`, `vin_cepage`, `identifiant_externe`, `emplacement`, `bouteille`,
`deplacement`, `seance`, `degustation`, `mouvement`, `note_critique`, `fenetre_degustation`, `valeur`,
`envie`, `bouteille_ouverte`, `condition_cave`, `inventaire`, `image`, `origine_champ`,
`journal_enrichissement`, `meta`. Vues : `v_dossier_vin`, `v_dossier_livre`.

- v1 = schéma complet ; v2 = formes normalisées des noms (`nom_normalise`, `cuvee_normalisee`) ;
  v3 = vues du dossier « Le vin » ; v4 = `image.fichier_original/retouche/texte_ocr`, table
  `fiche_externe`, formes normalisées recalculées (abréviations) ; v5 = `vin.style`, `vin.niveau_garde`
  (choix de l'utilisateur, NULL = automatique). **Une migration publiée ne se modifie jamais** (empreintes dans
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
- Phase 3 : règles du dossier lues dans `vendemiaire/regles/donnees/` (copie octet pour octet,
  [docs/regles_du_dossier.md](docs/regles_du_dossier.md)). Fenêtre calculée rangée avec
  `source='calcul'`, `detail_source='<style>/<niveau>'`, explication FR + détail du calcul.

## Chaîne de travail

```bash
python -m pip install -r requirements.txt pytest       # PyQt6
xvfb-run -a -s "-screen 0 1920x1080x24" python -m pytest -q tests/
xvfb-run -a -s "-screen 0 1920x1080x24" python outils/captures.py     # docs/captures/
node outils/rendre_logo.js && python -m vendemiaire.logo --assembler    # après toute retouche du logo
python run.py --demo                                                    # essayer à la main (avec LWIN et photos de démonstration)
python outils/registres_appellations.py                                 # rafraîchir les registres embarqués (réseau)
python outils/synchroniser_regles.py --verifier                         # règles identiques au dossier « Le vin » ?
python outils/synchroniser_regles.py                                    # recopier après une correction DANS le dossier
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

## Pièges payés (phase 2)

- LWIN se télécharge par un **formulaire HubSpot** (nom, courriel) : pas d'adresse directe. L'appli
  ouvre la page, l'utilisateur importe le fichier ; le lien direct reçu par courriel peut être retenu
  pour la mise à jour périodique. Ne jamais remplir le formulaire à sa place.
- En-têtes du vrai fichier LWIN **non vérifiés** (fichier non obtenu) : lecteur tolérant (seule la
  colonne `LWIN` est exigée, variantes d'en-têtes reconnues). À valider sur le vrai fichier.
- Open Food Facts : la **recherche par texte** répond souvent une page HTML « temporairement
  indisponible » ; seule la lecture par EAN est utilisée, et une réponse non JSON lève `ErreurReseau`.
- L'API eAmbrosia ignore `productType` : filtrer soi-même (`WINE`, sans `removedFlag`).
- Wikidata : « canton français (**ava**nt 2015) » passait pour une AVA → mots-clés de nature en mots entiers.
- `QListWidgetItem(QPixmap, texte)` n'existe pas : passer un `QIcon`.
- Clés de texte fabriquées en f-string (`f"ident.etat_{x}"`) : l'essai des clés les voit tronquées →
  tables explicites (`ETATS`, `DECISIONS`, `PRIORITES`).
- OCR sur la photo brute de travers : presque rien ; après redressement : tout. Le redressement
  d'abord.
- Import LWIN (≈ 205 000 lignes) : une transaction de `references.db` dans un fil ; la cave reste
  disponible (fichier séparé), import interrompu = ancienne copie intacte. Mesuré : ≈ 15 s, ≈ 60 Mo.

## Pièges payés (phase 3)

- Les expressions de `styles.json` sont des MOTIFS (`\bpx\b`) : recherche par expression régulière
  dans le texte normalisé (sans accents, traits d'union = espaces), pas une simple inclusion.
- Le classement littéral du dossier range **tout** champagne (même sans année) en `eff_millesime`
  (« champagne » est dans ses appellations) et un **banyuls rimage** en `mute_oxydatif` (« banyuls »
  dans ses appellations) : appliqué tel quel, signalé à l'utilisateur (style imposable dans la saisie) ;
  à corriger dans `scripts/regles.py` du dossier si on le veut autrement.
- « Moyenne de la région » : moyenne de la MÊME source sur la région (la régression du dossier a des
  effets propres à chaque région), pas la moyenne globale de `millesimes.json`.
- Arrondi des années : `round()` de Python est bancaire (2034,5 → 2034) ; arrondi « à la moitié
  supérieure » (`garde.arrondi`).
- La loi de Newton du dossier (τ air 2,58 h, seau 37,6 min ; pièce 20, frigo 4, eau glacée 0 °C) redonne
  ses tableaux à la minute : essai `test_sortie_de_cave_redonne_le_tableau`.
- Clés de règles (`cave.temperature`) en dur dans `ui/` : l'essai des clés de textes les prend pour des
  clés manquantes (préfixe `cave.`) → constantes `regles.conservation.TEMPERATURE/HYGROMETRIE`.
- `QTextDocument.print(QPdfWriter)` suffit pour la fiche « ce soir » en PDF (pas de QtPrintSupport).

## Reste à faire (prochaine reprise : phase 4)

1. **Carte des vins LaTeX « de grand restaurant »** (cahier des charges, section dédiée) : générée
   depuis la cave ou une sélection (« dîner de samedi ») ; ordre classique (effervescents → blancs →
   rosés → rouges → doux → mutés ; pays › région › appellation › producteur › millésime ; jamais par
   prix) ; ligne = BIN (`bouteille.bin`), producteur, cuvée, appellation, millésime, format, prix
   facultatif ; verticales regroupées ; modèles classique / moderne / bistrot ; livret A5/A4 ou carte
   simple ; aperçu HTML ; bilingue ; « menu du soir » → accords proposés par plat (réutiliser
   `regles.accords`) ; compilation dans un fil, temporaires supprimés, PDF format maison.
2. **Rapport d'assurance / d'inventaire PDF** (format maison) : liste, photos, état, niveau ET son sens
   (`regles.niveaux`), valeur datée et sourcée, total ; provenance et historique de stockage.
3. **Statistiques complètes** : graphiques par région, couleur, millésime, cépage, prix, valeur dans le
   temps et plus-value, rythme de consommation vs achats (mouvements), courbe d'apogée par couleur.
4. **Code-barres à l'image** (photo / webcam ; décodeur local à choisir : zbar via `pyzbar` ou ZXing ;
   pas d'envoi en ligne) et **étiquettes de casier à code QR** (`bouteille.code_interne`).
5. **Imports Vivino / Excel** : Excel via `openpyxl` en lecture seule (ou CSV), correspondance de
   colonnes assistée ; Vivino : pas d'export officiel documenté → n'accepter qu'un fichier que
   l'utilisateur fournit, colonnes à relever sur un vrai fichier.
6. Séances de dégustation (verticale, horizontale, à l'aveugle : on note avant de révéler) — table
   `seance` prête ; partage en lecture seule (HTML/PDF) ; liste d'achats générée ; alertes de prix.
7. Toujours : valider LWIN et CellarTracker sur de vrais fichiers ; manuel PDF en phase 5.

## Décisions pour l'utilisateur

- **LWIN** : remplir une fois le formulaire de Liv-ex (courriel), importer le fichier ; s'il donne un
  lien direct stable, le coller dans Références › Bases de référence et cocher la mise à jour
  mensuelle.
- **OCR** : Tesseract n'est pas embarqué dans les paquets (le kit ne sait embarquer des binaires que
  sous Windows, et à partir d'une archive zip) ; à installer à part (≈ 10–30 Mo selon les langues).
  L'embarquer = travail du kit (phase 5). OpenCV : facultatif, non embarqué (≈ 60 Mo).
- **Recherches en ligne** : désactivées tant que l'utilisateur ne les autorise pas.

- **Publier ?** Dépôt public depuis le 26/10 (CI verte). Publier = tag `v0.3.0` (VERSION déjà à 0.3.0 ; ou essai
  `gh workflow run release.yml -f version=0.3.0 -f essai=true`).
- **Emplacement de la base** : profil local (défaut) ou lecteur réseau partagé (menu Fichier › Dossier
  des données…) pour que le dossier « Le vin » la lise.
- **Règles du dossier à revoir peut-être (dans `scripts/regles.py`, pas dans l'appli)** : champagne sans
  année classé « millésimé ou de prestige », banyuls rimage classé « oxydatif » (classement littéral) ;
  magnum « plus lent » non chiffré (fenêtre inchangée) ; la note d'un critique sur le vin lui-même ne
  modifie pas la fenêtre (aucune règle) — seule la note du millésime le fait.
- **Rattachement appellation → région des millésimes** (`regles/millesimes.py`) : table de
  l'application, à reprendre dans le dossier si l'on veut une source unique.
- Formats : les noms au-delà du magnum varient selon les régions (bordelais / champenois) ; la liste
  actuelle est à valider avec le dossier « Le vin ».
- CellarTracker : valider l'import sur un vrai export (colonnes documentées dans
  [docs/import_cellartracker.md](docs/import_cellartracker.md)).
