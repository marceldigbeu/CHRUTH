"""Plateforme de veille Streamlit, testee sans navigateur (AppTest)."""
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app_veille.py")


def _etat(aos: dict, guide: str = "") -> dict:
    return {"version": 1, "maj_le": "2026-07-23T08:00:00Z", "guide_messages": guide,
            "aos": aos}


def _ao(objet="Nettoyage des locaux du MAC VAL", verdict="PERTINENT", vu="2026-07-23T08:00:00Z"):
    return {"objet": objet, "acheteur": "CD94", "ville": "CRETEIL", "departement": "94",
            "date_limite": "2026-09-28", "procedure": "MAPA", "score": "65",
            "priorite": "CHAUD", "url": "https://marches.maximilien.fr/consultation/1",
            "vu_le": vu, "notifie_le": None, "lu": False, "traitement": "nouveau",
            "correction_humaine": None,
            "tri": {"verdict": verdict, "etage": "listes", "motif": "mot-cle coeur"}}


@pytest.fixture
def etat_local(tmp_path, monkeypatch):
    chemin = tmp_path / "veille.json"
    monkeypatch.setenv("CHRUTH_VEILLE_SOURCE", "local")
    monkeypatch.setenv("CHRUTH_VEILLE_ETAT", str(chemin))
    monkeypatch.delenv("CHRUTH_VEILLE_GUIDE", raising=False)

    def ecrire(etat: dict) -> Path:
        chemin.write_text(json.dumps(etat, ensure_ascii=False, indent=2), encoding="utf-8")
        return chemin

    return ecrire


def _lancer() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    return at


def test_l_app_demarre_sur_un_etat_vide(etat_local):
    at = _lancer()
    assert not at.exception


def test_le_fil_affiche_un_bloc_par_ao(etat_local):
    etat_local(_etat({"MX-1": _ao(), "MX-2": _ao("Nettoyage des ecoles")}))
    at = _lancer()
    assert not at.exception
    textes = " ".join(m.value for m in at.markdown)
    assert "MAC VAL" in textes
    assert "Nettoyage des ecoles" in textes


def test_les_ao_rejetes_sont_masques_puis_affichables(etat_local):
    """Rejete ne veut pas dire invisible : c'est la que se corrige le tri."""
    etat_local(_etat({"MX-1": _ao(), "MX-2": _ao("Elagage des arbres", verdict="REJETE")}))

    at = _lancer()
    assert "Elagage" not in " ".join(m.value for m in at.markdown)

    at.checkbox(key="voir_rejetes").check().run()
    assert "Elagage" in " ".join(m.value for m in at.markdown)


def test_corriger_un_verdict_est_persiste(etat_local):
    chemin = etat_local(_etat({"MX-1": _ao()}))
    at = _lancer()
    at.button(key="ko_MX-1").click().run()

    assert not at.exception
    releve = json.loads(chemin.read_text(encoding="utf-8"))
    assert releve["aos"]["MX-1"]["correction_humaine"]["verdict"] == "REJETE"


def test_la_correction_survit_a_un_redemarrage_de_l_app(etat_local):
    etat_local(_etat({"MX-1": _ao("Elagage des arbres", verdict="REJETE")}))
    at = _lancer()
    at.checkbox(key="voir_rejetes").check().run()
    at.button(key="ok_MX-1").click().run()

    rouvert = _lancer()
    textes = " ".join(m.value for m in rouvert.markdown)
    assert "corrigé à la main" in textes
    assert "**PERTINENT**" in textes


def test_le_statut_de_traitement_est_persiste(etat_local):
    chemin = etat_local(_etat({"MX-1": _ao()}))
    at = _lancer()
    at.selectbox(key="trait_MX-1").select("a_traiter").run()

    releve = json.loads(chemin.read_text(encoding="utf-8"))
    assert releve["aos"]["MX-1"]["traitement"] == "a_traiter"


def test_le_guide_est_masque_par_defaut(etat_local):
    etat_local(_etat({"MX-1": _ao()}))
    at = _lancer()
    assert not any(ta.key == "guide" for ta in at.text_area)


def test_le_guide_est_editable_quand_il_est_active(etat_local, monkeypatch):
    chemin = etat_local(_etat({"MX-1": _ao()}))
    monkeypatch.setenv("CHRUTH_VEILLE_GUIDE", "1")

    at = _lancer()
    at.text_area(key="guide").input("CHRUTH nettoie des bureaux en IDF.").run()
    at.button(key="enregistrer_guide").click().run()

    releve = json.loads(chemin.read_text(encoding="utf-8"))
    assert releve["guide_messages"] == "CHRUTH nettoie des bureaux en IDF."


def test_le_filtre_de_priorite_restreint_le_fil(etat_local):
    chaud = _ao()
    froid = _ao("Nettoyage des abribus")
    froid["priorite"] = "FROID"
    etat_local(_etat({"MX-1": chaud, "MX-2": froid}))

    at = _lancer()
    at.multiselect(key="priorites").select("CHAUD").run()
    textes = " ".join(m.value for m in at.markdown)
    assert "MAC VAL" in textes
    assert "abribus" not in textes
