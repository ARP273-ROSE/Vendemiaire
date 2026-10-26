<!-- Copie neutre du cahier des charges (sans données personnelles), tenue à jour avec l'original. -->
# Vendémiaire — cahier des charges (v0, 26/10/2026)

Demande de l'utilisateur : « un programme de gestion de mes bouteilles avec livre de cave et tout, regarde ce qui
se fait sur internet, reprends toute la façon de faire de nos programmes avec le kit standard. Un truc
complet, avec accord mets-vin, qui donne la bonne date d'ouverture, comment le conserver, le servir…
bref fais enquête. » Nom et logo choisis le 26/10 : **Vendémiaire** (mois des vendanges du calendrier
républicain), logo `branding/logo.svg`.

## Ce qui existe (enquête du 26/10, à approfondir en phase 1)
- **CellarTracker** : référence des collectionneurs ; suivi bouteille par bouteille (prix d'achat,
  emplacement, fenêtre de dégustation), énorme base de notes de dégustation communautaires.
- **Vivino** : scanner d'étiquette et achat ; la cave n'y est qu'une fonction secondaire, limitée en gratuit.
- **InVintory** : cave en 3D, fenêtres de dégustation, valeur de marché, « sommelier IA » ; importe
  CellarTracker et Vivino (affirmations de l'éditeur).
- **Oeni** (français, abonnement), **Vinocell**, **Unicellar**, **Open Cellar**, **Cavus Vinifera**, **Caves
  Explorer** (multiplateforme), « À vos vins ».
- Critère qui revient chez les amateurs : la **qualité des fiches** (composition, accords, région,
  apogée estimée) et l'**import/export** (Excel/CSV).
Sources : invintory.com/blog/cellartracker-vs-vivino-wine-app-comparison, gitnux.org/best/wine-cellar-management-software,
lapassionduvin.com (fil « logiciel de gestion de cave », 2009-2016), clubic.com (Caves Explorer).

## Fonctions visées
1. **Cave** : vins (domaine, cuvée, appellation, région, pays, couleur/type, cépages et %, millésime,
   degré, contenance de la piccolo au nabuchodonosor), **bouteilles** individuelles (emplacement,
   prix et lieu d'achat, date d'entrée, état du bouchon/niveau), **plan de cave** (casiers, rangées,
   colonnes, glisser-déposer ; plusieurs caves : maison, résidence secondaire, cave de vieillissement…).
2. **Livre de cave** : journal de toutes les entrées/sorties (achat, cadeau, bue, offerte, cassée,
   bouchonnée), avec l'occasion, les convives, le plat, la note et le commentaire de dégustation
   (grille robe/nez/bouche, échelle /20 ou /100), photos de l'étiquette.
3. **Apogée / date d'ouverture** : fenêtre « à boire de… à… » et pic, estimée à partir du type, de
   l'appellation, du millésime et du niveau du vin (base de règles sourcée — partie « millésimes » et
   « conservation » du dossier Le vin), modifiable ; alertes « à boire cette année », « en déclin »,
   « trop jeune » ; graphique de la courbe d'apogée de la cave.
4. **Servir** : température de service, carafe (oui/non, combien de temps), verre conseillé, quand
   sortir la bouteille de la cave ; fiche « ce soir » imprimable.
