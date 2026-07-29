"""Alimente le miroir HTML autonome avec les donnees reelles.

`CHRUTH_PLATEFORME.html` reproduit la plateforme dans un fichier unique,
ouvrable sans Python, sans serveur et sans internet. Il portait jusqu'ici huit
appels d'offres d'exemple ecrits a la main : une maquette, pas un export. Ce
module convertit la base reelle vers la forme attendue par son JavaScript.

Deux regles tiennent tout le reste :

- **Aucune adresse email ne sort d'ici.** Le fichier est fait pour etre envoye
  ou ouvert sur un telephone ; les destinataires des alertes et l'expediteur
  n'y ont pas leur place. C'est aussi ce qui evitait de devoir l'expurger a
  chaque livraison.
- **Le fichier reste autonome.** Les donnees sont ecrites dans le HTML, jamais
  chargees a cote : un fichier unique se deplace, un dossier se disperse.
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any

import pandas as pd

# Au-dela, le fichier devient lourd a ouvrir sur un telephone pour un gain nul :
# personne ne fait defiler trois cents marches dans un onglet.
AOS_MAX = 120
ACHETEURS_MAX = 40

PRIORITES = {"CHAUD": "chaud", "TIEDE": "tiede", "FROID": "froid"}
CLES_INTERDITES = ("destinataires", "expediteur", "smtp_user", "smtp_password")


def _texte(valeur) -> str:
    return str(valeur if valeur is not None else "").strip()


def _jour_mois(valeur) -> str:
    """« 2026-07-22 » -> « 22.07 », format compact du miroir."""
    texte = _texte(valeur)[:10]
    try:
        d = date.fromisoformat(texte)
    except ValueError:
        return ""
    return f"{d.day:02d}.{d.month:02d}"


def _date_complete(valeur) -> str:
    texte = _texte(valeur)[:10]
    try:
        d = date.fromisoformat(texte)
    except ValueError:
        return ""
    return f"{d.day:02d}.{d.month:02d}.{d.year}"


def _score(valeur) -> float:
    try:
        return round(float(valeur), 1)
    except (TypeError, ValueError):
        return 0.0


def _public(acheteur: str, secteur: str) -> tuple[str, str]:
    """Nature de l'acheteur, deduite de son nom puis de son secteur.

    Le miroir distingue public et prive-droit : un acheteur mal classe n'est pas
    grave, mais le laisser vide casserait ses filtres.
    """
    nom = f"{acheteur} {secteur}".casefold()
    marqueurs = ("mairie", "commune", "ville de", "departement", "region", "prefecture",
                 "ccas", "syndicat", "communaute", "metropole", "conseil", "academie",
                 "universite", "hopital", "centre hospitalier", "etablissement public")
    if any(m in nom for m in marqueurs):
        return "public", "Collectivité ou établissement public"
    return "prive", "Personne privée soumise à la commande publique"


def ao_vers_miroir(ligne: dict[str, Any]) -> dict[str, Any]:
    """Une ligne de `ao_records` vers l'objet attendu par le JavaScript."""
    acheteur = _texte(ligne.get("acheteur"))
    secteur = _texte(ligne.get("secteur"))
    buyer, sous = _public(acheteur, secteur)
    verdict = _texte(ligne.get("verdict_tri")) or "NON TRIE"
    return {
        "id": _texte(ligne.get("id_ao")),
        "objet": _texte(ligne.get("objet"))[:180],
        "acheteur": acheteur,
        "ville": _texte(ligne.get("ville")),
        "dept": _texte(ligne.get("departement")),
        "source": _texte(ligne.get("source")) or "BOAMP",
        "ref": _texte(ligne.get("id_ao")),
        "procedure": _texte(ligne.get("procedure")),
        "publie": _jour_mois(ligne.get("date_publication")),
        "limite": _date_complete(ligne.get("date_limite")),
        "prio": PRIORITES.get(_texte(ligne.get("priorite")).upper(), "froid"),
        "score": _score(ligne.get("score_chruth")),
        "buyer": buyer,
        "sous": sous,
        "perso": _texte(ligne.get("categorie")).casefold() == "personnel",
        "verdict": verdict,
        "via": _texte(ligne.get("motif_tri"))[:120],
        "etage": "tri automatique",
        "neuf": False,
        "url": _texte(ligne.get("url_avis")) or _texte(ligne.get("url_dce")),
    }


def donnees_aos(df: pd.DataFrame, limite: int = AOS_MAX) -> list[dict[str, Any]]:
    """AO a embarquer : les mieux notes d'abord, marches expires exclus.

    Un marche dont la date limite est passee n'a aucune valeur dans un fichier
    qu'on consulte en mobilite — il occupe l'ecran sans jamais pouvoir servir.
    """
    if df is None or df.empty:
        return []
    travail = df.copy()
    # Meme regle que la page Messages : le score compte des mots-cles, et une
    # formation « lutte contre les discriminations » en collectionne autant
    # qu'un marche de nettoyage. Sans ce filtre, elle arrive en tete du miroir.
    if "verdict_tri" in travail.columns:
        travail = travail[travail["verdict_tri"].fillna("").astype(str) != "REJETE"]
    aujourd_hui = date.today().isoformat()
    if "date_limite" in travail.columns:
        limites = travail["date_limite"].fillna("").astype(str).str[:10]
        travail = travail[(limites == "") | (limites >= aujourd_hui)]
    if "score_chruth" in travail.columns:
        travail = travail.assign(
            _tri=pd.to_numeric(travail["score_chruth"], errors="coerce").fillna(0)
        ).sort_values("_tri", ascending=False)
    return [ao_vers_miroir(l) for l in travail.head(limite).to_dict("records")]


