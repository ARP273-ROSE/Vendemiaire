# Documents de Vendémiaire (phase 4)

Menu **Documents** : carte des vins, rapport d'assurance / d'inventaire, partage en lecture seule,
étiquettes de casier à code QR. Menu **Cave › Scanner une bouteille**. Menu **Fichier** : import d'un
tableau Excel/CSV et d'un export Vivino. Onglets **Statistiques** et **Dégustations**.

Exemples sur la cave de démonstration (producteurs inventés) : [`docs/exemples/`](exemples/)
(`python outils/exemples.py`).

## Moteur PDF : LaTeX, sinon Qt

Les PDF « soignés » (carte des vins, rapport d'assurance) sont écrits en LaTeX. Le moteur est cherché dans
cet ordre (`vendemiaire/documents/latex.py`) :

1. celui choisi dans la carte des vins (**Moteur LaTeX…**, réglage `documents/moteur`) ou la variable
   `VENDEMIAIRE_LATEX` ;
2. **Tectonic** livré avec le paquet (`outils/tectonic/`, voir plus bas), puis celui du `PATH` ;
3. une distribution installée : XeLaTeX, LuaLaTeX puis pdfLaTeX (`PATH`, puis les dossiers usuels de
   MiKTeX, TeX Live et MacTeX).

Sans moteur, ou si la compilation échoue, **le même contenu** est écrit par Qt (`QTextDocument` →
`QPdfWriter`) : toujours disponible, hors ligne, typographie plus simple (pas de points de conduite,
polices du système). L'interface dit quel moteur a servi.

**Tectonic embarqué (1.0.0).** Le kit commun (clé `outils` de `kit.json`) pose Tectonic 0.17.0 (licence MIT,
archives officielles, empreintes SHA-256 vérifiées) dans `outils/tectonic/` des paquets Windows, macOS
(arm64, x86_64) et Linux (x86_64, arm64), avec un **cache pré-rempli** : à la construction, les documents
de `docs/prechauffage/` (cartes classique, moderne, bistrot ; rapports d'assurance FR et EN — régénérés par
`outils/exemples.py`) et les deux manuels sont compilés, puis recompilés avec `--only-cached` : la
construction échoue si le cache ne suffit pas hors ligne (≈ 55 Mo). À l'usage, ce cache est recopié une fois
dans le profil (`<profil>/cache/tectonic`, jamais dans le dossier d'installation), puis Tectonic compile
**sans réseau** (`--only-cached`) ; si un paquet LaTeX manque (document modifié), une seconde tentative le
télécharge. Les modèles compilent aussi sous pdfLaTeX (sans fontspec).

La compilation se fait dans un dossier temporaire supprimé ensuite (seul le PDF est rendu), dans un fil :
l'interface ne gèle pas.

## Carte des vins « de grand restaurant »

`vendemiaire/documents/carte.py`, fenêtre `ui/carte_vins.py`. Règles du cahier des charges :

- **ordre classique** : effervescents → blancs → (orange) → rosés → rouges → doux et liquoreux → mutés ;
  dans chaque couleur, **pays** (France d'abord en option) › **région** › **appellation**, puis
  **producteur** et **millésime** — **jamais par prix** ;
- **une ligne** : BIN, producteur, cuvée, millésime, format, prix (si affiché), degré et cépages en option,
  une ligne d'accord (saisie, sinon tirée des accords du dossier « Le vin » pour le style du vin) ;
- **verticales regroupées** (même producteur, même cuvée, plusieurs millésimes) ;
- à part : **au verre / à la carafe** (vins cochés, prix au verre), **demi-bouteilles** (≤ 50 cl) et
  **grands formats** (≥ magnum) ; le prix saisi est celui de la bouteille, jamais recopié sur une demie
  ou un magnum ;
- **coups de cœur** (case « coup de cœur » du vin) mis en avant, **dernière bouteille** signalée ;
- page de garde (logo, titre, lieu, date), **mot d'accueil**, **menu du soir** (un plat par ligne : vin
  de la carte proposé d'après les accords du dossier, avec le pourquoi ; plat inconnu = dit, rien
  d'inventé), **petites cartes des régions**, **index des producteurs** (pages) ;
- trois modèles : **classique** (EB Garamond, petites capitales, bordeaux et or, cadre doré),
  **moderne** (Source Sans, noir et bordeaux), **bistrot** (fond kraft, bandeaux ardoise, Josefin Sans
  et Libre Baskerville) ; livret **A4**, livret **A5**, ou **carte simple** (A4, deux colonnes) ;
- **FR / EN** (langue du document indépendante de l'interface : pays, régions, sections, accords) ;
- **BIN** : celui des bouteilles s'il existe, sinon un numéro par section (1xx effervescents, 2xx blancs…,
  8xx demies, 9xx grands formats) ; **Inscrire les numéros BIN** les écrit dans la cave ;
- **mise à jour d'un clic** : une carte enregistrée (tables `carte`, `carte_vin`) garde ses options, sa
  sélection et ses prix ; « Mettre à jour le PDF » la régénère d'après la cave du jour, au même endroit
  (une bouteille bue disparaît).

### Petites cartes des régions

Les cartes du dossier « Le vin » pèsent 136 Mo (relief, aires parcellaires INAO, rivières OpenStreetMap
sous ODbL) : trop lourdes pour l'application. `outils/cartes_simplifiees.py` fabrique
`vendemiaire/donnees/cartes_simplifiees.json` (≈ 250 Ko) : contours de 33 pays du vin d'après
**Natural Earth 1:10 m (domaine public)**, recadrés et simplifiés, et 77 positions de régions reprises
des étiquettes et cadres des cartes du dossier. Dessinées en TikZ (LaTeX) ou en SVG (aperçu, repli Qt).

## Rapport d'assurance / d'inventaire

`documents/assurance.py` (format maison : Latin Modern, titres bleu ciel et rouge, encadrés, page de
garde). Une ligne par bouteille : emplacement et code, format, **niveau et son sens pour l'âge** (règles
du dossier), état de l'étiquette, de la capsule et du bouchon, **caisse** (CBO complète ou non, repère),
**provenance**, historique de stockage, facture, achat (prix, date, lieu), et **valeur datée et
sourcée** : la dernière valeur saisie pour ce vin dans ce format ; à défaut le prix d'achat, dit comme
tel ; à défaut « non évaluée ». Photo d'étiquette du vin. Résumé chiffré et attestation à signer.

## Partage en lecture seule

`documents/partage.py` : un HTML **autonome** (vignettes incluses, aucun script, aucun lien en ligne) ou
son PDF. Par défaut ni prix, ni valeurs, ni emplacements, ni notes privées : on les ajoute en cochant.

## Statistiques

`vendemiaire/statistiques.py`, onglet `ui/statistiques.py` : répartition par pays, région, couleur,
cépage (au prorata des pourcentages), millésime, tranche de prix, format, cave — en bouteilles ou en
valeur ; valeur de la cave dans le temps (coût d'achat et valeur retenue à chaque fin de mois) ; entrées
et sorties par année (livre de cave) et rythme comparé à la courbe d'apogée ; courbe d'apogée par couleur
(petits multiples). Graphiques à un seul axe, deux séries au plus avec légende (couleurs vérifiées pour les
daltoniens), infobulles.

## Codes QR et codes-barres

- Lecture **à l'image** (webcam, photo) : `zxing-cpp` (Apache 2.0, ≈ 1 Mo, roues Windows/macOS/Linux,
  sans dépendance), en local. Une douchette USB (qui « tape » le code) marche aussi dans le champ de saisie.
- **Étiquettes de casier** : `segno` (BSD, Python pur) dessine le QR du code interne de chaque bouteille
  (« V » + 10 caractères) ; planche A4 vectorielle (3 × 8 de 70 × 37 mm, ou 3 × 7 de 63,5 × 38,1 mm),
  départ possible sur une planche entamée.
- **Scanner une bouteille** : code interne → la bouteille (lieu, statut) et « Sortir cette bouteille… » ;
  EAN → les vins de la cave qui portent ce code.

## Imports Excel et Vivino

`vendemiaire/imports_tableur.py`, fenêtre `ui/import_tableur.py` : XLSX lu directement (sans
dépendance ; dates Excel converties) ou CSV ; **correspondance des colonnes** proposée d'après les
en-têtes (FR/EN) et modifiable ; aperçu des premières lignes. Jamais d'écrasement d'une saisie manuelle.

**Vivino** : pas de format d'export documenté. Le profil « Vivino » propose une correspondance à partir
d'en-têtes plausibles (`Winery`, `Wine name`, `Vintage`, `Region`, `Country`, `Wine type`, `Your rating`,
`Your review`, `Scan date`…) **non vérifiés sur un vrai fichier** : à relire avant d'importer, et à
confirmer sur un véritable export. Une note (étoiles) devient une dégustation sur 5 ; une ligne sans
quantité crée le vin seul.

## Séances de dégustation

`vendemiaire/seances.py`, onglet « Dégustations » : verticale (« Proposer » ajoute les autres millésimes du
même vin en cave), horizontale (même millésime, même appellation ou région), **à l'aveugle** (ordre tiré
au hasard, lettres A, B, C… ; on note chaque verre, puis « Révéler » ; après, les notes sont **figées**),
libre. Les notes sont des dégustations ordinaires (fiche du vin), rattachées à la séance.