5. **Accords mets-vins** : dans les deux sens (« j'ai ce plat → quelles bouteilles de MA cave ? » et
   « j'ouvre ce vin → quels plats ? »), base de règles sourcée et expliquée (pourquoi ça marche).
6. **Conservation** : conseils par type (température, hygrométrie, lumière, position), alerte de
   bouteilles au bouchon fatigué (vieux millésimes), suivi optionnel de la température de la cave.
7. **Valeur** : prix d'achat, valeur estimée datée (saisie ou import), total de la cave, statistiques
   (par région, couleur, millésime, cépage, prix), graphiques.
8. **Saisie rapide** : recherche/complétion dans une base de référence (appellations, cépages,
   domaines) ; photo d'étiquette ; lecture de code-barres si webcam (option) ; import/export CSV et
   import CellarTracker ; sauvegardes automatiques.
9. **Liste d'achats / cave idéale**, et « que boire ce soir ? » (filtres + apogée + plat + budget).

## Fonctions des spécialistes et des meilleurs logiciels (demande du 26/10 : « tout ce qu'utilisent les spécialistes et les meilleurs logiciels »)
Enquête complémentaire du 26/10 : CellarTracker (support.cellartracker.com/article/32-what-can-be-tracked,
mobileapp.cellartracker.com), outils de sommellerie (home.binwise.com, restroworks.com), maisons de ventes et
garde-meubles de vins (winebid.com/Help/AuctionTerminology, uovo.com « Understanding Ullage », catalogue Webb's
nov. 2025, decanter.com). Chaque fonction ci-dessous doit exister dans Vendémiaire.

**Collectionneur (CellarTracker, InVintory, Vinocell…)**
- Statut de chaque bouteille : **en cave / en attente de livraison / achetée en primeur (futures) / bue / offerte /
  vendue / cassée / bouchonnée** ; suivi des **achats en primeur** (date de livraison prévue, relance).
- **Emplacements à plusieurs niveaux** (cave › meuble › casier › rangée › colonne) et **déplacement en lot** ;
  historique des déplacements ; plan visuel des casiers (et vue 3D simple si faisable).
- **Fenêtres de dégustation à trois sources** : la mienne, celle des critiques (saisie), celle calculée par
  Vendémiaire — avec le **pourquoi** de l'estimation ; plusieurs modèles d'apogée (courbe en cloche, plateau).
- **Notes de critiques** (Parker/RP, Wine Spectator, Decanter, Bettane+Desseauve, Jancis Robinson…) saisies avec
  leur échelle, et **conversion** /100 ↔ /20 ↔ étoiles ; mes notes de dégustation privées ou exportables.
- **Valeur** : prix d'achat, prix de marché saisi ou importé avec date et source, plus/moins-value, évolution.
- **Liste d'envies**, alertes de prix, « cave idéale » par région et par millésime.
- Import **CellarTracker / Vivino / CSV / Excel**, export identique : aucune donnée prisonnière.
- **Lecture d'étiquette** (photo → recherche des champs) et **code-barres** EAN si une webcam est disponible ;
  **impression d'étiquettes de casier** (code QR par bouteille → scanner pour sortir une bouteille).
- **Tableaux de bord** : répartition par pays, région, couleur, cépage, millésime, prix, apogée
  (« combien de bouteilles à boire chaque année pendant 20 ans ») ; rythme de consommation vs achats.

**Maisons de ventes, assureurs, garde-meubles**
- **Niveau du vin (ullage)** avec l'échelle des ventes aux enchères, illustrée : bordelaise (into neck, top
  shoulder, very high shoulder, high shoulder, mid shoulder, low shoulder…) et bourguignonne (en cm sous le
  bouchon), avec ce que chaque niveau signifie selon l'âge du vin.
- **État** : étiquette (abîmée, tachée, déchirée), capsule (coupée, corrodée, fuite), bouchon (enfoncé, sorti),
  **caisse bois d'origine (CBO / OWC)** ou carton, caisse complète ou non ; photos.
- **Provenance** : origine de l'achat, historique de stockage (« achetée au domaine, jamais déplacée »), facture.
- **Rapport d'assurance / d'inventaire en PDF** (format maison) : liste, photos, état, valeur datée et sourcée.

**Sommellerie (BinWise, outils de restaurant), utiles aussi à un particulier**
- **Seuil de réassort** par vin (« garder au moins 6 bouteilles de ce champagne ») et liste d'achats générée.
- **Inventaire de contrôle** (compter un casier, écarts signalés).
- **Bouteille ouverte** : suivi de ce qui reste et de combien de jours elle se garde selon le type et le mode
  de conservation (bouchon, gaz, Coravin).
- **Carte des vins imprimable** de ma cave (pour un dîner : liste des vins proposés avec les accords).

**Dégustation et partage**
- Dégustations **verticales** (un vin sur plusieurs millésimes) et **horizontales** (plusieurs vins d'un même
  millésime), **à l'aveugle** (on note avant de révéler) ; fiche de dégustation structurée (robe, nez, bouche,
  finale, arômes choisis dans la roue des arômes).
