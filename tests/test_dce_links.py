from ao_dce import extract_dce_links


def test_prefers_direct_pdf():
    donnees = {"a": {"url": "https://profil.example/dce"}, "b": "voir https://serveur.fr/dce.pdf"}
    r = extract_dce_links(donnees)
    assert r["url_dce"] == "https://serveur.fr/dce.pdf"


def test_prefers_known_profil_over_random():
    donnees = {"x": "https://random.example/page", "y": "https://www.marches-publics.info/annonce/123"}
    r = extract_dce_links(donnees)
    assert "marches-publics.info" in r["url_dce"]
    assert r["url_profil_acheteur"] == r["url_dce"]


def test_excludes_boamp():
    donnees = {"u": "https://www.boamp.fr/avis/123"}
    r = extract_dce_links(donnees)
    assert r["url_dce"] == ""


def test_accepts_json_string():
    r = extract_dce_links('{"k": "https://serveur.fr/doc.zip"}')
    assert r["url_dce"] == "https://serveur.fr/doc.zip"


def test_empty():
    assert extract_dce_links(None) == {"url_dce": "", "url_profil_acheteur": ""}
