"""Un seul interrupteur de notifications, quelle que soit la page.

Deux commutateurs portant le meme nom coexistaient : la page Veille ecrivait
`etat["notifications"]` (lu par le veilleur cloud) et la page Reglages
`etat["reglages"]["notifications"]` (lu par le pipeline local). Couper sur l'une
laissait l'autre ouverte, sans que rien ne le signale — c'est arrive.

L'etat porte deja le bloc `reglages` : `veille_etat` y lit et y ecrit, sans
importer `reglages` (ce qui bouclerait : reglages -> veille_depot -> veille_etat).
"""
import reglages
import veille_depot
import veille_etat


def _etat(reg=None, ancienne=None):
    e = {"version": 1, "maj_le": "", "aos": {}, "guide_messages": ""}
    if reg is not None:
        e["reglages"] = reg
    if ancienne is not None:
        e["notifications"] = ancienne
    return e


def test_la_page_veille_lit_le_bloc_reglages():
    assert veille_etat.notifications_actives(_etat(reg={"notifications": False})) is False
    assert veille_etat.notifications_actives(_etat(reg={"notifications": True})) is True


def test_l_ancienne_cle_sert_de_repli():
    """Migration douce : un etat en service ne porte pas encore le bloc reglages."""
    assert veille_etat.notifications_actives(_etat(ancienne=False)) is False


def test_une_coupure_deja_posee_n_est_jamais_re_armee():
    """Le bloc dit ON, l'ancienne cle dit OFF : un coupe-circuit ne se rouvre pas seul."""
    etat = _etat(reg={"notifications": True}, ancienne=False)
    assert veille_etat.notifications_actives(etat) is False


def test_un_etat_muet_laisse_les_notifications_actives():
    assert veille_etat.notifications_actives(_etat()) is True


def test_couper_depuis_la_page_veille_ecrit_dans_le_bloc_reglages():
    etat = _etat(reg={"notifications": True})
    veille_etat.definir_notifications(etat, False)
    assert etat["reglages"]["notifications"] is False


def test_couper_depuis_la_page_veille_purge_l_ancienne_cle():
    """Laisser l'ancienne cle derriere soi recreerait la divergence."""
    etat = _etat(reg={"notifications": True}, ancienne=True)
    veille_etat.definir_notifications(etat, False)
    assert "notifications" not in etat


def test_les_deux_pages_voient_la_meme_chose(tmp_path, monkeypatch):
    """Le test qui aurait attrape le bug : couper d'un cote, lire de l'autre."""
    monkeypatch.setattr(reglages, "CACHE", tmp_path / "cache.json")
    etat = _etat(reg={"notifications": True})
    veille_etat.definir_notifications(etat, False)          # page Veille
    monkeypatch.setattr(veille_depot, "lire", lambda: (etat, None))
    reglages.invalider()
    assert reglages.lire()["notifications"] is False        # page Reglages


def test_reglages_adopte_l_ancienne_cle(tmp_path, monkeypatch):
    monkeypatch.setattr(reglages, "CACHE", tmp_path / "cache.json")
    monkeypatch.setattr(veille_depot, "lire", lambda: (_etat(ancienne=False), None))
    reglages.invalider()
    assert reglages.lire()["notifications"] is False


def test_ecrire_purge_l_ancienne_cle(tmp_path, monkeypatch):
    """Sans cette purge, « une coupure posee l'emporte » devient un piege.

    Une ancienne cle restee a False rendrait l'interrupteur IMPOSSIBLE a rouvrir
    depuis la page Reglages : le repli ecraserait indefiniment le bloc.
    """
    monkeypatch.setattr(reglages, "CACHE", tmp_path / "cache.json")
    etat = _etat(reg={"notifications": False}, ancienne=False)
    monkeypatch.setattr(veille_depot, "lire", lambda: (etat, None))
    monkeypatch.setattr(veille_depot, "ecrire", lambda e, sha, message="x": "sha")

    reglages.invalider()
    reglages.ecrire({"notifications": True})
    assert "notifications" not in etat
    assert etat["reglages"]["notifications"] is True

    reglages.invalider()
    assert reglages.lire()["notifications"] is True   # reactivable, enfin
