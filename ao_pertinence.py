"""Tri de pertinence des AO avant notification.

Deux etages : des listes deterministes qui tranchent les cas nets, puis un
arbitrage IA sur les seuls cas ambigus.

Ce module est une PORTE DEVANT LA NOTIFICATION, pas devant la collecte : la
base et le cockpit gardent le filet large, seuls les emails se resserrent.
Il ne connait ni le web, ni l'email, ni la base.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from ao_config import (
    AO_EXCLUSION_DURES,
    AO_EXCLUSION_TRI,
    AO_KEYWORDS_CORE,
    AO_KEYWORDS_RH,
    AO_KEYWORDS_SECONDARY,
)
from ao_extract_fields import normalize_text

PERTINENT = "PERTINENT"
REJETE = "REJETE"


@dataclass
class Verdict:
    verdict: str  # PERTINENT | REJETE
    etage: str    # listes | ia | correction
    motif: str


def _exclusions() -> list[str]:
    return list(AO_EXCLUSION_TRI) + list(AO_EXCLUSION_DURES)


def _mots_cles() -> list[str]:
    """Mots-cles qui declenchent un verdict PERTINENT a l'etage 1.

    Les mots-cles de personnel sont inclus inconditionnellement ici ; la tache 8
    les rendra pilotables depuis les reglages partages.
    """
    return list(AO_KEYWORDS_CORE) + list(AO_KEYWORDS_SECONDARY) + list(AO_KEYWORDS_RH)


def _present(terme: str, texte_norm: str) -> bool:
    """Le terme apparait-il en DEBUT de mot dans le texte deja normalise ?

    Frontiere en tete seulement : « ascenseur » doit reconnaitre « ascenseurs »,
    mais « menage » ne doit pas se declencher dans « amenagement » (cas reel
    observe le 2026-07-23, un marche de travaux classe pertinent).
    """
    return re.search(r"\b" + re.escape(normalize_text(terme)), texte_norm) is not None


def trier_listes(objet: str, detail: str = "") -> Verdict | None:
    """Verdict deterministe, ou None si le cas doit etre arbitre.

    L'exclusion prime sur le mot-cle coeur : elle est plus specifique.
    Un mot-cle trouve uniquement dans le detail ne suffit jamais a notifier
    (regle centrale : le detail n'autorise plus a notifier).
    """
    objet_norm = normalize_text(objet or "")

    for terme in _exclusions():
        if _present(terme, objet_norm):
            return Verdict(REJETE, "listes", f"exclusion metier : {terme}")

    for mot in _mots_cles():
        if _present(mot, objet_norm):
            return Verdict(PERTINENT, "listes", f"mot-cle coeur dans l'intitule : {mot}")

    return None


# --- Etage 2 : arbitrage IA des cas ambigus --------------------------------

SYSTEM_TRI = (
    "Tu es un expert des marchés publics de propreté. Tu décides si un appel d'offres "
    "relève du métier de l'entreprise décrite, ou non. Tu réponds uniquement en JSON."
)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def prompt_tri(objet: str, detail: str = "", guide: str = "",
               corrections: list[dict] | None = None) -> str:
    """Prompt d'arbitrage. Garde-fous : pas d'invention, JSON strict, doute = PERTINENT."""
    bloc_guide = f"\n\nL'ENTREPRISE :\n{guide.strip()}" if guide.strip() else ""

    bloc_exemples = ""
    if corrections:
        lignes = "\n".join(
            f"- « {c['objet']} » -> {c['verdict']}" for c in corrections[:10]
        )
        bloc_exemples = (
            "\n\nDÉCISIONS DÉJÀ TRANCHÉES PAR L'UTILISATEUR (fais-toi le même jugement) :\n"
            + lignes
        )

    return (
        "Cet appel d'offres relève-t-il du nettoyage et de la propreté de locaux ?"
        f"{bloc_guide}{bloc_exemples}\n\n"
        f"INTITULÉ : {objet}\n"
        f"DÉTAIL : {(detail or '')[:800]}\n\n"
        "RÈGLES :\n"
        "- Réponds NON_PERTINENT pour la maintenance technique (ascenseurs, incendie, "
        "ventilation), les espaces verts, la conservation d'archives ou d'œuvres, "
        "la dératisation, la restauration collective, les travaux.\n"
        "- Réponds PERTINENT pour l'entretien courant de locaux, la vitrerie, "
        "le bionettoyage, la remise en état.\n"
        "- N'invente aucune information absente de l'intitulé.\n"
        "- En cas de doute réel, réponds PERTINENT.\n\n"
        'Réponds exactement : {"verdict": "PERTINENT" ou "NON_PERTINENT", '
        '"motif": "une phrase courte"}'
    )


def _lire_reponse(brut: str) -> tuple[str, str] | None:
    """Extrait (verdict, motif) d'une reponse LLM, tolerante aux fences markdown."""
    m = _JSON_RE.search(brut or "")
    if not m:
        return None
    try:
        data = json.loads(m.group(0), strict=False)
    except Exception:  # noqa: BLE001
        return None
    verdict = str(data.get("verdict") or "").strip().upper()
    motif = str(data.get("motif") or "").strip()
    if verdict not in ("PERTINENT", "NON_PERTINENT"):
        return None
    return (PERTINENT if verdict == "PERTINENT" else REJETE), motif


def trier(objet: str, detail: str = "", guide: str = "", client=None,
          corrections: list[dict] | None = None) -> Verdict:
    """Verdict final. L'IA n'est consultee que si les listes ne tranchent pas.

    Principe : le doute profite a l'AO. Un faux positif coute un email, un faux
    negatif coute un marche.
    """
    verdict = trier_listes(objet, detail)
    if verdict is not None:
        return verdict

    if client is None:
        import llm_client as client  # import tardif : le module reste testable sans LLM

    try:
        if not client.moteur_auto():
            return Verdict(PERTINENT, "listes", "ambigu, tri IA indisponible")
        brut = client.generer(prompt_tri(objet, detail, guide, corrections),
                              system=SYSTEM_TRI, timeout=60, temperature=0.1)
    except Exception as exc:  # noqa: BLE001
        return Verdict(PERTINENT, "listes", f"ambigu, tri IA en echec ({type(exc).__name__})")

    lu = _lire_reponse(brut)
    if lu is None:
        return Verdict(PERTINENT, "listes", "ambigu, reponse IA illisible")
    return Verdict(lu[0], "ia", lu[1] or "arbitrage IA")
