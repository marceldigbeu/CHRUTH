import fitz  # PyMuPDF

import ao_dce
from ao_dce import extract_pdf_text, match_manual_pdf, try_download_direct


def test_match_manual_pdf(tmp_path):
    (tmp_path / "26-55964_dce.pdf").write_bytes(b"%PDF-1.4 test")
    (tmp_path / "99-00000.pdf").write_bytes(b"%PDF-1.4 autre")
    assert match_manual_pdf("26-55964", tmp_path).name == "26-55964_dce.pdf"
    assert match_manual_pdf("11-11111", tmp_path) is None


def test_extract_pdf_text_roundtrip(tmp_path):
    pdf = tmp_path / "doc.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "nettoyage estime a 250 000 EUR")
    doc.save(str(pdf)); doc.close()
    text = extract_pdf_text(pdf)
    assert "nettoyage" in text.lower()


def test_try_download_direct_rejects_non_pdf(tmp_path, monkeypatch):
    class FakeResp:
        status_code = 200
        headers = {"content-type": "text/html"}
        content = b"<html>captcha</html>"
        def raise_for_status(self): pass
    monkeypatch.setattr(ao_dce.requests, "get", lambda *a, **k: FakeResp())
    # URL non .pdf -> rejet immediat
    assert try_download_direct("https://profil.example/page", tmp_path) is None
    # URL .pdf mais reponse HTML -> rejet aussi
    assert try_download_direct("https://x.fr/d.pdf", tmp_path) is None


def test_try_download_direct_saves_pdf(tmp_path, monkeypatch):
    class FakeResp:
        status_code = 200
        headers = {"content-type": "application/pdf"}
        content = b"%PDF-1.4 fake body"
        def raise_for_status(self): pass
    monkeypatch.setattr(ao_dce.requests, "get", lambda *a, **k: FakeResp())
    path = try_download_direct("https://x.fr/dce.pdf", tmp_path, filename="26-1.pdf")
    assert path is not None and path.exists()
    assert path.read_bytes().startswith(b"%PDF")
