"""Genere CHRUTH_Moteur_IA.ipynb : interface pour diagnostiquer/tester le moteur LLM.

Le notebook ne remplace pas llm_client.py : il l'importe pour afficher le moteur
detecte (cle cloud / Ollama / repli) et tester un prompt.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nb_build import code, md, save_notebook  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "CHRUTH_Moteur_IA.ipynb"


def build(out_path: str | Path | None = None) -> Path:
    cells = [
        md(
            "# CHRUTH - Moteur IA\n\n"
            "Interface pour `llm_client.py`. Le moteur se règle **tout seul** :\n"
            "clé cloud dans `.env` (anthropic > mistral > groq, une seule suffit) → sinon\n"
            "Ollama local → sinon brouillon déterministe.\n\n"
            "Ce notebook affiche le moteur détecté et permet de tester un prompt.",
            "intro",
        ),
        md("## 1. Setup", "setup-md"),
        code(
            "import sys, pathlib, os\n"
            "sys.path.insert(0, str(pathlib.Path.cwd()))\n"
            "try:\n"
            "    from dotenv import load_dotenv; load_dotenv()\n"
            "except Exception:\n"
            "    pass\n"
            "import llm_client\n"
            "print('llm_client charge.')",
            "setup-code",
        ),
        md("## 2. Diagnostic du moteur", "diag-md"),
        code(
            "print('Moteur auto     :', llm_client.moteur_auto() or 'aucun -> repli deterministe')\n"
            "print('Fournisseur cloud:', llm_client.cloud_provider() or '(aucune cle cloud)')\n"
            "print('Ollama dispo    :', llm_client.llm_disponible('ollama'))\n"
            "cles = {'ANTHROPIC_API_KEY', 'MISTRAL_API_KEY', 'GROQ_API_KEY'}\n"
            "presentes = [k for k in cles if os.environ.get(k)]\n"
            "print('Cles cloud presentes :', presentes or '(aucune)')",
            "diag-code",
        ),
        md(
            "## 3. Tester un prompt\n\n"
            "Édite `SYSTEM` et `PROMPT`. Utilise le moteur détecté. Si aucun moteur "
            "(pas de clé, Ollama éteint), rien n'est appelé.",
            "test-md",
        ),
        code(
            "SYSTEM = 'Tu es un assistant concis. Reponds en francais.'\n"
            "PROMPT = 'Redige une phrase de presentation pour une societe de nettoyage en Ile-de-France.'\n"
            "\n"
            "provider = llm_client.moteur_auto()\n"
            "if provider is None:\n"
            "    print('Aucun moteur : colle une cle cloud dans .env ou lance Ollama.')\n"
            "else:\n"
            "    print('Moteur utilise :', provider)\n"
            "    print('-' * 60)\n"
            "    print(llm_client.generer(PROMPT, SYSTEM, provider=provider))",
            "test-code",
        ),
    ]
    return save_notebook(cells, out_path or OUT)


if __name__ == "__main__":
    print(build())
