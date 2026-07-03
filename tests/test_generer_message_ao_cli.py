import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "outils"))
import generer_message_ao as cli  # noqa: E402


def test_formater_contient_sections_et_contexte():
    rec = {"objet": "Nettoyage locaux", "acheteur": "Mairie X", "ville": "Paris",
           "date_limite": "2099-01-01"}
    msg = {"email": "Bonjour Mairie X", "script": "Appel Mairie X", "source": "ia"}
    txt = cli.formater(rec, msg)
    assert "OBJET : Nettoyage locaux" in txt
    assert "ACHETEUR : Mairie X" in txt
    assert "===== EMAIL =====" in txt and "Bonjour Mairie X" in txt
    assert "===== SCRIPT D'APPEL =====" in txt and "Appel Mairie X" in txt
    assert "SOURCE : ia" in txt
