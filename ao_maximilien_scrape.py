"""Collecte MAXIMILIEN sans compte ni API (mode *pull*).

Interroge la recherche publique de marches.maximilien.fr (accessible sans
authentification), filtre sur les mots-cles nettoyage + categorie Services,
parse les consultations, les score et les injecte dans la base CHRUTH.

Contrairement a la voie IMAP (ao_maximilien_ingest.py), qui exige une alerte
enregistree cote Maximilien (donc un compte), ce collecteur ne demande RIEN :
il va chercher les avis publics. L'IMAP reste disponible en secours.

Techniquement : le site tourne sous Prado (postback avec jeton PRADO_PAGESTATE).
On reproduit ce postback avec requests : GET du formulaire pour recuperer le
jeton + les champs par defaut, puis POST avec nos criteres.
"""
from __future__ import annotations

import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from ao_config import (
    IDF_DEPARTEMENTS,
    LOG_DIR,
    REQUEST_TIMEOUT_SECONDS,
)
from ao_db import AO_DB_PATH, connect, log_update, upsert_records
from ao_extract_fields import classify_categorie, detect_secteur, normalize_text
from ao_scoring import compute_ao_score

logger = logging.getLogger(__name__)

# --- Constantes site -------------------------------------------------------

BASE_URL = "https://marches.maximilien.fr"
SEARCH_PAGE = f"{BASE_URL}/?page=Entreprise.EntrepriseAdvancedSearch&searchAnnCons"
FORM_PREFIX = "ctl0$CONTENU_PAGE$AdvancedSearch$"
# UA navigateur : le site Prado sert differemment un UA "robot".
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 CHRUTH-Veille/1.0")
CATEGORIE_SERVICES = "3"

# Mots-cles interroges (une recherche par terme, resultats dedupliques).
# NB : "entretien des locaux" volontairement exclu -> trop large (ramenait
# ascenseurs, elagage, bouches d'incendie...). La recherche Maximilien etant
# full-text/floue, "nettoyage" capte deja les "entretien des locaux" pertinents.
KEYWORDS = ["nettoyage", "propreté", "bionettoyage"]

CONSULT_RE = re.compile(r"/entreprise/consultation/(\d+)\?orgAcronyme=(\w+)")
CP_RE = re.compile(r"\((\d{5})\s*-\s*([^)]+)\)")

# --- Pagination ------------------------------------------------------------
PAGE_SIZE = "20"
MAX_PAGES = 20  # cap de securite : 20 pages x 20 = 400 resultats par mot-cle
RESULT_PREFIX = "ctl0$CONTENU_PAGE$resultSearch$"
NB_RESULTATS_RE = re.compile(r"r[eé]sultats?\s*:\s*(\d+)", re.IGNORECASE)

MOIS_FR = {
    "janv": 1, "janvier": 1, "févr": 2, "fevr": 2, "février": 2, "fevrier": 2,
    "mars": 3, "avr": 4, "avril": 4, "mai": 5, "juin": 6, "juil": 7,
    "juillet": 7, "août": 8, "aout": 8, "sept": 9, "septembre": 9,
    "oct": 10, "octobre": 10, "nov": 11, "novembre": 11, "déc": 12,
    "dec": 12, "décembre": 12, "decembre": 12,
}


# --- Requetes Prado --------------------------------------------------------

def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def _champs_formulaire(soup: BeautifulSoup) -> dict[str, str]:
    """Tous les champs par defaut du formulaire (incl. PRADO_PAGESTATE)."""
    data: dict[str, str] = {}
    for inp in soup.find_all("input"):
        name = inp.get("name")
        if not name or inp.get("type") in ("submit", "button", "image", "checkbox", "radio"):
            continue
        data[name] = inp.get("value", "")
    for sel in soup.find_all("select"):
        name = sel.get("name")
        if not name:
            continue
        opt = sel.find("option", selected=True) or sel.find("option")
        data[name] = opt.get("value", "") if opt else ""
    for ta in soup.find_all("textarea"):
        if ta.get("name"):
            data[ta.get("name")] = ta.get_text()
    return data


def _rechercher(session: requests.Session, keyword: str, page: int = 1,
                page_size: str = PAGE_SIZE) -> str:
    """GET le formulaire puis POST la recherche. Renvoie le HTML des resultats.

    page=1 lance la recherche ; page>1 rejoue le postback de pagination sur la
    page de resultats obtenue, car le jeton PRADO_PAGESTATE change a chaque reponse.
    """
    r = session.get(SEARCH_PAGE, timeout=REQUEST_TIMEOUT_SECONDS)
    r.raise_for_status()
    data = _champs_formulaire(BeautifulSoup(r.text, "html.parser"))
    if "PRADO_PAGESTATE" not in data:
        raise RuntimeError("PRADO_PAGESTATE absent : structure du formulaire modifiee ?")

    data[FORM_PREFIX + "keywordSearch"] = keyword
    data[FORM_PREFIX + "categorie"] = CATEGORIE_SERVICES
    data[FORM_PREFIX + "lancerRecherche"] = "Lancer la recherche"
    data["PRADO_POSTBACK_TARGET"] = FORM_PREFIX + "lancerRecherche"
    data["PRADO_POSTBACK_PARAMETER"] = ""

    rp = session.post(SEARCH_PAGE, data=data, timeout=REQUEST_TIMEOUT_SECONDS)
    rp.raise_for_status()
    html = rp.text

    # Passer a 20 resultats par page (moins de requetes, moins de charge pour le site).
    html = _postback(session, html, {RESULT_PREFIX + "listePageSizeTop": page_size},
                     RESULT_PREFIX + "listePageSizeTop")
    if page > 1:
        html = _postback(session, html, {RESULT_PREFIX + "numPageTop": str(page)},
                         RESULT_PREFIX + "DefaultButtonTop")
    return html


