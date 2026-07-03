"""Helpers pour generer les notebooks-interface CHRUTH.

Les builders qui utilisent ce module produisent des notebooks qui IMPORTENT ou
LANCENT les modules .py : ils ne les remplacent jamais et n'utilisent pas
%%writefile (piege de revert connu).
"""
from __future__ import annotations

import json
from pathlib import Path


def md(text: str, cell_id: str) -> dict:
    """Cellule markdown (source decoupee en lignes)."""
    return {
        "cell_type": "markdown",
        "id": cell_id,
        "metadata": {},
        "source": text.splitlines(keepends=True),
    }


def code(text: str, cell_id: str) -> dict:
    """Cellule code non executee."""
    return {
        "cell_type": "code",
        "id": cell_id,
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


def save_notebook(cells: list[dict], path: str | Path) -> Path:
    """Enveloppe les cellules dans un notebook nbformat 4 et l'ecrit ; renvoie le chemin."""
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    p = Path(path)
    p.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    return p
