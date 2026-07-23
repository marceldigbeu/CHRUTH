"""Bouton d'activation/desactivation des notifications dans l'app."""
import json
from pathlib import Path

import veille_etat as ve
from ao_pertinence import PERTINENT, Verdict
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app_veille.py")


def _preparer(tmp_path, monkeypatch, notifications=None) -> Path:
    chemin = tmp_path / "veille.json"
    monkeypatch.setenv("CHRUTH_VEILLE_SOURCE", "local")
    monkeypatch.setenv("CHRUTH_VEILLE_ETAT", str(chemin))
    monkeypatch.delenv("CHRUTH_VEILLE_GUIDE", raising=False)

    etat = ve.charger(chemin)
    ve.ajouter(etat, {"id_ao": "MX-1", "objet": "Nettoyage des locaux",
                      "date_publication": "2026-07-20"},
               Verdict(PERTINENT, "listes", "ok"), None)
    if notifications is not None:
        ve.definir_notifications(etat, notifications)
    chemin.write_text(json.dumps(etat, ensure_ascii=False), encoding="utf-8")
    return chemin


def _lancer() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    return at


def test_le_bouton_propose_de_couper_quand_les_notifications_sont_actives(tmp_path, monkeypatch):
    _preparer(tmp_path, monkeypatch)
    at = _lancer()
    assert at.button(key="notifs").label == "Désactiver les notifications"


def _relu(chemin: Path) -> bool:
    """Passe par l'accesseur, jamais par la cle brute.

    Ces tests affirmaient `etat["notifications"]`, donc un emplacement. C'est ce
    qui a laissé deux interrupteurs diverger sans que rien ne le signale : la page
    Reglages ecrivait ailleurs et ces tests restaient verts.
    """
    return ve.notifications_actives(json.loads(chemin.read_text(encoding="utf-8")))


def test_un_clic_coupe_les_notifications_et_le_persiste(tmp_path, monkeypatch):
    chemin = _preparer(tmp_path, monkeypatch)
    at = _lancer()
    at.button(key="notifs").click().run()

    assert not at.exception
    assert _relu(chemin) is False


def test_l_etat_coupe_est_annonce_et_reactivable(tmp_path, monkeypatch):
    chemin = _preparer(tmp_path, monkeypatch, notifications=False)
    at = _lancer()

    assert at.button(key="notifs").label == "Activer les notifications"
    assert any("suspendues" in m.value.lower() for m in at.warning)

    at.button(key="notifs").click().run()
    assert _relu(chemin) is True


def test_couper_les_notifications_n_arrete_pas_le_fil(tmp_path, monkeypatch):
    """La veille continue de montrer les AO : seul l'email est suspendu."""
    _preparer(tmp_path, monkeypatch, notifications=False)
    at = _lancer()
    assert "Nettoyage des locaux" in " ".join(m.value for m in at.markdown)
