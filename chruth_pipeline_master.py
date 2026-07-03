from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from ao_config import collecte_active
import prospect_messages as pm
import suivi_messages as sm
import perf_messages as perf
import export_messages as em


# Sortie en UTF-8 : on reaffiche la sortie des sous-process (qui peut contenir des
# caracteres non-ASCII) ; sur une console Windows cp1252 ca planterait sans ca.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
OUTPUT_DIR = BASE / "output"
LOG_DIR = BASE / "logs"


def latest_file(folder: Path, pattern: str) -> Path:
    files = sorted(folder.glob(pattern), key=lambda path: path.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"Aucun fichier {pattern} dans {folder}")
    return files[-1]


def latest_raw() -> Path:
    return latest_file(DATA_DIR, "raw_*.json")


def latest_excel() -> Path:
    fichiers = list(OUTPUT_DIR.glob("Base_Prospects_CHRUTH*.xlsm")) + \
               list(OUTPUT_DIR.glob("Base_Prospects_CHRUTH*.xlsx"))
    if not fichiers:
        raise FileNotFoundError(f"Aucun Base_Prospects_CHRUTH*.xls(m/x) dans {OUTPUT_DIR}")
    return max(fichiers, key=lambda p: p.stat().st_mtime)


def run_command(command: list[str], label: str) -> int:
    print(f"\n=== {label} ===")
    print("Commande :", " ".join(command))
    process = subprocess.Popen(
        command,
        cwd=BASE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="")
    code = process.wait()
    print("Code retour :", code)
    if code != 0:
        raise RuntimeError(f"Etape echouee : {label} (code {code})")
    return code


def run_script(script_name: str, label: str, *args: str) -> int:
    return run_command([sys.executable, str(BASE / script_name), *args], label)


def collect(scope: str = "test", departements: str = "69", regions: str = "", label: str = "notebook") -> int:
    args = ["--scope", scope, "--label", label, "--yes"]
    if scope == "departements":
        args.extend(["--departements", departements])
    if scope == "region":
        args.extend(["--regions", regions])
    return run_script("collect_api_entreprises.py", "Collecte API", *args)


def clean_classify() -> int:
    return run_script("clean_classify.py", "Nettoyage + classification")


def enrich_finess() -> int:
    return run_script("enrich_finess.py", "Enrichissement FINESS")


def scoring_export() -> int:
    return run_script("scoring_export.py", "Scoring + export Excel")


def control_quality() -> pd.DataFrame:
    source = latest_excel()
    df = pd.read_excel(source, sheet_name="Prospects")

    def nb_vides(column: str) -> int:
        if column not in df.columns:
            return len(df)
        values = df[column].fillna("").astype(str).str.strip().str.lower()
        return int(values.isin(["", "nan", "none"]).sum())

    checks = [
        {"controle": "source_excel", "valeur": source.name, "alerte": "NON"},
        {"controle": "lignes_total", "valeur": len(df), "alerte": "NON"},
        {"controle": "siret_vides", "valeur": nb_vides("siret"), "alerte": "OUI" if nb_vides("siret") else "NON"},
        {"controle": "denomination_vides", "valeur": nb_vides("denomination"), "alerte": "OUI" if nb_vides("denomination") else "NON"},
        {"controle": "categorie_vides", "valeur": nb_vides("categorie_chruth"), "alerte": "OUI" if nb_vides("categorie_chruth") else "NON"},
        {"controle": "domaine_vides", "valeur": nb_vides("domaine_chruth"), "alerte": "OUI" if nb_vides("domaine_chruth") else "NON"},
        {"controle": "ville_vides", "valeur": nb_vides("libelle_commune"), "alerte": "OUI" if nb_vides("libelle_commune") else "NON"},
        {"controle": "adresse_vides", "valeur": nb_vides("adresse_complete"), "alerte": "OUI" if nb_vides("adresse_complete") else "NON"},
        {"controle": "priorite_vides", "valeur": nb_vides("priorite"), "alerte": "OUI" if nb_vides("priorite") else "NON"},
        {"controle": "doublons_siret", "valeur": int(df["siret"].duplicated().sum()), "alerte": "OUI" if df["siret"].duplicated().sum() else "NON"},
        {"controle": "villes_distinctes", "valeur": int(df["libelle_commune"].nunique()) if "libelle_commune" in df.columns else 0, "alerte": "NON"},
        {"controle": "societes_distinctes", "valeur": int(df["siren"].nunique()) if "siren" in df.columns else 0, "alerte": "NON"},
        {"controle": "score_min", "valeur": int(df["signal_besoin"].min()), "alerte": "NON"},
        {"controle": "score_max", "valeur": int(df["signal_besoin"].max()), "alerte": "NON"},
    ]
    result = pd.DataFrame(checks)
    path = OUTPUT_DIR / "CONTROLE_QUALITE_CHRUTH.csv"
    result.to_csv(path, index=False, encoding="utf-8-sig", sep=";")
    print(f"Controle qualite exporte : {path}")
    return result


