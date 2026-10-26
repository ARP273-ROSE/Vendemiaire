# -*- coding: utf-8 -*-
"""Photos d'étiquette (phase 2) : détection des bords et redressement sur des
photos de DÉMONSTRATION dessinées par l'application (libres de droits),
déroulage, vignettes en cache, original gardé ; OCR local (Tesseract) et
chaîne complète photo -> texte -> candidats LWIN."""
import math

import pytest

from vendemiaire import demo_photos, images, ocr

VIN = {"producteur": "Château des Trois Chênes", "cuvee": "Grand vin", "appellation": "Pauillac",
       "millesime": 2015, "couleur": "rouge", "degre": 13.5}


@pytest.fixture
def photo(app, tmp_path):
    return demo_photos.generer(VIN, tmp_path / "photo.jpg")


def _ecart(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


@pytest.mark.parametrize("graine", [3, 7, 11])
def test_detection_des_bords(app, tmp_path, graine):
    chemin, vrais = demo_photos.generer(VIN, tmp_path / f"p{graine}.jpg", graine=graine)
    img = images.charger(chemin)
    d = images.detecter_etiquette(img)
    assert d is not None and d.confiance > 0.8
    diagonale = math.hypot(img.width(), img.height())
    assert all(_ecart(a, b) < 0.025 * diagonale for a, b in zip(d.coins, vrais)), (d.coins, vrais)


def test_rien_a_detecter_sur_une_photo_uniforme(app):
    from PyQt6.QtGui import QColor, QImage
    img = QImage(400, 300, QImage.Format.Format_RGB32)
    img.fill(QColor("#404040"))
    assert images.detecter_etiquette(img) is None


def test_redressement_et_deroulage(app, photo):
    chemin, vrais = photo
    img = images.charger(chemin)
    plat = images.redresser(img, vrais)
    assert abs(plat.width() / plat.height() - 900 / 1200) < 0.06        # proportions de l'étiquette
    deroule = images.derouler(plat, 0.6)
    assert deroule.width() > plat.width() and deroule.height() == plat.height()
    r = images.Retouche(coins=vrais, quarts=1, courbure=0.2, auto=True)
    assert images.Retouche.depuis_json(r.json()).coins == [tuple(c) for c in vrais]
    tourne = images.appliquer(img, images.Retouche(quarts=1))
    assert (tourne.width(), tourne.height()) == (img.height(), img.width())


def test_vignettes_en_cache(app, photo, tmp_path):
    chemin, _ = photo
    cache = tmp_path / "vignettes"
    v1 = images.vignette(chemin, 150, 200, cache)
    assert v1 is not None and v1.exists()
    assert images.vignette(chemin, 150, 200, cache) == v1               # relue, pas refaite
    from PyQt6.QtGui import QImage
    q = QImage(str(v1))
    assert q.width() <= 150 and q.height() <= 200
    assert images.vignette(tmp_path / "absente.jpg", 10, 10, cache) is None


def test_photo_retouchee_original_garde(app, cave, photo, tmp_path):
    chemin, vrais = photo
    vin = cave.enregistrer_vin({"producteur": "Château des Trois Chênes"})
    img = images.charger(chemin)
    r = images.Retouche(coins=vrais, auto=True)
    traite = images.enregistrer(images.appliquer(img, r), tmp_path / "t.jpg")
    iid = cave.ajouter_image(traite, vin_id=vin, original=chemin, retouche=r.json(), texte_ocr="PAUILLAC")
    im = cave.image(iid)
    assert cave.chemin_image(im["fichier"]) and cave.chemin_image(im["fichier_original"])
    assert cave.image_principale(vin) == cave.chemin_image(im["fichier"])
    # nouvelle retouche : l'original reste, l'ancienne version redressée part
    ancien = cave.chemin_image(im["fichier"])
    r2 = images.Retouche(coins=None, quarts=2)
    traite2 = images.enregistrer(images.appliquer(img, r2), tmp_path / "t2.jpg")
    cave.retoucher_image(iid, traite2, r2.json())
    im2 = cave.image(iid)
    assert im2["fichier_original"] == im["fichier_original"] and im2["texte_ocr"] == "PAUILLAC"
    assert not ancien.exists() and cave.chemin_image(im2["fichier"])
    assert len(cave.mur(statut="tous")) == 1 and cave.mur(statut="tous")[0]["photo"]
    cave.supprimer_image(iid)
    assert cave.images(vin) == [] and not (cave.dossier_images / im["fichier_original"]).exists()


# ---------------------------------------------------------------- OCR
def test_indices_d_une_etiquette():
    texte = ("CHÂTEAU DES\nTROIS CHENES\nGrand vin\nPauillac\nAPPELLATION PAUILLAC CONTRÔLÉE\n2015\n"
             "MIS EN BOUTEILLE AU CHÂTEAU\n13,5 % vol 75 cl\nEAN 3017620422003")
    i = ocr.indices(texte)
    assert (i.millesime, i.degre, i.contenance_cl) == (2015, 13.5, 75.0)
    assert i.eans == ["3017620422003"] and i.couleur is None
    assert ocr.indices("Vin rouge — 12 % vol — 1,5 L").couleur == "rouge"
    assert ocr.indices("12 % vol 1,5 L").contenance_cl == 150.0
    assert ocr.indices("Château Rougemont").couleur is None            # pas « rouge »


def test_lecture_du_tsv_de_tesseract():
    tsv = ("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
           "5\t1\t1\t1\t1\t1\t10\t10\t200\t60\t95\tCHÂTEAU\n"
           "5\t1\t1\t1\t1\t2\t220\t10\t100\t60\t93\tDES\n"
           "5\t1\t1\t1\t2\t1\t10\t90\t50\t20\t91\tGrand\n"
           "5\t1\t1\t1\t2\t2\t70\t90\t40\t20\t12\t~~\n")
    mots = ocr.analyser_tsv(tsv)
    assert [m.texte for m in mots] == ["CHÂTEAU", "DES", "Grand"]          # confiance < 30 écartée
    r = ocr.ResultatOCR(ocr.texte_depuis_mots(mots), mots)
    assert r.texte == "CHÂTEAU DES\nGrand" and r.lignes_principales(1) == ["CHÂTEAU DES"]


tesseract = pytest.mark.skipif(not ocr.moteur(), reason="Tesseract absent (installé en CI)")


@tesseract
def test_ocr_sur_une_photo_de_demonstration(app, photo):
    chemin, vrais = photo
    img = images.charger(chemin)
    plat = images.appliquer(img, images.Retouche(coins=images.detecter_etiquette(img).coins))
    r = ocr.lire(plat)
    t = r.texte.upper()
    assert "TROIS" in t and "PAUILLAC" in t and "2015" in t
    i = ocr.indices(r.texte)
    assert i.millesime == 2015 and i.degre == 13.5


@tesseract
def test_chaine_photo_texte_candidats(app, photo, cave_demo):
    """Une bouteille inconnue : photo -> redressement -> OCR -> registre -> LWIN -> candidat."""
    from vendemiaire import demo
    from vendemiaire.mondial import appariement
    demo.references_demo(cave_demo)
    chemin, _ = photo
    img = images.charger(chemin)
    plat = images.appliquer(img, images.Retouche(coins=images.detecter_etiquette(img).coins))
    r = ocr.lire(plat)
    refs = cave_demo.references
    ind = ocr.indices(r.texte, r.lignes_principales(), refs)
    assert "Pauillac" in ind.appellations
    d = appariement.decider(appariement.candidats_lwin(refs, ocr.requete_depuis_indices(ind)))
    assert d.candidats[0].libelle.startswith("Château des Trois Chênes")
    assert d.motif in ("sur", "ambigu")
