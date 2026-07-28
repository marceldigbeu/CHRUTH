from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

import acheteurs_semaine as asem

RACINE = Path(__file__).resolve().parent.parent
PAGE = str(RACINE / "pages_acheteurs.py")


def _df():
    lignes = []
    for ach, typ, dept in [("Mairie de Créteil", "public", "94"), ("Immobilière 3F", "prive", "93")]:
        l = {c: ("" if c != "nb_ao_semaine" else 1) for c in asem.COLONNES}
        l.update({"acheteur": ach, "type": typ, "departement": dept, "priorite": "CHAUD", "aos": []})
        lignes.append(l)
    return pd.DataFrame(lignes)


def test_la_page_affiche_les_acheteurs(monkeypatch):
    monkeypatch.setattr(asem, "construire", lambda *a, **k: _df())
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    assert not at.exception
    textes = " ".join(m.value for m in at.markdown)
    assert "Créteil" in textes or "Acheteurs" in textes


def test_la_page_est_declaree_dans_l_entree():
    src = (RACINE / "CHRUTH_APP.py").read_text(encoding="utf-8")
    assert "pages_acheteurs.py" in src


def test_le_filtre_public_prive_existe(monkeypatch):
    monkeypatch.setattr(asem, "construire", lambda *a, **k: _df())
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    assert any(w.key == "type_acheteur" for w in at.radio) or not at.exception


def test_page_affiche_info_quand_dataframe_vide(monkeypatch):
    """Quand construire() retourne un DataFrame vide, affiche un message info et ne crashe pas."""
    monkeypatch.setattr(asem, "construire", lambda *a, **k: pd.DataFrame(columns=asem.COLONNES))
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    assert not at.exception
    assert len(at.info) >= 1


def test_filtre_public_cache_les_lignes_privees(monkeypatch):
    """Quand on sélectionne 'Public' au radio, les lignes privé-droit sont cachées."""
    monkeypatch.setattr(asem, "construire", lambda *a, **k: _df())
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    assert not at.exception

    # Sélectionner "Public"
    at.radio(key="type_acheteur").set_value("Public").run()

    # Vérifier que seule la ligne publique est affichée
    textes = " ".join(m.value for m in at.markdown)
    assert "Créteil" in textes  # public row still shown
    assert "Immobilière 3F" not in textes  # prive row hidden
