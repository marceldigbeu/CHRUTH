"""Quelles pages un compte a le droit de voir.

L'inscription est ouverte : n'importe qui peut se creer un compte CHRUTH. La
plateforme contient pourtant la base des appels d'offres, le CRM et les
reglages — le fonds de commerce. Il fallait donc separer ce qui appartient au
membre de ce qui appartient a l'entreprise.

La separation se fait a la navigation plutot que page par page, parce qu'une
page absente de `st.navigation` n'est pas seulement masquee : elle n'est pas
routable. Une garde ecrite en tete de chaque page protegerait tout aussi bien,
mais il faudrait ne l'oublier nulle part, aujourd'hui et a chaque page future.

La liste ci-dessous nomme donc ce qui est OUVERT, et tout le reste est reserve.
Une page ajoutee demain sans qu'on y pense tombe du cote ferme : un oubli coute
un acces manquant, jamais une fuite.
"""
from __future__ import annotations

ACCUEIL = "Accueil"

# Titres visibles par tout compte connecte. Le reste demande l'administration.
PAGES_MEMBRE = (
    ACCUEIL,
    "Veille appels d'offres",
    "Mes appels d'offres",
    "Mes messages",
    "Mon espace",
)


def pages_visibles(catalogue, admin: bool):
    """Le catalogue tel quel pour un administrateur, sa part ouverte sinon.

    `catalogue` est la liste (fichier, titre) de la navigation complete ; l'ordre
    est conserve, car il porte le sens de lecture de la barre laterale.
    """
    if admin:
        return list(catalogue)
    return [(chemin, titre) for chemin, titre in catalogue
            if titre in PAGES_MEMBRE]


def page_par_defaut(pages_visibles_, preference: str) -> str:
    """Titre de la page a ouvrir en premier.

    La preference du membre est respectee tant qu'elle designe une page qu'il
    voit encore. Un membre retrograde garde sa preference d'hier : sans ce
    repli, la navigation ouvrirait sur une page absente d'elle-meme.
    """
    titres = [titre for _, titre in pages_visibles_]
    if preference in titres:
        return preference
    if ACCUEIL in titres:
        return ACCUEIL
    return titres[0] if titres else ACCUEIL
