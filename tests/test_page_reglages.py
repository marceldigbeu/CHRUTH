"""Page Reglages : ecrit dans la source unique, n'expose jamais un secret."""
from pathlib import Path

import reglages
from streamlit.testing.v1 import AppTest

PAGE = str(Path(__file__).resolve().parent.parent / "pages_reglages.py")


def _lancer(monkeypatch, valeurs=None, ecrits=None):
    valeurs = valeurs or dict(reglages.DEFAUTS)
    monkeypatch.setattr(reglages, "lire", lambda: dict(valeurs))
    if ecrits is not None:
        monkeypatch.setattr(reglages, "ecrire", lambda m: ecrits.append(m) or {**valeurs, **m})
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    return at


def test_la_page_demarre(monkeypatch):
    at = _lancer(monkeypatch)
    assert not at.exception


def test_les_destinataires_sont_enregistres(monkeypatch):
    ecrits = []
    at = _lancer(monkeypatch, ecrits=ecrits)
    at.text_area(key="destinataires").input("a@x.fr\nb@x.fr").run()
    at.button(key="enregistrer_destinataires").click().run()
    assert ecrits[-1] == {"destinataires": ["a@x.fr", "b@x.fr"]}


def test_l_expediteur_est_affiche_sans_etre_modifiable(monkeypatch):
    """Adresse et mot de passe forment une paire : changer l'une ici casserait l'envoi."""
    at = _lancer(monkeypatch, valeurs={**reglages.DEFAUTS, "expediteur": "envoi@x.fr"})
    assert "envoi@x.fr" in " ".join(m.value for m in at.markdown)
    assert not any(ti.key == "expediteur" for ti in at.text_input)


def test_aucun_mot_de_passe_n_est_affiche(monkeypatch):
    at = _lancer(monkeypatch)
    tout = " ".join(m.value for m in at.markdown).lower()
    assert "mot de passe" not in tout or "jamais" in tout


def test_l_interrupteur_des_mots_cles_rh(monkeypatch):
    ecrits = []
    at = _lancer(monkeypatch, ecrits=ecrits)
    at.button(key="basculer_rh").click().run()
    assert ecrits[-1] == {"mots_cles_rh_actifs": False}
