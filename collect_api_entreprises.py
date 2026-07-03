import argparse
import requests
import time
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from config import (
    CODES_NAF, API_BASE_URL, API_PER_PAGE, REQUEST_DELAY_SECONDS,
    REQUEST_USER_AGENT, DEPARTEMENTS_TEST, DEPARTEMENTS_FRANCE,
    REQUEST_MAX_RETRIES, REQUEST_RETRY_BACKOFF_SECONDS,
    departements_des_regions,
)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": REQUEST_USER_AGENT})


def fetch_page(naf: str, departement: str, page: int) -> dict | None:
    params = {
        "activite_principale": naf,
        "departement": departement,
        "page": page,
        "per_page": API_PER_PAGE,
        "etat_administratif": "A",
    }
    for attempt in range(1, REQUEST_MAX_RETRIES + 1):
        try:
            resp = SESSION.get(API_BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            if attempt >= REQUEST_MAX_RETRIES:
                print(f"  [ERREUR] {naf} - {departement} p.{page} : {e}")
                return None
            wait = REQUEST_RETRY_BACKOFF_SECONDS * attempt
            print(
                f"  [RETRY {attempt}/{REQUEST_MAX_RETRIES}] "
                f"{naf} - {departement} p.{page} dans {wait:.1f}s : {e}"
            )
            time.sleep(wait)


def best_effectif(et: dict, entreprise: dict) -> str:
    """L'effectif au niveau etablissement vaut souvent 'NN' (non renseigne).
    La vraie valeur est au niveau entreprise (unite legale). On prend le code
    etablissement seulement s'il est reellement renseigne, sinon l'entreprise."""
    code_et = str(et.get("tranche_effectif_salarie") or "").strip()
    if code_et and code_et != "NN":
        return code_et
    code_ent = str(entreprise.get("tranche_effectif_salarie") or "").strip()
    return code_ent or code_et or "NN"


def dept_from_cp(code_postal: str) -> str:
    cp = str(code_postal or "").strip()
    if len(cp) >= 2 and cp[:2].isdigit():
        return cp[:3] if cp[:2] == "97" else cp[:2]
    return ""


def first_enseigne(et: dict) -> str:
    ens = et.get("liste_enseignes") or []
    if isinstance(ens, list) and ens:
        return str(ens[0])
    return et.get("nom_commercial") or ""


def extract_etablissements(entreprise: dict, naf: str, dept: str) -> list[dict]:
    """Extrait tous les etablissements (siege + secondaires) d'une entreprise."""
    results = []
    siege = entreprise.get("siege") or {}
    etablissements = entreprise.get("matching_etablissements") or []

    all_ets = []
    if siege:
        all_ets.append(siege)
    for et in etablissements:
        if et.get("siret") != siege.get("siret"):
            all_ets.append(et)

    # nom_complet est le champ le plus fiable (renseigne pour societes ET
    # associations) ; nom_raison_sociale est nul pour les personnes physiques.
    denom = (entreprise.get("nom_complet")
             or entreprise.get("nom_raison_sociale") or "")

    for et in all_ets:
        code_postal = et.get("code_postal") or ""
        results.append({
            "siret": et.get("siret"),
            "siren": entreprise.get("siren"),
            "denomination": denom or first_enseigne(et),
            "enseigne": first_enseigne(et),
            "naf_code": et.get("activite_principale") or naf,
            "naf_libelle": "",
            "adresse": et.get("adresse") or et.get("geo_adresse") or "",
            "numero_voie": et.get("numero_voie") or "",
            "type_voie": et.get("type_voie") or "",
            "libelle_voie": et.get("libelle_voie") or "",
            "complement_adresse": et.get("complement_adresse") or "",
            "code_postal": code_postal,
            "libelle_commune": et.get("libelle_commune") or "",
            "code_departement": et.get("departement") or dept_from_cp(code_postal) or dept,
            "region": et.get("region") or "",
            "latitude": et.get("latitude"),
            "longitude": et.get("longitude"),
            "tranche_effectif_salarie": best_effectif(et, entreprise),
            "caractere_employeur": et.get("caractere_employeur", ""),
            "date_creation": et.get("date_creation") or entreprise.get("date_creation") or "",
            "etat_administratif": et.get("etat_administratif") or "A",
            "est_siege": et.get("est_siege", False),
            "nombre_etablissements": entreprise.get("nombre_etablissements"),
            "nature_juridique": entreprise.get("nature_juridique") or "",
            "categorie_entreprise": entreprise.get("categorie_entreprise") or "",
            "liste_finess": json.dumps(et.get("liste_finess") or [], ensure_ascii=False),
            "liste_uai": json.dumps(et.get("liste_uai") or [], ensure_ascii=False),
            "sigle": entreprise.get("sigle") or "",
            "_naf_recherche": naf,
            "_timestamp": datetime.now().isoformat(),
        })
    return results


def collect_all(departements: list[str]) -> list[dict]:
    all_results = []
    total_naf = len(CODES_NAF)
    total_dept = len(departements)
    grand_total = total_naf * total_dept
    done = 0
    total_ets = 0

    print("=== COLLECTE API RECHERCHE ENTREPRISES ===")
    print(f"  Endpoint : {API_BASE_URL}")
    print(f"  NAF      : {total_naf}")
    print(f"  Dept     : {total_dept}")
    print(f"  Total    : {grand_total} combinaisons")
    print(f"  Delai    : {REQUEST_DELAY_SECONDS}s")
    print("=" * 50)

    for naf_code in CODES_NAF:
        naf_label = CODES_NAF[naf_code]["label"]
        for dept in departements:
            done += 1
            page = 1
            naf_ets = 0
            while True:
                data = fetch_page(naf_code, dept, page)
                if data is None:
                    break

                entreprises = data.get("results") or []
                if not entreprises:
                    break

                for ent in entreprises:
                    ets = extract_etablissements(ent, naf_code, dept)
                    all_results.extend(ets)
                    naf_ets += len(ets)

                total_pages = data.get("total_pages", 1)
                total_results = data.get("total_results", 0)

                if page % 5 == 1 or page == total_pages:
                    print(f"  [{done}/{grand_total}] {naf_code} {dept} p.{page}/{total_pages} "
                          f"({total_results} total, {naf_ets} ets collectes)")

                if page >= total_pages:
                    break

                page += 1
                time.sleep(REQUEST_DELAY_SECONDS)

            if naf_ets > 0:
                print(f"  [{done}/{grand_total}] {naf_code} {dept} -> {naf_ets} etablissements [OK]")
            total_ets += naf_ets

    print(f"\n=== COLLECTE TERMINEE ===")
    print(f"  Total etablissements collectes : {total_ets}")
    return all_results


def save_raw(results: list[dict], label: str = "collecte"):
    filename = f"raw_{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = DATA_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  Sauvegarde : {filepath}")
    return filepath


