"""Ce qu'un membre voit, et ce qu'il ne voit pas.

L'inscription est ouverte : n'importe qui peut creer un compte CHRUTH depuis
l'ecran de connexion. Sans cloisonnement, ce compte donnerait acces au CRM, a la
base complete et aux reglages — c'est-a-dire a tout le fonds de commerce.

Le cloisonnement se fait a la navigation : une page absente de `st.navigation`
n'est pas seulement invisible, elle n'est pas routable. Ces tests fixent la
frontiere, parce qu'une page ajoutee plus tard sans y penser tomberait du bon
cote par hasard, pas par construction.
"""
from __future__ import annotations

import navigation_acces as nav

CATALOGUE = [
    ("pages_accueil.py", "Accueil"),
    ("app_veille.py", "Veille appels d'offres"),
    ("pages_donnees.py", "Base de données"),
    ("app_messages.py", "Messages et CRM"),
    ("administration.py", "Administration"),
    ("mes_ao.py", "Mes appels d'offres"),
]


def _titres(pages) -> list[str]:
    return [titre for _, titre in pages]


def test_le_membre_ne_voit_que_son_espace_et_la_veille():
    visibles = _titres(nav.pages_visibles(CATALOGUE, admin=False))
    assert visibles == ["Accueil", "Veille appels d'offres", "Mes appels d'offres"]


def test_l_administrateur_voit_tout():
    assert nav.pages_visibles(CATALOGUE, admin=True) == CATALOGUE


def test_le_crm_et_la_base_sont_hors_de_portee_du_membre():
    """Les deux pages qui contiennent les donnees commerciales."""
    visibles = _titres(nav.pages_visibles(CATALOGUE, admin=False))
    assert "Messages et CRM" not in visibles
    assert "Base de données" not in visibles


def test_une_page_inconnue_est_refusee_au_membre():
    """Par defaut fermee : une page ajoutee sans decision explicite reste admin.

    L'inverse — ouvrir par defaut — ferait d'un oubli une fuite.
    """
    catalogue = CATALOGUE + [("page_neuve.py", "Page neuve")]
    assert "Page neuve" not in _titres(nav.pages_visibles(catalogue, admin=False))


def test_la_page_par_defaut_suit_la_preference_quand_elle_est_visible():
    visibles = nav.pages_visibles(CATALOGUE, admin=False)
    assert nav.page_par_defaut(visibles, "Mes appels d'offres") == "Mes appels d'offres"


def test_une_preference_invisible_retombe_sur_l_accueil():
    """Un membre retrograde garde « Messages et CRM » en preference : sans ce
    repli, la navigation ouvrirait sur une page qu'elle ne contient pas."""
    visibles = nav.pages_visibles(CATALOGUE, admin=False)
    assert nav.page_par_defaut(visibles, "Messages et CRM") == "Accueil"


def test_la_page_par_defaut_tient_sans_accueil():
    """Catalogue reduit : on prend la premiere page visible plutot que rien."""
    visibles = [("mes_ao.py", "Mes appels d'offres")]
    assert nav.page_par_defaut(visibles, "Messages et CRM") == "Mes appels d'offres"


def test_les_pages_reelles_de_l_application_sont_reparties():
    """La frontiere s'applique au vrai catalogue, pas seulement a un exemple."""
    import ast
    from pathlib import Path

    source = Path(__file__).resolve().parent.parent / "CHRUTH_APP.py"
    module = ast.parse(source.read_text(encoding="utf-8"))
    catalogue = next(
        ast.literal_eval(n.value) for n in module.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "PAGES_DEF" for t in n.targets))

    membre = _titres(nav.pages_visibles(catalogue, admin=False))
    assert membre == ["Accueil", "Veille appels d'offres",
                      "Mes appels d'offres", "Mes messages", "Mon espace"]
    for reserve in ("Base de données", "Messages et CRM", "Réglages",
                    "Développeur", "Administration", "Pilotage", "Collecte"):
        assert reserve not in membre