def export_kpi() -> pd.DataFrame:
    source = latest_excel()
    df = pd.read_excel(source, sheet_name="Prospects")
    total = len(df)
    chaude = int((df["priorite"] == "CHAUDE").sum())
    tiede = int((df["priorite"] == "TIEDE").sum())
    froide = int((df["priorite"] == "FROIDE").sum())
    if "domaine_chruth" not in df.columns:
        categories = df["categorie_chruth"].fillna("").astype(str).str.upper()
        df["domaine_chruth"] = "PRIVE"
        df.loc[categories.str.startswith("PUB_"), "domaine_chruth"] = "PUBLIC"
        df.loc[categories.isin(["", "AUTRE", "NAN", "NONE"]), "domaine_chruth"] = "A_CLASSER"
    domaine = df["domaine_chruth"].astype(str).str.upper()
    secteur_public = int((domaine == "PUBLIC").sum())
    secteur_prive = int((domaine == "PRIVE").sum())
    a_classer = int((domaine == "A_CLASSER").sum())
    kpi = pd.DataFrame(
        [
            {"kpi": "Source Excel", "valeur": source.name},
            {"kpi": "Total prospects", "valeur": total},
            {"kpi": "Prospects CHAUDE", "valeur": chaude},
            {"kpi": "Prospects TIEDE", "valeur": tiede},
            {"kpi": "Prospects FROIDE", "valeur": froide},
            {"kpi": "Taux CHAUDE", "valeur": round(chaude / total, 4) if total else 0},
            {"kpi": "Score moyen", "valeur": round(float(df["signal_besoin"].mean()), 2)},
            {"kpi": "Domaine PUBLIC", "valeur": secteur_public},
            {"kpi": "Domaine PRIVE", "valeur": secteur_prive},
            {"kpi": "Domaine A_CLASSER", "valeur": a_classer},
            {"kpi": "Villes distinctes", "valeur": int(df["libelle_commune"].nunique()) if "libelle_commune" in df.columns else 0},
            {"kpi": "Societes distinctes", "valeur": int(df["siren"].nunique()) if "siren" in df.columns else 0},
        ]
    )
    path = OUTPUT_DIR / "KPI_CHRUTH.csv"
    kpi.to_csv(path, index=False, encoding="utf-8-sig", sep=";")
    print(f"KPI exportes : {path}")
    return kpi


def create_crm() -> pd.DataFrame:
    source = latest_excel()
    df = pd.read_excel(source, sheet_name="CHAUDE")
    tracking_columns = {
        "statut_contact": "A contacter",
        "responsable": "",
        "canal": "",
        "date_contact": "",
        "date_relance": "",
        "reponse": "",
        "rdv_obtenu": "",
        "client_signe": "",
        "montant_estime": "",
        "commentaire": "",
    }
    for column, default in tracking_columns.items():
        if column not in df.columns:
            df[column] = default
    path = OUTPUT_DIR / "CRM_CHRUTH_CHAUDE.xlsx"
    df.to_excel(path, index=False)
    print(f"CRM cree : {path}")
    return df


def _segment_angle(category: object) -> str:
    value = str(category or "")
    if value.startswith("PUB_"):
        return "structurer vos donnees et prioriser vos actions de suivi"
    if "SANTE" in value:
        return "simplifier le suivi de vos contacts et gagner du temps"
    if "IMMO" in value:
        return "prioriser vos prospects et mieux suivre votre portefeuille"
    if "COMMERCE" in value or "RESTAURANT" in value:
        return "ameliorer votre suivi client et votre visibilite locale"
    return "automatiser une partie de votre prospection et de votre analyse commerciale"


def _email_message(row: pd.Series) -> str:
    name = row.get("denomination") or "votre structure"
    city = row.get("libelle_commune") or ""
    angle = _segment_angle(row.get("categorie_chruth"))
    return (
        "Bonjour,\n\n"
        f"Je vous contacte pour CHRUTH. Nous identifions des structures comme {name} "
        f"a {city} qui pourraient {angle}.\n\n"
        "L'objectif est simple : utiliser les donnees pour mieux cibler les priorites "
        "et gagner du temps dans le suivi commercial.\n\n"
        "Seriez-vous disponible pour un court echange de 15 minutes ?\n\n"
        "Cordialement,"
    )


