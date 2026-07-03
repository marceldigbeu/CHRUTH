"""Tests des builders de notebooks-compagnons (outils/build_notebook_*.py).

Verifie : JSON nbformat 4 valide, cellules cles presentes, invariant anti-revert
(jamais de %%writefile), + smokes headless sans reseau de la logique des cellules.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "outils"))

import nb_build  # noqa: E402
import build_notebook_pipeline_unique as bpu  # noqa: E402
import build_notebook_alertes as bal  # noqa: E402
import build_notebook_moteur_ia as bmi  # noqa: E402
import build_notebook_messages_prospects as bmp  # noqa: E402


def _charge(p) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _sources(nb: dict) -> str:
    return "\n".join("".join(c["source"]) for c in nb["cells"])


# --- nb_build --------------------------------------------------------------

def test_nb_build_save_et_types(tmp_path):
    cells = [nb_build.md("# Titre", "m"), nb_build.code("print(1)", "c")]
    p = nb_build.save_notebook(cells, tmp_path / "x.ipynb")
    nb = _charge(p)
    assert nb["nbformat"] == 4
    assert nb["cells"][0]["cell_type"] == "markdown"
    assert nb["cells"][1]["cell_type"] == "code"
    assert nb["cells"][1]["execution_count"] is None
    assert nb["cells"][1]["outputs"] == []


# --- les 4 builders --------------------------------------------------------

_BUILDERS = [
    (bpu, "pipeline", ["CHRUTH_PIPELINE_UNIQUE.py", "subprocess"]),
    (bal, "alertes", ["construire_email", "ENVOYER"]),
    (bmi, "moteur", ["moteur_auto", "generer"]),
    (bmp, "prospects", ["generer_templates", "rendre"]),
]


def test_builders_produisent_un_notebook_valide(tmp_path):
    for mod, nom, mots in _BUILDERS:
        p = mod.build(out_path=tmp_path / f"{nom}.ipynb")
        nb = _charge(p)
        assert nb["nbformat"] == 4, nom
        assert nb["cells"], nom
        src = _sources(nb)
        assert "%%writefile" not in src, nom  # invariant anti-revert
        for m in mots:
            assert m in src, (nom, m)


# --- smokes headless (aucun reseau) ----------------------------------------

def test_smoke_alertes_construire_email():
    import ao_alertes
    rec = {"id_ao": "T1", "objet": "Nettoyage ecole", "acheteur": "Mairie", "secteur": "Mairie",
           "categorie": "Batiments", "ville": "Paris", "date_publication": "2026-06-14",
           "date_limite": "2099-01-01", "budget_annuel_eur": "40000", "budget_estime_eur": "40000",
           "url_dce": "", "url_avis": "", "priorite": "CHAUD", "score_chruth": "70"}
    sujet, html, texte = ao_alertes.construire_email([rec], datetime(2026, 6, 14, 9, 0))
    assert sujet and html and texte


def test_smoke_moteur_auto_offline(monkeypatch):
    import llm_client
    for k in ("ANTHROPIC_API_KEY", "MISTRAL_API_KEY", "GROQ_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv("CHRUTH_LLM_PROVIDER", raising=False)
    monkeypatch.setattr(llm_client, "llm_disponible", lambda p=None: False)
    assert llm_client.moteur_auto() is None


def test_smoke_generer_templates_repli(tmp_path):
    import prospect_messages as pm

    class _NoLLM:
        def llm_disponible(self):
            return False

        def generer(self, *a, **k):
            raise RuntimeError("offline")

    templates = pm.generer_templates([("PRIV_BUREAU", "CHAUDE")], refresh=True,
                                     cache_path=tmp_path / "c.json", client=_NoLLM())
    tpl = templates["PRIV_BUREAU|CHAUDE"]
    assert tpl["email"] and tpl["script"]
    rendu = pm.rendre(tpl["email"], {"denomination": "SOCIETE X",
                                     "libelle_commune": "Paris", "effectif_label": "10 a 19"})
    assert "SOCIETE X" in rendu
