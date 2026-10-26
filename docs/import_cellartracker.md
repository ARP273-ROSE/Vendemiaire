# Import d'un export CellarTracker

Menu **Fichier › Importer un export CellarTracker…** (`echanges.importer_cellartracker`).
Une sauvegarde « avant-import » de la base est faite d'abord.

## Fichiers acceptés

CellarTracker exporte ses tables en CSV (ou texte tabulé) depuis son menu d'export. Deux formes sont reconnues :

| Forme | Reconnue à | Une ligne = |
|---|---|---|
| **Inventory** (bouteilles) | colonne `iInventory` | une bouteille |
| **List / My Cellar** (vins) | pas de `iInventory` | un vin : `Quantity` bouteilles en cave + `Pending` en attente de livraison |

Encodage : UTF-8 (avec ou sans BOM) ou Windows-1252 ; séparateur `,` `;` ou tabulation (détectés).
Les noms de colonnes sont comparés sans tenir compte de la casse. La valeur `Unknown`, que CellarTracker
écrit dans les champs non renseignés, est traitée comme un champ vide.

## Correspondance des colonnes

| CellarTracker | Vendémiaire |
|---|---|
| `Producer` | producteur |
| `Designation` (à défaut : `Wine` sans le producteur) | cuvée |
| `Vintage` (`1001` = non millésimé) | millésime, case « non millésimé » |
| `Appellation`, `Region`, `SubRegion`, `Country` | appellation, région, sous-région, pays |
| `Color` + `Type` | couleur (rouge, blanc, rosé, orange) |
| `Category` + `Type` (`Sparkling`, `Sweet`/`Dessert`, `Fortified`) | type (effervescent, doux, muté ; sinon tranquille) |
| `Varietal` (à défaut `MasterVarietal`) | cépage (sans pourcentage) |
| `UPC` / `EAN` | code-barres |
| `iWine` | identifiant externe `cellartracker` (confirmé) |
| `Size` (`750ml`, `1.5L`, `375ml`…) | format le plus proche (bouteille, magnum, demi…) |
| `Price` (à défaut `NativePrice`), `Currency` | prix d'achat, devise |
| `StoreName` | lieu d'achat |
| `PurchaseDate` (`M/J/AAAA` ou ISO) | date d'achat |
| `Location` › `Bin` | emplacement « cave › casier » (créé s'il manque, sans grille) |
| `Valuation` / `Value` | valeur datée du jour de l'import, source `cellartracker` |
| `BeginConsume`, `EndConsume` | fenêtre de dégustation, source « critique », détail « CellarTracker » |
| `WA`, `WS`, `JR`, `IWC`, `BH`, `AG`, `WE`, `JS`, `VM`, `DEC`, `CT` | notes des critiques (WA = Robert Parker / Wine Advocate ; JR sur 20, les autres sur 100) |
| `Note` / `PurchaseNote` | notes de la bouteille |

Ce qui est ignoré : les autres colonnes (taux de change, vignoble, etc.) — elles restent dans le fichier d'origine.

## Règles

- Un vin déjà présent (même producteur, cuvée, millésime et appellation, comparés sur leurs formes
  normalisées) est **complété**, jamais remplacé : seuls ses champs vides sont remplis, et jamais un champ
  saisi ou vidé à la main (`origine_champ`). Chaque remplissage est noté dans `journal_enrichissement`.
- Réimporter le même export « Inventory » ne crée pas de doublon (code interne `CT<iInventory>`).
  Un export « List » n'a pas d'identifiant de bouteille : le réimporter ajoute à nouveau ses quantités.
- Les bouteilles importées n'ajoutent pas de ligne au livre de cave (ce n'est pas un achat du jour).

## À vérifier sur un vrai export

Les noms de colonnes ci-dessus suivent les exports CellarTracker documentés et couramment rencontrés ;
les essais (`tests/test_echanges.py`) utilisent des fichiers **fictifs** de cette forme
(`tests/donnees/`). Un premier import réel dira s'il manque une colonne (à ajouter dans
`echanges.importer_cellartracker`, avec un essai).
