"""Le bouton de mise a jour : collecte locale ou declenchement du workflow.

Distinction vitale : quand l'app est branchee sur l'etat PARTAGE (source github),
elle ne doit JAMAIS collecter elle-meme. Elle marquerait les AO comme vus sans
qu'aucun email ne parte — le veilleur ne les proposerait plus jamais.
"""
import json
from pathlib import Path

import ao_maximilien_veille
import veille_depot
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app_veille.py")


def _etat_vide() -> dict:
    return {"version": 1, "maj_le": "", "guide_messages": "", "aos": {}}


def _ao(objet="Nettoyage des locaux du MAC VAL"):
    return {"objet": objet, "acheteur": "CD94", "ville": "CRETEIL", "departement": "94",
            "date_limite": "2026-09-28", "procedure": "MAPA", "score": "65",
            "priorite": "CHAUD", "url": "https://marches.maximilien.fr/consultation/1",
            "vu_le": "2026-07-23T09:00:00Z", "notifie_le": None, "lu": False,
            "traitement": "nouveau", "correction_humaine": None,
            "tri": {"verdict": "PERTINENT", "etage": "listes", "motif": "mot-cle coeur"}}


def _preparer_local(tmp_path, monkeypatch) -> Path:
    chemin = tmp_path / "veille.json"
    chemin.write_text(json.dumps(_etat_vide()), encoding="utf-8")
    monkeypatch.setenv("CHRUTH_VEILLE_SOURCE", "local")
    monkeypatch.setenv("CHRUTH_VEILLE_ETAT", str(chemin))
    monkeypatch.delenv("CHRUTH_VEILLE_GUIDE", raising=False)
    return chemin


def test_en_local_la_mise_a_jour_collecte_et_rafraichit_le_fil(tmp_path, monkeypatch):
    chemin = _preparer_local(tmp_path, monkeypatch)
    appels = []

    def fausse_veille(etat_path=None, envoyer=True, client=None):
        appels.append({"chemin": str(etat_path), "envoyer": envoyer})
        etat = _etat_vide()
        etat["aos"]["MX-1"] = _ao()
        Path(etat_path).write_text(json.dumps(etat), encoding="utf-8")
        return 0

    monkeypatch.setattr(ao_maximilien_veille, "veiller", fausse_veille)

    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert "MAC VAL" not in " ".join(m.value for m in at.markdown)

    at.button(key="maj").click().run()

    assert not at.exception
    assert len(appels) == 1
    assert appels[0]["chemin"] == str(chemin)
    assert appels[0]["envoyer"] is False  # l'app affiche, elle ne notifie pas
    assert "MAC VAL" in " ".join(m.value for m in at.markdown)


def test_en_mode_github_la_mise_a_jour_ne_collecte_jamais_en_local(monkeypatch):
    monkeypatch.setenv("CHRUTH_VEILLE_SOURCE", "github")
    monkeypatch.setenv("CHRUTH_GITHUB_REPO", "<votre-compte>/CHRUTH")
    monkeypatch.setenv("CHRUTH_GITHUB_TOKEN", "jeton-de-test")
    monkeypatch.delenv("CHRUTH_VEILLE_GUIDE", raising=False)
    monkeypatch.setattr(veille_depot, "lire", lambda: (_etat_vide(), "sha1"))

    collectes = []
    monkeypatch.setattr(ao_maximilien_veille, "veiller",
                        lambda **kw: collectes.append(kw))
    dispatches = []
    monkeypatch.setattr(veille_depot, "declencher_veille",
                        lambda: dispatches.append(1) or True)

    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.button(key="maj").click().run()

    assert not at.exception
    assert dispatches == [1]
    assert collectes == []


def test_un_echec_de_mise_a_jour_est_affiche_sans_casser_l_app(tmp_path, monkeypatch):
    _preparer_local(tmp_path, monkeypatch)

    def veille_en_panne(**kw):
        raise RuntimeError("site indisponible")

    monkeypatch.setattr(ao_maximilien_veille, "veiller", veille_en_panne)

    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.button(key="maj").click().run()

    assert not at.exception
    assert any("site indisponible" in e.value for e in at.error)


def test_le_bouton_est_annonce_selon_la_source(tmp_path, monkeypatch):
    _preparer_local(tmp_path, monkeypatch)
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert at.button(key="maj").label == "Mettre à jour maintenant"
