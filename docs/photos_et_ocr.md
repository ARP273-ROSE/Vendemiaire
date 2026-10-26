# Photos d'étiquette et lecture du texte (OCR)

## La « pochette »

Chaque vin a son visuel : la photo de son étiquette (ou une étiquette dessinée), affichée dans la
liste, la fiche et le **mur d'étiquettes**. Ajout : bouton « Photo de l'étiquette… », fenêtre
« Photos… », glisser-déposer sur la pochette de la fiche ou sur une case du mur, webcam si
l'ordinateur en a une (QtMultimedia). Types : étiquette, contre-étiquette, capsule, caisse,
bouteille, autre.

## Recadrage et redressement

- Détection automatique des bords (sans dépendance : niveaux de gris, seuil d'Otsu, zone d'un
  seul tenant, enveloppe convexe réduite à 4 coins), ≈ 0,1 s ; OpenCV est utilisé s'il est installé
  (`opencv-python-headless`, facultatif, ≈ 60 Mo : pas embarqué).
- Correction de perspective (Qt, `QTransform.quadToQuad`), quarts de tour, **déroulage** d'une
  étiquette enroulée sur la bouteille (réglage), coins déplaçables à la main.
- La **photo d'origine est gardée** ; la version redressée (≤ 2 400 px, JPEG 90) est un autre
  fichier ; les réglages sont gardés (JSON) pour tout reprendre.
- Vignettes en **cache disque** (`vignettes/` à côté de la cave), lues directement à la bonne taille.

## OCR : choix du moteur

| Moteur | Poids (mesuré le 26/10/2026) | Trois systèmes | Retenu |
|---|---|---|---|
| **Tesseract 5** (Apache 2.0), programme externe | bibliothèque ≈ 2,3 Mo + Leptonica ≈ 1,8 Mo + modèles fra+eng ≈ 5 Mo (« fast ») à 9 Mo | oui (Windows : installeur UB Mannheim ; macOS : Homebrew ; Linux : paquet) | **oui** |
| RapidOCR (PaddleOCR en ONNX) | ≈ 120 Mo de roues (onnxruntime 24 Mo, OpenCV 61 Mo, numpy 17 Mo, modèles 16 Mo) ; Python < 3.13 ; tire une OpenCV « avec interface » en conflit avec le Qt de PyQt6 | oui | non |

Tesseract est cherché dans : le réglage de l'utilisateur, `TESSERACT_CMD`, un dossier `ocr/` du
paquet (s'il l'embarque un jour), le `PATH`, puis les emplacements usuels. Absent, l'interface dit
comment l'installer et la recherche par texte tapé reste possible. Lecture ≈ 0,3 s par étiquette
redressée, hors ligne. Sur la photo brute (de travers), Tesseract ne lit presque rien : le
redressement d'abord est ce qui rend l'OCR utile.

## De la photo au vin

Photo → redressement → OCR → indices (millésime, degré, contenance, code-barres, couleur,
appellations du registre trouvées dans le texte, lignes écrites le plus gros) → candidats LWIN (et,
sur demande, Wikidata / Open Food Facts) → confirmation → vin créé avec sa photo.

Les photos de démonstration (essais, captures) sont **dessinées par l'application** : aucune
étiquette réelle ni image protégée.