def parse_departements(value: str) -> list[str]:
    return [dept.strip().upper() for dept in value.split(",") if dept.strip()]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collecte les etablissements cibles CHRUTH depuis l'API Recherche Entreprises."
    )
    parser.add_argument(
        "--scope",
        choices=["test", "france", "departements", "region"],
        default=None,
        help="Perimetre : test=DEPARTEMENTS_TEST, france=tout, departements=liste custom, region=une ou plusieurs regions.",
    )
    parser.add_argument(
        "--departements",
        default="",
        help="Liste de departements separes par des virgules, ex: 69,75,92. Utilise avec --scope departements.",
    )
    parser.add_argument(
        "--regions",
        default="",
        help="Liste de regions separees par des virgules, ex: \"Île-de-France,Bretagne\". Utilise avec --scope region.",
    )
    parser.add_argument(
        "--label",
        default="collecte",
        help="Libelle ajoute au nom du fichier raw genere.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Lance sans confirmation interactive. Obligatoire pour une tache planifiee.",
    )
    return parser


def parse_regions(value: str) -> list[str]:
    return [region.strip() for region in value.split(",") if region.strip()]


def select_departements_from_args(args: argparse.Namespace) -> list[str]:
    if args.scope == "france":
        return DEPARTEMENTS_FRANCE
    if args.scope == "departements":
        departements = parse_departements(args.departements)
        if not departements:
            raise ValueError("--departements doit contenir au moins un departement, ex: --departements 69,75")
        return departements
    if args.scope == "region":
        regions = parse_regions(args.regions)
        if not regions:
            raise ValueError("--regions doit contenir au moins une region, ex: --regions \"Île-de-France\"")
        return departements_des_regions(regions)
    return DEPARTEMENTS_TEST


def main(argv: list[str] | None = None):
    argv = sys.argv[1:] if argv is None else argv

    if argv:
        args = build_arg_parser().parse_args(argv)
        departements = select_departements_from_args(args)
        if not args.yes:
            raise SystemExit("Ajoute --yes pour confirmer la collecte non interactive.")

        print(f"Mode CLI : {args.scope or 'test'}")
        print(f"Cibles : {len(departements)} departement(s)")
        debut = datetime.now()
        results = collect_all(departements)
        duree = (datetime.now() - debut).total_seconds()
        filepath = save_raw(results, label=args.label)

        print(f"\n=== RESULTAT ===")
        print(f"  Duree      : {duree:.0f}s ({duree/60:.1f}min)")
        print(f"  Total      : {len(results)} etablissements")
        print(f"  Fichier    : {filepath}")
        print(f"  Prochaine  : python clean_classify.py")
        return

    mode = input("Mode [1=TEST(69) / 2=FRANCE] : ").strip()
    departements = DEPARTEMENTS_TEST if mode != "2" else DEPARTEMENTS_FRANCE

    print(f"Cibles : {len(departements)} departement(s)")
    confirm = input("Lancer la collecte ? (O/N) : ").strip().upper()
    if confirm != "O":
        print("Annule.")
        return

    debut = datetime.now()
    results = collect_all(departements)
    duree = (datetime.now() - debut).total_seconds()
    filepath = save_raw(results)

    print(f"\n=== RESULTAT ===")
    print(f"  Duree      : {duree:.0f}s ({duree/60:.1f}min)")
    print(f"  Total      : {len(results)} etablissements")
    print(f"  Fichier    : {filepath}")
    print(f"  Prochaine  : python clean_classify.py")


if __name__ == "__main__":
    main()
