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


def _secrets(monkeypatch, tmp_path, contenu=None):
    """Redirige les identifiants vers un fichier jetable."""
    import json

    import identifiants_smtp
    chemin = tmp_path / "alertes_secrets.json"
    if contenu is not None:
        chemin.write_text(json.dumps(contenu), encoding="utf-8")
    monkeypatch.setattr(identifiants_smtp, "ALERTE_SECRETS_FILE", chemin)
    return chemin


def test_l_expediteur_est_affiche_et_modifiable(monkeypatch, tmp_path):
    _secrets(monkeypatch, tmp_path, {"smtp_user": "envoi@x.fr", "smtp_password": "secret"})
    at = _lancer(monkeypatch)
    assert "envoi@x.fr" in " ".join(m.value for m in at.markdown)
    assert any(ti.key == "expediteur_envoi" for ti in at.text_input)


def test_l_expediteur_et_le_mot_de_passe_s_enregistrent_ensemble(monkeypatch, tmp_path):
    """Ils forment une paire : les changer separement casse tous les envois."""
    import identifiants_smtp
    chemin = _secrets(monkeypatch, tmp_path, {})
    ecrits = []
    at = _lancer(monkeypatch, ecrits=ecrits)
    at.text_input(key="expediteur_envoi").set_value("nouveau@x.fr")
    at.text_input(key="mdp_application").set_value("abcd efgh ijkl mnop")
    # Le bouton d'un formulaire porte une cle prefixee par Streamlit.
    soumettre = next(b for b in at.button if b.key.startswith("FormSubmitter:identifiants_envoi"))
    soumettre.click().run()

    assert identifiants_smtp.expediteur(chemin) == "nouveau@x.fr"
    assert identifiants_smtp.mot_de_passe_defini(chemin) is True
    assert {"expediteur": "nouveau@x.fr"} in ecrits,         "l'adresse, non secrete, doit aussi aller dans les reglages partages"


def test_le_mot_de_passe_enregistre_n_apparait_jamais_sur_la_page(monkeypatch, tmp_path):
    """Le garde-fou de cette page : on peut saisir un secret, jamais le relire."""
    _secrets(monkeypatch, tmp_path,
             {"smtp_user": "envoi@x.fr", "smtp_password": "mot-de-passe-tres-secret"})
    at = _lancer(monkeypatch)
    tout = " ".join(
        [m.value for m in at.markdown] + [c.value for c in at.caption]
        + [str(ti.value) for ti in at.text_input]
    )
    assert "mot-de-passe-tres-secret" not in tout


def test_l_absence_de_mot_de_passe_est_signalee(monkeypatch, tmp_path):
    """Sans lui aucun email ne part : le silence laisserait croire que tout va bien."""
    _secrets(monkeypatch, tmp_path, {"smtp_user": "envoi@x.fr"})
    at = _lancer(monkeypatch)
    tout = " ".join(m.value for m in at.markdown).lower()
    assert "absent" in tout


def test_l_interrupteur_des_mots_cles_rh(monkeypatch):
    ecrits = []
    at = _lancer(monkeypatch, ecrits=ecrits)
    at.button(key="basculer_rh").click().run()
    assert ecrits[-1] == {"mots_cles_rh_actifs": False}