- **Partage** en lecture seule de la cave (export HTML/PDF), sans service en ligne obligatoire.

**Conditions de cave**
- Saisie ou import de la **température et de l'hygrométrie** (sonde USB, CSV, Home Assistant si présent) ;
  courbes et alertes hors plage.

**Principes**
- Tout fonctionne **hors ligne** et en local (données chez l'utilisateur, pas d'abonnement) ; les recherches en ligne
  (prix, fiches) restent optionnelles et sourcées.
- Toutes les règles d'apogée, de service, d'accords et de niveaux viennent du dossier « Le vin », avec leurs
  sources, et sont affichées avec leur explication.

## Référencer chaque bouteille dans une base mondiale (demande du 26/10 : « comme pour un morceau de musique »)
Équivalent vin de MusicBrainz pour MusicOthèque : chaque vin de la cave reçoit un **identifiant mondial** et ses
fiches se remplissent seules. Enquête du 26/10 :
- **LWIN (Liv-ex Wine Identification Number)** — le « code ISBN du vin » du commerce des grands vins : base
  **gratuite sous licence Creative Commons**, téléchargeable (XLSX), plus de 200 000 vins et spiritueux, code à
  7 chiffres (6 + clé de contrôle) pour le vin, 11 chiffres avec le millésime (liv-ex.com/lwin, get-lwin-database).
  → copie locale dans Vendémiaire, recherche **hors ligne**, mise à jour périodique ; c'est l'identifiant principal.
- **Wikidata** (requêtes SPARQL, données libres CC0) : domaines, châteaux, maisons, appellations, cépages —
  coordonnées, date de fondation, propriétaires, photos Wikimedia Commons, liens Wikipédia.
- **Open Food Facts** (API REST ouverte, licence ODbL) : lecture du **code-barres EAN** de la bouteille → nom,
  degré, photo ; l'utilisateur peut y contribuer les bouteilles manquantes.
- **Registres officiels des appellations** : eAmbrosia / GIview de l'UE (export Excel, géré par l'EUIPO) et
  données de l'INAO (data.gouv) → liste exacte et orthographe officielle des AOP/IGP ; équivalents étrangers
  (AVA américaines, GI australiennes…) si publiés.
- **CellarTracker** : import du fichier exporté par l'utilisateur (ses propres données).
- **Vivino, Wine-Searcher** : **pas d'API publique officielle** (l'API de Vivino est bloquée ; les « API » trouvées
  sont des aspirateurs tiers qui contreviennent probablement à leurs conditions) → **aucun aspirateur** ; un bouton
  ouvre seulement la page du vin dans le navigateur.
Règles d'appariement à reprendre de MusicOthèque (mémoire « Apparier un morceau à MusicBrainz ») : normalisation
des noms (accents, « Château », « Domaine », abréviations), proposition des meilleurs candidats avec un score
expliqué, **confirmation par l'utilisateur** avant d'écrire, jamais d'écrasement d'une donnée saisie à la main
(COALESCE), journal de ce qui a été rempli et d'où.

## Photo de l'étiquette = « pochette » du vin (demande du 26/10)
Chaque vin a son **visuel**, affiché partout comme la pochette d'un disque dans MusicOthèque (liste, plan de
cave, fiche, carte des vins, livre de cave) :
- **Ma photo** (webcam, fichier, photo du téléphone déposée dans un dossier partagé) : recadrage et redressement
  automatiques de l'étiquette (détection des bords + correction de perspective ; « déroulage » de l'étiquette
  sur la bouteille cylindrique si faisable), réglage manuel possible ; recto, contre-étiquette, capsule, caisse.
- **Images libres** trouvées automatiquement : Open Food Facts (photos de produit, licence CC BY-SA) et Wikimedia
  Commons (étiquettes et bouteilles de domaines célèbres), crédit et licence enregistrés avec l'image.
- **Pas de téléchargement automatique** d'images protégées (sites des domaines, marchands, Vivino) : l'utilisateur peut
  en glisser une à la main pour son usage personnel.
- La photo sert aussi à **identifier le vin** : lecture du texte de l'étiquette (OCR local) → recherche dans
  LWIN / Wikidata / Open Food Facts → candidats proposés.
