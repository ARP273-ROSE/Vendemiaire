# Bases mondiales, registres et appariement

Menu **Références** : identifier un vin, une bouteille d'après sa photo ou son code-barres, et
gérer les bases de référence. Tout ce qui suit est **facultatif** : la cave fonctionne sans.

## Sources et licences

| Source | Ce qu'elle apporte | Accès | Licence (affichée dans l'application) |
|---|---|---|---|
| **LWIN** (Liv-ex) | identifiant mondial du vin (LWIN-7, LWIN-11 = + millésime), producteur, région, sous-région, couleur, type, classement | copie **locale** du fichier XLSX, recherche hors ligne | CC BY 4.0 — « LWIN © Liv-ex Ltd », copie convertie (modification signalée) |
| **Wikidata** | domaines, châteaux, appellations, cépages : fondation, coordonnées, propriétaires, site, liens Wikipédia | API `wbsearchentities` + SPARQL | CC0 |
| **Wikimedia Commons** | image d'un domaine | API `imageinfo` (auteur, licence, vignette) | licence de chaque fichier, enregistrée avec l'image |
| **Open Food Facts** | lecture du code-barres EAN : nom, degré, photo | API REST, lecture sans compte | base ODbL, contenus DbCL, photos CC BY-SA (crédit « Open Food Facts contributors ») |
| **INAO** (data.gouv.fr) | appellations et dénominations françaises, orthographe officielle | CSV embarqué + mise à jour en ligne | Licence Ouverte 2.0 |
| **eAmbrosia** (Commission européenne) | AOP/IGP viticoles de l'UE et des pays tiers protégés | copie embarquée + API publique | © UE, réutilisation autorisée (décision 2011/833/UE) |

**Jamais d'aspirateur** : Vivino et Wine-Searcher n'ont pas d'API publique ; un menu « Sur le Web »
ouvre seulement une recherche dans le navigateur.

## LWIN : copie locale

Liv-ex remet le fichier par un **formulaire** (nom, adresse électronique) : le bouton « Page de
téléchargement de Liv-ex » l'ouvre dans le navigateur, puis « Importer le fichier LWIN… » le convertit
(XLSX ou CSV, lecteur en flux sans dépendance). Si Liv-ex fournit un **lien direct**, on peut le
retenir et cocher la mise à jour tous les 30 jours (seulement si les recherches en ligne sont permises).

- Le fichier n'est **pas dans le dépôt** (taille, et il se remet par formulaire) ; il est converti dans
  `references.db`, à côté de `cave.db` (hors des sauvegardes de la cave).
- Mesure sur 205 000 lignes : import ≈ 15 s dans un fil de fond (la cave reste utilisable), base
  ≈ 60 Mo avec l'index plein texte (FTS5), recherche ≈ 0,15 s.
- Import **tout ou rien** : un fichier tronqué laisse l'ancienne copie intacte.
- En-têtes reconnus : `LWIN, STATUS, DISPLAY_NAME, PRODUCER_TITLE, PRODUCER_NAME, WINE, COUNTRY,
  REGION, SUB_REGION, SITE, PARCEL, COLOUR, TYPE, SUB_TYPE, DESIGNATION, CLASSIFICATION,
  VINTAGE_CONFIG, FIRST_VINTAGE, FINAL_VINTAGE, DATE_ADDED, DATE_UPDATED` (casse indifférente) ; les
  lignes `Deleted` sont écartées.

## Appariement (règles reprises de MusicOthèque)

1. Formes **normalisées** (accents, casse, « Château », « Domaine », « St » → saint, « 1er » → premier…).
2. Score **calculé par Vendémiaire**, critère par critère, et **expliqué** : domaine (45 %), cuvée
   (20 %), appellation (15 %), couleur (10 %, une contradiction divise le score), pays (5 %),
   millésime dans la période produite (5 %). Le rang plein texte de la source ne compte pas.
3. Sous 0,45 : rien n'est présélectionné. Si les deux premiers sont à moins de 0,05 : Vendémiaire
   **renonce** à choisir.
4. **Confirmation** : la fenêtre montre, champ par champ, ce qui sera rempli ; seuls les champs
   **vides et non saisis à la main** peuvent l'être (`COALESCE`), chaque remplissage est noté au
   **journal** (fiche du vin › Références) avec sa source, et l'identifiant est gardé avec son score
   et son explication.
5. L'appellation n'est proposée que si la sous-région ou le site LWIN **est** une appellation des
   registres officiels.

## Réseau

Hors ligne par défaut : l'accord est demandé à la première recherche en ligne (modifiable dans
Références › Bases de référence). User-Agent `Vendemiaire/<version> (+https://github.com/ARP273-ROSE/Vendemiaire)`,
une requête par seconde au plus par service, `Retry-After` respecté (plafonné à 30 s).

## Contribuer à Open Food Facts (option)

Une bouteille absente d'Open Food Facts peut y être ajoutée **par l'utilisateur** (site ou
application mobile d'Open Food Facts, page `https://world.openfoodfacts.org/product/<EAN>`) ; ses
photos y sont alors publiées sous CC BY-SA. Vendémiaire n'écrit jamais dans Open Food Facts.
