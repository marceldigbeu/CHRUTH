"""Un run ne doit pas relire l'etat partage une fois par AO.

`ao_pertinence._mots_cles` interroge les reglages pour savoir si les mots-cles de
personnel sont actifs, et il est appele DANS la boucle de tri. En mode cloud
(CHRUTH_VEILLE_SOURCE=github), chaque lecture est une requete HTTP vers l'API
GitHub, avec 20 s de timeout : sans memoire de processus, un run de 14 AO faisait
14 requetes pour la meme reponse.
"""
import reglages
import veille_depot


def _etat(reg=None):
    e = {"version": 1, "maj_le": "", "aos": {}, "guide_messages": ""}
    if reg is not None:
        e["reglages"] = reg
    return e


def test_l_etat_partage_n_est_lu_qu_une_fois_par_run(tmp_path, monkeypatch):
    monkeypatch.setattr(reglages, "CACHE", tmp_path / "cache.json")
    appels = {"n": 0}

    def compte():
        appels["n"] += 1
        return _etat({"destinataires": ["a@x.fr"]}), None

    monkeypatch.setattr(veille_depot, "lire", compte)
    for _ in range(10):
        assert reglages.lire()["destinataires"] == ["a@x.fr"]
    assert appels["n"] == 1


def test_ecrire_rend_la_nouvelle_valeur_visible(tmp_path, monkeypatch):
    """La memoire de processus ne doit jamais servir une valeur perimee par nos soins."""
    monkeypatch.setattr(reglages, "CACHE", tmp_path / "cache.json")
    monkeypatch.setattr(veille_depot, "lire", lambda: (_etat(), None))
    monkeypatch.setattr(veille_depot, "ecrire", lambda etat, sha, message="x": "sha")

    assert reglages.lire()["notifications"] is True
    reglages.ecrire({"notifications": False})
    assert reglages.lire()["notifications"] is False


def test_rafraichir_force_une_relecture(tmp_path, monkeypatch):
    """Le point d'entree d'un run local doit repartir de l'etat partage."""
    monkeypatch.setattr(reglages, "CACHE", tmp_path / "cache.json")
    appels = {"n": 0}

    def compte():
        appels["n"] += 1
        return _etat({"destinataires": [f"a{appels['n']}@x.fr"]}), None

    monkeypatch.setattr(veille_depot, "lire", compte)
    assert reglages.lire()["destinataires"] == ["a1@x.fr"]
    assert reglages.rafraichir()["destinataires"] == ["a2@x.fr"]
