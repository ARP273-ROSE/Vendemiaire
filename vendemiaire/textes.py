# -*- coding: utf-8 -*-
"""Textes de l'interface, en français et en anglais. Une clé = un texte.

Les libellés des codes (statuts, formats, couleurs…) sont dans referentiels.py.
"""

T: dict[str, dict[str, str]] = {
    # -------------------------------------------------------------- général
    "app.nom": {"fr": "Vendémiaire", "en": "Vendémiaire"},
    "onglet.tableau": {"fr": "Tableau de bord", "en": "Dashboard"},
    "onglet.cave": {"fr": "Cave", "en": "Cellar"},
    "onglet.plan": {"fr": "Plan des casiers", "en": "Rack plan"},
    "onglet.livre": {"fr": "Livre de cave", "en": "Cellar book"},
    "bouton.enregistrer": {"fr": "Enregistrer", "en": "Save"},
    "bouton.annuler": {"fr": "Annuler", "en": "Cancel"},
    "bouton.ajouter": {"fr": "Ajouter", "en": "Add"},
    "bouton.creer": {"fr": "Créer", "en": "Create"},
    "filtre.images": {"fr": "Images", "en": "Images"},
    "etat.base": {"fr": "Base : {chemin}", "en": "Database: {chemin}"},
    "etat.exporte": {"fr": "{n} lignes exportées dans {chemin}", "en": "{n} rows exported to {chemin}"},
    "etat.sauvegarde": {"fr": "Sauvegarde écrite : {nom}", "en": "Backup written: {nom}"},
    "etat.sortie": {"fr": "Sortie inscrite au livre de cave.", "en": "Recorded in the cellar book."},

    # ---------------------------------------------------------------- menus
    "menu.fichier": {"fr": "&Fichier", "en": "&File"},
    "menu.importer_csv": {"fr": "Importer un CSV de Vendémiaire…", "en": "Import a Vendémiaire CSV..."},
    "menu.importer_ct": {"fr": "Importer un export CellarTracker…", "en": "Import a CellarTracker export..."},
    "menu.exporter_csv": {"fr": "Exporter en CSV (une ligne par bouteille)…",
                          "en": "Export to CSV (one row per bottle)..."},
    "menu.exporter_json": {"fr": "Exporter tout en JSON…", "en": "Export everything to JSON..."},
    "menu.sauvegarder": {"fr": "Sauvegarder maintenant", "en": "Back up now"},
    "menu.restaurer": {"fr": "Restaurer une sauvegarde…", "en": "Restore a backup..."},
    "menu.dossier_sauvegardes": {"fr": "Ouvrir le dossier des sauvegardes",
                                 "en": "Open the backup folder"},
    "menu.dossier_donnees": {"fr": "Dossier des données…", "en": "Data folder..."},
    "menu.quitter": {"fr": "Quitter", "en": "Quit"},
    "menu.cave": {"fr": "&Cave", "en": "&Cellar"},
    "menu.modifier_vin": {"fr": "Modifier le vin…", "en": "Edit wine..."},
    "menu.ajouter_bouteilles": {"fr": "Ajouter des bouteilles…", "en": "Add bottles..."},
    "menu.sortir": {"fr": "Sortir la bouteille choisie…", "en": "Take out the selected bottle..."},
    "menu.supprimer_vin": {"fr": "Supprimer le vin…", "en": "Delete wine..."},
    "menu.langue": {"fr": "&Langue", "en": "&Language"},
    "menu.aide": {"fr": "&Aide", "en": "&Help"},
    "menu.apropos": {"fr": "À propos de Vendémiaire", "en": "About Vendémiaire"},
    "action.nouveau_vin": {"fr": "Nouveau vin…", "en": "New wine..."},
    "apropos.texte": {
        "fr": "Gestion de cave à vin : bouteilles, plan des casiers, livre de cave.\n"
              "Tout reste sur cet ordinateur, sans abonnement ni service en ligne.\n\n"
              "Base : {base}",
        "en": "Wine cellar manager: bottles, rack plan, cellar book.\n"
              "Everything stays on this computer, with no subscription or online service.\n\n"
              "Database: {base}"},

    # ---------------------------------------------------------- messages
    "message.choisir_vin": {"fr": "Choisissez d'abord un vin dans la liste.",
                            "en": "Select a wine in the list first."},
    "message.choisir_bouteille": {"fr": "Choisissez d'abord une bouteille dans la fiche du vin.",
                                  "en": "Select a bottle in the wine sheet first."},
    "message.supprimer_vin": {
        "fr": "Supprimer « {vin} » et ses {n} bouteilles ?\n\nLe livre de cave garde ses lignes. "
              "Une sauvegarde est faite avant.",
        "en": "Delete \"{vin}\" and its {n} bottles?\n\nThe cellar book keeps its entries. "
              "A backup is made first."},
    "message.restaurer": {
        "fr": "Remplacer la cave actuelle par la sauvegarde « {nom} » ?\n\n"
              "La cave actuelle est d'abord mise de côté dans le dossier des sauvegardes.",
        "en": "Replace the current cellar with the backup \"{nom}\"?\n\n"
              "The current cellar is first set aside in the backup folder."},
    "message.donnees_existantes": {
        "fr": "Une cave existe déjà dans {dossier}.\n\nL'utiliser à partir du prochain démarrage ?",
        "en": "A cellar already exists in {dossier}.\n\nUse it from the next start?"},
    "message.donnees_copier": {
        "fr": "Copier la cave actuelle dans {dossier} et l'utiliser à partir du prochain démarrage ?\n\n"
              "Sur un partage réseau, une seule copie de Vendémiaire à la fois peut l'ouvrir ; "
              "les autres programmes la lisent en lecture seule.",
        "en": "Copy the current cellar to {dossier} and use it from the next start?\n\n"
              "On a network share, only one copy of Vendémiaire at a time can open it; "
              "other programs read it read-only."},
    "message.redemarrer": {"fr": "Le changement prendra effet au prochain démarrage.",
                           "en": "The change will take effect at the next start."},
    "erreur.demarrage": {
        "fr": "Vendémiaire n'a pas pu démarrer.\n\n{erreur}\n\nDétails enregistrés dans :\n{chemin}",
        "en": "Vendémiaire could not start.\n\n{erreur}\n\nDetails saved in:\n{chemin}"},
    "erreur.deja_ouverte": {
        "fr": "Cette cave est déjà ouverte par Vendémiaire (poste {hote}, processus {pid}).\n\n"
              "Une seule copie à la fois peut y écrire. Si ce poste a été éteint brutalement, "
              "supprimez le fichier « vendemiaire.verrou » du dossier des données.",
        "en": "This cellar is already open in Vendémiaire (computer {hote}, process {pid}).\n\n"
              "Only one copy at a time can write to it. If that computer was switched off abruptly, "
              "delete the \"vendemiaire.verrou\" file from the data folder."},
    "erreur.base_verrouillee": {
        "fr": "Un autre programme est en train d'écrire dans la base. Réessayez dans un instant.",
        "en": "Another program is writing to the database. Try again in a moment."},
    "erreur.base_recente": {
        "fr": "Cette cave a été enregistrée par une version plus récente de Vendémiaire. "
              "Mettez l'application à jour pour l'ouvrir.",
        "en": "This cellar was saved by a newer version of Vendémiaire. "
              "Update the application to open it."},

    # -------------------------------------------------------------- cave
    "cave.recherche": {"fr": "Rechercher : domaine, cuvée, appellation, cépage, millésime…",
                       "en": "Search: producer, cuvée, appellation, grape, vintage..."},
    "cave.filtre_couleur": {"fr": "Couleur", "en": "Colour"},
    "cave.filtre_pays": {"fr": "Pays", "en": "Country"},
    "cave.filtre_statut": {"fr": "Bouteilles", "en": "Bottles"},
    "cave.toutes": {"fr": "Toutes", "en": "All"},
    "cave.tous": {"fr": "Tous", "en": "All"},
    "cave.statut_presents": {"fr": "En cave ou à venir", "en": "In cellar or coming"},
    "cave.statut_tous": {"fr": "Tous les vins", "en": "All wines"},
    "cave.compte": {"fr": "{vins} vins · {bouteilles} bouteilles", "en": "{vins} wines · {bouteilles} bottles"},
    "col.pochette": {"fr": "Étiquette", "en": "Label"},
    "col.producteur": {"fr": "Producteur", "en": "Producer"},
    "col.cuvee": {"fr": "Cuvée", "en": "Cuvée"},
    "col.appellation": {"fr": "Appellation", "en": "Appellation"},
    "col.millesime": {"fr": "Millésime", "en": "Vintage"},
    "col.couleur": {"fr": "Couleur", "en": "Colour"},
    "col.type": {"fr": "Type", "en": "Type"},
    "col.region": {"fr": "Région", "en": "Region"},
    "col.pays": {"fr": "Pays", "en": "Country"},
    "col.cepages": {"fr": "Cépages", "en": "Grapes"},
    "col.degre": {"fr": "Degré", "en": "ABV"},
    "col.formats": {"fr": "Formats", "en": "Sizes"},
    "col.en_cave": {"fr": "En cave", "en": "In cellar"},
    "col.a_venir": {"fr": "À venir", "en": "Coming"},
    "col.prix_moyen": {"fr": "Prix moyen", "en": "Average price"},
    "col.valeur": {"fr": "Valeur", "en": "Value"},
    "col.classement": {"fr": "Classement", "en": "Classification"},
    "col.lwin": {"fr": "LWIN", "en": "LWIN"},

    # -------------------------------------------------------------- vin
    "vin.nm": {"fr": "NM", "en": "NV"},
    "vin.coup_de_coeur": {"fr": "Coup de cœur", "en": "Favourite"},
    "vin.producteur": {"fr": "Producteur", "en": "Producer"},
    "vin.cuvee": {"fr": "Cuvée", "en": "Cuvée"},
    "vin.appellation": {"fr": "Appellation", "en": "Appellation"},
    "vin.region": {"fr": "Origine", "en": "Origin"},
    "vin.region_seule": {"fr": "Région", "en": "Region"},
    "vin.sous_region": {"fr": "Sous-région", "en": "Sub-region"},
    "vin.pays": {"fr": "Pays", "en": "Country"},
    "vin.classement": {"fr": "Classement", "en": "Classification"},
    "vin.couleur": {"fr": "Couleur", "en": "Colour"},
    "vin.type": {"fr": "Type", "en": "Type"},
    "vin.couleur_type": {"fr": "Couleur, type", "en": "Colour, type"},
    "vin.millesime": {"fr": "Millésime", "en": "Vintage"},
    "vin.degre": {"fr": "Degré", "en": "ABV"},
    "vin.cepages": {"fr": "Cépages", "en": "Grapes"},
    "vin.lwin": {"fr": "LWIN", "en": "LWIN"},
    "vin.ean": {"fr": "Code-barres (EAN)", "en": "Barcode (EAN)"},
    "vin.seuil": {"fr": "Seuil de réassort", "en": "Restock threshold"},
    "vin.notes": {"fr": "Notes", "en": "Notes"},

    # -------------------------------------------------------------- fiche
    "fiche.aucun": {"fr": "Aucun vin choisi", "en": "No wine selected"},
    "fiche.aucun_aide": {"fr": "Choisissez un vin dans la liste, ou créez-en un.",
                         "en": "Select a wine in the list, or create one."},
    "fiche.modifier": {"fr": "Modifier le vin…", "en": "Edit wine..."},
    "fiche.photo": {"fr": "Photo de l'étiquette…", "en": "Label photo..."},
    "fiche.fenetres": {"fr": "Fenêtres de dégustation", "en": "Drinking windows"},
    "fiche.f_source": {"fr": "Source", "en": "Source"},
    "fiche.f_debut": {"fr": "De", "en": "From"},
    "fiche.f_apogee": {"fr": "Apogée", "en": "Peak"},
    "fiche.f_fin": {"fr": "À", "en": "To"},
    "fiche.f_pourquoi": {"fr": "Pourquoi", "en": "Why"},
    "fiche.regles_a_venir": {
        "fr": "Fenêtre calculée par Vendémiaire : les règles d'apogée viendront du dossier "
              "« Le vin », avec leurs sources. Aucune estimation n'est inventée en attendant.",
        "en": "Window computed by Vendémiaire: the peak rules will come from the \"Le vin\" "
              "study, with their sources. No estimate is made up in the meantime."},
    "fiche.critiques": {"fr": "Notes des critiques", "en": "Critics' scores"},
    "fiche.c_critique": {"fr": "Critique", "en": "Critic"},
    "fiche.c_note": {"fr": "Note", "en": "Score"},
    "fiche.c_date": {"fr": "Date", "en": "Date"},
    "fiche.bouteilles": {"fr": "Bouteilles", "en": "Bottles"},
    "fiche.bouteilles_age": {"fr": "Bouteilles ({n}) — vin de {age} ans",
                             "en": "Bottles ({n}) — wine aged {age} years"},
    "fiche.b_statut": {"fr": "Statut", "en": "Status"},
    "fiche.b_format": {"fr": "Format", "en": "Size"},
    "fiche.b_emplacement": {"fr": "Emplacement", "en": "Location"},
    "fiche.b_prix": {"fr": "Prix", "en": "Price"},
    "fiche.b_entree": {"fr": "Date", "en": "Date"},
    "fiche.b_niveau": {"fr": "Niveau", "en": "Fill level"},
    "fiche.b_etat": {"fr": "État", "en": "Condition"},
    "fiche.ajouter_bouteilles": {"fr": "Ajouter…", "en": "Add..."},
    "fiche.sortir": {"fr": "Sortir…", "en": "Take out..."},
    "fiche.modifier_bouteille": {"fr": "Détails…", "en": "Details..."},
    "fiche.recevoir": {"fr": "Réceptionner", "en": "Receive"},
    "fiche.voir_plan": {"fr": "Voir au plan", "en": "Show on plan"},
    "fiche.valeur": {"fr": "Valeur estimée : {montant} la bouteille ({date}, {source})",
                     "en": "Estimated value: {montant} per bottle ({date}, {source})"},

    # -------------------------------------------------------------- saisie
    "saisie.titre_nouveau": {"fr": "Nouveau vin", "en": "New wine"},
    "saisie.titre_modifier": {"fr": "Modifier le vin", "en": "Edit wine"},
    "saisie.titre_ajout": {"fr": "Ajouter des bouteilles — {vin}", "en": "Add bottles — {vin}"},
    "saisie.titre_bouteille": {"fr": "Bouteille — {vin}", "en": "Bottle — {vin}"},
    "saisie.onglet_vin": {"fr": "Le vin", "en": "Wine"},
    "saisie.onglet_bouteilles": {"fr": "Bouteilles à ajouter", "en": "Bottles to add"},
    "saisie.onglet_achat": {"fr": "Achat", "en": "Purchase"},
    "saisie.onglet_etat": {"fr": "Niveau et état", "en": "Fill level and condition"},
    "saisie.onglet_provenance": {"fr": "Provenance", "en": "Provenance"},
    "saisie.non_millesime": {"fr": "Non millésimé", "en": "Non-vintage"},
    "saisie.cepages_aide": {"fr": "ex. Merlot 70 %; Cabernet franc 30 %",
                            "en": "e.g. Merlot 70%; Cabernet Franc 30%"},
    "saisie.coup_de_coeur": {"fr": "Coup de cœur", "en": "Favourite"},
    "saisie.nombre": {"fr": "Nombre", "en": "Quantity"},
    "saisie.format": {"fr": "Format", "en": "Size"},
    "saisie.statut": {"fr": "Statut", "en": "Status"},
    "saisie.prix": {"fr": "Prix d'achat (unité)", "en": "Purchase price (each)"},
    "saisie.lieu_achat": {"fr": "Lieu d'achat", "en": "Bought from"},
    "saisie.date_achat": {"fr": "Date d'achat", "en": "Purchase date"},
    "saisie.date_entree": {"fr": "Entrée en cave", "en": "Into the cellar"},
    "saisie.livraison": {"fr": "Livraison prévue", "en": "Expected delivery"},
    "saisie.caisse": {"fr": "Caisse", "en": "Case"},
    "saisie.caisse_complete": {"fr": "Caisse complète", "en": "Full case"},
    "saisie.caisse_ref": {"fr": "Repère de la caisse", "en": "Case reference"},
    "saisie.provenance": {"fr": "Provenance", "en": "Provenance"},
    "saisie.historique": {"fr": "Historique de stockage", "en": "Storage history"},
    "saisie.facture": {"fr": "Facture", "en": "Invoice"},
    "saisie.bin": {"fr": "Numéro de carte (BIN)", "en": "List number (BIN)"},
    "saisie.emplacement": {"fr": "Casier", "en": "Rack"},
    "saisie.sans_emplacement": {"fr": "Sans emplacement", "en": "No location"},
    "saisie.placer_libres": {"fr": "Placer dans les premières cases libres",
                             "en": "Put in the first free slots"},
    "saisie.niveau": {"fr": "Niveau (bordelaise)", "en": "Fill level (Bordeaux bottle)"},
    "saisie.niveau_cm": {"fr": "Niveau (bourguignonne, sous le bouchon)",
                         "en": "Fill level (Burgundy bottle, below the cork)"},
    "saisie.etiquette": {"fr": "Étiquette", "en": "Label"},
    "saisie.capsule": {"fr": "Capsule", "en": "Capsule"},
    "saisie.bouchon": {"fr": "Bouchon", "en": "Cork"},
    "saisie.niveau_aide_titre": {"fr": "Échelle des niveaux", "en": "Fill-level scale"},
    "saisie.niveau_aide": {
        "fr": "Vocabulaire des ventes aux enchères, du plus haut au plus bas : dans le goulot, base "
              "du goulot, très haut d'épaule, haut d'épaule, haute épaule, mi-épaule, bas d'épaule. "
              "Ce que chaque niveau signifie selon l'âge du vin viendra du dossier « Le vin ».",
        "en": "Auction vocabulary, from highest to lowest: into neck, base of neck, very top "
              "shoulder, top shoulder, high shoulder, mid shoulder, low shoulder. What each level "
              "means for the wine's age will come from the \"Le vin\" study."},
    "saisie.erreur_nom": {"fr": "Indiquez au moins le producteur, la cuvée ou l'appellation.",
                          "en": "Enter at least the producer, the cuvée or the appellation."},
    "saisie.erreur_cepages": {"fr": "Les pourcentages des cépages font {total} % (plus de 100).",
                              "en": "The grape percentages add up to {total}% (over 100)."},

    # -------------------------------------------------------------- sortie
    "sortie.titre": {"fr": "Sortir une bouteille — {vin}", "en": "Take out a bottle — {vin}"},
    "sortie.type": {"fr": "Motif", "en": "Reason"},
    "sortie.date": {"fr": "Date", "en": "Date"},
    "sortie.occasion": {"fr": "Occasion", "en": "Occasion"},
    "sortie.convives": {"fr": "Convives", "en": "Guests"},
    "sortie.plat": {"fr": "Plat", "en": "Dish"},
    "sortie.note": {"fr": "Note", "en": "Score"},
    "sortie.prix_vente": {"fr": "Prix (vente)", "en": "Price (sale)"},
    "sortie.commentaire": {"fr": "Commentaire", "en": "Comment"},
    "sortie.commentaire_aide": {"fr": "Robe, nez, bouche, finale… et ce qu'on en a pensé.",
                                "en": "Colour, nose, palate, finish... and what you thought."},
    "sortie.valider": {"fr": "Inscrire au livre de cave", "en": "Record in the cellar book"},

    # -------------------------------------------------------------- plan
    "plan.titre": {"fr": "Plan des casiers", "en": "Rack plan"},
    "plan.emplacements": {"fr": "Caves, meubles, casiers", "en": "Cellars, units, racks"},
    "plan.bouteilles": {"fr": "Bouteilles", "en": "Bottles"},
    "plan.nouvelle_cave": {"fr": "Nouvelle cave…", "en": "New cellar..."},
    "plan.nouveau_meuble": {"fr": "Nouveau meuble…", "en": "New unit..."},
    "plan.nouveau_casier": {"fr": "Nouveau casier…", "en": "New rack..."},
    "plan.renommer": {"fr": "Renommer…", "en": "Rename..."},
    "plan.nom": {"fr": "Nom", "en": "Name"},
    "plan.rangees": {"fr": "Rangées", "en": "Rows"},
    "plan.colonnes": {"fr": "Colonnes", "en": "Columns"},
    "plan.choisir_parent": {
        "fr": "Choisissez d'abord dans l'arbre la cave (pour un meuble) ou le meuble (pour un casier).",
        "en": "First select in the tree the cellar (for a unit) or the unit (for a rack)."},
    "plan.aide": {
        "fr": "Glissez une bouteille vers une case libre, ou sur une autre pour les échanger. "
              "Encadrez plusieurs bouteilles à la souris pour les déplacer ensemble. "
              "Cercle doré : grand format.",
        "en": "Drag a bottle to a free slot, or onto another one to swap them. "
              "Draw a box around several bottles to move them together. Gold ring: large format."},
    "plan.aucun_casier": {"fr": "Aucun casier : créez une cave, un meuble puis un casier.",
                          "en": "No rack: create a cellar, a unit, then a rack."},
    "plan.case": {"fr": "rangée {r}, colonne {c}", "en": "row {r}, column {c}"},
    "plan.etat": {"fr": "{n} bouteilles · {libres} cases libres · {choisies} choisies",
                  "en": "{n} bottles · {libres} free slots · {choisies} selected"},
    "plan.tout_selectionner": {"fr": "Tout choisir", "en": "Select all"},
    "plan.deplacer_selection": {"fr": "Déplacer la sélection vers…", "en": "Move selection to..."},
    "plan.ranger_sans_case": {"fr": "Ranger ici les bouteilles sans case",
                              "en": "Put bottles without a slot here"},
    "plan.ranger_aide": {"fr": "{n} bouteilles sans emplacement, {m} sans case dans ce casier",
                         "en": "{n} bottles without a location, {m} without a slot in this rack"},
    "plan.rien_a_ranger": {"fr": "Aucune bouteille à ranger, ou plus de case libre ici.",
                           "en": "No bottle to put away, or no free slot left here."},
    "plan.deplacer_titre": {"fr": "Déplacer {n} bouteilles", "en": "Move {n} bottles"},
    "plan.destination": {"fr": "Vers le casier", "en": "To rack"},
    "plan.casier_libres": {"fr": "{chemin} — {n} cases libres", "en": "{chemin} — {n} free slots"},
    "plan.motif": {"fr": "Motif (facultatif)", "en": "Reason (optional)"},
    "plan.deplacer": {"fr": "Déplacer", "en": "Move"},
    "plan.pas_assez": {"fr": "{n} bouteilles à placer, mais seulement {libres} cases libres.",
                       "en": "{n} bottles to place, but only {libres} free slots."},
    "plan.motif_glisser": {"fr": "glisser-déposer", "en": "drag and drop"},
    "plan.motif_lot": {"fr": "déplacement en lot", "en": "batch move"},
    "plan.motif_ranger": {"fr": "rangement", "en": "putting away"},

    # -------------------------------------------------------------- livre
    "livre.recherche": {"fr": "Rechercher : vin, occasion, convives, plat, commentaire…",
                        "en": "Search: wine, occasion, guests, dish, comment..."},
    "livre.tout": {"fr": "Entrées et sorties", "en": "Ins and outs"},
    "livre.entrees": {"fr": "Entrées", "en": "Ins"},
    "livre.sorties": {"fr": "Sorties", "en": "Outs"},
    "livre.compte": {"fr": "{n} lignes · {e} entrées · {s} sorties", "en": "{n} entries · {e} in · {s} out"},
    "livre.date": {"fr": "Date", "en": "Date"},
    "livre.type": {"fr": "Mouvement", "en": "Movement"},
    "livre.vin": {"fr": "Vin", "en": "Wine"},
    "livre.millesime": {"fr": "Millésime", "en": "Vintage"},
    "livre.occasion": {"fr": "Occasion", "en": "Occasion"},
    "livre.convives": {"fr": "Convives", "en": "Guests"},
    "livre.plat": {"fr": "Plat", "en": "Dish"},
    "livre.note": {"fr": "Note", "en": "Score"},
    "livre.commentaire": {"fr": "Commentaire", "en": "Comment"},
    "livre.aide": {"fr": "Double-cliquez sur une ligne pour compléter l'occasion, le plat, la note.",
                   "en": "Double-click a row to fill in the occasion, dish, score."},
    "livre.modifier_titre": {"fr": "Ligne du livre de cave", "en": "Cellar book entry"},

    # -------------------------------------------------------------- tableau
    "tableau.bouteilles": {"fr": "bouteilles en cave", "en": "bottles in the cellar"},
    "tableau.vins": {"fr": "vins différents", "en": "different wines"},
    "tableau.a_venir": {"fr": "à venir (primeurs, livraisons)", "en": "coming (futures, deliveries)"},
    "tableau.litres": {"fr": "litres", "en": "litres"},
    "tableau.prix_total": {"fr": "payés", "en": "paid"},
    "tableau.valeur_estimee": {"fr": "valeur estimée", "en": "estimated value"},
    "tableau.par_couleur": {"fr": "Par couleur", "en": "By colour"},
    "tableau.par_pays": {"fr": "Par pays", "en": "By country"},
    "tableau.par_region": {"fr": "Par région", "en": "By region"},
    "tableau.par_decennie": {"fr": "Par millésime (décennie)", "en": "By vintage (decade)"},
    "tableau.decennie": {"fr": "années {d}", "en": "{d}s"},
    "tableau.non_millesime": {"fr": "non millésimé", "en": "non-vintage"},
    "tableau.inconnu": {"fr": "non renseigné", "en": "not set"},
    "tableau.autres": {"fr": "autres", "en": "others"},
    "tableau.alertes": {"fr": "À surveiller", "en": "To watch"},
    "tableau.aucune_alerte": {"fr": "Rien à signaler.", "en": "Nothing to report."},
    "tableau.alerte_primeur": {"fr": "{n} × {vin} : livraison prévue le {date}",
                               "en": "{n} × {vin}: delivery expected on {date}"},
    "tableau.alerte_reassort": {"fr": "{vin} : {n} en cave, seuil de réassort {seuil}",
                                "en": "{vin}: {n} in the cellar, restock threshold {seuil}"},
    "tableau.derniers": {"fr": "Derniers mouvements", "en": "Latest movements"},
    "tableau.mouvements_12": {"fr": "Douze derniers mois : {e} entrées, {s} sorties",
                              "en": "Last twelve months: {e} in, {s} out"},
    "tableau.apogee_a_venir": {
        "fr": "La courbe d'apogée de la cave (« combien de bouteilles à boire chaque année ») "
              "arrivera avec les règles du dossier « Le vin ».",
        "en": "The cellar's peak curve (\"how many bottles to drink each year\") will come "
              "with the rules of the \"Le vin\" study."},

    # -------------------------------------------------------------- import
    "import.titre": {"fr": "Import terminé", "en": "Import finished"},
    "import.rapport": {
        "fr": "{lignes} lignes lues : {crees} vins créés, {completes} complétés, "
              "{bouteilles} bouteilles ajoutées, {deja} déjà présentes.\n\n"
              "Aucune donnée saisie à la main n'a été remplacée.",
        "en": "{lignes} rows read: {crees} wines created, {completes} completed, "
              "{bouteilles} bottles added, {deja} already present.\n\n"
              "No manually entered data was replaced."},
    "dialogue.photo": {"fr": "Choisir la photo de l'étiquette", "en": "Choose the label photo"},
}
