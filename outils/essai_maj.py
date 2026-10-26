# -*- coding: utf-8 -*-
"""Essai RÉEL de la mise à jour automatique sous Linux, avant de publier.

Une Release en BROUILLON est invisible pour `releases/latest` : l'updater d'une
installation ne la verrait pas. Cet essai fait tourner l'updater DÉJÀ INSTALLÉ
(celui de l'ancienne version, avec son propre Python) contre les VRAIS fichiers
du brouillon, téléchargés à part (`gh release download`) : seule la lecture
réseau est remplacée — la réponse de l'API (les métadonnées du brouillon,
`gh api`) et les adresses de téléchargement (les fichiers locaux). Choix de
l'archive, contrôle de taille et de SHA256SUMS, vérification de l'archive,
remplacement de app/ : tout le reste est le code installé.

    python outils/essai_maj.py <dossier installé> <release.json> <dossier des fichiers> <ancienne version>

À lancer avec le Python de l'installation : <dossier installé>/python/bin/python3.
"""
import io
import json
import sys
from pathlib import Path


def main() -> int:
    installe, release_json, fichiers, ancienne = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
    sys.path.insert(0, str(installe / "app"))
    import updater
    release = json.loads(release_json.read_text(encoding="utf-8"))
    vrai_open = updater._open

    class Reponse(io.BytesIO):
        def __init__(self, donnees):
            super().__init__(donnees)
            self.headers = {"Content-Length": str(len(donnees))}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            self.close()

    def faux_open(url):
        if url == updater.API_LATEST:
            print(f"  API (brouillon {release['tag_name']}, {len(release['assets'])} fichiers)")
            return Reponse(json.dumps(release).encode("utf-8"))
        nom = url.rsplit("/", 1)[-1]
        chemin = fichiers / nom
        if chemin.is_file():
            print(f"  téléchargement : {nom} ({chemin.stat().st_size / 1e6:.1f} Mo, fichier du brouillon)")
            return Reponse(chemin.read_bytes())
        return vrai_open(url)

    updater._open = faux_open
    print(f"version installée : {ancienne} ; dépôt : {updater.REPO} ; paquet reconnu : {updater.is_packaged()}")
    maj = updater.check(ancienne)
    if not maj:
        print("ÉCHEC : aucune mise à jour trouvée")
        return 1
    print(f"mise à jour trouvée : {maj['version']} — archive {maj['nom']} ({maj['size'] / 1e6:.1f} Mo)")
    print("notes (fr) :", updater.notes_dans_la_langue(maj["notes"], "fr")[:160].replace("\n", " "), "…")
    ok = updater.download_and_apply(maj)
    print("posée :", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
