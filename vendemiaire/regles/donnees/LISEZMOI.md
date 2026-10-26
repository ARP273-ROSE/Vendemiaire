# Règles du vin — données partagées entre le dossier « Le vin » et Vendémiaire

Ces fichiers JSON sont la **source unique** des règles de service, de garde, de conservation, d'accords,
de niveaux, de notes et de défauts. Le dossier LaTeX (Parties V et VI) en tire ses tableaux
(`gen/regles_*.tex`) ; le logiciel Vendémiaire (phase 3, `vendemiaire/regles/`) doit les lire **tels
quels** : une règle se corrige ici, à un seul endroit, puis on relance `python3 scripts/regles.py`
et `./build.sh`.

- Générés par `scripts/regles.py` (ne pas éditer les JSON à la main : modifier le script).
- Calculs amont : `scripts/garde_empirique.sage` (fenêtres de garde tirées des tableaux de millésimes),
  `scripts/calculs_partie5.sage` (refroidir et chambrer une bouteille), `scripts/millesimes_croisement.sage`
  (millésimes croisés), `scripts/accords_corpus.py` (accords attestés).
- Version et date en tête de chaque fichier (`version`, `date`) ; `schema` renvoie à ce document.

## Champs communs d'une règle

| Champ | Contenu |
|---|---|
| `id` | identifiant stable (`temp.rouge_puissant`, `carafe.vieux_rouge_depot`…) : Vendémiaire le range dans `fenetre_degustation.detail_source` |
| `styles` | liste d'identifiants de `styles.json`, ou `["*"]` pour tous |
| `valeur` | la recommandation chiffrée (températures en °C, durées en minutes, heures, jours ou années) |
| `marge` | marge d'incertitude, mêmes unités que `valeur` (`{"c": 2}` = ±2 °C ; `{"relative": 0.3}` = ±30 %) |
| `confiance` | `haute` (plusieurs sources concordantes), `moyenne` (une source sérieuse, ou des sources qui divergent un peu), `faible` (avis isolé ou **convention du dossier**, source `DOSSIER`) |
| `explication_fr`, `explication_en` | le « pourquoi », à afficher avec la règle |
| `sources` | identifiants de `sources.json` (titre, fichier archivé dans le dépôt, nature) |

Une règle dont la source est `DOSSIER` est une **convention** faute de chiffre publié : l'interface doit
le dire et laisser l'utilisateur la changer.

## Les fichiers

