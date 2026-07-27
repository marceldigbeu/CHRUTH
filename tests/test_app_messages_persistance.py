"""Le message généré doit survivre à une interaction.

Streamlit relance le script à chaque interaction. Quand le résultat n'est affiché
que dans le bloc `if st.button(...)`, le bouton repasse à False au rerun suivant
et le message disparaît sous les yeux de l'utilisateur dès qu'il édite le texte.
On vérifie ici qu'il persiste.
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

RACINE = Path(__file__).resolve().parent.parent
PAGE = str(RACINE / "app_messages.py")


@pytest.fixture
def page_prete(monkeypatch, tmp_path):
    """App lançable hors réseau : base AO vide, génération prospect déterministe.

    On remplace `generer_templates` pour ne pas appeler de LLM ni écrire le cache
    du dépôt (`output/segments_messages.json`).
    """
    monkeypatch.setenv("CHRUTH_AO_DB", str(tmp_path / "ao.sqlite"))
    import prospect_messages as pm

    def _templates(segments, **_):
        return {
            f"{cat}|{prio}": {
                "email": "Bonjour {denomination}", "script": "Script pour {ville}",
                "source": "defaut", "categorie": cat, "priorite": prio,
            }
            for cat, prio in segments
        }

    monkeypatch.setattr(pm, "generer_templates", _templates)


def test_le_message_prospect_survit_a_un_rerun(page_prete):
    """Deux garanties, dans l'ordre où elles importent.

    1. Le message s'affiche juste après la génération (chemin de rendu).
    2. Il est rangé sous une clé de *données* qui survit à un rerun — l'ancien code
       n'écrivait rien en session, donc rien ne persistait quand Streamlit relançait
       le script (à la moindre édition d'un champ). C'est là qu'était le bug.
    """
    at = AppTest.from_file(PAGE, default_timeout=90)
    at.run()
    assert not at.exception
    assert "msg_prospect" not in at.session_state, "rien de mémorisé avant génération"

    at.button(key="gen_prospect").click().run()
    assert not at.exception
    apparus = [t.value for t in at.text_area]
    assert any("Bonjour" in v for v in apparus), "le message n'a pas été affiché"
    assert "msg_prospect" in at.session_state, "le message doit être mémorisé"

    # Un rerun quelconque (ce que provoque toute interaction en vrai Streamlit) ne
    # doit pas effacer le message mémorisé.
    at.run()
    assert not at.exception
    assert "msg_prospect" in at.session_state, "le message a disparu de la session au rerun"
    assert at.session_state["msg_prospect"].get("email", "").startswith("Bonjour")
