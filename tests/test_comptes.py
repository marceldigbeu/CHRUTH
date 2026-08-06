"""Tests de l'identite : Google, compte local, mode poste sans authentification.

Couvre le refus d'un mauvais mot de passe, le compte local desactive, et
l'utilisateur local par defaut quand aucun fournisseur n'est configure.
"""
from __future__ import annotations

import pytest

import comptes
import espace
import espace_depot


@pytest.fixture(autouse=True)
def espace_local(tmp_path, monkeypatch):
    espace_depot._reinitialiser_cle()
    monkeypatch.setenv("CHRUTH_ESPACE_SOURCE", "local")
    monkeypatch.setenv("CHRUTH_ESPACE_DIR", str(tmp_path / "membres"))
    yield
    espace_depot._reinitialiser_cle()


class Session:
    def __init__(self):
        self._donnees = {}

    def get(self, cle, defaut=None):
        return self._donnees.get(cle, defaut)

    def __setitem__(self, cle, valeur):
        self._donnees[cle] = valeur

    def __getitem__(self, cle):
        return self._donnees[cle]


class Utilisateur:
    def __init__(self, email="", nom="", photo="", connecte=False):
        self.email = email
        self.name = nom
        self.picture = photo
        self.is_logged_in = connecte


class StFake:
    """Substitut minimal de streamlit pour les tests de resolution d'identite."""

    def __init__(self, secrets=None, user=None, session=None):
        self.secrets = secrets if secrets is not None else {}
        self.user = user or Utilisateur()
        self.session_state = session or Session()


def _avec_auth():
    return {"auth": {"google": {}}}


def test_utilisateur_local_par_defaut_sans_authentification():
    st = StFake(secrets={})
    assert comptes.utilisateur_courant(st) == comptes.utilisateur_local_defaut()


def test_utilisateur_local_defaut_personnalisable(monkeypatch):
    monkeypatch.setenv("CHRUTH_UTILISATEUR_LOCAL", "poste@chruth")
    st = StFake(secrets={})
    assert comptes.utilisateur_courant(st) == "poste@chruth"


def test_utilisateur_courant_depuis_google():
    st = StFake(secrets=_avec_auth(),
                user=Utilisateur(email="alice@chruth.fr", connecte=True))
    assert comptes.utilisateur_courant(st) == "alice@chruth.fr"


def test_utilisateur_courant_depuis_connexion_locale():
    st = StFake(secrets=_avec_auth())
    comptes.connecter_local(st, "bob@chruth.fr")
    assert comptes.utilisateur_courant(st) == "bob@chruth.fr"


def test_utilisateur_courant_vide_sans_entree():
    st = StFake(secrets=_avec_auth())
    assert comptes.utilisateur_courant(st) == ""


def test_est_admin_poste_local():
    st = StFake(secrets={})
    assert comptes.est_admin_courant(st)


def test_est_admin_google_selon_liste():
    st = StFake(secrets=_avec_auth(),
                user=Utilisateur(email="alice@chruth.fr", connecte=True))
    comptes.connecter_local(st, "alice@chruth.fr")
    st.session_state = Session()
    assert not comptes.est_admin_courant(st)


def test_est_connecte_poste_sans_session():
    st = StFake(secrets={})
    assert not comptes.est_connecte(st)


def test_est_connecte_apres_connexion_locale():
    st = StFake(secrets=_avec_auth())
    comptes.connecter_local(st, "alice@chruth.fr")
    assert comptes.est_connecte(st)
    comptes.deconnecter(st)
    assert not comptes.est_connecte(st)


def test_est_connecte_depuis_google():
    st = StFake(secrets=_avec_auth(),
                user=Utilisateur(email="alice@chruth.fr", connecte=True))
    assert comptes.est_connecte(st)


def test_est_admin_respecte_liste_sans_auth():
    secrets = {"acces": {"admins": ["alice@chruth.fr"]}}
    st = StFake(secrets=secrets)
    comptes.connecter_local(st, "bob@chruth.fr")
    assert not comptes.est_admin_courant(st)
    comptes.connecter_local(st, "alice@chruth.fr")
    assert comptes.est_admin_courant(st)


# --- Mots de passe ----------------------------------------------------------

def test_hacher_et_verifier():
    h = comptes.hacher("mot-de-passe")
    assert h.startswith("scrypt$")
    assert comptes.verifier_mot_de_passe("mot-de-passe", h)
    assert not comptes.verifier_mot_de_passe("autre", h)


def test_deux_hachages_du_meme_mot_de_passe_different():
    h1 = comptes.hacher("mot-de-passe")
    h2 = comptes.hacher("mot-de-passe")
    assert h1 != h2


def test_creer_compte_local_stocke_un_hachage():
    comptes.creer_compte_local("alice@chruth.fr", "Alice", "secret-solide")
    assert espace.mot_de_passe("alice@chruth.fr").startswith("scrypt$")
    assert espace.mot_de_passe("alice@chruth.fr") != "secret-solide"
    assert espace.profil("alice@chruth.fr")["nom_affiche"] == "Alice"


def test_creer_compte_local_mot_de_passe_trop_court():
    with pytest.raises(ValueError):
        comptes.creer_compte_local("alice@chruth.fr", "Alice", "court")


def test_creer_compte_local_email_invalide():
    with pytest.raises(ValueError):
        comptes.creer_compte_local("pas-une-adresse", "Alice", "secret-solide")


def test_authentifier_local_ok_et_refuse():
    comptes.creer_compte_local("alice@chruth.fr", "Alice", "secret-solide")
    assert comptes.authentifier_local("alice@chruth.fr", "secret-solide")
    assert not comptes.authentifier_local("alice@chruth.fr", "mauvais")


def test_authentifier_local_compte_desactive_refuse():
    comptes.creer_compte_local("alice@chruth.fr", "Alice", "secret-solide")
    espace.desactiver("alice@chruth.fr")
    assert not comptes.authentifier_local("alice@chruth.fr", "secret-solide")


def test_authentifier_local_compte_inconnu_refuse():
    assert not comptes.authentifier_local("personne@chruth.fr", "secret-solide")


def test_connecter_et_deconnecter_local():
    st = StFake(secrets=_avec_auth())
    comptes.connecter_local(st, "alice@chruth.fr")
    assert comptes.utilisateur_courant(st) == "alice@chruth.fr"
    comptes.deconnecter(st)
    assert comptes.utilisateur_courant(st) == ""


def test_identite_google_avec_photo():
    st = StFake(secrets=_avec_auth(),
                user=Utilisateur(email="alice@chruth.fr", nom="Alice",
                                 photo="https://photo", connecte=True))
    identite = comptes.identite(st)
    assert identite["email"] == "alice@chruth.fr"
    assert identite["nom"] == "Alice"
    assert identite["photo"] == "https://photo"
