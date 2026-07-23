import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "outils"))
import refresh_runner as rr


def test_resoudre_ao():
    fichier, cmd = rr.resoudre("ao", None)
    assert fichier.name == "AO_CHRUTH.xlsm"
    assert any("ao_weekly_update.py" in str(c) for c in cmd)


def test_resoudre_prospects_vite_et_complet():
    f1, c1 = rr.resoudre("prospects", "vite")
    f2, c2 = rr.resoudre("prospects", "complet")
    assert f1.name == "Base_Prospects_CHRUTH.xlsm"
    assert "--collect" not in c1
    assert "--collect" in c2 and "france" in c2


def test_attendre_deverrouillage_fichier_absent(tmp_path):
    assert rr.attendre_deverrouillage(tmp_path / "absent.xlsm", timeout=1) is True


def test_attendre_deverrouillage_timeout(tmp_path, monkeypatch):
    f = tmp_path / "verrou.xlsm"
    f.write_bytes(b"x")
    def toujours_verrouille(*a, **k):
        raise PermissionError("locked")
    monkeypatch.setattr("builtins.open", toujours_verrouille)
    assert rr.attendre_deverrouillage(f, timeout=1) is False
