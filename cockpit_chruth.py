"""Cockpit web CHRUTH — interface unique no-code.

Entree principale : COCKPIT_CHRUTH.bat (double-clic).

Lance un petit serveur local (aucune dependance externe, stdlib uniquement)
et ouvre le navigateur sur http://127.0.0.1:8770 :
- statut des 4 missions de la fiche de poste (+ extension AO) ;
- generation des livrables (pipeline unique, mise a jour AO) ;
- messages prospects par segment et messages AO ;
- envoi email Gmail ;
- acces a tous les livrables, guides, notebooks et logs.

Le cockpit reutilise les modules du dossier (CHRUTH_PIPELINE_UNIQUE.py,
prospect_messages.py, ao_messages.py, chruth_email.py...). Il ne remplace rien.
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
PACK_DIR = ROOT.parent / "CHRUTH_LIVRAISON_NOTEBOOK"
PORT_DEFAUT = 8770

sys.path.insert(0, str(ROOT))



def taille_lisible(octets: int) -> str:
    if octets >= 1_000_000:
        return f"{octets / 1_000_000:.1f} Mo"
    if octets >= 1_000:
        return f"{octets / 1_000:.0f} Ko"
    return f"{octets} o"


def duree_lisible(secondes: float) -> str:
    secondes = max(0, int(secondes))
    minutes, secs = divmod(secondes, 60)
    heures, minutes = divmod(minutes, 60)
    if heures:
        return f"{heures}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def fichiers_modifies_depuis(started_at: float | None) -> list[dict]:
    if not started_at or not OUTPUT.exists():
        return []
    cutoff = started_at - 1.0
    fichiers: list[dict] = []
    for path in OUTPUT.rglob("*"):
        if not path.is_file() or path.name.startswith("~$"):
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_mtime < cutoff:
            continue
        elapsed = max(0.0, stat.st_mtime - started_at)
        fichiers.append({
            "chemin": path.relative_to(ROOT).as_posix(),
            "temps": duree_lisible(elapsed),
            "secondes": round(elapsed, 1),
            "date": datetime.fromtimestamp(stat.st_mtime).strftime("%H:%M:%S"),
            "taille": taille_lisible(stat.st_size),
        })
    fichiers.sort(key=lambda row: row["secondes"])
    return fichiers[-120:]


# --------------------------------------------------------------------------- #
# Referentiel : missions de la fiche de poste et livrables associes
# --------------------------------------------------------------------------- #
MISSIONS = [
    {
        "titre": "Mission 1 — Data Foundation",
        "objectif": "Creer un actif data reutilisable (base prospects B2B).",
        "fichiers": [
            "output/Base_Prospects_CHRUTH.xlsm",
            "output/prospects_nettoyes.csv",
            "output/prospects_enrichis.csv",
            "output/Carte_Prospects_CHRUTH.html",
        ],
    },
    {
        "titre": "Mission 2 — Segmentation & scoring",
        "objectif": "Ne plus prospecter a l'aveugle (segments, scoring, zones).",
        "fichiers": [
            "output/KPI_CHRUTH.csv",
            "output/CONTROLE_QUALITE_CHRUTH.csv",
            "output/powerbi_sources/Top_Cibles.csv",
            "output/powerbi_sources/Villes.csv",
        ],
    },
    {
        "titre": "Mission 3 — AI-Driven Sales",
        "objectif": "Messages personnalises par segment, variantes A/B, suivi de performance.",
        "fichiers": [
            "output/Prospects_CHAUDS_messages.xlsx",
            "output/segments_messages.json",
            "prompts/PROMPTS_CHRUTH.md",
            "suivi/suivi_envois.csv",
        ],
    },
    {
        "titre": "Mission 4 — Data Insights (CRM & rentabilite)",
        "objectif": "Piloter l'activite avec des donnees (CRM, rentabilite, previsions).",
        "fichiers": [
            "output/CRM_CHRUTH_CHAUDE.xlsx",
            "output/Modele_Financier_CHRUTH.xlsx",
            "output/notion_import_chruth/IMPORT_NOTION.md",
        ],
    },
    {
        "titre": "Extension — Appels d'offres publics",
        "objectif": "Detecter les marches publics pertinents (BOAMP), scorer, alerter, rediger.",
        "fichiers": [
            "output/AO_CHRUTH.xlsm",
            "data/ao_chruth.sqlite",
            "config_chruth/fiche_chruth.md",
        ],
    },
]

# Livrables et documents ouvrables depuis l'onglet Livrables (cle -> chemin).
LIVRABLES = {
    # --- Livrables principaux
    "cockpit_ao": ("Cockpit AO (Excel)", OUTPUT / "AO_CHRUTH.xlsm", "principal"),
    "base_prospects": ("Base prospects (Excel)", OUTPUT / "Base_Prospects_CHRUTH.xlsm", "principal"),
    "carte": ("Carte interactive", OUTPUT / "Carte_Prospects_CHRUTH.html", "principal"),
    "crm": ("CRM prospects chauds", OUTPUT / "CRM_CHRUTH_CHAUDE.xlsx", "principal"),
    "messages_xlsx": ("Messages prospects (Excel)", OUTPUT / "Prospects_CHAUDS_messages.xlsx", "principal"),
    "finance": ("Modele financier", OUTPUT / "Modele_Financier_CHRUTH.xlsx", "principal"),
    # --- Exports
    "powerbi": ("Sources Power BI", OUTPUT / "powerbi_sources", "exports"),
    "notion": ("Import Notion (CSV)", OUTPUT / "notion_import_chruth", "exports"),
    "kpi": ("KPI (CSV)", OUTPUT / "KPI_CHRUTH.csv", "exports"),
    "qualite": ("Controle qualite (CSV)", OUTPUT / "CONTROLE_QUALITE_CHRUTH.csv", "exports"),
    "manifest": ("Manifest JSON", OUTPUT / "MANIFEST_CHRUTH.json", "exports"),
    "dossier_output": ("Dossier output complet", OUTPUT, "exports"),
    "pack": ("Dossier portable (pack)", PACK_DIR, "exports"),
    # --- Messages
    "msg_prospect_txt": ("Dernier message prospect", OUTPUT / "_message_prospect_segment.txt", "messages"),
    "msg_ao_txt": ("Dernier message AO", OUTPUT / "_message_ao.txt", "messages"),
    "messages_ao_md": ("Messages AO rediges (.md)", OUTPUT / "messages_ao", "messages"),
    "suivi_envois": ("Suivi des envois (CSV)", ROOT / "suivi" / "suivi_envois.csv", "messages"),
    "fiche_chruth": ("Fiche CHRUTH (a remplir)", ROOT / "config_chruth" / "fiche_chruth.md", "messages"),
    "prompts": ("Prompts IA", ROOT / "prompts" / "PROMPTS_CHRUTH.md", "messages"),
    # --- Guides & docs
    "guide_html": ("Guide d'utilisation (HTML)", ROOT / "GUIDE_UTILISATION_CHRUTH.html", "docs"),
    "guide_pdf": ("Guide d'utilisation (PDF)", ROOT / "GUIDE_UTILISATION_CHRUTH.pdf", "docs"),
    "guide_demarrage": ("Guide de demarrage", ROOT / "README_DEMARRAGE_NO_CODE.md", "docs"),
    "guide_livraison": ("Notice de livraison", ROOT / "README_LIVRAISON.md", "docs"),
    "readme": ("README projet", ROOT / "README.md", "docs"),
    "guide_ao_html": ("Guide AO (HTML)", ROOT / "GUIDE_AO_CHRUTH.html", "docs"),
    "missions_doc": ("Missions vs fiche de poste", ROOT / "docs" / "MISSION_CHRUTH.md", "docs"),
    "audit": ("Rapport d'audit objectifs", ROOT / "docs" / "RAPPORT_AUDIT_FICHE_POSTE.md", "docs"),
    "fiche_poste": ("Fiche de poste (PDF)", ROOT / "docs" / "source" / "Fiche de poste CHRUTH.pdf", "docs"),
    "docs_dir": ("Docs techniques", ROOT / "docs", "docs"),
    # --- Notebooks & avance
    "nb_pipeline": ("Notebook pipeline unique", ROOT / "CHRUTH_Pipeline_Unique.ipynb", "avance"),
    "nb_msg_ao": ("Notebook messages AO", ROOT / "CHRUTH_Messages_AO.ipynb", "avance"),
    "nb_msg_prospects": ("Notebook messages prospects", ROOT / "CHRUTH_Messages_Prospects.ipynb", "avance"),
    "nb_alertes": ("Notebook alertes AO", ROOT / "CHRUTH_Alertes.ipynb", "avance"),
    "nb_moteur": ("Notebook moteur IA", ROOT / "CHRUTH_Moteur_IA.ipynb", "avance"),
    "nb_prompts": ("Notebook prompt playground", ROOT / "CHRUTH_Prompt_Playground.ipynb", "avance"),
    "dce": ("DCE telecharges (PDF)", ROOT / "dce_auto", "avance"),
    "logs": ("Logs des pipelines", ROOT / "logs", "avance"),
    "interface_tk": ("Ancienne interface Tkinter", ROOT / "OUVRIR_MOI_CHRUTH.bat", "avance"),
    "installer": ("Installer / automatiser Windows", ROOT / "INSTALLER.bat", "avance"),
    "bat_pipeline": ("Lancer pipeline (BAT)", ROOT / "LANCER_PIPELINE_CHRUTH.bat", "avance"),
    "bat_update_ao": ("Lancer mise a jour AO (BAT)", ROOT / "LANCER_UPDATE_AO_CHRUTH.bat", "avance"),
}


# --------------------------------------------------------------------------- #
# Gestion d'un job (une seule action lourde a la fois)
# --------------------------------------------------------------------------- #
class Job:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.lines: list[str] = []
        self.running = False
        self.label = ""
        self.code: int | None = None
        self.started_at: float | None = None
        self.finished_at: float | None = None

    def start(self, cmd: list[str], label: str) -> bool:
        with self.lock:
            if self.running:
                return False
            self.running = True
            self.label = label
            self.code = None
            self.started_at = time.time()
            self.finished_at = None
            self.lines = [
                "$ " + " ".join(cmd),
                "",
                f"Debut : {datetime.now().strftime('%H:%M:%S')}",
                "",
            ]
        threading.Thread(target=self._run, args=(cmd,), daemon=True).start()
        return True

    def _run(self, cmd: list[str]) -> None:
        code = -1
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                with self.lock:
                    self.lines.append(line.rstrip())
            code = proc.wait()
        except Exception as exc:  # noqa: BLE001
            with self.lock:
                self.lines.append(f"ERREUR : {exc}")
        finally:
            with self.lock:
                self.code = code
                self.running = False
                self.finished_at = time.time()
                self.lines.append("")
                self.lines.append(f"Fin : {datetime.now().strftime('%H:%M:%S')}")
                self.lines.append(f"--- Termine (code {code}) ---")

    def state(self) -> dict:
        with self.lock:
            started_at = self.started_at
            end_at = time.time() if self.running else self.finished_at
            elapsed = duree_lisible((end_at - started_at) if started_at and end_at else 0)
            return {
                "running": self.running,
                "label": self.label,
                "code": self.code,
                "started_at": datetime.fromtimestamp(started_at).strftime("%H:%M:%S") if started_at else "",
                "elapsed": elapsed,
                "fichiers": fichiers_modifies_depuis(started_at),
                "log": "\n".join(self.lines[-500:]),
            }

JOB = Job()


# --------------------------------------------------------------------------- #
# Actions metier (reutilisent les modules du projet)
# --------------------------------------------------------------------------- #
def commande_pipeline(opts: dict) -> list[str]:
    cmd = [sys.executable, "CHRUTH_PIPELINE_UNIQUE.py"]
    if opts.get("collect_ao"):
        cmd.append("--collect-ao")
    if opts.get("collect_prospects"):
        cmd.extend(["--collect-prospects", "--scope", "france"])
    if opts.get("messages_ia"):
        cmd.append("--generer-messages")
    if opts.get("pack"):
        cmd.extend(["--pack", "--package-dir", str(PACK_DIR)])
    return cmd


def info_fichier(rel: str) -> dict:
    p = ROOT / rel
    if not p.exists():
        return {"chemin": rel, "present": False, "date": "", "taille": ""}
    try:
        stat = p.stat()
        date = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M")
        octets = stat.st_size
        if p.is_dir():
            taille = f"{sum(1 for _ in p.iterdir())} fichiers"
        else:
            taille = taille_lisible(octets)
    except OSError:
        date, taille = "", ""
    return {"chemin": rel, "present": True, "date": date, "taille": taille}


def statut_missions() -> list[dict]:
    result = []
    for mission in MISSIONS:
        fichiers = [info_fichier(rel) for rel in mission["fichiers"]]
        result.append(
            {
                "titre": mission["titre"],
                "objectif": mission["objectif"],
                "fichiers": fichiers,
                "ok": all(f["present"] for f in fichiers),
            }
        )
    return result


def statut_general() -> dict:
    fiche = ROOT / "config_chruth" / "fiche_chruth.md"
    fiche_remplie = False
    if fiche.exists():
        contenu = fiche.read_text(encoding="utf-8", errors="replace")
        utiles = [
            l.strip()
            for l in contenu.splitlines()
            if l.strip() and not l.strip().startswith(("#", "<!--"))
        ]
        fiche_remplie = len(utiles) > 0
    env = ROOT / ".env"
    cle_ia = False
    if env.exists():
        for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith(("ANTHROPIC_API_KEY=", "MISTRAL_API_KEY=", "GROQ_API_KEY=", "GEMINI_API_KEY=")):
                if line.split("=", 1)[1].strip():
                    cle_ia = True
    manifest = {}
    mpath = OUTPUT / "MANIFEST_CHRUTH.json"
    if mpath.exists():
        try:
            manifest = json.loads(mpath.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            manifest = {}
    livrables = []
    for key, (label, path, categorie) in LIVRABLES.items():
        livrables.append(
            {
                "cle": key,
                "label": label,
                "categorie": categorie,
                "present": path.exists(),
            }
        )
    return {
        "missions": statut_missions(),
        "fiche_chruth_remplie": fiche_remplie,
        "cle_ia_configuree": cle_ia,
        "derniere_generation": manifest.get("generated_at", ""),
        "livrables": livrables,
        "collecte_active": (ROOT / "collecte_active.flag").exists(),
        "notifications_actives": notifications_actives_status(),
    }


def lister_segments() -> dict:
    import pandas as pd

    path = OUTPUT / "powerbi_sources" / "Prospects.csv"
    if not path.exists():
        path = OUTPUT / "prospects_enrichis.csv"
    if not path.exists():
        raise FileNotFoundError("Aucune source prospects dans output/. Lance d'abord la generation.")
    try:
        df = pd.read_csv(path, dtype=str, sep=";").fillna("")
        if len(df.columns) <= 1:
            df = pd.read_csv(path, dtype=str).fillna("")
    except Exception:  # noqa: BLE001
        df = pd.read_csv(path, dtype=str).fillna("")
    if "priorite" not in df.columns or "categorie_chruth" not in df.columns:
        raise ValueError("Source prospects incomplete (priorite / categorie_chruth manquantes).")
    work = df[df["priorite"].astype(str).str.upper().isin(["CHAUDE", "TIEDE"])]
    segments = {}
    for _, row in work.iterrows():
        cat = str(row.get("categorie_chruth") or "").strip()
        prio = str(row.get("priorite") or "").strip().upper()
        if not cat or not prio:
            continue
        key = f"{cat}|{prio}"
        if key not in segments:
            segments[key] = {
                "denomination": str(row.get("denomination") or ""),
                "ville": str(row.get("libelle_commune") or row.get("ville") or ""),
                "effectif": str(row.get("effectif_label") or row.get("effectif_nombre") or ""),
            }
    if not segments:
        raise ValueError("Aucun segment CHAUDE/TIEDE trouve.")
    return {"segments": [{"cle": k, **v} for k, v in sorted(segments.items())]}


def generer_message_prospect(data: dict) -> dict:
    import prospect_messages as pm

    key = str(data.get("segment") or "")
    if "|" not in key:
        raise ValueError("Segment invalide.")
    cat, prio = key.split("|", 1)
    templates = pm.generer_templates([(cat, prio)], refresh=True)
    tpl = templates[f"{cat}|{prio}"]
    row = {
        "denomination": str(data.get("denomination") or ""),
        "libelle_commune": str(data.get("ville") or ""),
        "effectif_label": str(data.get("effectif") or ""),
    }
    email = pm.rendre(tpl["email"], row)
    script = pm.rendre(tpl["script"], row)
    out = OUTPUT / "_message_prospect_segment.txt"
    out.parent.mkdir(exist_ok=True)
    out.write_text(
        f"SEGMENT : {cat} / {prio}\nSOURCE : {tpl.get('source', '')}\n\n"
        f"===== EMAIL =====\n{email}\n\n===== SCRIPT D'APPEL =====\n{script}\n",
        encoding="utf-8",
    )
    return {"email": email, "script": script, "source": tpl.get("source", "")}


def lister_aos() -> dict:
    from ao_config import AO_DB_PATH
    from ao_db import connect

    with connect(AO_DB_PATH) as conn:
        rows = conn.execute(
            "SELECT * FROM ao_records WHERE priorite IN ('CHAUD','TIEDE') "
            "ORDER BY CAST(score_chruth AS INTEGER) DESC LIMIT 200"
        ).fetchall()
    records = [dict(r) for r in rows]
    if not records:
        raise ValueError("Aucun AO CHAUD/TIEDE. Lance d'abord la mise a jour AO.")
    aos = []
    for rec in records:
        aos.append(
            {
                "id": str(rec.get("id_ao") or ""),
                "label": (
                    f"{rec.get('priorite','')} | {rec.get('score_chruth','')} | "
                    f"{str(rec.get('objet') or '')[:70]} | {str(rec.get('acheteur') or '')[:35]}"
                ),
                "details": {
                    k: str(rec.get(k) or "")
                    for k in (
                        "id_ao", "priorite", "score_chruth", "objet", "acheteur",
                        "ville", "date_limite", "budget_annuel_eur", "url_avis",
                    )
                },
            }
        )
    return {"aos": aos}


def generer_message_ao_api(data: dict) -> dict:
    import ao_messages
    from ao_config import AO_DB_PATH
    from ao_db import connect
    from outils.generer_message_ao import formater

    id_ao = str(data.get("id") or "")
    with connect(AO_DB_PATH) as conn:
        row = conn.execute("SELECT * FROM ao_records WHERE id_ao = ?", (id_ao,)).fetchone()
    if row is None:
        raise ValueError(f"AO introuvable : {id_ao}")
    rec = dict(row)
    msg = ao_messages.generer_message_ao(rec)
    out = OUTPUT / "_message_ao.txt"
    out.parent.mkdir(exist_ok=True)
    out.write_text(formater(rec, msg), encoding="utf-8")
    return {"email": msg.get("email", ""), "script": msg.get("script", "")}


def notifications_actives_status() -> bool:
    from ao_config import notifications_actives

    return bool(notifications_actives())


def normaliser_emails(value: object) -> list[str]:
    import chruth_email

    if isinstance(value, list):
        raw = value
    else:
        raw = re.split(r"[,;\n]+", str(value or ""))
    emails: list[str] = []
    for item in raw:
        email = str(item or "").strip()
        if not email:
            continue
        if not chruth_email.valid_email(email):
            raise ValueError(f"Adresse email invalide : {email}")
        emails.append(email)
    return list(dict.fromkeys(emails))


def sync_destinataires_secrets(emails: list[str]) -> None:
    from ao_config import ALERTE_SECRETS_FILE

    path = Path(ALERTE_SECRETS_FILE)
    data: dict[str, object] = {}
    if path.exists():
        raw = path.read_text(encoding="utf-8").strip()
        if raw:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                data = loaded
    data["destinataire"] = ", ".join(emails)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def config_email() -> dict:
    import chruth_email

    data = chruth_email.read_secrets()
    recipients = chruth_email.read_recipients()
    smtp_ok, smtp_msg = chruth_email.config_ready()
    prete = smtp_ok and bool(recipients)
    if not smtp_ok:
        message = smtp_msg
    elif not recipients:
        message = "Aucun destinataire configure."
    else:
        message = f"Configuration email prete ({len(recipients)} destinataire(s))."
    return {
        "expediteur": str(data.get("smtp_user") or ""),
        "mot_de_passe_defini": bool(data.get("smtp_password")),
        "destinataire": recipients[0] if recipients else "",
        "destinataires": "\n".join(recipients),
        "nb_destinataires": len(recipients),
        "notifications_actives": notifications_actives_status(),
        "prete": prete,
        "message": message,
    }


def enregistrer_email(data: dict) -> dict:
    import chruth_email

    current = chruth_email.read_secrets()
    password = str(data.get("mot_de_passe") or "").strip()
    if not password:
        password = str(current.get("smtp_password") or "")
    expediteur = str(data.get("expediteur") or "").strip()
    chruth_email.save_secrets(expediteur, password)

    raw_dest = data.get("destinataires")
    if raw_dest is None:
        raw_dest = data.get("destinataire")
    if str(raw_dest or "").strip():
        emails = chruth_email.save_recipients(str(raw_dest))
    else:
        emails = chruth_email.read_recipients()
    if emails:
        sync_destinataires_secrets(emails)
    return config_email()


def envoyer_email(data: dict) -> dict:
    import chruth_email

    raw_dest = data.get("destinataires")
    if raw_dest is None:
        raw_dest = data.get("destinataire")
    destinataires = normaliser_emails(raw_dest)
    sujet = str(data.get("sujet") or "CHRUTH - Message").strip()
    corps = str(data.get("corps") or "").strip()
    if not destinataires or not corps:
        raise ValueError("Destinataire et message obligatoires.")
    for destinataire in destinataires:
        chruth_email.send_email(destinataire, sujet, corps)
    return {"ok": True, "message": f"Email envoye a {len(destinataires)} destinataire(s)."}


def lire_fiche_chruth() -> dict:
    path = ROOT / "config_chruth" / "fiche_chruth.md"
    texte = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return {"chemin": str(path), "contenu": texte, "present": path.exists()}


def enregistrer_fiche_chruth(data: dict) -> dict:
    path = ROOT / "config_chruth" / "fiche_chruth.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(data.get("contenu") or ""), encoding="utf-8")
    return lire_fiche_chruth()


def definir_notifications(data: dict) -> dict:
    from ao_config import set_notifications

    if "actif" not in data:
        raise ValueError("Etat des notifications manquant.")
    value = data.get("actif")
    if isinstance(value, str):
        actif = value.strip().upper() in {"1", "ON", "TRUE", "OUI", "YES"}
    else:
        actif = bool(value)
    set_notifications(actif)
    return config_email()


def ouvrir_livrable(cle: str) -> dict:
    if cle not in LIVRABLES:
        raise ValueError(f"Livrable inconnu : {cle}")
    label, path, _cat = LIVRABLES[cle]
    if not path.exists():
        raise FileNotFoundError(f"{label} introuvable : {path}")
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]  # noqa: S606
    else:
        subprocess.Popen(["xdg-open", str(path)])  # noqa: S603,S607
    return {"ok": True, "message": f"Ouverture : {label}"}


# --------------------------------------------------------------------------- #
# Serveur HTTP
# --------------------------------------------------------------------------- #
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:  # silence console
        pass

    def _json(self, payload: dict, code: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _erreur(self, exc: Exception) -> None:
        self._json({"ok": False, "erreur": str(exc)}, code=400)

    def _corps_json(self) -> dict:
        longueur = int(self.headers.get("Content-Length") or 0)
        if not longueur:
            return {}
        try:
            return json.loads(self.rfile.read(longueur).decode("utf-8"))
        except Exception:  # noqa: BLE001
            return {}

    def do_GET(self) -> None:  # noqa: N802
        chemin = urlparse(self.path).path
        try:
            if chemin in ("/", "/index.html"):
                body = PAGE.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif chemin == "/api/statut":
                self._json(statut_general())
            elif chemin == "/api/job":
                self._json(JOB.state())
            elif chemin == "/api/segments":
                self._json(lister_segments())
            elif chemin == "/api/aos":
                self._json(lister_aos())
            elif chemin == "/api/email":
                self._json(config_email())
            elif chemin == "/api/fiche":
                self._json(lire_fiche_chruth())
            else:
                self._json({"erreur": "inconnu"}, code=404)
        except Exception as exc:  # noqa: BLE001
            self._erreur(exc)

    def do_POST(self) -> None:  # noqa: N802
        chemin = urlparse(self.path).path
        data = self._corps_json()
        try:
            if chemin == "/api/lancer":
                action = str(data.get("action") or "")
                if action == "pipeline":
                    cmd = commande_pipeline(data.get("options") or {})
                    label = "Generation des livrables"
                elif action == "ao_update":
                    cmd = [sys.executable, "ao_weekly_update.py"]
                    label = "Mise a jour appels d'offres"
                elif action == "messages_excel":
                    cmd = [
                        sys.executable, "CHRUTH_PIPELINE_UNIQUE.py",
                        "--skip-ao", "--skip-finance", "--generer-messages",
                    ]
                    label = "Messages prospects dans Excel"
                elif action == "finance_only":
                    cmd = [sys.executable, str(ROOT / "outils" / "generer_modele_financier.py")]
                    label = "Modele financier"
                elif action == "pack_only":
                    cmd = [sys.executable, "CHRUTH_PIPELINE_UNIQUE.py", "--pack", "--package-dir", str(PACK_DIR)]
                    label = "Creation du dossier portable"
                elif action == "alertes_run":
                    cmd = [sys.executable, "ao_alertes_run.py"]
                    label = "Controle et alerte AO"
                else:
                    raise ValueError(f"Action inconnue : {action}")
                if not JOB.start(cmd, label):
                    raise RuntimeError("Une action est deja en cours. Attends la fin.")
                self._json({"ok": True, "label": label})
            elif chemin == "/api/message_prospect":
                self._json(generer_message_prospect(data))
            elif chemin == "/api/message_ao":
                self._json(generer_message_ao_api(data))
            elif chemin == "/api/email":
                self._json(enregistrer_email(data))
            elif chemin == "/api/notifications":
                self._json(definir_notifications(data))
            elif chemin == "/api/fiche":
                self._json(enregistrer_fiche_chruth(data))
            elif chemin == "/api/envoyer":
                self._json(envoyer_email(data))
            elif chemin == "/api/ouvrir":
                self._json(ouvrir_livrable(str(data.get("cle") or "")))
            else:
                self._json({"erreur": "inconnu"}, code=404)
        except Exception as exc:  # noqa: BLE001
            self._erreur(exc)


# --------------------------------------------------------------------------- #
# Page HTML (une seule page, aucune ressource externe)
# --------------------------------------------------------------------------- #
PAGE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CHRUTH — Cockpit</title>
<style>
:root{
  --teal:#0F766E; --teal-dark:#0b5d57; --teal-light:#ccfbf1;
  --bg:#f4f6f8; --card:#ffffff; --txt:#1f2937; --muted:#6b7280;
  --ok:#16a34a; --ko:#dc2626; --warn:#d97706; --border:#e5e7eb;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--txt);font-size:15px}
header{background:var(--teal);color:#fff;padding:16px 28px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;position:sticky;top:0;z-index:20;box-shadow:0 2px 8px rgba(0,0,0,.15)}
header h1{font-size:20px;font-weight:700}
header .sous{font-size:12.5px;opacity:.85}
#etat{margin-left:auto;background:rgba(255,255,255,.15);padding:6px 14px;border-radius:20px;font-size:13px;font-weight:600}
nav{background:#fff;border-bottom:1px solid var(--border);padding:0 20px;display:flex;gap:4px;overflow-x:auto;position:sticky;top:64px;z-index:19}
nav a{padding:12px 14px;text-decoration:none;color:var(--muted);font-weight:600;font-size:13.5px;border-bottom:3px solid transparent;white-space:nowrap}
nav a:hover,nav a.actif{color:var(--teal);border-bottom-color:var(--teal)}
main{max-width:1180px;margin:0 auto;padding:24px 20px 80px}
section{margin-bottom:34px;scroll-margin-top:130px}
h2{font-size:17px;margin-bottom:12px;color:var(--teal-dark)}
.carte{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.grille{display:grid;gap:14px}
.grille.missions{grid-template-columns:repeat(auto-fit,minmax(330px,1fr))}
.badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:700}
.badge.ok{background:#dcfce7;color:var(--ok)} .badge.ko{background:#fee2e2;color:var(--ko)} .badge.warn{background:#fef3c7;color:var(--warn)}
.mission h3{font-size:14.5px;margin-bottom:4px;display:flex;justify-content:space-between;gap:8px;align-items:center}
.mission p{font-size:13px;color:var(--muted);margin-bottom:10px}
.mission ul{list-style:none;font-size:12.5px}
.mission li{padding:3px 0;display:flex;gap:6px;align-items:baseline}
.mission li .f{flex:1;font-family:Consolas,monospace;font-size:11.5px;word-break:break-all}
.mission li .d{color:var(--muted);font-size:11px;white-space:nowrap}
button{background:var(--teal);color:#fff;border:none;border-radius:8px;padding:10px 18px;font-size:14px;font-weight:600;cursor:pointer;font-family:inherit}
button:hover{background:var(--teal-dark)} button:disabled{background:#9ca3af;cursor:wait}
button.sec{background:#fff;color:var(--teal);border:1.5px solid var(--teal)}
button.sec:hover{background:var(--teal-light)}
button.petit{padding:7px 12px;font-size:12.5px}
.options{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:8px;margin:12px 0}
.options label{display:flex;gap:8px;align-items:flex-start;font-size:13.5px;background:#f9fafb;border:1px solid var(--border);border-radius:8px;padding:10px}
.options input{margin-top:3px}
.options .hint{display:block;font-size:11.5px;color:var(--muted)}
.rang{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:8px}
select,input[type=text],input[type=password]{padding:9px 10px;border:1px solid var(--border);border-radius:8px;font-size:13.5px;font-family:inherit;background:#fff;min-width:0}
select{max-width:100%}
.champ{display:flex;flex-direction:column;gap:4px;font-size:12.5px;color:var(--muted);flex:1;min-width:150px}
pre.journal{background:#0f172a;color:#d1fae5;border-radius:10px;padding:14px;font-size:12px;font-family:Consolas,monospace;max-height:340px;overflow:auto;white-space:pre-wrap;margin-top:12px;display:none}
.fichiers-job{display:none;margin-top:12px;border:1px solid var(--border);border-radius:10px;overflow:hidden;background:#fff}
.fichiers-job .head{background:#f9fafb;padding:10px 12px;font-size:12.5px;font-weight:700;color:var(--teal-dark);border-bottom:1px solid var(--border)}
.fichiers-job table{width:100%;border-collapse:collapse;font-size:12px}
.fichiers-job th,.fichiers-job td{border-bottom:1px solid var(--border);padding:7px 9px;text-align:left;vertical-align:top}
.fichiers-job th{background:#f0fdfa;color:var(--teal-dark);font-size:11.5px;text-transform:uppercase;letter-spacing:.2px}
.fichiers-job .path{font-family:Consolas,monospace;word-break:break-all}
.fichiers-job .empty{padding:10px 12px;font-size:12.5px;color:var(--muted)}
.deux{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:12px}
@media(max-width:800px){.deux{grid-template-columns:1fr}}
textarea{width:100%;min-height:220px;border:1px solid var(--border);border-radius:10px;padding:12px;font-size:13.5px;font-family:inherit;resize:vertical}
.champ textarea{min-height:78px;padding:9px 10px}
.config-actions{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:8px;margin-top:10px}
.config-actions button{width:100%;text-align:center}
.statut-ligne{font-size:12.5px;color:var(--muted);margin:6px 0 10px}
button.warnbtn{background:#b45309} button.warnbtn:hover{background:#92400e}
.libelle{font-size:12.5px;font-weight:700;color:var(--muted);margin-bottom:4px;display:flex;justify-content:space-between;align-items:center}
.livr-grp{margin-bottom:16px}
.livr-grp h3{font-size:13px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px;margin-bottom:8px}
.livr{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:8px}
.livr button{background:#fff;color:var(--txt);border:1px solid var(--border);text-align:left;font-weight:500;font-size:13px;padding:10px 12px;display:flex;gap:8px;align-items:center}
.livr button:hover{border-color:var(--teal);background:var(--teal-light)}
.livr button.absent{opacity:.45}
.point{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.point.ok{background:var(--ok)} .point.ko{background:var(--ko)}
.alerte{border-left:4px solid var(--warn);background:#fffbeb;padding:10px 14px;border-radius:8px;font-size:13px;margin-bottom:8px}
#toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:#111827;color:#fff;padding:11px 22px;border-radius:10px;font-size:13.5px;opacity:0;transition:opacity .3s;pointer-events:none;z-index:50;max-width:90%}
#toast.visible{opacity:1}
.detail-ao{background:#f9fafb;border:1px solid var(--border);border-radius:8px;padding:10px;font-family:Consolas,monospace;font-size:11.5px;margin-top:10px;white-space:pre-wrap;display:none}
</style>
</head>
<body>
<header>
  <div>
    <h1>CHRUTH — Cockpit</h1>
    <div class="sous">Interface unique : missions, generation, messages, email, livrables — sans coder.</div>
  </div>
  <div id="etat">Chargement…</div>
</header>
<nav>
  <a href="#missions" class="actif">Missions</a>
  <a href="#generer">1. Generer</a>
  <a href="#prospects">2. Messages prospects</a>
  <a href="#ao">3. Messages AO</a>
  <a href="#config">4. Config & automatisation</a>
  <a href="#email">5. Envoyer email</a>
  <a href="#livrables">6. Livrables</a>
</nav>
<main>

<section id="missions">
  <h2>Etat des missions (fiche de poste)</h2>
  <div id="alertes"></div>
  <div class="grille missions" id="listeMissions"></div>
</section>

<section id="generer">
  <h2>1. Generer les documents</h2>
  <div class="carte">
    <div style="font-size:13.5px;color:var(--muted)">Mode recommande : ne rien cocher — la pipeline retraite les donnees locales et regenere tous les livrables (Excel, carte, CRM, finance, exports) en quelques minutes, sans internet.</div>
    <div class="options">
      <label><input type="checkbox" id="optAO"><span>Recollecter les appels d'offres BOAMP/DCE<span class="hint">Internet requis, ~2 minutes.</span></span></label>
      <label><input type="checkbox" id="optProspects"><span>Recollecter les prospects API Entreprises<span class="hint">Toute la France : long (~dizaines de minutes).</span></span></label>
      <label><input type="checkbox" id="optIA"><span>Generer les brouillons IA<span class="hint">Utilise la cle .env ou Ollama si disponibles.</span></span></label>
      <label><input type="checkbox" id="optPack" checked><span>Creer le dossier portable<span class="hint">Copie prete a envoyer (sans secrets).</span></span></label>
    </div>
    <div class="rang">
      <button id="btnPipeline" onclick="lancer('pipeline')">Generer tous les documents</button>
      <button class="sec" id="btnAOupd" onclick="lancer('ao_update')">Mettre a jour les AO seulement</button>
      <button class="sec" id="btnAlertesNow" onclick="lancer('alertes_run')">Lancer alertes AO maintenant</button>
      <button class="sec" id="btnMsgXlsx" onclick="lancer('messages_excel')">Messages prospects dans Excel</button>
    </div>
    <pre class="journal" id="journal"></pre>
    <div class="fichiers-job" id="fichiersJob"></div>
  </div>
</section>

<section id="prospects">
  <h2>2. Messages prospects par segment</h2>
  <div class="carte">
    <div class="rang">
      <button class="sec petit" onclick="chargerSegments()">Charger les segments</button>
      <select id="selSegment" style="flex:1" onchange="exempleSegment()"></select>
    </div>
    <div class="rang">
      <label class="champ">Denomination<input type="text" id="pDeno" value="CABINET DENTAIRE DU MARAIS"></label>
      <label class="champ">Ville<input type="text" id="pVille" value="PARIS"></label>
      <label class="champ">Effectif<input type="text" id="pEff" value="10 a 19"></label>
    </div>
    <div class="rang">
      <button id="btnMsgP" onclick="genererProspect()">Generer email + script</button>
      <button class="sec petit" onclick="copier('pEmail')">Copier l'email</button>
      <button class="sec petit" onclick="copier('pScript')">Copier le script</button>
      <button class="sec petit" onclick="versEmail('pEmail','CHRUTH - Entretien et proprete de vos locaux')">Envoyer par email →</button>
    </div>
    <div class="deux">
      <div><div class="libelle">Email</div><textarea id="pEmail"></textarea></div>
      <div><div class="libelle">Script d'appel</div><textarea id="pScript"></textarea></div>
    </div>
  </div>
</section>

<section id="ao">
  <h2>3. Messages appels d'offres</h2>
  <div class="carte">
    <div class="rang">
      <button class="sec petit" onclick="chargerAOs()">Charger les AO chauds/tiedes</button>
      <select id="selAO" style="flex:1" onchange="detailsAO()"></select>
    </div>
    <div class="detail-ao" id="aoDetails"></div>
    <div class="rang">
      <button id="btnMsgAO" onclick="genererAO()">Generer email + script AO</button>
      <button class="sec petit" onclick="copier('aoEmail')">Copier l'email</button>
      <button class="sec petit" onclick="copier('aoScript')">Copier le script</button>
      <button class="sec petit" onclick="versEmail('aoEmail','CHRUTH - Appel d\'offres nettoyage')">Envoyer par email →</button>
    </div>
    <div class="deux">
      <div><div class="libelle">Email AO</div><textarea id="aoEmail"></textarea></div>
      <div><div class="libelle">Script AO</div><textarea id="aoScript"></textarea></div>
    </div>
  </div>
</section>


<section id="config">
  <h2>4. Configuration & automatisation</h2>
  <div class="deux">
    <div class="carte">
      <h2 style="margin-bottom:8px">Email, destinataires et alertes</h2>
      <div class="statut-ligne" id="nStatut">Chargement de la configuration...</div>
      <div class="rang">
        <button class="petit" onclick="setNotifications(true)">Activer alertes</button>
        <button class="sec petit" onclick="setNotifications(false)">Couper alertes</button>
      </div>
      <div class="statut-ligne">Les destinataires se modifient dans la section Email ci-dessous. Le cockpit met a jour <code>destinataires.txt</code> et <code>alertes_secrets.json</code>.</div>
    </div>
    <div class="carte">
      <h2 style="margin-bottom:8px">Fiche CHRUTH utilisee par l'IA</h2>
      <div class="statut-ligne">Renseigne uniquement des faits vrais : prestations, zones, points forts, limites a ne pas inventer.</div>
      <textarea id="ficheTxt" style="min-height:180px"></textarea>
      <div class="rang">
        <button class="petit" onclick="sauverFiche()">Enregistrer fiche</button>
        <button class="sec petit" onclick="chargerFiche()">Recharger</button>
        <button class="sec petit" onclick="ouvrir('fiche_chruth')">Ouvrir fichier</button>
      </div>
    </div>
  </div>
  <div class="carte" style="margin-top:14px">
    <h2 style="margin-bottom:8px">Actions rapides sans sortir du cockpit</h2>
    <div class="config-actions">
      <button onclick="lancer('finance_only')">Regenerer modele financier</button>
      <button onclick="lancer('pack_only')">Creer dossier portable</button>
      <button class="warnbtn" onclick="lancer('alertes_run')">Lancer alertes AO maintenant</button>
      <button class="sec" onclick="ouvrir('guide_html')">Ouvrir guide</button>
      <button class="sec" onclick="ouvrir('dossier_output')">Ouvrir output</button>
      <button class="sec" onclick="ouvrir('installer')">Lancer INSTALLER.bat</button>
    </div>
  </div>
</section>

<section id="email">
  <h2>5. Envoyer un email (Gmail)</h2>
  <div class="carte">
    <div style="font-size:13px;color:var(--muted);margin-bottom:10px">Utilise un <b>mot de passe d'application</b> Gmail (pas le mot de passe du compte). Configuration stockee localement, jamais dans les packs.</div>
    <div class="rang">
      <label class="champ">Email expediteur Gmail<input type="text" id="eUser"></label>
      <label class="champ">Mot de passe d'application<input type="password" id="ePass" placeholder="(inchange si vide)"></label>
      <label class="champ">Destinataires (un par ligne)<textarea id="eDests"></textarea></label>
      <button class="petit" onclick="sauverEmailCfg()">Enregistrer</button>
    </div>
    <div id="eStatut" style="font-size:12.5px;color:var(--muted);margin:6px 0"></div>
    <div class="rang">
      <label class="champ" style="flex:2">Sujet<input type="text" id="eSujet" value="CHRUTH - Message"></label>
      <button id="btnEnvoyer" onclick="envoyerEmail()">Envoyer l'email</button>
    </div>
    <div class="libelle" style="margin-top:10px">Message a envoyer</div>
    <textarea id="eCorps" style="min-height:180px"></textarea>
  </div>
</section>

<section id="livrables">
  <h2>6. Livrables & documents</h2>
  <div class="carte" id="zoneLivrables"></div>
</section>

</main>
<div id="toast"></div>
<script>
const $ = id => document.getElementById(id);
const CATS = [["principal","Livrables principaux"],["exports","Exports (Power BI, Notion, KPI)"],["messages","Messages & IA"],["docs","Guides & documentation"],["avance","Notebooks, logs & avance"]];
let jobActif = false;

function toast(msg, ms=3200){ const t=$("toast"); t.textContent=msg; t.classList.add("visible"); setTimeout(()=>t.classList.remove("visible"), ms); }
function esc(v){ return String(v ?? "").replace(/[&<>"']/g, c=>{ if(c==="&") return "&amp;"; if(c==="<") return "&lt;"; if(c===">") return "&gt;"; if(c==='"') return "&quot;"; return "&#39;"; }); }
async function api(chemin, corps){
  const opt = corps ? {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(corps)} : {};
  const rep = await fetch(chemin, opt);
  const data = await rep.json();
  if(!rep.ok) throw new Error(data.erreur || "Erreur serveur");
  return data;
}

// ------------------------------------------------------------- statut ------
async function rafraichirStatut(){
  try{
    const s = await api("/api/statut");
    const nb = s.missions.filter(m=>m.ok).length;
    $("etat").textContent = `Missions : ${nb}/${s.missions.length} completes` + (s.derniere_generation ? ` · Derniere generation : ${s.derniere_generation.replace("T"," ").slice(0,16)}` : "");
    $("listeMissions").innerHTML = s.missions.map(m=>`
      <div class="carte mission">
        <h3>${m.titre} <span class="badge ${m.ok?"ok":"ko"}">${m.ok?"OK":"INCOMPLET"}</span></h3>
        <p>${m.objectif}</p>
        <ul>${m.fichiers.map(f=>`<li><span class="point ${f.present?"ok":"ko"}"></span><span class="f">${f.chemin}</span><span class="d">${f.present?(f.date+" · "+f.taille):"manquant"}</span></li>`).join("")}</ul>
      </div>`).join("");
    const alertes = [];
    if(!s.fiche_chruth_remplie) alertes.push("La <b>fiche CHRUTH</b> (config_chruth/fiche_chruth.md) est encore vide : les messages IA restent generiques. Ouvre-la depuis l'onglet Livrables et remplis-la avec des faits vrais.");
    if(!s.cle_ia_configuree) alertes.push("Aucune <b>cle IA</b> dans .env : les brouillons utilisent les templates deterministes (ou Ollama local si installe).");
    $("alertes").innerHTML = alertes.map(a=>`<div class="alerte">${a}</div>`).join("");
    const grp = {};
    s.livrables.forEach(l=>{ (grp[l.categorie]=grp[l.categorie]||[]).push(l); });
    $("zoneLivrables").innerHTML = CATS.map(([cle,titre])=>{
      const items = grp[cle]||[];
      return `<div class="livr-grp"><h3>${titre}</h3><div class="livr">` +
        items.map(l=>`<button class="${l.present?"":"absent"}" onclick="ouvrir('${l.cle}')"><span class="point ${l.present?"ok":"ko"}"></span>${l.label}</button>`).join("") +
      `</div></div>`;
    }).join("");
  }catch(e){ $("etat").textContent = "Statut indisponible"; }
}

async function ouvrir(cle){
  try{ const r = await api("/api/ouvrir",{cle}); toast(r.message); }
  catch(e){ toast("⚠ " + e.message, 4500); }
}

// -------------------------------------------------------------- jobs -------
function boutonsJob(off){
  ["btnPipeline","btnAOupd","btnAlertesNow","btnMsgXlsx"].forEach(id=>$(id).disabled = off);
  document.querySelectorAll("#config button[onclick^='lancer']").forEach(b=>b.disabled = off);
}
function afficherFichiersJob(fichiers, elapsed){
  const z = $("fichiersJob");
  if(!z) return;
  z.style.display = "block";
  if(!fichiers || !fichiers.length){
    z.innerHTML = `<div class="head">Temps par fichier</div><div class="empty">Aucun fichier du dossier output mis a jour pour l'instant.</div>`;
    return;
  }
  z.innerHTML = `<div class="head">Fichiers mis a jour depuis le lancement - temps ecoule : ${esc(elapsed || "0s")}</div>` +
    `<table><thead><tr><th>Temps</th><th>Fichier</th><th>Taille</th><th>Heure</th></tr></thead><tbody>` +
    fichiers.map(f=>`<tr><td>${esc(f.temps)}</td><td class="path">${esc(f.chemin)}</td><td>${esc(f.taille)}</td><td>${esc(f.date)}</td></tr>`).join("") +
    `</tbody></table>`;
}
async function lancer(action){
  if(jobActif) return;
  const options = {collect_ao:$("optAO").checked, collect_prospects:$("optProspects").checked, messages_ia:$("optIA").checked, pack:$("optPack").checked};
  if(action==="pipeline" && options.collect_prospects && !confirm("La recollecte prospects France peut durer plusieurs dizaines de minutes. Continuer ?")) return;
  if(action==="alertes_run" && !confirm("Cette action controle les nouveaux AO et peut envoyer les alertes email aux destinataires configures. Continuer ?")) return;
  try{
    await api("/api/lancer",{action, options});
    jobActif = true; boutonsJob(true);
    $("journal").style.display="block"; $("journal").textContent="Demarrage…";
    suivreJob();
  }catch(e){ toast("⚠ " + e.message, 4500); }
}
async function suivreJob(){
  try{
    const j = await api("/api/job");
    $("journal").textContent = j.log;
    $("journal").scrollTop = $("journal").scrollHeight;
    $("etat").textContent = j.running ? ("⏳ " + j.label + "…") : $("etat").textContent;
    if(j.running){ setTimeout(suivreJob, 1500); }
    else{
      jobActif = false; boutonsJob(false);
      toast(j.code===0 ? "✅ " + j.label + " : termine." : "⚠ " + j.label + " : erreur (voir journal).", 5000);
      rafraichirStatut();
    }
  }catch(e){ setTimeout(suivreJob, 3000); }
}

// --------------------------------------------------------- prospects -------
let segs = {};
async function chargerSegments(){
  try{
    const d = await api("/api/segments");
    segs = {};
    $("selSegment").innerHTML = d.segments.map(s=>{ segs[s.cle]=s; return `<option value="${s.cle}">${s.cle.replace("|"," — ")}</option>`; }).join("");
    exempleSegment();
    toast(d.segments.length + " segments charges.");
  }catch(e){ toast("⚠ " + e.message, 4500); }
}
function exempleSegment(){
  const s = segs[$("selSegment").value];
  if(s){ $("pDeno").value=s.denomination; $("pVille").value=s.ville; $("pEff").value=s.effectif; }
}
async function genererProspect(){
  const segment = $("selSegment").value;
  if(!segment){ toast("Charge d'abord les segments."); return; }
  $("btnMsgP").disabled = true;
  try{
    const r = await api("/api/message_prospect",{segment, denomination:$("pDeno").value, ville:$("pVille").value, effectif:$("pEff").value});
    $("pEmail").value = r.email; $("pScript").value = r.script;
    toast("Message prospect genere (source : " + (r.source||"template") + ").");
  }catch(e){ toast("⚠ " + e.message, 4500); }
  finally{ $("btnMsgP").disabled = false; }
}

// ---------------------------------------------------------------- AO -------
let aos = {};
async function chargerAOs(){
  try{
    const d = await api("/api/aos");
    aos = {};
    $("selAO").innerHTML = d.aos.map(a=>{ aos[a.id]=a; return `<option value="${a.id}">${a.label}</option>`; }).join("");
    detailsAO();
    toast(d.aos.length + " AO charges.");
  }catch(e){ toast("⚠ " + e.message, 4500); }
}
function detailsAO(){
  const a = aos[$("selAO").value];
  const z = $("aoDetails");
  if(a){ z.style.display="block"; z.textContent = Object.entries(a.details).map(([k,v])=>k+" : "+v).join("\n"); }
  else z.style.display="none";
}
async function genererAO(){
  const id = $("selAO").value;
  if(!id){ toast("Charge d'abord les AO."); return; }
  $("btnMsgAO").disabled = true;
  try{
    const r = await api("/api/message_ao",{id});
    $("aoEmail").value = r.email; $("aoScript").value = r.script;
    toast("Message AO genere.");
  }catch(e){ toast("⚠ " + e.message, 4500); }
  finally{ $("btnMsgAO").disabled = false; }
}

// ------------------------------------------------------------- email -------
function decouperSujet(texte, defaut){
  const lignes = (texte||"").split("\n");
  if(lignes.length && lignes[0].toLowerCase().startsWith("objet")){
    const i = lignes[0].indexOf(":");
    return [i>=0 ? lignes[0].slice(i+1).trim() || defaut : defaut, lignes.slice(1).join("\n").trim()];
  }
  return [defaut, (texte||"").trim()];
}
function versEmail(idZone, defaut){
  const [sujet, corps] = decouperSujet($(idZone).value, defaut);
  if(!corps){ toast("Genere d'abord un message."); return; }
  $("eSujet").value = sujet; $("eCorps").value = corps;
  location.hash = "#email";
  toast("Message charge dans l'onglet Email.");
}
async function chargerEmailCfg(){
  try{
    const c = await api("/api/email");
    $("eUser").value = c.expediteur; $("eDests").value = c.destinataires || c.destinataire || "";
    $("eStatut").textContent = c.prete ? "Configuration email prete : " + c.nb_destinataires + " destinataire(s)." : c.message;
    $("nStatut").textContent = "Alertes email : " + (c.notifications_actives ? "ON" : "OFF") + " | " + c.nb_destinataires + " destinataire(s).";
  }catch(e){}
}
async function sauverEmailCfg(){
  try{
    const c = await api("/api/email",{expediteur:$("eUser").value, mot_de_passe:$("ePass").value, destinataires:$("eDests").value});
    $("ePass").value = "";
    $("eDests").value = c.destinataires || "";
    $("eStatut").textContent = c.prete ? "Configuration email prete : " + c.nb_destinataires + " destinataire(s)." : c.message;
    $("nStatut").textContent = "Alertes email : " + (c.notifications_actives ? "ON" : "OFF") + " | " + c.nb_destinataires + " destinataire(s).";
    toast("Configuration enregistree.");
  }catch(e){ toast("Attention : " + e.message, 4500); }
}
async function envoyerEmail(){
  const dest = $("eDests").value.trim();
  if(!$("eCorps").value.trim()){ toast("Le message est vide."); return; }
  if(!dest){ toast("Aucun destinataire."); return; }
  if(!confirm("Envoyer cet email aux destinataires indiques ?")) return;
  $("btnEnvoyer").disabled = true;
  try{
    const r = await api("/api/envoyer",{destinataires:dest, sujet:$("eSujet").value, corps:$("eCorps").value});
    toast(r.message, 5000);
  }catch(e){ toast("Attention : " + e.message, 6000); }
  finally{ $("btnEnvoyer").disabled = false; }
}

// ----------------------------------------------------------- config -------
async function setNotifications(actif){
  try{
    const c = await api("/api/notifications",{actif});
    $("nStatut").textContent = "Alertes email : " + (c.notifications_actives ? "ON" : "OFF") + " | " + c.nb_destinataires + " destinataire(s).";
    toast(c.notifications_actives ? "Alertes email activees." : "Alertes email coupees.");
    rafraichirStatut();
  }catch(e){ toast("Attention : " + e.message, 4500); }
}
async function chargerFiche(){
  try{
    const f = await api("/api/fiche");
    $("ficheTxt").value = f.contenu || "";
  }catch(e){ toast("Attention : " + e.message, 4500); }
}
async function sauverFiche(){
  try{
    await api("/api/fiche",{contenu:$("ficheTxt").value});
    toast("Fiche CHRUTH enregistree.");
    rafraichirStatut();
  }catch(e){ toast("Attention : " + e.message, 4500); }
}

// ------------------------------------------------------------- divers ------
function copier(id){
  const t = $(id).value;
  if(!t.trim()){ toast("Rien a copier."); return; }
  navigator.clipboard.writeText(t).then(()=>toast("Copie dans le presse-papiers."));
}
document.querySelectorAll("nav a").forEach(a=>a.addEventListener("click",()=>{
  document.querySelectorAll("nav a").forEach(x=>x.classList.remove("actif")); a.classList.add("actif");
}));

rafraichirStatut();
chargerEmailCfg();
chargerFiche();
api("/api/job").then(j=>{ if(j.running){ jobActif=true; boutonsJob(true); $("journal").style.display="block"; suivreJob(); } }).catch(()=>{});
</script>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# Lancement
# --------------------------------------------------------------------------- #
def port_libre(prefere: int) -> int:
    for port in range(prefere, prefere + 20):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
            return port
        except OSError:
            continue
    return prefere


def main() -> None:
    port = port_libre(PORT_DEFAUT)
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    serveur = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print("=" * 60)
    print("CHRUTH — Cockpit web")
    print(f"Interface : {url}")
    print("Laisser cette fenetre ouverte. Fermer = arreter le cockpit.")
    print("=" * 60)
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
