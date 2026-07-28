"""Acheteurs actifs de la semaine : les organisations ayant publié un AO
propreté pertinent sur 7 jours glissants, classées et enrichies.

Remplace l'ancienne collecte « toutes les entreprises IDF » comme source de
prospection (celle-ci est mise en sommeil, non supprimée).
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from ao_extract_fields import normalize_text
import veille_etat

FENETRE_JOURS = 7
PRIORITES_PERTINENTES = ("CHAUD", "TIEDE", "TIÈDE")

COLONNES = ["acheteur", "type", "type_incertain", "priorite", "nb_ao_semaine",
            "departement", "ville", "code_postal", "adresse", "effectif",
            "nature_juridique", "siret", "siren", "enrichi", "source", "aos"]

RACINE = Path(__file__).resolve().parent
XLSX_DEFAUT = RACINE / "output" / "Acheteurs_Semaine_CHRUTH.xlsx"
CSV_DEFAUT = RACINE / "output" / "Acheteurs_Semaine_CHRUTH.csv"

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


def enrichir(acheteur: dict, chercher=None) -> dict:
    """Enrichit un acheteur avec données SIRET (adresse, code_postal, effectif, nature_juridique).
    Classe toujours le type (public/prive) via classer().
    Best-effort: pas de SIRET, pas de fiche, ou chercher qui lève -> enrichi=False, row conservée.
    """
    if chercher is None:
        from collect_api_entreprises import fetch_by_siret as chercher
    a = dict(acheteur)
    fiche = None
    if a.get("siret"):
        try:
            fiche = chercher(str(a["siret"]))
        except Exception:  # noqa: BLE001 — best-effort
            fiche = None
    if fiche:
        a["adresse"] = fiche.get("adresse") or ""
        a["code_postal"] = fiche.get("code_postal") or ""
        a["ville"] = a.get("ville") or fiche.get("libelle_commune") or ""
        a["effectif"] = fiche.get("tranche_effectif_salarie") or ""
        a["nature_juridique"] = fiche.get("nature_juridique") or ""
        a["enrichi"] = True
    else:
        a.setdefault("adresse", ""); a.setdefault("code_postal", "")
        a.setdefault("effectif", ""); a["nature_juridique"] = ""; a["enrichi"] = False
    a["type"], a["type_incertain"] = classer(a.get("nature_juridique", ""), a.get("acheteur", ""))
    return a


def construire(jours: int = FENETRE_JOURS, aujourd_hui=None, records_boamp=None,
               etat_maximilien=None, chercher=None) -> "pd.DataFrame":
    """Pipeline complet: collecte AOs récents -> extrait acheteurs -> enrichit chacun
    -> assemble en DataFrame avec COLONNES fixes, trié par priorité (CHAUD>TIEDE) puis nb_ao_semaine desc.
    """
    aos = collecter_aos_recents(jours, aujourd_hui, records_boamp, etat_maximilien)
    acheteurs = [enrichir(a, chercher) for a in extraire_acheteurs(aos)]
    df = pd.DataFrame(acheteurs)
    for c in COLONNES:
        if c not in df.columns:
            df[c] = "" if c != "nb_ao_semaine" else 0
    df = df[COLONNES]
    if not df.empty:
        df["_rang"] = df["priorite"].map({"CHAUD": 3, "TIEDE": 2, "TIÈDE": 2}).fillna(0)
        df = df.sort_values(["_rang", "nb_ao_semaine"], ascending=False).drop(columns="_rang").reset_index(drop=True)
    return df


def _aplatir_aos(aos) -> str:
    if not isinstance(aos, list):
        return str(aos or "")
    return " | ".join(f"{a.get('objet','')} ({a.get('date_publication','')}, {a.get('priorite','')})"
                      for a in aos)


def exporter(df, xlsx_path: Path, csv_path: Path) -> None:
    plat = df.copy()
    if "aos" in plat.columns:
        plat["aos"] = plat["aos"].map(_aplatir_aos)
    Path(xlsx_path).parent.mkdir(parents=True, exist_ok=True)
    plat.to_excel(xlsx_path, index=False)
    plat.to_csv(csv_path, index=False, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    df = construire()
    exporter(df, XLSX_DEFAUT, CSV_DEFAUT)
    pub = int((df["type"] == "public").sum()) if not df.empty else 0
    print(f"[ACHETEURS-SEMAINE] {len(df)} acheteur(s) — {pub} public(s), {len(df) - pub} prive-droit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
