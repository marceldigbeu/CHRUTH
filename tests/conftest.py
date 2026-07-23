import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _reglages_neufs(tmp_path_factory, monkeypatch):
    """Isole les reglages : memoire de processus vidée, cache detourne du depot.

    Deux accidents a empecher. D'une part la memoire de processus : sans purge, le
    premier test qui lit les reglages fixerait la reponse servie a tous les
    suivants, et les monkeypatch de veille_depot.lire seraient ignores. D'autre
    part le cache : `reglages.ecrire` est desormais appele en cascade par des
    fonctions anodines (sync_destinataires.ecrire_fichier), et un test l'a
    reellement fait ecrire des destinataires de test dans le reglages_cache.json
    du depot — donc dans la configuration de production du poste.

    Un test qui detourne CACHE lui-meme reste prioritaire : son monkeypatch
    s'applique apres celui-ci.
    """
    import reglages
    bac = tmp_path_factory.mktemp("reglages")
    monkeypatch.setattr(reglages, "CACHE", bac / "cache.json")
    # `reglages.ecrire` pousse aussi dans l'etat partage, qui en local est le
    # etat/veille.json du depot : sans ce detournement, un test y injecte un bloc
    # `reglages` a cote des vrais AO de la veille. C'est arrive.
    monkeypatch.setenv("CHRUTH_VEILLE_ETAT", str(bac / "veille.json"))
    # Meme raison pour les drapeaux ON/OFF : `outils.set_*.appliquer` les pose en
    # plus des reglages, et la suite a deja eteint pour de bon la veille du poste.
    import ao_config
    monkeypatch.setattr(ao_config, "ALERTE_ACTIVE_FILE", bac / "alertes_actives.flag")
    monkeypatch.setattr(ao_config, "COLLECTE_ACTIVE_FILE", bac / "collecte_active.flag")
    reglages.invalider()
    yield
    reglages.invalider()
