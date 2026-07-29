"""Le controle d'acces : ce qui ouvre, ce qui ferme, et ce qui ne casse rien."""
from __future__ import annotations

import pytest

from connexion import (authentification_configuree, est_admin, est_autorise,
                       lire_acces, message_refus, normaliser)

AUTORISES = ["collaboratrice@exemple.fr", "Responsable@Exemple.fr"]
ADMINS = ["responsable@exemple.fr"]


def test_une_adresse_de_la_liste_entre():
    assert est_autorise("collaboratrice@exemple.fr", AUTORISES)


def test_la_comparaison_ignore_la_casse_et_les_espaces():
    """Les fournisseurs d'identite ne renvoient pas tous la meme casse."""
    assert est_autorise("  RESPONSABLE@exemple.FR ", AUTORISES)


def test_une_adresse_absente_de_la_liste_est_refusee():
    assert not est_autorise("inconnu@ailleurs.fr", AUTORISES)


def test_une_liste_vide_laisse_entrer_tout_compte_authentifie():
    assert est_autorise("quelqu.un@ailleurs.fr", [])


def test_une_adresse_vide_n_entre_jamais():
    """Un compte sans email n'est pas identifiable : il ne doit pas passer,
    meme quand la liste est ouverte."""
    assert not est_autorise("", [])
    assert not est_autorise(None, [])
    assert not est_autorise("   ", AUTORISES)


def test_les_entrees_vides_de_la_liste_sont_ignorees():
    """Une ligne laissee vide dans le fichier de secrets ne doit pas
    transformer une liste fermee en liste ouverte."""
    assert not est_autorise("inconnu@ailleurs.fr", ["collaboratrice@exemple.fr", "", "  "])


def test_l_admin_est_reconnu():
    assert est_admin("responsable@exemple.fr", ADMINS)
    assert est_admin("RESPONSABLE@EXEMPLE.FR", ADMINS)


def test_sans_liste_d_admin_personne_n_est_admin():
    """L'inverse de l'acces : un droit d'administration par defaut serait
    accorde a tort."""
    assert not est_admin("responsable@exemple.fr", [])
    assert not est_admin("", [])


def test_un_simple_utilisateur_n_est_pas_admin():
    assert not est_admin("collaboratrice@exemple.fr", ADMINS)


def test_normaliser_est_stable():
    assert normaliser(" A@B.FR ") == "a@b.fr"
    assert normaliser(None) == ""


class _SecretsAbsents:
    def __getitem__(self, cle):
        raise FileNotFoundError("pas de secrets.toml")


def test_sans_fichier_de_secrets_la_plateforme_reste_ouverte():
    """Le poste local n'a pas de secrets : la garde ne doit pas l'empecher
    de demarrer."""
    assert lire_acces(_SecretsAbsents()) == ([], [])
    assert authentification_configuree(_SecretsAbsents()) is False


def test_les_listes_sont_lues_dans_les_secrets():
    secrets = {"acces": {"emails": ["a@b.fr"], "admins": ["c@d.fr"]}}
    assert lire_acces(secrets) == (["a@b.fr"], ["c@d.fr"])


def test_une_section_acces_incomplete_ne_casse_rien():
    assert lire_acces({"acces": {}}) == ([], [])
    assert lire_acces({"acces": {"emails": None, "admins": None}}) == ([], [])


def test_l_authentification_est_detectee_quand_elle_est_configuree():
    assert authentification_configuree({"auth": {"redirect_uri": "http://x"}}) is True
    assert authentification_configuree({"auth": {}}) is False
    assert authentification_configuree({}) is False


def test_le_refus_nomme_l_administrateur_a_contacter():
    message = message_refus("inconnu@ailleurs.fr", ADMINS)
    assert "inconnu@ailleurs.fr" in message
    assert "responsable@exemple.fr" in message


def test_le_refus_reste_lisible_sans_administrateur_declare():
    message = message_refus("inconnu@ailleurs.fr", [])
    assert "inconnu@ailleurs.fr" in message
    assert message.endswith(".")


@pytest.mark.parametrize("email", ["a@b.fr", "A@B.FR", " a@b.fr "])
def test_la_meme_personne_est_reconnue_quelle_que_soit_la_forme(email):
    assert est_autorise(email, ["a@b.fr"])


def test_le_fichier_de_secrets_est_ignore_par_git():
    """Il porte les identifiants OAuth et la liste des acces : le commiter
    ouvrirait l'application a qui lit le depot."""
    from pathlib import Path
    racine = Path(__file__).resolve().parent.parent
    regles = (racine / ".gitignore").read_text(encoding="utf-8")
    assert ".streamlit/secrets.toml" in regles


def test_le_fichier_de_secrets_est_exclu_de_la_copie_de_demo():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "outils"))
    import preparer_dossier_demo as pdd
    assert "secrets.toml" in pdd.EXCLUS
