"""La copie de demo ne doit emporter aucun secret — c'est sa seule raison d'etre."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "outils"))

import preparer_dossier_demo as pdd  # noqa: E402


def _dossier_source(tmp_path: Path) -> Path:
    src = tmp_path / "livraison"
    (src / "etat").mkdir(parents=True)
    (src / "logs").mkdir()
    (src / "data").mkdir()
    (src / "__pycache__").mkdir()

    (src / ".env").write_text("ANTHROPIC_API_KEY=sk-secret\n", encoding="utf-8")
    (src / "alertes_secrets.json").write_text(
        json.dumps({"smtp_user": "a@b.fr", "smtp_password": "motdepasse"}), encoding="utf-8")
    (src / "destinataires.txt").write_text("client@exemple.fr\n", encoding="utf-8")
    (src / "logs" / "veille.log").write_text("envoi a client@exemple.fr", encoding="utf-8")
    (src / "__pycache__" / "x.pyc").write_bytes(b"\x00")

    (src / "CHRUTH_APP.py").write_text("import streamlit\n", encoding="utf-8")
    (src / "data" / "ao.sqlite").write_bytes(b"SQLite")
    (src / "reglages_cache.json").write_text(
        json.dumps({"collecte": True, "destinataires": ["client@exemple.fr"],
                    "expediteur": "moi@gmail.com"}), encoding="utf-8")
    (src / "etat" / "veille.json").write_text(
        json.dumps({"aos": {"1": {"objet": "Nettoyage"}},
                    "reglages": {"destinataires": ["client@exemple.fr"],
                                 "expediteur": "moi@gmail.com"}}), encoding="utf-8")
    return src


def test_les_fichiers_secrets_ne_sont_pas_copies(tmp_path):
    src = _dossier_source(tmp_path)
    r = pdd.preparer(src, tmp_path / "demo")
    cible = r["cible"]

    assert not (cible / ".env").exists()
    assert not (cible / "alertes_secrets.json").exists()
    assert not (cible / "destinataires.txt").exists()
    assert not (cible / "logs").exists()
    assert not (cible / "__pycache__").exists()
    assert r["restants"] == []


def test_ce_qui_sert_a_la_demo_est_conserve(tmp_path):
    src = _dossier_source(tmp_path)
    cible = pdd.preparer(src, tmp_path / "demo")["cible"]

    assert (cible / "CHRUTH_APP.py").exists()
    assert (cible / "data" / "ao.sqlite").exists()
    etat = json.loads((cible / "etat" / "veille.json").read_text(encoding="utf-8"))
    assert etat["aos"], "les AO sont la matiere de la demo, ils doivent rester"


def test_les_adresses_email_sont_expurgees_des_json_conserves(tmp_path):
    src = _dossier_source(tmp_path)
    cible = pdd.preparer(src, tmp_path / "demo")["cible"]

    reglages = json.loads((cible / "reglages_cache.json").read_text(encoding="utf-8"))
    assert reglages["destinataires"] == []
    assert reglages["expediteur"] == ""
    assert reglages["collecte"] is True, "seules les adresses partent"

    etat = json.loads((cible / "etat" / "veille.json").read_text(encoding="utf-8"))
    assert etat["reglages"]["destinataires"] == []
    assert etat["reglages"]["expediteur"] == ""


def test_une_cible_existante_est_remplacee(tmp_path):
    src = _dossier_source(tmp_path)
    cible = tmp_path / "demo"
    cible.mkdir()
    (cible / "vieux_fichier.txt").write_text("ancienne copie", encoding="utf-8")

    pdd.preparer(src, cible)

    assert not (cible / "vieux_fichier.txt").exists(), \
        "une copie perimee laisserait croire que le contenu est a jour"


def test_les_sauvegardes_horodatees_ne_sont_pas_copiees(tmp_path):
    """Une sauvegarde d'etat porte les reglages d'avant, adresses comprises :
    l'exclure est le seul moyen de ne pas re-livrer ce qu'on vient d'expurger."""
    src = _dossier_source(tmp_path)
    (src / "etat" / "veille.json.bak_20260728").write_text(
        json.dumps({"reglages": {"destinataires": ["client@exemple.fr"]}}), encoding="utf-8")
    (src / "base.sqlite.backup").write_bytes(b"vieux")

    cible = pdd.preparer(src, tmp_path / "demo")["cible"]

    assert not (cible / "etat" / "veille.json.bak_20260728").exists()
    assert not (cible / "base.sqlite.backup").exists()


def test_les_adresses_du_poste_sont_apprises_des_fichiers_exclus(tmp_path):
    src = _dossier_source(tmp_path)
    adresses = pdd.adresses_du_poste(src)
    assert "client@exemple.fr" in adresses
    assert "moi@gmail.com" in adresses


def test_une_adresse_recopiee_ailleurs_est_masquee(tmp_path):
    """Le cas reel : un export HTML et une note de documentation recopiaient les
    destinataires. Ni l'un ni l'autre n'est un fichier de secrets."""
    src = _dossier_source(tmp_path)
    (src / "EXPORT.html").write_text(
        '<script>destinataires:["client@exemple.fr"]</script>', encoding="utf-8")
    (src / "GUIDE.md").write_text("Aujourd'hui : `client@exemple.fr`.", encoding="utf-8")

    cible = pdd.preparer(src, tmp_path / "demo")["cible"]

    for nom in ("EXPORT.html", "GUIDE.md"):
        contenu = (cible / nom).read_text(encoding="utf-8")
        assert "client@exemple.fr" not in contenu
        assert pdd.REMPLACEMENT in contenu


def test_le_masquage_ne_touche_pas_au_reste_du_texte(tmp_path):
    src = _dossier_source(tmp_path)
    (src / "GUIDE.md").write_text("# Titre\n\nEcrire a client@exemple.fr pour l'acces.",
                                  encoding="utf-8")
    cible = pdd.preparer(src, tmp_path / "demo")["cible"]
    contenu = (cible / "GUIDE.md").read_text(encoding="utf-8")
    assert contenu.startswith("# Titre")
    assert "pour l'acces." in contenu


def test_sans_adresse_configuree_rien_n_est_modifie(tmp_path):
    src = tmp_path / "vierge"
    src.mkdir()
    (src / "GUIDE.md").write_text("Aucune adresse ici.", encoding="utf-8")
    cible = pdd.preparer(src, tmp_path / "demo")["cible"]
    assert (cible / "GUIDE.md").read_text(encoding="utf-8") == "Aucune adresse ici."
