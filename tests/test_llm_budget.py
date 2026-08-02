"""Plafonner ce qu'on envoie et ce qu'on recoit d'une API payante.

Sans plafond, une fiche CHRUTH bavarde ou un intitule de marche a rallonge
part tel quel, et la reponse n'a aucune borne : la facture suit le texte. Ces
tests fixent les deux bouts — l'entree tronquee, la sortie bornee — et
l'estimation affichee avant de payer.
"""
from __future__ import annotations

import llm_client


# --- Estimation -------------------------------------------------------------

def test_l_estimation_croit_avec_la_longueur():
    court = llm_client.estimer_tokens("Nettoyage des locaux")
    long = llm_client.estimer_tokens("Nettoyage des locaux " * 50)
    assert 0 < court < long


def test_un_texte_vide_ne_coute_rien():
    assert llm_client.estimer_tokens("") == 0
    assert llm_client.estimer_tokens(None) == 0


def test_l_estimation_reste_dans_l_ordre_de_grandeur_du_francais():
    """Environ quatre caracteres par token : on veut un ordre de grandeur
    honnete, pas une comptabilite exacte que seul le fournisseur connait."""
    texte = "a" * 4000
    assert 800 <= llm_client.estimer_tokens(texte) <= 1200


# --- Troncature de l'entree -------------------------------------------------

def test_un_texte_court_n_est_pas_touche():
    texte = "Nettoyage des locaux communaux"
    assert llm_client.tronquer(texte, 1000) == texte


def test_un_texte_trop_long_est_coupe():
    texte = "mot " * 5000
    coupe = llm_client.tronquer(texte, 100)
    assert len(coupe) < len(texte)
    assert llm_client.estimer_tokens(coupe) <= 100


def test_la_troncature_signale_qu_elle_a_coupe():
    """Un texte coupe en silence produit une reponse etrange sans qu'on
    comprenne pourquoi."""
    coupe = llm_client.tronquer("mot " * 5000, 50)
    assert coupe.rstrip().endswith(llm_client.MARQUE_TRONCATURE)


def test_un_plafond_absurde_ne_produit_pas_de_texte_vide():
    assert llm_client.tronquer("Nettoyage des locaux", 0) != ""
    assert llm_client.tronquer("Nettoyage des locaux", -5) != ""


# --- Le plafond arrive bien jusqu'a l'appel ---------------------------------

class _ReponseFactice:
    def __init__(self, charge):
        self._charge = charge

    def raise_for_status(self):
        pass

    def json(self):
        return self._charge


def _capturer(monkeypatch, charge):
    """Intercepte l'appel HTTP et rend la charge utile envoyee."""
    vu = {}

    def faux_post(url, json=None, headers=None, timeout=None):
        vu["url"] = url
        vu["payload"] = json
        return _ReponseFactice(charge)

    monkeypatch.setattr(llm_client.requests, "post", faux_post)
    return vu


def test_anthropic_recoit_le_plafond_demande(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "cle-de-test")
    monkeypatch.setenv("CHRUTH_LLM_MODEL", "modele-test")
    vu = _capturer(monkeypatch, {"content": [{"text": "ok"}]})
    llm_client.generer("prompt", provider="anthropic", max_tokens=256)
    assert vu["payload"]["max_tokens"] == 256


def test_gemini_recoit_le_plafond_demande(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "cle-de-test")
    vu = _capturer(monkeypatch, {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})
    llm_client.generer("prompt", provider="gemini", max_tokens=256)
    assert vu["payload"]["generationConfig"]["maxOutputTokens"] == 256


def test_mistral_recoit_le_plafond_demande(monkeypatch):
    """Mistral et Groq n'avaient aucune borne de sortie : une reponse longue
    partait sans limite."""
    monkeypatch.setenv("MISTRAL_API_KEY", "cle-de-test")
    vu = _capturer(monkeypatch, {"choices": [{"message": {"content": "ok"}}]})
    llm_client.generer("prompt", provider="mistral", max_tokens=256)
    assert vu["payload"]["max_tokens"] == 256


def test_ollama_recoit_aussi_le_plafond(monkeypatch):
    """Local et gratuit, mais c'est la longueur qui fait les trois minutes
    d'attente : le plafond y sert de frein au temps, pas au cout."""
    vu = _capturer(monkeypatch, {"response": "ok"})
    llm_client.generer("prompt", provider="ollama", max_tokens=256)
    assert vu["payload"]["options"]["num_predict"] == 256


def test_le_prompt_trop_long_est_tronque_avant_l_envoi(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "cle-de-test")
    monkeypatch.setenv("CHRUTH_LLM_MODEL", "modele-test")
    vu = _capturer(monkeypatch, {"content": [{"text": "ok"}]})
    llm_client.generer("mot " * 20000, provider="anthropic", max_tokens_entree=200)
    envoye = vu["payload"]["messages"][0]["content"]
    assert llm_client.estimer_tokens(envoye) <= 200


def test_sans_plafond_explicite_la_valeur_par_defaut_s_applique(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "cle-de-test")
    monkeypatch.setenv("CHRUTH_LLM_MODEL", "modele-test")
    vu = _capturer(monkeypatch, {"content": [{"text": "ok"}]})
    llm_client.generer("prompt", provider="anthropic")
    assert vu["payload"]["max_tokens"] == llm_client.MAX_TOKENS_DEFAUT


# --- Estimation par appel d'offres ------------------------------------------

def _ao(**over):
    ao = {"objet": "Nettoyage des locaux communaux", "acheteur": "Mairie de X",
          "ville": "Paris", "date_limite": "2026-09-01", "secteur": "Ecole",
          "categorie": "Batiments", "budget_annuel_eur": 50000}
    ao.update(over)
    return ao


def test_le_cout_d_un_ao_est_chiffre_avant_l_appel():
    import ao_messages
    cout = ao_messages.cout_estime(_ao(), fiche="")
    assert cout["entree"] > 0
    assert cout["sortie_max"] == llm_client.MAX_TOKENS_DEFAUT
    assert cout["total_max"] == cout["entree"] + cout["sortie_max"]


def test_un_ao_plus_bavard_coute_plus_cher():
    import ao_messages
    court = ao_messages.cout_estime(_ao(), fiche="")["entree"]
    long = ao_messages.cout_estime(_ao(objet="Nettoyage " * 300), fiche="")["entree"]
    assert long > court


def test_la_fiche_chruth_entre_dans_le_cout():
    """Elle est recopiee dans le prompt a chaque message : une fiche a rallonge
    se paie a chaque AO, pas une fois."""
    import ao_messages
    sans = ao_messages.cout_estime(_ao(), fiche="")["entree"]
    avec = ao_messages.cout_estime(_ao(), fiche="Zone : IDF. " * 200)["entree"]
    assert avec > sans


def test_le_plafond_choisi_se_reflete_dans_le_cout():
    import ao_messages
    cout = ao_messages.cout_estime(_ao(), fiche="", max_tokens=256)
    assert cout["sortie_max"] == 256