def generate_messages(source_df: pd.DataFrame | None = None, suivi_path=None,
                      output_path=None, client=None,
                      utiliser_ia: bool = False) -> pd.DataFrame:
    if source_df is None:
        source = latest_excel()
        df = pd.read_excel(source, sheet_name="CHAUDE")
    else:
        df = source_df.copy()
    df["siret"] = df["siret"].astype(str).map(sm._norm_siret)
    suivi_path = suivi_path or sm.SUIVI_PATH
    output_path = output_path or (OUTPUT_DIR / "Prospects_CHAUDS_messages.xlsx")
    seuil = perf.SEUIL_DEFAUT

    # 1) perf sur l'historique deja saisi -> recommandations
    df_perf_avant = perf.calculer_perf(sm.charger(suivi_path))
    recommandations = perf.variante_recommandee(df_perf_avant, seuil=seuil)

    # 2) synchroniser le suivi (assigne A/B, preserve les statuts saisis)
    df_suivi = sm.synchroniser(df, recommandations=recommandations, path=suivi_path)

    # 3) generer les 2 variantes par segment
    segments = pm.segments_activables(df)
    variantes = pm.generer_variantes(segments, client=client, utiliser_ia=utiliser_ia)

    # 4) rendre email + script selon la variante assignee a chaque prospect
    var_par_siret = dict(zip(df_suivi["siret"], df_suivi["variante"]))
    emails, scripts, col_var, col_tpl = [], [], [], []
    for _, row in df.iterrows():
        var = var_par_siret.get(str(row["siret"]), "A")
        cle = pm.cle_var(row["categorie_chruth"], row["priorite"], var)
        tpl = variantes.get(cle)
        if tpl is None:
            tpl = pm.template_par_defaut(row["categorie_chruth"], row["priorite"], var)
        emails.append(pm.rendre(tpl["email"], row))
        scripts.append(pm.rendre(tpl["script"], row))
        col_var.append(var)
        col_tpl.append(cle)
    df["variante"] = col_var
    df["template_id"] = col_tpl
    df["message_email"] = emails
    df["message_script"] = scripts

    # 5) perf apres synchro (affichage) + ecriture des 3 feuilles
    # Guard NaN: neutralise les NaN dans le df messages avant ecriture xlsx
    # (rendre() gere deja les NaN pour les placeholders ; ici on protege
    # les colonnes brutes qui iraient dans la feuille Messages telles quelles)
    df_perf = perf.calculer_perf(df_suivi)
    df_messages_xlsx = df.fillna("")
    em.ecrire_classeur(df_messages_xlsx, df_suivi, df_perf, recommandations,
                       path=output_path, seuil=seuil)
    print(f"Messages generes : {output_path}")
    return df


def export_excel_sheets_to_csv(
    output_folder: Path,
    sheets: Iterable[str] = (
        "Prospects", "Top_Cibles", "CHAUDE", "Domaine_PUBLIC", "Domaine_PRIVE",
        "MAPA_Prioritaires", "Villes", "Adresses", "Societes", "Veille", "Stats",
    ),
    sep: str = ";",
) -> list[Path]:
    source = latest_excel()
    output_folder.mkdir(parents=True, exist_ok=True)
    generated = []
    for sheet in sheets:
        df = pd.read_excel(source, sheet_name=sheet)
        path = output_folder / f"{sheet}.csv"
        df.to_csv(path, index=False, encoding="utf-8-sig", sep=sep)
        generated.append(path)
        print(f"Export CSV : {path}")
    return generated


def export_notion() -> list[Path]:
    folder = OUTPUT_DIR / "notion_import_chruth"
    files = export_excel_sheets_to_csv(
        folder,
        sheets=("CHAUDE", "Top_Cibles", "Domaine_PUBLIC", "Domaine_PRIVE", "MAPA_Prioritaires", "Villes", "Societes", "Veille", "Stats"),
    )
    readme = folder / "IMPORT_NOTION.md"
    readme.write_text(
        "# Import Notion CHRUTH\n\n"
        "Dans Notion : Settings > Import > CSV.\n\n"
        "Ordre conseille :\n"
        "1. CHAUDE.csv\n"
        "2. Top_Cibles.csv\n"
        "3. Domaine_PUBLIC.csv\n"
        "4. Domaine_PRIVE.csv\n"
        "5. MAPA_Prioritaires.csv\n"
        "6. Villes.csv\n"
        "7. Societes.csv\n"
        "8. Veille.csv\n"
        "9. Stats.csv\n",
        encoding="utf-8",
    )
    files.append(readme)
    print(f"Notice Notion : {readme}")
    return files


