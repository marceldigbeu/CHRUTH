"""Le miroir HTML doit s'afficher, pas seulement peser le bon nombre d'octets.

Deux fausses verifications ont precede ce test. La premiere mesurait le DOM
rendu par un navigateur, qui reste volumineux meme quand le script echoue :
il contient le code source. La seconde cherchait le contenu apres la balise
`</script>`, alors qu'il est ecrit dans `<main>`, situe avant elle.

La seule verification qui vaut est fonctionnelle : charger le script et
regarder ce que chaque ecran produit. C'est ce que fait `verifier_miroir.js`,
que ce test appelle.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
MIROIR = RACINE / "CHRUTH_PLATEFORME.html"
VERIFICATEUR = RACINE / "outils" / "verifier_miroir.js"


def _node() -> str | None:
    return shutil.which("node")


@pytest.mark.skipif(_node() is None, reason="Node.js absent : verification impossible")
def test_tous_les_ecrans_du_miroir_s_affichent():
    resultat = subprocess.run(
        [_node(), str(VERIFICATEUR), str(MIROIR)],
        capture_output=True, text=True, timeout=120)
    assert resultat.returncode == 0, (
        "un ecran du miroir ne s'affiche pas :\n"
        f"{resultat.stdout}\n{resultat.stderr}")
    assert "Tous les ecrans" in resultat.stdout


def test_le_verificateur_est_livre():
    """Sans lui, la seule verification possible redevient visuelle — donc omise."""
    assert VERIFICATEUR.is_file()


@pytest.mark.skipif(_node() is None, reason="Node.js absent")
def test_le_script_du_miroir_est_syntaxiquement_valide(tmp_path):
    """La panne d'origine : un horodatage insere dans une chaine JavaScript y a
    glisse un retour a la ligne, ce qui rompt la chaine et arrete tout le script.

    Un controle de syntaxe l'attrape immediatement, la ou une inspection du DOM
    laissait croire que la page fonctionnait.
    """
    import re
    texte = MIROIR.read_text(encoding="utf-8")
    script = re.search(r"<script[^>]*>([\s\S]*)</script>", texte).group(1)
    fichier = tmp_path / "miroir.js"
    fichier.write_text(script, encoding="utf-8")

    resultat = subprocess.run([_node(), "--check", str(fichier)],
                              capture_output=True, text=True, timeout=60)
    assert resultat.returncode == 0, "syntaxe invalide :\n" + resultat.stderr


def test_le_miroir_porte_un_horodatage():
    texte = MIROIR.read_text(encoding="utf-8")
    assert "var GENERE_LE" in texte, \
        "la date des donnees doit vivre dans une variable, pas dans une chaine de rendu"
