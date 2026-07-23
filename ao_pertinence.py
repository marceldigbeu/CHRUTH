"""Tri de pertinence des AO avant notification.

Deux etages : des listes deterministes qui tranchent les cas nets, puis un
arbitrage IA sur les seuls cas ambigus.

Ce module est une PORTE DEVANT LA NOTIFICATION, pas devant la collecte : la
base et le cockpit gardent le filet large, seuls les emails se resserrent.
Il ne connait ni le web, ni l'email, ni la base.
"""
from __future__ import annotations

from dataclasses import dataclass

from ao_config import (
    AO_EXCLUSION_DURES,
    AO_EXCLUSION_TRI,
    AO_KEYWORDS_CORE,
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
    return list(AO_KEYWORDS_CORE) + list(AO_KEYWORDS_SECONDARY)


def trier_listes(objet: str, detail: str = "") -> Verdict | None:
    """Verdict deterministe, ou None si le cas doit etre arbitre.

    L'exclusion prime sur le mot-cle coeur : elle est plus specifique.
    Un mot-cle trouve uniquement dans le detail ne suffit jamais a notifier
    (regle centrale : le detail n'autorise plus a notifier).
    """
    objet_norm = normalize_text(objet or "")

    for terme in _exclusions():
        if normalize_text(terme) in objet_norm:
            return Verdict(REJETE, "listes", f"exclusion metier : {terme}")

    for mot in _mots_cles():
        if normalize_text(mot) in objet_norm:
            return Verdict(PERTINENT, "listes", f"mot-cle coeur dans l'intitule : {mot}")

    return None
