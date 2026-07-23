import zipfile

import openpyxl
import pytest

import ao_config

TEMPLATE = ao_config.AO_TEMPLATE_XLSM


def _zip_names(path):
    with zipfile.ZipFile(path) as z:
        return z.namelist()


@pytest.mark.skipif(not TEMPLATE.exists(), reason="gabarit non encore cree (Task 3)")
def test_openpyxl_roundtrip_preserves_vba_and_button(tmp_path):
    """GATE: openpyxl keep_vba doit preserver la macro ET le bouton Forms.

    Verifie en 2026-06-08 via COM : le bouton 'Mettre a jour les AO'
    (OnAction=Update_AO_CHRUTH) et le module VBA survivent au round-trip.
    drawing1.xml (DrawingML) est droppe par openpyxl mais c'est inoffensif :
    le bouton Forms s'appuie sur vmlDrawing + ctrlProps, qui survivent.
    """
    out = tmp_path / "roundtrip.xlsm"
    wb = openpyxl.load_workbook(TEMPLATE, keep_vba=True)
    ws = wb["Pilotage"]
    ws["A1"] = "test"
    wb.save(out)

    names = _zip_names(out)
    assert any("vbaProject.bin" in n for n in names), "macro VBA perdue au round-trip"
    has_button_parts = any("vmldrawing" in n.lower() for n in names) and any(
        "ctrlprop" in n.lower() for n in names
    )
    assert has_button_parts, "BOUTON perdu au round-trip openpyxl -> GATE FAIL"
