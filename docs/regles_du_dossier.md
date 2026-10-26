# Les règles du dossier « Le vin » dans Vendémiaire

Vendémiaire n'invente aucune règle d'œnologie. Garde, service, conservation, niveaux, accords,
défauts et arômes viennent des fichiers `data/regles/*.json` du dossier « Le vin » — les mêmes qui
produisent les tableaux du dossier —, copiés **octet pour octet** dans `vendemiaire/regles/donnees/`.

## Copie et contrôle

- `outils/synchroniser_regles.py` copie les fichiers et écrit `MANIFESTE.json` (empreinte SHA-256,
  version et date de chaque fichier, date de l'audit des règles : 2026-10-26).
- `outils/synchroniser_regles.py --verifier` compare sans rien écrire (code 1 s'il y a une différence).
  Le dossier est cherché dans `VENDEMIAIRE_DOSSIER_VIN`, sinon à côté du dépôt (`../_docs/Vin`).
- Au chargement (`regles/jeu.py`), un fichier dont l'empreinte diffère du manifeste est refusé, de
  même qu'une règle à la source ou au style inconnus. Une règle se corrige **dans le dossier**.
- Les essais `tests/test_regles.py` vérifient les cinq vins de référence du dossier (muscadet,
  Nuits-Saint-Georges, Léoville Las Cases, Dom Pérignon, Petrus) et, quand le dossier est présent,
  relisent ses tableaux générés pour comparer **toutes** les fenêtres, températures et accords.

## Ce que l'application calcule, et comment

| Sujet | Fichier | Méthode |
|---|---|---|
| Style | `styles.json` | styles par priorité ; couleur et type, puis au moins une expression trouvée dans l'appellation, la cuvée, la région ou les cépages. Imposable à la main (saisie du vin). |
| Fenêtre | `garde.json`, `millesimes.json` | niveau `garde` par défaut (au choix : courant, primeur, Nouveau Monde) ; âges après le millésime (sans millésime : après l'entrée en cave) ; décalage de 0,44 an par point sur 100 (1,76 sur 10) au-dessus de la moyenne de la région dans le même tableau (Wine Enthusiast, puis The Wine Society, Wine Spectator, Berry Bros.) ; durées divisées par 2^((T−12)/10) pour la température moyenne **mesurée** de la cave ; modèle plateau ou cloche (pic au milieu de l'apogée). Marges affichées séparément. |
| Service | `service.json` | température du style, +1 °C pour un vieux rouge de garde (15 ans), plafond 18 °C ; on verse au bas de la plage ; sortie de cave par la loi de Newton du dossier (τ = 2,58 h dans l'air, 37,6 min en seau ; pièce 20 °C, réfrigérateur 4 °C, eau glacée 0 °C) ; carafe et verre du style. |
| Conservation | `conservation.json` | plages 10–15 °C et 55–75 % (mesures hors plage signalées), contrôle des bouchons au-delà de 15 ans. |
| Bouteille ouverte | `bouteille_ouverte.json` | jours selon le style et le mode (bouchon ; pompe à vide ou gaz ; Coravin). La date « à finir avant » est le haut de la fourchette. |
| Niveaux | `niveaux.json` | normal / excellent / bas pour l'âge / risqué, échelle bordelaise et bourguignonne. |
| Accords | `accords.json` | « j'ouvre ce vin » = plats qui citent le style ; « j'ai ce plat » = recherche tolérante, bouteilles du style, urgences d'abord. |
| Défauts, arômes | `defauts.json`, `aromes.json` | aide au diagnostic ; roue des arômes de la fiche de dégustation (`degustation.aromes` = « CODE:descripteur » séparés par « ; »). |

La fenêtre calculée est rangée dans `fenetre_degustation` avec `source='calcul'` et
`detail_source='<style>/<niveau>'`. Votre fenêtre (« la mienne ») puis celle d'un critique passent
toujours avant.

## Ce qui n'est PAS calculé

- **Format** : le dossier dit qu'un magnum vieillit plus lentement et une demi-bouteille plus vite,
  sans chiffre : l'application le signale, la fenêtre ne change pas.
- **Note d'un critique sur le vin lui-même** : aucune règle du dossier ne la relie à la garde ; seule la
  note du **millésime** (tableaux publiés) décale la fenêtre.
- Une règle de source `DOSSIER` est une convention faute de chiffre publié : l'interface le dit.

## Données de l'application (pas du dossier)

- `regles/millesimes.py`, table `RATTACHEMENT` : quelles appellations entrent dans chacune des 27
  régions des tableaux de millésimes (le dossier nomme ses régions sans liste d'appellations).
- `regles/anglais.py` : traduction anglaise des libellés qui n'existent qu'en français dans les JSON
  (aucune valeur changée). Les titres des sources restent dans la langue du document cité.