def _marches_de(brut: Any) -> list[dict[str, Any]]:
    """Sous-liste des marches d'un acheteur.

    Elle arrive en liste depuis `acheteurs_semaine`, mais en chaine apres un
    aller-retour par CSV — on accepte les deux plutot que d'imposer au appelant
    de savoir d'ou vient sa donnee.
    """
    if isinstance(brut, str):
        import ast
        try:
            brut = ast.literal_eval(brut)
        except (ValueError, SyntaxError):
            return []
    return brut if isinstance(brut, list) else []


def donnees_acheteurs(acheteurs: Any, limite: int = ACHETEURS_MAX) -> list[dict[str, Any]]:
    """Acheteurs de la semaine vers la forme du miroir.

    Accepte le DataFrame rendu par `acheteurs_semaine.construire` comme une
    liste de dictionnaires : le generateur ne doit pas avoir a convertir.
    """
    if acheteurs is None:
        return []
    if isinstance(acheteurs, pd.DataFrame):
        if acheteurs.empty:
            return []
        acheteurs = acheteurs.to_dict("records")
    if not acheteurs:
        return []

    sortie = []
    for a in list(acheteurs)[:limite]:
        marches = [
            {"o": _texte(m.get("objet"))[:120],
             "d": _jour_mois(m.get("date_publication")),
             "p": _texte(m.get("priorite")).upper()}
            for m in _marches_de(a.get("aos"))
        ]
        try:
            nb = int(a.get("nb_ao_semaine") or len(marches))
        except (TypeError, ValueError):
            nb = len(marches)
        type_acheteur = _texte(a.get("type")) or "public"
        incertain = _texte(a.get("type_incertain")).casefold() in ("true", "1", "oui")
        sortie.append({
            "nom": _texte(a.get("acheteur")),
            "type": type_acheteur,
            "sous": ("à confirmer" if incertain else
                     "Collectivité ou établissement public" if type_acheteur == "public"
                     else "Personne privée soumise à la commande publique"),
            "cp": _texte(a.get("code_postal")),
            "ville": _texte(a.get("ville")),
            "dept": _texte(a.get("departement")),
            "eff": _texte(a.get("effectif")),
            "nb": nb,
            "prio": _texte(a.get("priorite")).upper() or "TIEDE",
            "aos": marches,
        })
    return sortie


def reglages_publics(reglages: dict[str, Any] | None) -> dict[str, Any]:
    """Reglages embarquables : les interrupteurs, jamais les adresses.

    La fiche CHRUTH est conservee — elle decrit l'entreprise et n'est pas une
    donnee personnelle — mais tout ce qui ressemble a une boite mail saute.
    """
    reglages = reglages or {}
    propres = {
        "notifications": bool(reglages.get("notifications", True)),
        "collecte": bool(reglages.get("collecte", True)),
        "rh": bool(reglages.get("mots_cles_rh_actifs", True)),
        "destinataires": [],
        "fiche": _texte(reglages.get("fiche_chruth")),
    }
    for interdite in CLES_INTERDITES:
        propres.pop(interdite, None) if interdite != "destinataires" else None
    return propres


def _js(valeur: Any) -> str:
    """Litteral JavaScript. On passe par JSON : les guillemets, accents et
    retours a la ligne y sont deja echappes correctement."""
    return json.dumps(valeur, ensure_ascii=False)


def bloc_js(nom: str, donnees: Any) -> str:
    """Declaration JavaScript complete, prete a remplacer l'ancienne."""
    return f"var {nom} = {_js(donnees)};"


def remplacer_tableau(html: str, nom: str, donnees: Any) -> str:
    """Remplace `var NOM = [ ... ];` par les donnees fournies.

    On compte les crochets plutot que d'utiliser une expression reguliere : les
    intitules de marches contiennent des crochets, et une regex gourmande
    tronquerait le tableau au premier venu.
    """
    debut = html.find(f"var {nom} = [")
    if debut < 0:
        raise ValueError(f"tableau introuvable dans le modele : {nom}")
    i = html.index("[", debut)
    profondeur = 0
    for j in range(i, len(html)):
        if html[j] == "[":
            profondeur += 1
        elif html[j] == "]":
            profondeur -= 1
            if profondeur == 0:
                fin = html.index(";", j) + 1
                return html[:debut] + bloc_js(nom, donnees) + html[fin:]
    raise ValueError(f"tableau non termine dans le modele : {nom}")


def vider_destinataires(html: str) -> str:
    """Remplace la liste de destinataires ecrite en dur par une liste vide.

    Elle vit dans l'objet des reglages par defaut, pas dans un `var` : elle
    echappait donc a `remplacer_tableau`, et c'est elle qui a fait echouer le
    garde-fou de sortie a la premiere generation.
    """
    import re
    return re.sub(r"destinataires\s*:\s*\[[^\]]*\]", "destinataires:[]", html)


def contient_une_adresse_email(html: str) -> bool:
    """Garde-fou de sortie : le fichier est fait pour etre envoye."""
    import re
    return bool(re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", html))
