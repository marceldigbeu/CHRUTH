"""Creer un compte depuis l'ecran de connexion.

L'inscription est ouverte a tous : c'est desormais la premiere chose que fait
un visiteur, et la seule qu'il ne peut pas contourner. Elle merite donc d'etre
tenue par un test de bout en bout, du champ saisi jusqu'au compte utilisable.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from streamlit.testing.v1 import AppTest

import comptes

RACINE = Path(__file__).resolve().parent.parent
ENTREE = str(RACINE / "CHRUTH_APP.py")

ADRESSE = "nouveau@chruth.fr"
MOT_DE_PASSE = "motdepasse123"


@pytest.fixture
def espace_isole(tmp_path, monkeypatch):
    """Un depot d'espaces vide et jetable, avec sa propre cle de chiffrement."""
    monkeypatch.setenv("CHRUTH_ESPACE_DIR", str(tmp_path / "membres"))
    monkeypatch.setenv("CHRUTH_ESPACE_CLE", Fernet.generate_key().decode())
    monkeypatch.setenv("CHRUTH_AO_DB", str(tmp_path / "ao.sqlite"))
    return tmp_path


def _bouton(at, libelle: str):
    for bouton in at.button:
        if bouton.label == libelle:
            return bouton
    raise AssertionError(
        f"bouton « {libelle} » absent (trouves : {[b.label for b in at.button]})")


def test_le_bouton_cree_un_compte_utilisable(espace_isole):
    """Le geste reel : on remplit les trois champs, on clique, le compte existe.

    Passer les valeurs en `args` d'un `on_click` les fige au rendu precedent :
    le callback recevait les champs vides et refusait le mot de passe.
    """
    at = AppTest.from_file(ENTREE, default_timeout=90)
    at.run()

    at.text_input(key="creer_email").set_value(ADRESSE)
    at.text_input(key="creer_nom").set_value("Nouveau Membre")
    at.text_input(key="creer_mdp").set_value(MOT_DE_PASSE)
    _bouton(at, "Créer le compte").click().run()

    assert not at.exception
    assert comptes.authentifier_local(ADRESSE, MOT_DE_PASSE), \
        "le compte n'est pas utilisable apres creation"


def test_la_confirmation_reste_affichee(espace_isole):
    """Un message ecrit depuis un callback est perdu avant le rendu : le
    visiteur clique et ne voit rien, donc recommence."""
    at = AppTest.from_file(ENTREE, default_timeout=90)
    at.run()

    at.text_input(key="creer_email").set_value(ADRESSE)
    at.text_input(key="creer_nom").set_value("Nouveau Membre")
    at.text_input(key="creer_mdp").set_value(MOT_DE_PASSE)
    _bouton(at, "Créer le compte").click().run()

    assert any("Compte créé" in m.value for m in at.success), \
        f"aucune confirmation affichee (succes : {[m.value for m in at.success]})"


def test_un_mot_de_passe_trop_court_est_refuse_avec_son_motif(espace_isole):
    at = AppTest.from_file(ENTREE, default_timeout=90)
    at.run()

    at.text_input(key="creer_email").set_value(ADRESSE)
    at.text_input(key="creer_nom").set_value("Nouveau Membre")
    at.text_input(key="creer_mdp").set_value("court")
    _bouton(at, "Créer le compte").click().run()

    assert not comptes.authentifier_local(ADRESSE, "court")
    assert any("trop court" in m.value for m in at.error), \
        f"motif du refus absent (erreurs : {[m.value for m in at.error]})"


def test_une_adresse_invalide_est_refusee_avec_son_motif(espace_isole):
    at = AppTest.from_file(ENTREE, default_timeout=90)
    at.run()

    at.text_input(key="creer_email").set_value("pas-une-adresse")
    at.text_input(key="creer_nom").set_value("Nouveau Membre")
    at.text_input(key="creer_mdp").set_value(MOT_DE_PASSE)
    _bouton(at, "Créer le compte").click().run()

    assert any("adresse invalide" in m.value for m in at.error), \
        f"motif du refus absent (erreurs : {[m.value for m in at.error]})"
