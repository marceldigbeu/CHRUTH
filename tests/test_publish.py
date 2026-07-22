import ao_publish


def test_dossier_non_configure_ignore(tmp_path, monkeypatch):
    monkeypatch.delenv("CHRUTH_DOSSIER_PARTAGE", raising=False)
    monkeypatch.setattr(ao_publish, "DOSSIER_PARTAGE", "")
    assert ao_publish.publier(dest=None) == []


def test_copie_vers_dossier(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    fichier = src / "AO_CHRUTH.xlsm"
    fichier.write_bytes(b"contenu")
    dest = tmp_path / "partage"
    copies = ao_publish.publier(fichiers=[fichier], dest=dest)
    assert copies == [dest / "AO_CHRUTH.xlsm"]
    assert (dest / "AO_CHRUTH.xlsm").read_bytes() == b"contenu"


def test_dest_via_env(tmp_path, monkeypatch):
    fichier = tmp_path / "AO_CHRUTH.xlsm"
    fichier.write_bytes(b"x")
    dest = tmp_path / "via_env"
    monkeypatch.setenv("CHRUTH_DOSSIER_PARTAGE", str(dest))
    copies = ao_publish.publier(fichiers=[fichier])
    assert (dest / "AO_CHRUTH.xlsm").exists()
    assert copies


def test_fichier_absent_ignore(tmp_path):
    dest = tmp_path / "out"
    copies = ao_publish.publier(fichiers=[tmp_path / "introuvable.xlsx"], dest=dest)
    assert copies == []
