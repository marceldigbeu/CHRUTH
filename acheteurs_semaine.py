"""Acheteurs actifs de la semaine : les organisations ayant publié un AO
propreté pertinent sur 7 jours glissants, classées et enrichies.

Remplace l'ancienne collecte « toutes les entreprises IDF » comme source de
prospection (celle-ci est mise en sommeil, non supprimée).
"""
from __future__ import annotations

from datetime import date, timedelta

from ao_extract_fields import normalize_text
import veille_etat

FENETRE_JOURS = 7
PRIORITES_PERTINENTES = ("CHAUD", "TIEDE", "TIÈDE")

_RANG_PRIO = {"CHAUD": 3, "TIEDE": 2, "TIÈDE": 2, "FROID": 1, "": 0}

# Indices de droit public dans le nom, quand la catégorie juridique manque.
_MOTS_PUBLIC = ("mairie", "commune", "ville de", "departement", "département",
                "prefecture", "préfecture", "region", "région", "hopital",
                "hôpital", "centre hospitalier", "ccas", "etablissement public",
                "établissement public", "communaute", "communauté", "metropole",
                "métropole", "syndicat", "academie", "académie", "rectorat")


def classer(nature_juridique: str, nom: str = "") -> tuple[str, bool]:
    """(type, incertain) : 'public' si catégorie juridique niveau I = « 7 »,
    sinon 'prive'. Sans catégorie, repli sur le nom, marqué incertain."""
    code = str(nature_juridique or "").strip()
    if code[:1] == "7":
        return ("public", False)
    if code:
        return ("prive", False)
    n = normalize_text(nom or "")
    for mot in _MOTS_PUBLIC:
        if normalize_text(mot) in n:
            return ("public", True)
    return ("prive", True)


def _date_ok(datep, aujourd_hui, jours) -> bool:
    s = str(datep or "").strip()[:10]
    if not s:
        return False
    try:
        d = date.fromisoformat(s)
    except ValueError:
        return False
    return aujourd_hui - timedelta(days=jours) <= d <= aujourd_hui


def collecter_aos_recents(jours: int = FENETRE_JOURS, aujourd_hui: date | None = None,
                          records_boamp=None, etat_maximilien=None) -> list[dict]:
    aujourd_hui = aujourd_hui or date.today()

    if records_boamp is None:
        import ao_db
        records_boamp = ao_db.fetch_records().to_dict("records")
    if etat_maximilien is None:
        import veille_depot
        etat_maximilien, _ = veille_depot.lire()

    aos = []
    for r in records_boamp or []:
        if str(r.get("priorite") or "").upper() not in PRIORITES_PERTINENTES:
            continue
        if not _date_ok(r.get("date_publication"), aujourd_hui, jours):
            continue
        aos.append({
            "acheteur": r.get("acheteur") or "", "siret": str(r.get("siret_acheteur") or ""),
            "siren": str(r.get("siren_acheteur") or ""), "ville": r.get("ville") or "",
            "departement": str(r.get("departement") or ""), "date_publication": str(r.get("date_publication") or ""),
            "url": r.get("url_avis") or "", "objet": r.get("objet") or "",
            "priorite": str(r.get("priorite") or "").upper(), "source": "BOAMP",
        })

    for e in (etat_maximilien or {}).get("aos", {}).values():
        if veille_etat.verdict_effectif(e) != "PERTINENT":
            continue
        if not _date_ok(e.get("date_publication"), aujourd_hui, jours):
            continue
        aos.append({
            "acheteur": e.get("acheteur") or "", "siret": "", "siren": "",
            "ville": e.get("ville") or "", "departement": str(e.get("departement") or ""),
            "date_publication": str(e.get("date_publication") or ""), "url": e.get("url") or "",
            "objet": e.get("objet") or "", "priorite": str(e.get("priorite") or "").upper(),
            "source": "Maximilien",
        })
    return aos


def _cle(ao) -> str:
    s = "".join(c for c in str(ao.get("siret") or "") if c.isdigit())
    if len(s) == 14:
        return "siret:" + s
    normalized_name = " ".join(normalize_text(ao.get("acheteur") or "").split())
    return "nom:" + normalized_name + "|" + str(ao.get("departement") or "")


def extraire_acheteurs(aos: list[dict]) -> list[dict]:
    par_cle: dict[str, dict] = {}
    for ao in aos:
        cle = _cle(ao)
        a = par_cle.get(cle)
        if a is None:
            a = {"acheteur": ao.get("acheteur") or "", "siret": str(ao.get("siret") or ""),
                 "siren": str(ao.get("siren") or ""), "ville": ao.get("ville") or "",
                 "departement": str(ao.get("departement") or ""), "priorite": "",
                 "nb_ao_semaine": 0, "aos": [], "source": ao.get("source") or ""}
            par_cle[cle] = a
        a["nb_ao_semaine"] += 1
        a["aos"].append({"objet": ao.get("objet") or "", "date_publication": ao.get("date_publication") or "",
                         "priorite": ao.get("priorite") or "", "url": ao.get("url") or ""})
        if _RANG_PRIO.get(ao.get("priorite") or "", 0) > _RANG_PRIO.get(a["priorite"], 0):
            a["priorite"] = ao.get("priorite") or ""
        if not a["siret"] and ao.get("siret"):
            a["siret"] = str(ao.get("siret"))
    return list(par_cle.values())