def _postback(session: requests.Session, html: str, champs: dict[str, str],
              cible: str) -> str:
    """Rejoue un postback Prado depuis une page deja chargee."""
    data = _champs_formulaire(BeautifulSoup(html, "html.parser"))
    data.update(champs)
    data["PRADO_POSTBACK_TARGET"] = cible
    data["PRADO_POSTBACK_PARAMETER"] = ""
    rp = session.post(SEARCH_PAGE, data=data, timeout=REQUEST_TIMEOUT_SECONDS)
    rp.raise_for_status()
    return rp.text


def nb_resultats(html: str) -> int:
    """Nombre total de resultats annonce par la page ; 0 si non trouve."""
    m = NB_RESULTATS_RE.search(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    return int(m.group(1)) if m else 0


def _pages_resultats(session: requests.Session, keyword: str):
    """Rend le HTML de chaque page de resultats, page 1 comprise."""
    premiere = _rechercher(session, keyword, page=1)
    yield premiere

    total = nb_resultats(premiere)
    taille = int(PAGE_SIZE)
    nb_pages = min((total + taille - 1) // taille, MAX_PAGES) if total else 1
    for page in range(2, nb_pages + 1):
        yield _rechercher(session, keyword, page=page)
        time.sleep(0.5)  # courtoisie envers le site


# --- Parsing ---------------------------------------------------------------

def _parse_date_fr(texte: str) -> str:
    """'14 Avril 2026 12:00' -> '2026-04-14' ; '' si non reconnu."""
    m = re.search(r"(\d{1,2})\s+([A-Za-zéèûôàê\.]+)\s+(\d{4})", texte or "")
    if not m:
        return ""
    jour, mois_txt, annee = m.group(1), m.group(2).strip(".").lower(), m.group(3)
    mois = MOIS_FR.get(mois_txt) or MOIS_FR.get(mois_txt[:4]) or MOIS_FR.get(mois_txt[:3])
    if not mois:
        return ""
    try:
        return f"{int(annee):04d}-{mois:02d}-{int(jour):02d}"
    except ValueError:
        return ""


def _txt(el) -> str:
    return el.get_text(" ", strip=True) if el else ""


def _parse_resultats(html: str) -> list[dict[str, Any]]:
    """Extrait une liste brute de consultations depuis le HTML de resultats."""
    soup = BeautifulSoup(html, "html.parser")
    vus: set[str] = set()
    brut: list[dict[str, Any]] = []

    for objet_line in soup.select(".objet-line"):
        # Remonter au bloc de ligne contenant le lien de consultation.
        row = objet_line
        lien = None
        for _ in range(8):
            row = row.parent
            if row is None:
                break
            lien = row.find("a", href=CONSULT_RE)
            if lien is not None:
                break
        if row is None or lien is None:
            continue

        m = CONSULT_RE.search(lien.get("href", ""))
        if not m:
            continue
        cid, org = m.group(1), m.group(2)
        if cid in vus:
            continue
        vus.add(cid)

        # Reference | Intitule
        ref, intitule = "", _txt(objet_line)
        if "|" in intitule:
            ref, intitule = [p.strip() for p in intitule.split("|", 1)]

        row_txt = _txt(row)
        mo = re.search(r"Objet\s*:\s*(.+?)\s*(?:Organisme\s*:|$)", row_txt)
        objet_desc = mo.group(1).strip() if mo else ""
        morg = re.search(r"Organisme\s*:\s*(.+?)\s*\(\d{5}", row_txt)
        organisme = morg.group(1).strip() if morg else ""
        mcp = CP_RE.search(row_txt)
        cp, ville = (mcp.group(1), mcp.group(2).strip()) if mcp else ("", "")

        brut.append({
            "cid": cid,
            "org": org,
            "reference": ref,
            "intitule": intitule,
            "objet_desc": objet_desc,
            "organisme": organisme,
            "cp": cp,
            "ville": ville,
            "procedure": _txt(row.select_one(".cons_procedure")),
            "date_limite_txt": _txt(row.select_one(".cons_dateEnd")),
            "url": f"{BASE_URL}/entreprise/consultation/{cid}?orgAcronyme={org}",
        })
    return brut


# --- Mise au format AO -----------------------------------------------------

def _to_ao(b: dict[str, Any]) -> dict[str, Any]:
    objet = b["intitule"] or b["objet_desc"] or "Consultation Maximilien"
    acheteur = b["organisme"]
    dept = b["cp"][:2] if b["cp"] else ""
    date_limite = _parse_date_fr(b["date_limite_txt"])

    ao: dict[str, Any] = {
        "source": "MAXIMILIEN",
        "id_ao": f"MX-{b['cid']}",
        "objet": objet,
        "acheteur": acheteur,
        "ville": b["ville"],
        "departement": dept,
        "procedure": b["procedure"],
        "url_avis": b["url"],
        "url_dce": b["url"],
        "date_limite": date_limite,
        "date_publication": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "categorie": classify_categorie(f"{objet} {b['objet_desc']}"),
        "secteur": detect_secteur(acheteur, objet),
        "budget_statut": "A_VERIFIER_BUDGET",
        # Donnee structuree fiable (recherche ciblee) -> confiance suffisante pour
        # que le scoring ne rabatte pas en A_VERIFIER. On NE met PAS
        # statut_extraction=DCE_A_TELECHARGER, sinon l'AO ne serait jamais alerte.
        "niveau_confiance": "60",
        "statut_extraction": "LISTING_MAXIMILIEN",
        "mots_cles_detectes": ", ".join(
            kw for kw in ["nettoyage", "vitres", "entretien", "proprete", "hygiene", "menage"]
            if kw in normalize_text(f"{objet} {b['objet_desc']}")
        ),
    }
    score, priorite, raisons = compute_ao_score(ao)
    ao["score_chruth"] = score
    ao["priorite"] = priorite
    ao["raisons_scoring"] = raisons
    return ao


# --- Orchestration ---------------------------------------------------------

def collecter_maximilien(
    db_path: Path | None = None,
    keywords: list[str] | None = None,
) -> int:
    """Collecte publique Maximilien -> injecte les nouveaux AO. Renvoie le nb insere."""
    db_path = db_path or AO_DB_PATH
    keywords = keywords or KEYWORDS
    session = _session()

    collectes: dict[str, dict[str, Any]] = {}
    for kw in keywords:
        try:
            for html in _pages_resultats(session, kw):
                for b in _parse_resultats(html):
                    collectes.setdefault(b["cid"], b)  # dedup inter-pages et inter-mots-cles
        except Exception as exc:  # noqa: BLE001
            logger.warning("Recherche '%s' echouee : %s", kw, exc)
            continue
        time.sleep(1.0)  # courtoisie envers le site

    if not collectes:
        logger.info("Aucune consultation Maximilien collectee.")
        log_update("MAXIMILIEN", 0, 0, 0, "aucun resultat", db_path=db_path)
        return 0

    aos = [_to_ao(b) for b in collectes.values()]

    # Ne garder que l'IDF quand le departement est identifiable (le portail est
    # deja francilien ; on garde les AO sans CP lisible plutot que de les perdre).
    gardes = [a for a in aos if not a["departement"] or a["departement"] in IDF_DEPARTEMENTS]

    # Ne pousser en base que les consultations pas encore connues.
    nouveaux: list[dict[str, Any]] = []
    with connect(db_path) as conn:
        for ao in gardes:
            row = conn.execute("SELECT 1 FROM ao_records WHERE id_ao=?", (ao["id_ao"],)).fetchone()
            if not row:
                nouveaux.append(ao)

    inseres = upsert_records(nouveaux, db_path=db_path) if nouveaux else 0
    log_update("MAXIMILIEN", len(collectes), len(gardes), inseres,
               f"{len(keywords)} mots-cles", db_path=db_path)
    for ao in nouveaux:
        logger.info("  Nouveau MAXIMILIEN [%s/%s] %s | %s",
                    ao["priorite"], ao["score_chruth"], ao["objet"][:55], ao["acheteur"])
    logger.info("Maximilien : %s collectes, %s IDF, %s nouveaux inseres",
                len(collectes), len(gardes), inseres)
    return inseres


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    dry = "--dry" in sys.argv
    if dry:
        session = _session()
        collectes: dict[str, dict[str, Any]] = {}
        for kw in KEYWORDS:
            try:
                for html in _pages_resultats(session, kw):
                    for b in _parse_resultats(html):
                        collectes.setdefault(b["cid"], b)
            except Exception as exc:  # noqa: BLE001
                print(f"[DRY] '{kw}' echec : {exc}")
            time.sleep(1.0)
        print(f"[DRY] {len(collectes)} consultations uniques collectees :\n")
        for b in collectes.values():
            ao = _to_ao(b)
            print(f"  [{ao['priorite']:9} {ao['score_chruth']:3}] {ao['date_limite'] or '????-??-??'} "
                  f"| {ao['departement'] or '--'} | {ao['objet'][:60]}")
            print(f"      {ao['acheteur']} ({ao['ville']}) -> {ao['url_avis']}")
        return 0

    n = collecter_maximilien()
    print(f"[MAXIMILIEN-SCRAPE] {n} AO ingeres")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
