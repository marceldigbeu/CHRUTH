"""La date de publication traverse l'etat, l'email et le classement du fil."""
import json
from pathlib import Path

import ao_maximilien_veille as mv
import veille_etat as ve
from ao_pertinence import PERTINENT, Verdict
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app_veille.py")


def _ao(id_ao="MX-1", objet="Nettoyage des locaux", publie="2026-07-20"):
    return {"id_ao": id_ao, "objet": objet, "acheteur": "Mairie", "ville": "STAINS",
            "departement": "93", "date_limite": "2026-09-28", "procedure": "MAPA",
            "url": "https://marches.maximilien.fr/consultation/1", "score": "65",
            "priorite": "CHAUD", "date_publication": publie}


def test_l_etat_conserve_la_date_de_publication(tmp_path):
    etat = ve.charger(tmp_path / "veille.json")
    ve.ajouter(etat, _ao(), Verdict(PERTINENT, "listes", "ok"), None)
    ve.enregistrer(etat, tmp_path / "veille.json")

    relu = ve.charger(tmp_path / "veille.json")
    assert relu["aos"]["MX-1"]["date_publication"] == "2026-07-20"


def test_l_email_annonce_la_date_de_publication():
    _, html, texte = mv.construire_email_ao(_ao(), Verdict(PERTINENT, "listes", "ok"))
    assert "2026-07-20" in html
    assert "2026-07-20" in texte


def test_le_fil_classe_du_plus_recemment_publie_au_plus_ancien(tmp_path, monkeypatch):
    chemin = tmp_path / "veille.json"
    monkeypatch.setenv("CHRUTH_VEILLE_SOURCE", "local")
    monkeypatch.setenv("CHRUTH_VEILLE_ETAT", str(chemin))
    monkeypatch.delenv("CHRUTH_VEILLE_GUIDE", raising=False)

    etat = ve.charger(chemin)
    # Vus dans le desordre : l'ancien AO est entre en base en dernier.
    ve.ajouter(etat, _ao("MX-recent", "Nettoyage recent", "2026-07-22"),
               Verdict(PERTINENT, "listes", "ok"), None)
    ve.ajouter(etat, _ao("MX-ancien", "Nettoyage ancien", "2026-05-02"),
               Verdict(PERTINENT, "listes", "ok"), None)
    etat["aos"]["MX-ancien"]["vu_le"] = "2026-07-23T23:00:00Z"
    etat["aos"]["MX-recent"]["vu_le"] = "2026-07-23T01:00:00Z"
    chemin.write_text(json.dumps(etat, ensure_ascii=False), encoding="utf-8")

    at = AppTest.from_file(APP, default_timeout=60)
    at.run()

    textes = " ".join(m.value for m in at.markdown)
    assert textes.index("Nettoyage recent") < textes.index("Nettoyage ancien")


def test_le_fil_affiche_la_date_de_publication(tmp_path, monkeypatch):
    chemin = tmp_path / "veille.json"
    monkeypatch.setenv("CHRUTH_VEILLE_SOURCE", "local")
    monkeypatch.setenv("CHRUTH_VEILLE_ETAT", str(chemin))
    monkeypatch.delenv("CHRUTH_VEILLE_GUIDE", raising=False)

    etat = ve.charger(chemin)
    ve.ajouter(etat, _ao(publie="2026-07-20"), Verdict(PERTINENT, "listes", "ok"), None)
    chemin.write_text(json.dumps(etat, ensure_ascii=False), encoding="utf-8")

    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert "2026-07-20" in " ".join(m.value for m in at.markdown)


def test_un_ao_sans_date_de_publication_reste_visible(tmp_path, monkeypatch):
    """Les AO deja en etat n'ont pas ce champ : ils ne doivent pas disparaitre."""
    chemin = tmp_path / "veille.json"
    monkeypatch.setenv("CHRUTH_VEILLE_SOURCE", "local")
    monkeypatch.setenv("CHRUTH_VEILLE_ETAT", str(chemin))
    monkeypatch.delenv("CHRUTH_VEILLE_GUIDE", raising=False)

    etat = ve.charger(chemin)
    ve.ajouter(etat, _ao("MX-daté", "Nettoyage date", "2026-07-22"),
               Verdict(PERTINENT, "listes", "ok"), None)
    ve.ajouter(etat, _ao("MX-sans", "Nettoyage sans date"),
               Verdict(PERTINENT, "listes", "ok"), None)
    del etat["aos"]["MX-sans"]["date_publication"]
    chemin.write_text(json.dumps(etat, ensure_ascii=False), encoding="utf-8")

    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception
    assert "Nettoyage sans date" in " ".join(m.value for m in at.markdown)
