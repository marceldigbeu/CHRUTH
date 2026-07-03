from ao_export_excel import vba_module_text


def test_macro_ao_refresh():
    src = vba_module_text()
    assert "refresh_runner.py ao" in src
    assert "ThisWorkbook.Close" in src
