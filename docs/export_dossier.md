# Export stable pour le dossier « Le vin »

Le dossier LaTeX « Le vin » lit la cave **en lecture seule** pour composer ses encadrés sur les bouteilles
de la cave. Deux accès, au choix :

1. **Vues SQL** `v_dossier_vin` et `v_dossier_livre` (schéma v3 et suivants), à lire avec une connexion en
   lecture seule : `sqlite3.connect("file:/chemin/cave.db?mode=ro", uri=True)` — ou `Base.lecture_seule()`.
2. **JSON** : `python -m vendemiaire.export_dossier <cave.db> <sortie.json> [--sorties-seulement]`.

Aucun des deux ne prend le verrou d'écriture : l'application peut rester ouverte (un seul écrivain, des
lecteurs). Sur un partage réseau, lire de préférence une **copie** de la base (ou la dernière sauvegarde
du dossier `sauvegardes/`) plutôt que le fichier vivant.

## Contrat de stabilité

- On peut **ajouter** des colonnes en fin de vue ; on n'en retire ni n'en renomme jamais.
  Une forme incompatible = une nouvelle vue suffixée `_v2`, et `version` du JSON passe à 2.
- `photo_etiquette` est **relatif** au dossier `images/` des données (à côté de `cave.db`) ;
  le JSON ajoute `photo_etiquette_absolue` quand le fichier existe.

## `v_dossier_vin` — une ligne par vin

| Colonne | Contenu |
|---|---|
| `vin_id` | identifiant du vin |
| `domaine` | producteur (domaine, château, maison) |
| `cuvee`, `appellation`, `region`, `sous_region`, `pays` | identité et origine |
| `couleur`, `type` | codes : `rouge`/`blanc`/`rose`/`orange` ; `tranquille`/`effervescent`/`doux`/`mute`/`autre` |
| `millesime` | année, ou NULL (non millésimé) |
| `cepages` | « Merlot 70%; Cabernet franc 30% » |
| `photo_etiquette`, `photo_credit`, `photo_licence` | photo principale de l'étiquette et ses droits |
| `notes` | notes libres du vin |
| `bouteilles_en_cave` | nombre de bouteilles présentes |

## `v_dossier_livre` — une ligne par entrée ou sortie du livre de cave

| Colonne | Contenu |
|---|---|
| `mouvement_id`, `date` (AAAA-MM-JJ), `type` | `entree_achat`, `sortie_bue`, `sortie_offerte`… |
| `vin_id`, `domaine`, `cuvee`, `appellation`, `region`, `pays`, `millesime` | le vin |
| `occasion`, `convives`, `plat`, `lieu` | le contexte |
| `note`, `echelle` | note et son échelle (`20`, `100`, `5`, `3`) |
| `commentaire` | commentaire de dégustation |
| `photo_etiquette` | photo principale de l'étiquette du vin |

## JSON (`format: vendemiaire-dossier`, `version: 1`)

```json
{"format": "vendemiaire-dossier", "version": 1, "schema_base": 3, "date": "2026-10-26",
 "vins":  [{"vin_id": 1, "domaine": "...", "...": "...", "photo_etiquette_absolue": null}],
 "livre": [{"mouvement_id": 12, "date": "2026-09-24", "type": "sortie_offerte", "...": "..."}]}
```

L'essai `tests/test_echanges.py::test_export_dossier_le_vin` garde la liste des clés.
