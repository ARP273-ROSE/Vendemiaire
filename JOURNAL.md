# Vendémiaire — journal

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