| Fichier | Contenu | Méthodes Vendémiaire (`FournisseurRegles`) |
|---|---|---|
| `sources.json` | registre des sources | — |
| `styles.json` | 28 familles de vins et leurs critères de classement | (classement préalable de tout vin) |
| `service.json` | `temperature` (min/max par style), `ajustements_temperature` (servir 1-2 °C sous la cible, +1 °C pour un vieux vin, plafond 18 °C), `sortie_de_cave` (minutes pour atteindre chaque température, loi de Newton calibrée), `carafe` (action `carafer` / `decanter` / `facultatif` / `non` / `aerer_si_odeur` / `ouvrir_a_l_avance`, durées), `verre` | `service(vin)` |
| `garde.json` | par style, une ou plusieurs fenêtres selon le `niveau` (`courant`, `garde`, `primeur`, `nouveau_monde`, `tous`) ; `ajustements` (millésime, température de cave, format) ; `regression` (calcul) | `fenetre_degustation(vin, bouteille)` |
| `millesimes.json` | notes des millésimes par région et par source (Wine Enthusiast 2018, The Wine Society 2026, Wine Spectator 2026, Berry Bros. & Rudd 2026), écart normalisé et désaccords | (ajustement millésime de la garde) |
| `conservation.json` | température, variations, hygrométrie, lumière, vibrations, position, réfrigérateur, bouchon fatigué | `conservation(vin, bouteille)` |
| `bouteille_ouverte.json` | jours de garde après ouverture par style et mode (`bouchon`, `vide/gaz`, `coravin`) | `bouteille_ouverte(vin, conservation)` |
| `niveaux.json` | échelle bordelaise (codes `IN BN VTS TS HS MS LS BLS` identiques à `referentiels.niveau`) et bourguignonne en cm, avec l'âge à partir duquel le niveau est normal | `sens_niveau(code, age)` |
| `notes.json` | table Decanter 100 ↔ 20 points (mentions, médailles), échelles Wine Spectator et Wine Enthusiast, étoiles Hachette, règle de conversion | `convertir_note(note, de, vers)` |
| `defauts.json` | défauts (molécule, seuil, ce qu'on sent, cause, que faire) | (fiche de dégustation, statut « bouchonnée ») |
| `aromes.json` | roue des arômes : codes `P.*` (primaires), `S.*` (secondaires), `T.*` (tertiaires), `X.DEF` (défauts) et descripteurs | `degustation.aromes` (codes séparés par « ; ») |
| `accords.json` | `principes` (poids, acidité, sucre, tanins, sel, gras, umami, piment, région, fromage), `plats` (plat → styles, pourquoi, sources, phrases attestées `preuves_corpus`), `accords_difficiles` | `accords_pour_vin(vin)` (inverser `plats`), `vins_pour_plat(plat, vins)` |
| `accords_corpus.json` | phrases d'accords extraites des articles Wikipédia archivés (article, URL, révision) | (preuves) |

## Classer un vin dans un style (`styles.json`)

Prendre les styles par `priorite` croissante ; un style convient si :
1. la couleur du vin est dans `criteres.couleur` et son type dans `criteres.type` ;
2. si au moins une des listes `appellations`, `regions`, `mots`, `cepages` est non vide, **au moins une**
   expression de ces listes est trouvée (insensible à la casse et aux accents) dans l'appellation, la cuvée,
   la région ou les cépages du vin.
Les styles de priorité ≥ 90 n'ont que couleur et type : ce sont les styles par défaut.

## Calculer une fenêtre de garde (`garde.json`)

1. Style du vin → liste de fenêtres ; choisir le `niveau` (`garde` par défaut ; `courant` pour un vin
   d'entrée de gamme ; `nouveau_monde`, `primeur` ou `tous` quand ils existent).
2. Années : `pret`, `apogee_debut`, `apogee_fin`, `fin` (après le millésime ; `null` = non chiffré).
3. Ajustement millésime : décaler toute la fenêtre de `ans_par_point_100 × (note − moyenne de la région)`
   (note Wine Enthusiast ou Wine Spectator) ou de `ans_par_point_10 × (note − moyenne)` (The Wine Society
   ou Berry Bros.), moyennes dans `millesimes.json`.
4. Ajustement cave : diviser les durées par `2^((T−12)/10)` si la cave n'est pas à 12 °C.
5. Afficher `marge_ans`, `modele` (`plateau` ou `cloche`), `confiance`, `explication_fr` et `sources`.
Ranger le résultat dans `fenetre_degustation` avec `source='calcul'` et `detail_source=<id de style>/<niveau>`.

## Origine des chiffres

- Températures : WSET, Comité et Bureau du Champagne, Mumm, iDealwine, formation Elephorm, tableau
  du Clube de Vinhos Portugueses, Catavino (xérès) ; vin jaune : avis d'amateurs (confiance faible).
- Garde : seuils de maturité tirés des 2 480 cases du tableau Wine Enthusiast 2018 (couleur des cases
  lue sur le rendu du PDF) et des formes de bouteille du tableau The Wine Society 2026 ; repères de
  Jancis Robinson ; régression SageMath « années par point de note ».
- Ouvert : Wine Folly, Decanter, Healthline, Catavino (fourchettes qui divergent : on garde l'enveloppe).
- Niveaux : WineBid, Tennants, Abbey's Auctions.
- Notes : Decanter (table publiée), Wine Spectator, Wine Enthusiast, Guide Hachette.
- Accords : Wikipédia EN « Wine and food pairing », spécification WSET niveau 3, études (fer et poisson,
  fromage et vin, piment et alcool), phrases attestées dans 155 articles d'appellations et de vins.
