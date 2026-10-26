# -*- coding: utf-8 -*-
"""Traduction anglaise des libellés des règles qui n'existent qu'en français
dans les fichiers du dossier « Le vin » (noms de plats, défauts, niveaux,
descripteurs d'arômes, conseils de conservation…).

Seuls les TEXTES AFFICHÉS sont traduits : les valeurs (températures, durées,
âges, styles, sources) restent celles du dossier, lues dans les JSON. La clé
est le texte français exact du dossier ; un essai vérifie que chaque texte
affiché a sa traduction (`tests/test_regles.py`).
"""
from __future__ import annotations

TRADUCTIONS: dict[str, str] = {
    # ------------------------------------------------------------ exemples des styles
    "Champagne millésimé, Dom Pérignon, Cristal, Krug, Franciacorta riserva":
        "Vintage Champagne, Dom Pérignon, Cristal, Krug, Franciacorta riserva",
    "Asti, Moscato d'Asti, clairette de Die tradition": "Asti, Moscato d'Asti, Clairette de Die tradition",
    "Champagne brut sans année, crémants, cava, prosecco, sekt":
        "Non-vintage brut Champagne, crémants, cava, prosecco, sekt",
    "Sauternes, Barsac, Tokaji aszú, Beerenauslese, Trockenbeerenauslese, Quarts de Chaume, Sélection de grains nobles":
        "Sauternes, Barsac, Tokaji aszú, Beerenauslese, Trockenbeerenauslese, Quarts de Chaume, "
        "Sélection de grains nobles",
    "Eiswein, icewine du Canada, vin de paille du Jura, vinsanto":
        "Eiswein, Canadian icewine, Jura straw wine, vinsanto",
    "Vouvray demi-sec, riesling Kabinett/Spätlese, Alsace vendanges tardives, Jurançon moelleux":
        "Off-dry Vouvray, Kabinett/Spätlese riesling, Alsace late harvest, sweet Jurançon",
    "Fino, manzanilla": "Fino, manzanilla",
    "Porto vintage, single quinta vintage": "Vintage port, single quinta vintage",
    "Porto tawny et colheita, madère, amontillado, oloroso, Pedro Ximénez, banyuls et rivesaltes tuilés, rancios":
        "Tawny and colheita port, Madeira, amontillado, oloroso, Pedro Ximénez, aged Banyuls and Rivesaltes, rancios",
    "Porto ruby et LBV, banyuls rimage, maury grenat, muscats de Beaumes-de-Venise, de Rivesaltes, de Frontignan":
        "Ruby and LBV port, Banyuls rimage, Maury grenat, Muscats of Beaumes-de-Venise, Rivesaltes, Frontignan",
    "Vin jaune, Château-Chalon": "Vin jaune, Château-Chalon",
    "Côtes de Provence, Tavel, Bandol rosé, rosés du monde": "Côtes de Provence, Tavel, Bandol rosé, rosés of the world",
    "Vins de macération du Frioul, qvevri de Géorgie": "Skin-contact wines of Friuli, Georgian qvevri wines",
    "Chablis premier et grand cru, riesling sec d'Alsace, d'Allemagne ou d'Autriche, Savennières, Vouvray sec, sémillon de la Hunter, assyrtiko de Santorin":
        "Chablis premier and grand cru, dry riesling from Alsace, Germany or Austria, Savennières, dry Vouvray, "
        "Hunter Valley semillon, Santorini assyrtiko",
    "Meursault, Puligny- et Chassagne-Montrachet, Corton-Charlemagne, Pessac-Léognan blanc, Hermitage et Châteauneuf blancs, chardonnays boisés du Nouveau Monde":
        "Meursault, Puligny- and Chassagne-Montrachet, Corton-Charlemagne, white Pessac-Léognan, white Hermitage "
        "and Châteauneuf, oaked New World chardonnays",
    "Muscadet, Sancerre, sauvignon de Marlborough, picpoul, albariño, vinho verde, pinot grigio, Mâcon, Soave":
        "Muscadet, Sancerre, Marlborough sauvignon, picpoul, albariño, vinho verde, pinot grigio, Mâcon, Soave",
    "Beaujolais et ses crus, gamay de Loire et de Savoie, pinot d'Alsace, Valpolicella, dolcetto, Bourgogne générique":
        "Beaujolais and its crus, Loire and Savoie gamay, Alsace pinot, Valpolicella, dolcetto, generic Burgundy",
    "Bourgogne villages, premiers et grands crus (Côte de Nuits, Côte de Beaune), Central Otago, Oregon, Martinborough":
        "Burgundy village, premier and grand cru (Côte de Nuits, Côte de Beaune), Central Otago, Oregon, Martinborough",
    "Barolo, Barbaresco, Gattinara, Valtellina": "Barolo, Barbaresco, Gattinara, Valtellina",
    "Brunello di Montalcino, Chianti Classico riserva et gran selezione, Vino Nobile":
        "Brunello di Montalcino, Chianti Classico riserva and gran selezione, Vino Nobile",
    "Rioja reserva et gran reserva, Ribera del Duero, Toro": "Rioja reserva and gran reserva, Ribera del Duero, Toro",
    "Médoc (Pauillac, Margaux, Saint-Julien, Saint-Estèphe), Pessac-Léognan, Pomerol, Saint-Émilion grand cru":
        "Médoc (Pauillac, Margaux, Saint-Julien, Saint-Estèphe), Pessac-Léognan, Pomerol, Saint-Émilion grand cru",
    "Côte-Rôtie, Hermitage, Cornas, Saint-Joseph, Crozes-Hermitage":
        "Côte-Rôtie, Hermitage, Cornas, Saint-Joseph, Crozes-Hermitage",
    "Châteauneuf-du-Pape, Gigondas, Vacqueyras, Côtes-du-Rhône villages, Languedoc, Roussillon, Priorat, Bandol":
        "Châteauneuf-du-Pape, Gigondas, Vacqueyras, Côtes-du-Rhône villages, Languedoc, Roussillon, Priorat, Bandol",
    "Napa, Coonawarra, Margaret River, Washington, Chili (Maipo), Hawke's Bay, Bolgheri":
        "Napa, Coonawarra, Margaret River, Washington, Chile (Maipo), Hawke's Bay, Bolgheri",
    "Barossa et McLaren Vale, Mendoza, Paso Robles, zinfandel de Californie, Amarone":
        "Barossa and McLaren Vale, Mendoza, Paso Robles, Californian zinfandel, Amarone",
    "Madiran, Cahors, Bandol, Taurasi et aglianico, Douro rouge, saperavi, xinomavro, tannat d'Uruguay":
        "Madiran, Cahors, Bandol, Taurasi and aglianico, red Douro, saperavi, xinomavro, Uruguayan tannat",
    "Bordeaux et Bordeaux supérieur, Côtes-du-Rhône, vins de pays et IGP, cépages du Nouveau Monde d'entrée de gamme":
        "Bordeaux and Bordeaux supérieur, Côtes-du-Rhône, country wines and IGPs, entry-level New World varietals",

    # ------------------------------------------------------------ plats
    "Huîtres, coquillages crus": "Oysters, raw shellfish",
    "Poisson grillé, poisson blanc": "Grilled fish, white fish",
    "Poisson en sauce, au beurre blanc, à la crème": "Fish in sauce, beurre blanc or cream",
    "Homard, langouste, crustacés": "Lobster, crayfish, shellfish",
    "Sushis, poisson cru": "Sushi, raw fish",
    "Charcuterie, terrines": "Charcuterie, terrines",
    "Volaille rôtie": "Roast poultry",
    "Volaille à la crème, aux morilles": "Chicken in cream, with morels",
    "Viande rouge grillée, côte de bœuf": "Grilled red meat, rib of beef",
    "Agneau": "Lamb",
    "Plats mijotés (bœuf bourguignon, daube, civet)": "Slow-cooked stews (beef bourguignon, daube, civet)",
    "Gibier": "Game",
    "Porc, veau, viandes blanches": "Pork, veal, white meats",
    "Canard, confit": "Duck, confit",
    "Foie gras": "Foie gras",
    "Fondue, raclette, tartiflette": "Fondue, raclette, tartiflette",
    "Champignons, truffe, risotto": "Mushrooms, truffle, risotto",
    "Pâtes à la tomate, pizza": "Pasta with tomato sauce, pizza",
    "Cuisine épicée (thaïe, Sichuan, indienne)": "Spicy food (Thai, Sichuan, Indian)",
    "Couscous, tajine": "Couscous, tagine",
    "Barbecue": "Barbecue",
    "Fromage de chèvre": "Goat's cheese",
    "Comté, beaufort, gruyère (pâtes pressées cuites)": "Comté, Beaufort, Gruyère (hard cooked cheeses)",
    "Époisses, munster, maroilles (croûte lavée)": "Époisses, Munster, Maroilles (washed-rind cheeses)",
    "Roquefort, bleus, stilton": "Roquefort, blue cheeses, Stilton",
    "Desserts aux fruits, tartes": "Fruit desserts, tarts",
    "Chocolat": "Chocolate",
    "Apéritif": "Aperitif",
    # exemples des plats
    "Muscadet, Chablis, Picpoul, champagne extra-brut": "Muscadet, Chablis, Picpoul, extra-brut Champagne",
    "Sancerre, Savennières, albariño": "Sancerre, Savennières, albariño",
    "Meursault, Pessac blanc, chenin sec": "Meursault, white Pessac, dry chenin",
    "Meursault, Corton-Charlemagne, champagne millésimé": "Meursault, Corton-Charlemagne, vintage Champagne",
    "champagne brut, riesling sec, muscadet": "brut Champagne, dry riesling, Muscadet",
    "Beaujolais, gamay, rosé": "Beaujolais, gamay, rosé",
    "Bourgogne rouge, Meursault": "red Burgundy, Meursault",
    "vin jaune, savagnin, grand chardonnay": "vin jaune, savagnin, fine chardonnay",
    "Pauillac, Napa, malbec, Cornas": "Pauillac, Napa, malbec, Cornas",
    "Pauillac, Rioja reserva, Châteauneuf": "Pauillac, Rioja reserva, Châteauneuf",
    "Bourgogne, Cahors, Madiran": "Burgundy, Cahors, Madiran",
    "vieux bourgogne, Côte-Rôtie, Barolo": "old Burgundy, Côte-Rôtie, Barolo",
    "Beaujolais, chenin, Bourgogne": "Beaujolais, chenin, Burgundy",
    "Madiran, Cahors, Saint-Émilion": "Madiran, Cahors, Saint-Émilion",
    "Sauternes, Jurançon, Alsace vendanges tardives": "Sauternes, Jurançon, Alsace late harvest",
    "Apremont, Crépy, Chignin-Bergeron": "Apremont, Crépy, Chignin-Bergeron",
    "vieux bourgogne, Barolo mûr": "old Burgundy, mature Barolo",
    "Chianti, barbera": "Chianti, barbera",
    "riesling Kabinett, gewurztraminer, rosé": "Kabinett riesling, gewurztraminer, rosé",
    "Boulaouane ou Guerrouane rouges, gris marocains, Collioure":
        "red Boulaouane or Guerrouane, Moroccan gris, Collioure",
    "zinfandel, shiraz, malbec": "zinfandel, shiraz, malbec",
    "Sancerre, Pouilly-Fumé, Savennières": "Sancerre, Pouilly-Fumé, Savennières",
    "vin jaune, savagnin, Meursault": "vin jaune, savagnin, Meursault",
    "gewurztraminer, marsannay": "gewurztraminer, Marsannay",
    "Sauternes, porto, banyuls": "Sauternes, port, Banyuls",
    "Coteaux du Layon, moscato d'Asti, Sauternes": "Coteaux du Layon, Moscato d'Asti, Sauternes",
    "Banyuls, Maury, porto ruby ou LBV": "Banyuls, Maury, ruby or LBV port",
    "champagne, crémant, fino": "Champagne, crémant, fino",
    # pourquoi des plats
    "Iode et sel appellent un blanc vif, sec, sans bois ; les bruts peu dosés (l'iode se marie mal avec le sucre).":
        "Iodine and salt call for a crisp, dry, unoaked white, or a low-dosage brut (iodine does not go with sugar).",
    "Chair délicate : blanc sec et vif ; un rouge tannique risque le goût métallique.":
        "Delicate flesh: a crisp dry white; a tannic red risks a metallic taste.",
    "La crème et le beurre demandent un blanc ample ou un blanc vif qui coupe le gras (contraste).":
        "Cream and butter call for a full-bodied white, or a crisp white that cuts the fat (contrast).",
    "Chair sucrée et riche : grand blanc ample ou champagne vineux.":
        "Sweet, rich flesh: a fine full-bodied white or a vinous Champagne.",
    "Pas de tanins (fer, poisson cru), acidité et fraîcheur ; bulles peu dosées.":
        "No tannin (iron, raw fish), acidity and freshness; low-dosage bubbles.",
    "Sel et gras : rouge léger et fruité, servi frais, ou rosé.":
        "Salt and fat: a light, fruity red served cool, or a rosé.",
    "Viande fine : pinot noir, grand blanc ou rouge léger.": "Delicate meat: pinot noir, a fine white or a light red.",
    "Accord régional jurassien : le vin jaune et sa note de noix avec la crème et les morilles (la recette elle-même se cuisine au vin jaune) ; les grands blancs de Bourgogne s'accordent aussi avec la volaille en sauce à la crème.":
        "A Jura regional pairing: vin jaune and its walnut note with cream and morels (the dish itself is cooked "
        "with vin jaune); fine white Burgundies also suit chicken in cream sauce.",
    "Protéines et gras assouplissent les tanins ; le grillé répond au boisé.":
        "Protein and fat soften tannins; the char echoes the oak.",
    "Viande grasse et parfumée : rouge charpenté ; classique bordelais (agneau de Pauillac).":
        "Rich, fragrant meat: a structured red; a Bordeaux classic (Pauillac lamb).",
    "Sauce au vin et longue cuisson : souvent le vin de la région qui a servi à la recette.":
        "Wine sauce and long cooking: often the regional wine used in the recipe.",
    "Goût puissant, sauvage : vieux rouge aux notes tertiaires (sous-bois, cuir).":
        "Strong, wild flavour: an old red with tertiary notes (forest floor, leather).",
    "Viandes douces : rouges souples ou blancs amples.": "Mild meats: supple reds or full-bodied whites.",
    "Accord du Sud-Ouest : le gras du canard contre les tanins du Madiran ou du Cahors.":
        "A South-West pairing: duck fat against the tannins of Madiran or Cahors.",
    "Accord classique de contraste et de richesse : le liquoreux répond au gras ; certains préfèrent un vin sec et vif.":
        "A classic pairing of contrast and richness: the sweet wine answers the fat; some prefer a crisp dry wine.",
    "Accord savoyard : blanc vif (jacquère, chasselas) qui coupe le fromage fondu.":
        "A Savoie pairing: a crisp white (jacquère, chasselas) that cuts through melted cheese.",
    "Umami : vins peu tanniques ou mûrs (attention, l'umami durcit les tanins jeunes).":
        "Umami: low-tannin or mature wines (umami hardens young tannins).",
    "La tomate est acide : un rouge italien, vif lui aussi.": "Tomato is acidic: an Italian red, crisp as well.",
    "Piment : vin frais, peu alcoolisé, peu tannique, au besoin un peu sucré.":
        "Chilli: a cool, low-alcohol, low-tannin wine, off-dry if needed.",
    "Épices douces et fruits secs : rouges méditerranéens souples ou rosés.":
        "Mild spices and dried fruit: supple Mediterranean reds or rosés.",
    "Fumé, sucré et grillé : rouges mûrs et fruités du Nouveau Monde.":
        "Smoky, sweet and charred: ripe, fruity New World reds.",
    "Classique de la Loire : crottin de Chavignol et sancerre ; l'acidité répond à l'acidité.":
        "A Loire classic: Crottin de Chavignol and Sancerre; acidity answers acidity.",
    "Fruité, noisette : vin jaune (« duo incontournable » du Jura), blancs de Bourgogne et de Chablis, macvin.":
        "Fruity, nutty: vin jaune (the Jura's \"essential duo\"), white Burgundy and Chablis, macvin.",
    "Fromages puissants : en Bourgogne, les rouges (Marsannay) avec l'Époisses ou l'Ami du Chambertin ; ailleurs, un blanc aromatique ou moelleux tient tête à la croûte lavée. Dans l'étude de Dijon, l'Époisses comme les autres fromages réduisait l'astringence et l'acidité perçues d'un Madiran.":
        "Strong cheeses: in Burgundy, reds (Marsannay) with Époisses or Ami du Chambertin; elsewhere an aromatic "
        "or sweet white stands up to the washed rind. In the Dijon study, Époisses, like the other cheeses, "
        "reduced the perceived astringency and acidity of a Madiran.",
    "Sel contre sucre : Sauternes et roquefort, porto et stilton.":
        "Salt against sugar: Sauternes and Roquefort, port and Stilton.",
    "Le vin doit être au moins aussi sucré que le dessert.": "The wine must be at least as sweet as the dessert.",
    "Amertume, sucre et gras du chocolat : vins mutés rouges (banyuls, maury, porto) ; les vins secs y deviennent amers.":
        "Bitterness, sugar and fat of chocolate: red fortified wines (Banyuls, Maury, port); dry wines turn bitter.",
    "Vins vifs qui ouvrent l'appétit (l'acidité fait saliver).":
        "Crisp wines that whet the appetite (acidity makes the mouth water).",

    # ------------------------------------------------------------ accords difficiles
    "Artichaut": "Artichoke",
    "La cynarine de l'artichaut agit sur les papilles : l'amertume augmente et même l'eau paraît ensuite sucrée ; un vin sec semble fade et étrange. Repli : un blanc très sec et vif.":
        "Cynarin in artichoke acts on the taste buds: bitterness rises and even water then tastes sweet; a dry "
        "wine seems flat and odd. Fallback: a very dry, crisp white.",
    "Vinaigrette, plats très vinaigrés": "Vinaigrette, very vinegary dishes",
    "Le vinaigre écrase l'acidité du vin, qui paraît plat. Repli : blanc très vif, ou adoucir la vinaigrette.":
        "Vinegar overwhelms the wine's acidity, which tastes flat. Fallback: a very crisp white, or soften the dressing.",
    "Piment fort et grand rouge tannique": "Hot chilli and a big tannic red",
    "Le piment exalte l'alcool et l'amertume ; l'alcool exalte le piment.":
        "Chilli heightens alcohol and bitterness; alcohol heightens the chilli.",
    "Poisson gras (sardine, maquereau) et rouge tannique": "Oily fish (sardine, mackerel) and tannic red",
    "Goût métallique, arrière-goût de poisson lié au fer du vin.":
        "Metallic taste, fishy aftertaste caused by the iron in the wine.",
    "Gâteau sucré et champagne brut": "Sweet cake and brut Champagne",
    "Un vin moins sucré que le dessert paraît aigre et maigre.": "A wine less sweet than the dessert tastes sour and thin.",

    # ------------------------------------------------------------ défauts
    "Goût de bouchon": "Cork taint",
    "2,4,6-trichloroanisole (TCA), parfois TBA": "2,4,6-trichloroanisole (TCA), sometimes TBA",
    "rejet vers 3,1-3,7 ng/L dans les blancs (une étude) ; même des traces de 1-2 ng/L peuvent s'additionner":
        "rejection at about 3.1-3.7 ng/L in whites (one study); even traces of 1-2 ng/L can add up",
    "carton mouillé, cave humide, champignon ; surtout un vin éteint, sans fruit : le TCA bloque les récepteurs de l'odorat (étude PNAS 2013) plus qu'il ne sent lui-même":
        "wet cardboard, damp cellar, mushroom; above all a muted wine with no fruit: TCA blocks the smell "
        "receptors (PNAS study, 2013) more than it smells itself",
    "contamination du liège, parfois de la cave entière (bois, produits chlorés)":
        "contaminated cork, sometimes the whole winery (wood, chlorinated products)",
    "Rapporter la bouteille au caviste ou la signaler au restaurant ; aucun remède fiable (le film de polyéthylène absorbe une partie du TCA).":
        "Return the bottle to the merchant or tell the restaurant; no reliable remedy (polyethylene film absorbs "
        "some of the TCA).",
    "Oxydation": "Oxidation",
    "éthanal (acétaldéhyde)": "ethanal (acetaldehyde)",
    "non chiffré ici": "not quantified here",
    "pomme blette, noix, xérès dans un vin qui ne devrait pas l'être ; robe qui brunit":
        "bruised apple, walnut, sherry in a wine that should not taste of it; browning colour",
    "trop d'oxygène : bouchon défaillant, bouteille mal conservée, vin ouvert depuis longtemps":
        "too much oxygen: faulty cork, badly stored bottle, wine opened long ago",
    "Rien à faire ; vérifier le niveau des autres bouteilles du même lot.":
        "Nothing to be done; check the fill level of the other bottles of the same lot.",
    "Réduction": "Reduction",
    "sulfure d'hydrogène (H2S), mercaptans, disulfures": "hydrogen sulphide (H2S), mercaptans, disulphides",
    "seuils très bas (mercaptans)": "very low thresholds (mercaptans)",
    "œuf pourri, allumette, caoutchouc, chou, égout": "rotten egg, struck match, rubber, cabbage, sewage",
    "levures en manque d'azote pendant la fermentation ; mercaptans formés quand le vin reste longtemps sur ses lies":
        "nitrogen-starved yeasts during fermentation; mercaptans formed when the wine stays long on its lees",
    "Aérer, carafer : l'odeur disparaît souvent en quelques minutes.":
        "Aerate, decant: the smell often disappears within minutes.",
    "Brett (Brettanomyces)": "Brett (Brettanomyces)",
    "4-éthylphénol, 4-éthylgaïacol, acide isovalérique": "4-ethylphenol, 4-ethylguaiacol, isovaleric acid",
    "4-éthylphénol au-delà d'environ 140 µg/L ; 4-éthylgaïacol au-delà d'environ 600 µg/L":
        "4-ethylphenol above about 140 µg/L; 4-ethylguaiacol above about 600 µg/L",
    "écurie, sueur de cheval, pansement, clou de girofle, fumé":
        "stable, horse sweat, sticking plaster, clove, smoky",
    "levure Brettanomyces dans les barriques ou le matériel mal entretenus ; à faible dose certains y voient de la complexité":
        "Brettanomyces yeast in poorly kept barrels or equipment; at low levels some see it as complexity",
    "Question de goût jusqu'à un certain point ; ne se corrige pas en bouteille.":
        "A matter of taste up to a point; cannot be corrected in bottle.",
    "Acidité volatile, piqûre acétique": "Volatile acidity, acetic spoilage",
    "acide acétique, acétate d'éthyle": "acetic acid, ethyl acetate",
    "fermentation normale : 0,2-0,3 g/L (équivalent H2SO4) ; plafond légal européen : 20 meq/L pour les rouges (0,98 g/L en équivalent H2SO4), 18 meq/L pour les blancs et rosés (0,88 g/L), avec des dérogations":
        "normal fermentation: 0.2-0.3 g/L (as H2SO4); EU legal ceiling: 20 meq/L for reds (0.98 g/L as H2SO4), "
        "18 meq/L for whites and rosés (0.88 g/L), with exemptions",
    "vinaigre, dissolvant, vernis à ongles ; une pointe peut « porter » les arômes":
        "vinegar, solvent, nail varnish; a touch can \"lift\" the aromas",
    "bactéries acétiques, fermentation mal maîtrisée": "acetic bacteria, poorly controlled fermentation",
    "Au-delà du seuil, le vin est impropre à la vente.": "Above the threshold, the wine is unfit for sale.",
    "Excès de soufre": "Excess sulphur",
    "dioxyde de soufre (SO2)": "sulphur dioxide (SO2)",
    "voir les teneurs légales (chapitre « La vigne soignée »)": "see the legal limits (chapter \"The tended vine\")",
    "allumette craquée, picotement du nez": "struck match, prickle in the nose",
    "sulfitage excessif, souvent dans les blancs et les liquoreux": "excessive sulphiting, often in whites and sweet wines",
    "Aérer : le SO2 libre s'évapore en partie.": "Aerate: free SO2 partly evaporates.",
    "Goût de terre": "Earthy taint",
    "géosmine": "geosmin",
    "jusqu'à 10 ng/L environ": "up to about 10 ng/L",
    "terre, betterave, navet": "earth, beetroot, turnip",
    "métabolite de micro-organismes (actinomycètes filamenteux) ; trouvée dans des rouges récents du Beaujolais, de Bordeaux, de Bourgogne et de la Loire":
        "a metabolite of micro-organisms (filamentous actinomycetes); found in recent reds from Beaujolais, "
        "Bordeaux, Burgundy and the Loire",
    "Ne se corrige pas.": "Cannot be corrected.",
    "Goût de géranium": "Geranium taint",
    "2-éthoxyhexa-3,5-diène": "2-ethoxyhexa-3,5-diene",
    "1 ng/L": "1 ng/L",
    "feuille de géranium écrasée": "crushed geranium leaf",
    "bactéries lactiques qui dégradent le sorbate de potassium ajouté comme conservateur":
        "lactic bacteria breaking down potassium sorbate added as a preservative",
    "Goût de fumée (incendies)": "Smoke taint (wildfires)",
    "phénols volatils (gaïacol, crésols) et leurs glycosides": "volatile phenols (guaiacol, cresols) and their glycosides",
    "variable": "variable",
    "fumé, médicinal, cendrier en fin de bouche": "smoky, medicinal, ashtray on the finish",
    "fumée d'incendie absorbée par les raisins (Californie 2020, Australie 2019-2020)":
        "wildfire smoke absorbed by the grapes (California 2020, Australia 2019-2020)",
    "L'élevage en barrique neuve atténue la perception (étude UC Davis 2026), sans l'effacer.":
        "Ageing in new oak reduces the perception (UC Davis study, 2026) without removing it.",
    "Vin cuit (chaleur)": "Cooked wine (heat damage)",
    "—": "—",
    "plus de 25 °C pendant longtemps": "above 25 °C for a long time",
    "fruits cuits, confiture, raisin sec ; bouchon parfois poussé, traces de coulure":
        "stewed fruit, jam, raisin; cork sometimes pushed out, signs of seepage",
    "stockage ou transport trop chauds": "storage or transport too hot",
    "Vérifier le haut de la capsule à l'achat (coulure, bouchon remonté).":
        "Check the top of the capsule when buying (seepage, raised cork).",
    "Cristaux de tartre (pas un défaut)": "Tartrate crystals (not a fault)",
    "bitartrate de potassium (« crème de tartre »)": "potassium bitartrate (\"cream of tartar\")",
    "petits cristaux (« diamants du vin ») au fond ou sous le bouchon, sans goût":
        "small crystals (\"wine diamonds\") at the bottom or under the cork, tasteless",
    "le bitartrate précipite quand la bouteille est gardée sous 10 °C environ ; il se redissout rarement":
        "the bitartrate precipitates when the bottle is kept below about 10 °C; it rarely redissolves",
    "Sans danger : c'est la crème de tartre de la pâtisserie ; on carafe ou on laisse au fond.":
        "Harmless: it is the cream of tartar used in baking; decant or leave it at the bottom.",

    # ------------------------------------------------------------ niveaux
    "Niveau parfait à tout âge ; « remarquable » pour un vin de plus de 10 ans (Tennants).":
        "Perfect level at any age; \"remarkable\" for a wine over 10 years old (Tennants).",
    "Niveau idéal, parfait pour toute bouteille, surtout de plus de 10 ans.":
        "Ideal level, perfect for any bottle, especially one over 10 years old.",
    "Remplissage un peu bas à la mise ou légère évaporation à travers le bouchon : excellent pour un vin de plus de 20 ans (WineBid) ; bon dès 15 ans (Abbey's).":
        "Slightly low fill at bottling or slight evaporation through the cork: excellent for a wine over 20 "
        "years old (WineBid); good from 15 years (Abbey's).",
    "Normal pour un bordeaux de plus de 15 ans ; très bon au-delà de 35 ans.":
        "Normal for a Bordeaux over 15 years old; very good beyond 35 years.",
    "Acceptable vers 20 ans, exceptionnel pour un vin d'avant 1950 (Tennants) ; normal à 20 ans et plus (Abbey's). Début d'usure du bouchon.":
        "Acceptable at about 20 years, exceptional for a pre-1950 wine (Tennants); normal at 20 years and over "
        "(Abbey's). The cork is starting to wear.",
    "Le niveau a baissé (bouchon fatigué ou conservation irrégulière) : pas anormal à 30-40 ans (Tennants), normal au-delà de 40 ans (WineBid), à 50 ans (Abbey's). Risque réel si l'on compte le boire.":
        "The level has dropped (tired cork or uneven storage): not abnormal at 30-40 years (Tennants), normal "
        "beyond 40 years (WineBid), at 50 years (Abbey's). A real risk if you mean to drink it.",
    "Risqué à tout âge : n'est accepté en vente que si la bouteille est exceptionnellement rare.":
        "Risky at any age: only accepted at auction if the bottle is exceptionally rare.",
    "En général imbuvable.": "Usually undrinkable.",
    "2 cm ou moins sous le bouchon : excellent à tout âge.": "2 cm or less below the cork: excellent at any age.",
    "3 cm : normal à 12 ans et plus, excellent au-delà de 25 ans ; 3,5-4 cm « excellent pour son âge » chez Tennants.":
        "3 cm: normal at 12 years and over, excellent beyond 25 years; 3.5-4 cm \"excellent for its age\" at Tennants.",
    "4 cm : normal après 20 ans, excellent après 35 ans.": "4 cm: normal after 20 years, excellent after 35 years.",
    "5 cm : courant à 30 ans et plus.": "5 cm: common at 30 years and over.",
    "5 à 7 cm : normal, voire bon, pour une bouteille de 50 ans ; même 7 cm est rarement un risque, car le bourgogne souffre moins de la vidange que le bordeaux (Tennants).":
        "5 to 7 cm: normal, even good, for a 50-year-old bottle; even 7 cm is rarely a risk, as Burgundy "
        "suffers less from ullage than Bordeaux (Tennants).",
    "aucun": "none",
    "faible": "low",
    "modéré": "moderate",
    "élevé": "high",
    "très élevé": "very high",
    "vin probablement perdu": "wine probably lost",

    # ------------------------------------------------------------ bouteille ouverte
    "réfrigérateur, bouchon hermétique": "refrigerator, airtight stopper",
    "réfrigérateur, rebouché": "refrigerator, recorked",
    "endroit frais et sombre ou réfrigérateur, rebouché": "cool dark place or refrigerator, recorked",
    "réfrigérateur": "refrigerator",
    "frais ou réfrigérateur": "cool place or refrigerator",
    "frais": "cool place",
    "semaines à mois (dires du fabricant)": "weeks to months (maker's claim)",

    # ------------------------------------------------------------ conservation (valeurs)
    "obscurité": "darkness",
    "éviter": "avoid",
    "couchée": "lying down",
    "indifférente": "does not matter",
    "couchée (CIVC) ou debout (débat)": "lying down (CIVC) or upright (debated)",
    "quelques semaines": "a few weeks",

    # ------------------------------------------------------------ verres
    "tulipe": "tulip",
    "un quart à un tiers": "a quarter to a third full",
    "tulipe haute": "tall tulip",
    "ballon large (type Bourgogne)": "wide balloon (Burgundy type)",
    "verre haut à large ouverture (type Bordeaux)": "tall glass with a wide opening (Bordeaux type)",
    "petit verre étroit (copita)": "small narrow glass (copita)",

    # ------------------------------------------------------------ descripteurs d'arômes
    "abricot": "apricot", "abricot sec": "dried apricot", "acacia": "acacia", "amande": "almond",
    "ananas": "pineapple", "aneth": "dill", "asperge": "asparagus", "banane": "banana",
    "banane séchée": "dried banana", "beurre": "butter", "biscuit": "biscuit", "bois brûlé": "charred wood",
    "bonbon anglais": "pear drop", "bourgeon de cassis": "blackcurrant leaf", "brioche": "brioche",
    "café": "coffee", "camomille": "chamomile", "canneberge": "cranberry", "canneberge séchée": "dried cranberry",
    "cannelle": "cinnamon", "caramel": "caramel", "caramel au beurre": "butterscotch",
    "carton mouillé": "wet cardboard", "cassis": "blackcurrant", "cerise noire": "black cherry",
    "cerise rouge": "red cherry", "champignon": "mushroom", "chocolat": "chocolate",
    "chèvrefeuille": "honeysuckle", "citron": "lemon", "citron vert": "lime", "clou de girofle": "clove",
    "coing": "quince", "confiture": "jam", "crème": "cream", "cuir": "leather", "cèdre": "cedar",
    "eucalyptus": "eucalyptus", "fenouil": "fennel", "ferme, écurie": "farmyard, stable",
    "feuille de tomate": "tomato leaf", "feuilles mouillées": "wet leaves", "figue": "fig",
    "fleur blanche": "white flower", "foin": "hay", "fraise": "strawberry", "framboise": "raspberry",
    "fromage": "cheese", "fruit de la passion": "passion fruit", "fruits cuits": "cooked fruit",
    "fumée": "smoke", "gibier": "game", "gingembre": "ginger", "goudron": "tar", "groseille": "redcurrant",
    "groseille à maquereau": "gooseberry", "géranium": "geranium", "herbe coupée": "cut grass",
    "kirsch": "kirsch", "kérosène": "kerosene", "laine mouillée": "wet wool", "lavande": "lavender",
    "litchi": "lychee", "mangue": "mango", "marmelade": "marmalade", "massepain": "marzipan",
    "melon": "melon", "menthe": "mint", "miel": "honey", "muscade": "nutmeg", "myrtille": "blueberry",
    "médicinal": "medicinal", "mûre": "blackberry", "mûre cuite": "cooked blackberry",
    "mûre séchée": "dried blackberry", "nectarine": "nectarine", "noisette": "hazelnut", "noix": "walnut",
    "noix de coco": "coconut", "pain": "bread", "pain grillé": "toast", "pamplemousse": "grapefruit",
    "pierre mouillée": "wet stone", "pierre à fusil": "flint", "poire": "pear", "poivre blanc": "white pepper",
    "poivre noir": "black pepper", "poivron vert": "green bell pepper", "pomme": "apple",
    "pomme séchée": "dried apple", "prune cuite": "cooked plum", "prune noire": "black plum",
    "prune rouge": "red plum", "pruneau": "prune", "pâte à pain": "bread dough", "pâtisserie": "pastry",
    "pétrole": "petrol", "pêche": "peach", "raisin": "grape", "raisin sec": "raisin", "rose": "rose",
    "réglisse": "liquorice", "résine": "resin", "salin, sapide": "saline, savoury", "soufre": "sulphur",
    "sous-bois": "forest floor", "sureau": "elderflower", "tabac": "tobacco", "terre": "earth",
    "toffee": "toffee", "vanille": "vanilla", "vernis": "varnish", "viande": "meat", "vinaigre": "vinegar",
    "violette": "violet", "végétal": "vegetal", "zeste de citron": "lemon zest", "écorce d'orange": "orange peel",
    "écurie": "stable", "œuf pourri": "rotten egg",
    "Codes de la roue des arômes : trois cercles (primaires du raisin et de la fermentation, secondaires de la vinification, tertiaires du vieillissement), familles et descripteurs du lexique WSET de niveau 3 ; les familles de la roue d'Ann C. Noble (UC Davis) sont ajoutées pour les défauts.":
        "Aroma wheel codes: three circles (primary aromas from the grape and fermentation, secondary from "
        "winemaking, tertiary from ageing), families and descriptors from the WSET Level 3 lexicon; families "
        "from Ann C. Noble's wheel (UC Davis) are added for faults.",
    "primaire": "primary", "secondaire": "secondary", "tertiaire": "tertiary", "défaut": "fault",
}


def en(texte_fr: str | None) -> str | None:
    """Texte anglais d'un libellé du dossier (le français si la traduction manque :
    l'essai `test_traductions_completes` empêche que cela arrive)."""
    if texte_fr is None:
        return None
    return TRADUCTIONS.get(texte_fr, texte_fr)