- Vignettes en cache, photo d'origine conservée, poids maîtrisé ; mur d'étiquettes (« vue galerie ») de la cave.

## Carte des vins « de grand restaurant » (demande du 26/10)
« Une belle carte des vins, présentation LaTeX ou autre comme grand restaurant, tu recherches et tu gères. »
Générée depuis la cave (tout ou sélection : « dîner de samedi »), en **PDF LaTeX** (qualité typographique, format
livret A5/A4 ou carte simple), avec aperçu HTML. Règles tirées de l'enquête du 26/10 (vinography.com « How to
Properly Design a Wine List » 2018 et « Mastering the Graphic Design » 2020 — l'auteur est juré des World's Best
Wine Lists ; musthavemenus.com ; matthewclark.co.uk ; étude ISCTE sur 61 restaurants haut de gamme portugais ;
cours d'hôtellerie TICFP et académie de Versailles ; lapassionduvin.com ; blick.ch) :
- **Ordre classique** : effervescents/champagnes → blancs → rosés → rouges → vins doux et liquoreux → vins mutés
  (porto, xérès) ; dans chaque couleur, **par pays puis région puis appellation** (France d'abord en option),
  sous-sections par cépage possibles ; au sein d'une appellation, par producteur puis millésime ; **jamais trié
  par prix** (option : prix croissant à l'intérieur d'une appellation, usage des écoles hôtelières).
- **Chaque ligne** : numéro de référence (BIN), **producteur / domaine**, cuvée, **appellation**, **millésime**,
  **format** (demi, bouteille, magnum…), prix (si l'on veut en afficher), éventuellement degré, cépages et une
  ligne de description ou d'accord ; **verticales** regroupées (un domaine sur plusieurs millésimes).
- **Typographie** : une ou deux polices lisibles (pas de cursive en petit), titres de sections plus grands et en
  gras, filets fins, points de conduite vers le millésime/prix alignés en tabulation, beaucoup de blanc ; modèles :
  « classique » (romain + petites capitales, bordeaux et or comme le logo), « moderne » (sans-serif), « bistrot ».
- **Extras de grande maison** : page de garde avec logo/nom du lieu et date, mot du sommelier, petites cartes des
  régions (réutiliser les cartes du dossier « Le vin »), section « au verre / à la carafe », demi-bouteilles et
  grands formats à part, coups de cœur et vins rares mis en avant, accords proposés pour un menu saisi
  (« menu du soir » → vin suggéré par plat), index des producteurs.
- Mise à jour d'un clic quand la cave change (une bouteille bue disparaît de la carte, comme chez BinWise).
- Bilingue FR/EN comme le reste de l'appli.

## Lien avec le dossier « Le vin »
Le dossier lit la base de Vendémiaire (copie en lecture seule) pour créer ses encadrés « Les bouteilles de
la cave ». Prévoir un export simple et stable (vue SQL ou
JSON documenté : vin, région, pays, millésime, photo d'étiquette, notes) et l'emplacement de la base
accessible au NAS (base partagée sur un lecteur réseau si l'appli tourne sur un PC).

## Forme : STANDARD des applications (mémoire `standard-applications-kit`)
Kit commun `_kit_windows` posé par `poser_le_kit.py --multiplateforme` ; Windows/macOS/Linux ; MAJ auto ;
rapports d'incident (poste = nom de machine) ; **bilingue FR/EN** testé ; tests en CI dont l'interface ;
**style fixé** (Fusion + palette Vendémiaire) ; **vrai explorateur de fichiers** ; **manuel PDF LaTeX**
(format maison, FR+EN, captures réelles) ; **icône et logo** dérivés de `branding/logo.svg` ; publication
VERSION + JOURNAL + README FR/EN ; commits noreply sans mention de Claude ; garde-fou de confidentialité
à empreintes si dépôt public. Données hors du dossier d'installation ; base SQLite, un seul écrivain.

## Organisation
Développement APRÈS la phase 1 du dossier « Le vin » . Les règles d'apogée, de
service et d'accords viennent des parties V et VI du dossier, avec leurs sources, pour que l'appli et le
dossier disent la même chose.
