"""Veille apprentissage : câblage dans le veilleur (mémoire + élagage)."""
import json
from datetime import datetime, timezone
from pathlib import Path

import ao_maximilien_veille
import ao_pertinence
import veille_etat
from ao_pertinence import Verdict


def _ecrire_etat(chemin, etat):
    chemin.write_text(json.dumps(etat, ensure_ascii=False), encoding="utf-8")


def test_veiller_elague_les_rejets_expires(tmp_path, monkeypatch):
    chemin = tmp_path / "veille.json"
    etat = veille_etat._vide()
    veille_etat.ajouter(etat, {"id_ao": "OLD", "objet": "Vieux", "date_limite": "2020-01-01"},
                        Verdict("REJETE", "listes", "m", terme="t"))
    _ecrire_etat(chemin, etat)

    monkeypatch.setattr(ao_maximilien_veille, "collecter", lambda: [])
    ao_maximilien_veille.veiller(etat_path=chemin, envoyer=False)

    releve = json.loads(chemin.read_text(encoding="utf-8"))
    assert "OLD" not in releve["aos"]


def test_veiller_nourrit_le_tri_avec_la_memoire(tmp_path, monkeypatch):
    chemin = tmp_path / "veille.json"
    etat = veille_etat._vide()
    etat["corrections_memoire"] = [
        {"objet": "Marche corrige", "verdict": "REJETE", "terme": "nettoyage", "date": ""}]
    _ecrire_etat(chemin, etat)

    captees = {}

    def faux_trier(objet, detail="", guide="", client=None, corrections=None):
        captees["corrections"] = corrections
        return Verdict("REJETE", "listes", "m", terme="t")

    monkeypatch.setattr(ao_pertinence, "trier", faux_trier)
    monkeypatch.setattr(ao_maximilien_veille, "collecter",
                        lambda: [{"id_ao": "N1", "objet": "Nouveau marche"}])
    ao_maximilien_veille.veiller(etat_path=chemin, envoyer=False)

    assert captees["corrections"] == [
        {"objet": "Marche corrige", "verdict": "REJETE", "terme": "nettoyage", "date": ""}]