def export_powerbi() -> list[Path]:
    folder = OUTPUT_DIR / "powerbi_sources"
    files = export_excel_sheets_to_csv(folder)
    for name in ["KPI_CHRUTH.csv", "CONTROLE_QUALITE_CHRUTH.csv"]:
        source = OUTPUT_DIR / name
        if source.exists():
            target = folder / name
            target.write_bytes(source.read_bytes())
            files.append(target)
            print(f"Copie Power BI : {target}")
    return files


def export_generic_csv() -> list[Path]:
    return export_excel_sheets_to_csv(OUTPUT_DIR / "exports_csv")


def carte() -> str:
    import prospects_carte
    df = prospects_carte.charger_prospects()
    centre = prospects_carte.geocode_adresse(prospects_carte.ADRESSE_CHRUTH)
    df = prospects_carte.ajouter_distance(df, centre)
    out = prospects_carte.build_carte(df, centre)
    print(f"Carte prospects generee : {out}")
    return str(out)


def full_update(
    scope: str = "test",
    departements: str = "69",
    regions: str = "",
    skip_collect: bool = True,
    label: str = "master",
) -> dict:
    LOG_DIR.mkdir(exist_ok=True)
    started = datetime.now()
    print("=" * 70)
    print("CHRUTH - Pipeline integree")
    print(f"Scope        : {scope}")
    print(f"Departements : {departements if scope == 'departements' else '-'}")
    print(f"Regions      : {regions if scope == 'region' else '-'}")
    print(f"Skip collect : {skip_collect}")
    print("=" * 70)

    collecte_ok = collecte_active()
    if not skip_collect and collecte_ok:
        collect(scope=scope, departements=departements, regions=regions, label=label)
    elif not skip_collect:
        print("[COLLECTE] Desactivee depuis Excel -> API Entreprises ignoree, retraitement local.")
    clean_classify()
    enrich_finess()
    scoring_export()
    carte()
    quality = control_quality()
    kpi = export_kpi()
    crm = create_crm()
    messages = generate_messages()
    notion_files = export_notion()
    powerbi_files = export_powerbi()

    return {
        "started": started,
        "ended": datetime.now(),
        "latest_excel": latest_excel(),
        "quality": quality,
        "kpi": kpi,
        "crm_rows": len(crm),
        "messages_rows": len(messages),
        "notion_files": notion_files,
        "powerbi_files": powerbi_files,
    }


def load_sheet(sheet_name: str = "Prospects") -> pd.DataFrame:
    source = latest_excel()
    df = pd.read_excel(source, sheet_name=sheet_name)
    print(f"Charge : {source.name} / {sheet_name} ({len(df)} lignes)")
    return df


def inventory() -> pd.DataFrame:
    rows = []
    for zone, folder in {
        "data": DATA_DIR,
        "output": OUTPUT_DIR,
        "logs": LOG_DIR,
        "root": BASE,
    }.items():
        if not folder.exists():
            continue
        for path in folder.glob("*"):
            if path.is_file():
                rows.append(
                    {
                        "zone": zone,
                        "fichier": path.name,
                        "taille_mo": round(path.stat().st_size / 1024 / 1024, 2),
                        "modifie": datetime.fromtimestamp(path.stat().st_mtime),
                        "chemin": str(path),
                    }
                )
    return pd.DataFrame(rows).sort_values(["zone", "modifie"], ascending=[True, False])


if __name__ == "__main__":
    import argparse

    _parser = argparse.ArgumentParser(description="Pipeline integre CHRUTH prospects (+ carte).")
    _parser.add_argument("--collect", action="store_true",
                         help="Recollecter de nouvelles societes via l'API (sinon retraite l'existant).")
    _parser.add_argument("--scope", choices=["test", "france", "departements", "region"], default="france",
                         help="Perimetre de collecte si --collect (defaut: france).")
    _parser.add_argument("--departements", default="69",
                         help="Liste de departements si --scope departements (ex: 69,75).")
    _parser.add_argument("--regions", default="",
                         help="Liste de regions si --scope region (ex: \"Île-de-France,Bretagne\").")
    _args = _parser.parse_args()
    full_update(scope=_args.scope, departements=_args.departements, regions=_args.regions,
                skip_collect=not _args.collect)
