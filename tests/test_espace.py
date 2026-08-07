"""Tests de l'espace membres : isolation, persistance, suppression.

Couvre les criteres d'acceptation centraux : deux utilisateurs ne se voient
jamais (isolation), les donnees survivent a une relecture depuis le disque
(persistance, simule le redemarrage), et la suppression complete au depart.
"""
from __future__ import annotations

import pytest

import espace
import espace_depot


@pytest.fixture(autouse=True)
def espace_local(tmp_path, monkeypatch):
    """Espace local propre : dossier temporaire, source locale."""
    espace_depot._reinitialiser_cle()
    monkeypatch.setenv("CHRUTH_ESPACE_SOURCE", "local")
    monkeypatch.setenv("CHRUTH_ESPACE_DIR", str(tmp_path / "membres"))
    yield
    espace_depot._reinitialiser_cle()


def test_profil_vide_par_defaut():
    assert espace.profil("alice@chruth.fr")["nom_affiche"] == ""


def test_existe_avant_et_apres_creation():
    assert not espace.existe("alice@chruth.fr")
    espace.creer("alice@chruth.fr")
    assert espace.existe("alice@chruth.fr")


def test_enregistrer_profil_puis_relire():
    espace.creer("alice@chruth.fr")
    espace.enregistrer_profil("alice@chruth.fr",
                              {"nom_affiche": "Alice", "role": "Commerciale"})
    profil = espace.profil("alice@chruth.fr")
    assert profil["nom_affiche"] == "Alice"
    assert profil["role"] == "Commerciale"


def test_enregistrer_profil_ne_garde_que_les_champs_connus():
    espace.creer("alice@chruth.fr")
    espace.enregistrer_profil("alice@chruth.fr", {"inconnu": "x"})
    assert "inconnu" not in espace.profil("alice@chruth.fr")


def test_preferences_enregistrees_et_relues():
    espace.creer("alice@chruth.fr")
    espace.enregistrer_preferences("alice@chruth.fr",
                                   {"departements": ["75", "92"], "periode": "14 derniers jours"})
    pref = espace.preferences("alice@chruth.fr")
    assert pref["departements"] == ["75", "92"]
    assert pref["periode"] == "14 derniers jours"


def test_deux_utilisateurs_isoles():
    espace.creer("alice@chruth.fr")
    espace.creer("bob@chruth.fr")
    espace.enregistrer_profil("alice@chruth.fr", {"nom_affiche": "Alice"})
    espace.sauver_note_ao("alice@chruth.fr", "AO-1", "note privee d'Alice")
    espace.definir_statut_ao("alice@chruth.fr", "AO-1", "favori")

    assert espace.profil("bob@chruth.fr")["nom_affiche"] == ""
    assert espace.note_ao("bob@chruth.fr", "AO-1") == ""
    assert espace.statut_ao("bob@chruth.fr", "AO-1") == ""
    assert espace.aos("bob@chruth.fr") == {}


def test_notes_et_statuts_par_ao():
    espace.creer("alice@chruth.fr")
    espace.definir_statut_ao("alice@chruth.fr", "AO-1", "a_voir")
    espace.sauver_note_ao("alice@chruth.fr", "AO-1", "contact a rappeler")
    assert espace.statut_ao("alice@chruth.fr", "AO-1") == "a_voir"
    assert espace.note_ao("alice@chruth.fr", "AO-1") == "contact a rappeler"

    espace.effacer_note_ao("alice@chruth.fr", "AO-1")
    assert espace.note_ao("alice@chruth.fr", "AO-1") == ""
    assert espace.statut_ao("alice@chruth.fr", "AO-1") == "a_voir"


def test_statut_invalide_refuse():
    espace.creer("alice@chruth.fr")
    with pytest.raises(ValueError):
        espace.definir_statut_ao("alice@chruth.fr", "AO-1", "pas_un_statut")


def test_aos_snapshot():
    espace.creer("alice@chruth.fr")
    espace.definir_statut_ao("alice@chruth.fr", "AO-1", "favori")
    espace.sauver_note_ao("alice@chruth.fr", "AO-1", "note")
    espace.definir_statut_ao("alice@chruth.fr", "AO-2", "mis_de_cote")
    suivi = espace.aos("alice@chruth.fr")
    assert suivi["AO-1"] == {"statut": "favori", "note": "note"}
    assert suivi["AO-2"] == {"statut": "mis_de_cote", "note": ""}


def test_messages_ajout_et_suppression():
    espace.creer("alice@chruth.fr")
    espace.ajouter_message("alice@chruth.fr",
                           {"objet": "Marché nettoyage Mairie", "email": "Bonjour...",
                            "script": "Appel", "source": "ia"})
    espace.ajouter_message("alice@chruth.fr",
                           {"objet": "Clinique", "email": "Bonjour...", "script": "",
                            "source": "base"})
    msgs = espace.messages("alice@chruth.fr")
    assert len(msgs) == 2
    assert msgs[0]["objet"] == "Clinique"
    espace.supprimer_message("alice@chruth.fr", 0)
    assert [m["objet"] for m in espace.messages("alice@chruth.fr")] == ["Marché nettoyage Mairie"]


def test_journal_plus_recent_en_premier():
    espace.creer("alice@chruth.fr")
    espace.noter("alice@chruth.fr", "a consulte l'AO AO-1")
    espace.noter("alice@chruth.fr", "a note l'AO AO-1")
    journal = espace.journal("alice@chruth.fr")
    assert len(journal) == 2
    assert journal[0]["evenement"] == "a note l'AO AO-1"


def test_desactiver_et_reactiver():
    espace.creer("alice@chruth.fr")
    assert espace.actif("alice@chruth.fr")
    espace.desactiver("alice@chruth.fr")
    assert not espace.actif("alice@chruth.fr")
    espace.reactiver("alice@chruth.fr")
    assert espace.actif("alice@chruth.fr")


def test_suppression_complete():
    espace.creer("alice@chruth.fr")
    espace.enregistrer_profil("alice@chruth.fr", {"nom_affiche": "Alice"})
    espace.sauver_note_ao("alice@chruth.fr", "AO-1", "note")
    espace.supprimer("alice@chruth.fr")
    assert not espace.existe("alice@chruth.fr")
    assert espace.lister_membres() == []
    assert espace.profil("alice@chruth.fr")["nom_affiche"] == ""


def test_mot_de_passe_stocke_et_relu():
    espace.creer("alice@chruth.fr")
    espace.definir_mot_de_passe("alice@chruth.fr", "hache-scrypt")
    assert espace.mot_de_passe("alice@chruth.fr") == "hache-scrypt"


def test_lister_membres_ordres():
    espace.creer("bob@chruth.fr")
    espace.creer("alice@chruth.fr")
    assert espace.lister_membres() == ["alice@chruth.fr", "bob@chruth.fr"]
