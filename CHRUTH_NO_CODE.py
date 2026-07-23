"""Interface no-code CHRUTH.

Entree principale : OUVRIR_MOI_CHRUTH.bat.

L'interface regroupe les actions utiles du dossier :
- generation de tous les livrables ;
- messages prospects par segment ;
- messages pour appels d'offres ;
- acces rapide aux fichiers de sortie et notices.
"""
from __future__ import annotations

import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
PACK_DIR = ROOT.parent / "CHRUTH_LIVRAISON_NOTEBOOK"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CHRUTH - Interface no-code")
        self.geometry("1040x720")
        self.minsize(920, 620)

        self.collect_ao = tk.BooleanVar(value=False)
        self.collect_prospects = tk.BooleanVar(value=False)
        self.generer_messages = tk.BooleanVar(value=False)
        self.creer_pack = tk.BooleanVar(value=True)
        self.running = False

        self.segment_values: list[str] = []
        self.segment_rows: dict[str, dict] = {}
        self.ao_labels: list[str] = []
        self.ao_records: dict[str, dict] = {}

        self.segment_var = tk.StringVar()
        self.ao_var = tk.StringVar()
        self.smtp_user_var = tk.StringVar()
        self.smtp_password_var = tk.StringVar()
        self.recipient_var = tk.StringVar()
        self.email_subject_var = tk.StringVar(value="CHRUTH - Message")
        self.denomination_var = tk.StringVar(value="CABINET DENTAIRE DU MARAIS")
        self.ville_var = tk.StringVar(value="PARIS")
        self.effectif_var = tk.StringVar(value="10 a 19")

        self._build()

    # ------------------------------------------------------------------ UI ---
    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = tk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        header.columnconfigure(0, weight=1)
        tk.Label(header, text="CHRUTH - Interface no-code", font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        tk.Label(
            header,
            text="Generation des livrables, messages prospects, messages AO, fichiers de sortie.",
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w")

        self.status = tk.Label(header, text="Pret.", anchor="e", font=("Segoe UI", 10, "bold"))
        self.status.grid(row=0, column=1, rowspan=2, sticky="e")

        self.tabs = ttk.Notebook(self)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=14, pady=6)

        self.tab_generation = tk.Frame(self.tabs)
        self.tab_prospects = tk.Frame(self.tabs)
        self.tab_ao = tk.Frame(self.tabs)
        self.tab_email = tk.Frame(self.tabs)
        self.tab_files = tk.Frame(self.tabs)
        self.tab_log = tk.Frame(self.tabs)

        for tab in (self.tab_generation, self.tab_prospects, self.tab_ao, self.tab_email, self.tab_files, self.tab_log):
            tab.columnconfigure(0, weight=1)

        self.tabs.add(self.tab_generation, text="1. Generer")
        self.tabs.add(self.tab_prospects, text="2. Messages prospects")
        self.tabs.add(self.tab_ao, text="3. Messages AO")
        self.tabs.add(self.tab_email, text="4. Email")
        self.tabs.add(self.tab_files, text="5. Livrables")
        self.tabs.add(self.tab_log, text="Journal")

        self._build_generation_tab()
        self._build_prospects_tab()
        self._build_ao_tab()
        self._build_email_tab()
        self._build_files_tab()
        self._build_log_tab()
        self.load_email_config(silent=True)

    def _build_generation_tab(self) -> None:
        frame = self.tab_generation
        options = tk.LabelFrame(frame, text="Options de generation", font=("Segoe UI", 10, "bold"))
        options.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        options.columnconfigure(0, weight=1)
        options.columnconfigure(1, weight=1)

        tk.Checkbutton(options, text="Recollecter les appels d'offres BOAMP/DCE", variable=self.collect_ao).grid(
            row=0, column=0, sticky="w", padx=12, pady=6
        )
        tk.Checkbutton(
            options,
            text="Recollecter les prospects API Entreprises (long)",
            variable=self.collect_prospects,
        ).grid(row=1, column=0, sticky="w", padx=12, pady=6)
        tk.Checkbutton(
            options,
            text="Generer les brouillons IA si un LLM est disponible",
            variable=self.generer_messages,
        ).grid(row=0, column=1, sticky="w", padx=12, pady=6)
        tk.Checkbutton(options, text="Creer le dossier portable pret a envoyer", variable=self.creer_pack).grid(
            row=1, column=1, sticky="w", padx=12, pady=6
        )

        actions = tk.Frame(frame)
        actions.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        self.generate_btn = tk.Button(
            actions,
            text="Generer tous les documents",
            command=self.generate_all,
            height=2,
            width=28,
            bg="#0F766E",
            fg="white",
            font=("Segoe UI", 10, "bold"),
        )
        self.generate_btn.pack(side="left")
        tk.Button(actions, text="Messages prospects dans Excel", command=self.generate_all_messages, height=2, width=28).pack(
            side="left", padx=10
        )
        tk.Button(actions, text="Ouvrir output", command=self.open_output, height=2, width=16).pack(side="left")

        info = (
            "Mode recommande : ne rien cocher au premier lancement. "
            "La pipeline retraitera les donnees locales et gardera la collecte internet sur OFF."
        )
        tk.Label(frame, text=info, wraplength=900, justify="left", font=("Segoe UI", 10)).grid(
            row=2, column=0, sticky="w", padx=12, pady=8
        )

    def _build_prospects_tab(self) -> None:
        frame = self.tab_prospects
        top = tk.Frame(frame)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top.columnconfigure(1, weight=1)

        tk.Button(top, text="Charger les segments", command=self.load_segments, width=22).grid(row=0, column=0, sticky="w")
        self.segment_combo = ttk.Combobox(top, textvariable=self.segment_var, values=[], state="readonly")
        self.segment_combo.grid(row=0, column=1, sticky="ew", padx=10)
        self.segment_combo.bind("<<ComboboxSelected>>", lambda _e: self.fill_segment_example())

        examples = tk.LabelFrame(frame, text="Exemple pour personnaliser le message", font=("Segoe UI", 10, "bold"))
        examples.grid(row=1, column=0, sticky="ew", padx=10, pady=6)
        for i in range(3):
            examples.columnconfigure(i, weight=1)
        self._entry(examples, "Denomination", self.denomination_var, 0)
        self._entry(examples, "Ville", self.ville_var, 1)
        self._entry(examples, "Effectif", self.effectif_var, 2)

        actions = tk.Frame(frame)
        actions.grid(row=2, column=0, sticky="ew", padx=10, pady=6)
        self.prospect_msg_btn = tk.Button(actions, text="Generer email + script", command=self.generate_prospect_message)
        self.prospect_msg_btn.pack(side="left")
        tk.Button(actions, text="Copier email", command=lambda: self.copy_text(self.prospect_email)).pack(side="left", padx=8)
        tk.Button(actions, text="Copier script", command=lambda: self.copy_text(self.prospect_script)).pack(side="left")
        tk.Button(actions, text="Ouvrir fichier message", command=lambda: self.open_file(OUTPUT_DIR / "_message_prospect_segment.txt")).pack(
            side="left", padx=8
        )

        texts = tk.Frame(frame)
        texts.grid(row=3, column=0, sticky="nsew", padx=10, pady=6)
        frame.rowconfigure(3, weight=1)
        texts.columnconfigure(0, weight=1)
        texts.columnconfigure(1, weight=1)
        tk.Label(texts, text="Email").grid(row=0, column=0, sticky="w")
        tk.Label(texts, text="Script d'appel").grid(row=0, column=1, sticky="w", padx=(10, 0))
        self.prospect_email = scrolledtext.ScrolledText(texts, height=18, font=("Segoe UI", 10))
        self.prospect_script = scrolledtext.ScrolledText(texts, height=18, font=("Segoe UI", 10))
        self.prospect_email.grid(row=1, column=0, sticky="nsew")
        self.prospect_script.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        texts.rowconfigure(1, weight=1)

    def _build_ao_tab(self) -> None:
        frame = self.tab_ao
        top = tk.Frame(frame)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top.columnconfigure(1, weight=1)

        tk.Button(top, text="Charger les AO chauds/tiedes", command=self.load_aos, width=26).grid(row=0, column=0)
        self.ao_combo = ttk.Combobox(top, textvariable=self.ao_var, values=[], state="readonly")
        self.ao_combo.grid(row=0, column=1, sticky="ew", padx=10)
        self.ao_combo.bind("<<ComboboxSelected>>", lambda _e: self.show_ao_details())

        self.ao_details = scrolledtext.ScrolledText(frame, height=7, font=("Consolas", 9))
        self.ao_details.grid(row=1, column=0, sticky="ew", padx=10, pady=6)

        actions = tk.Frame(frame)
        actions.grid(row=2, column=0, sticky="ew", padx=10, pady=6)
        self.ao_msg_btn = tk.Button(actions, text="Generer email + script AO", command=self.generate_ao_message)
        self.ao_msg_btn.pack(side="left")
        tk.Button(actions, text="Copier email", command=lambda: self.copy_text(self.ao_email)).pack(side="left", padx=8)
        tk.Button(actions, text="Copier script", command=lambda: self.copy_text(self.ao_script)).pack(side="left")
        tk.Button(actions, text="Ouvrir fichier message", command=lambda: self.open_file(OUTPUT_DIR / "_message_ao.txt")).pack(
            side="left", padx=8
        )

        texts = tk.Frame(frame)
        texts.grid(row=3, column=0, sticky="nsew", padx=10, pady=6)
        frame.rowconfigure(3, weight=1)
        texts.columnconfigure(0, weight=1)
        texts.columnconfigure(1, weight=1)
        tk.Label(texts, text="Email AO").grid(row=0, column=0, sticky="w")
        tk.Label(texts, text="Script AO").grid(row=0, column=1, sticky="w", padx=(10, 0))
        self.ao_email = scrolledtext.ScrolledText(texts, height=16, font=("Segoe UI", 10))
        self.ao_script = scrolledtext.ScrolledText(texts, height=16, font=("Segoe UI", 10))
        self.ao_email.grid(row=1, column=0, sticky="nsew")
        self.ao_script.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        texts.rowconfigure(1, weight=1)

    def _build_email_tab(self) -> None:
        frame = self.tab_email
        frame.rowconfigure(3, weight=1)

        config = tk.LabelFrame(frame, text="Configuration Gmail", font=("Segoe UI", 10, "bold"))
        config.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        for i in range(4):
            config.columnconfigure(i, weight=1)

        tk.Label(config, text="Email expediteur Gmail").grid(row=0, column=0, sticky="w", padx=8, pady=(6, 0))
        tk.Entry(config, textvariable=self.smtp_user_var).grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        tk.Label(config, text="Mot de passe d'application").grid(row=0, column=1, sticky="w", padx=8, pady=(6, 0))
        tk.Entry(config, textvariable=self.smtp_password_var, show="*").grid(
            row=1, column=1, sticky="ew", padx=8, pady=(0, 8)
        )
        tk.Button(config, text="Enregistrer config", command=self.save_email_config).grid(
            row=1, column=2, sticky="ew", padx=8, pady=(0, 8)
        )
        tk.Button(config, text="Recharger config", command=self.load_email_config).grid(
            row=1, column=3, sticky="ew", padx=8, pady=(0, 8)
        )

        send = tk.LabelFrame(frame, text="Message a envoyer", font=("Segoe UI", 10, "bold"))
        send.grid(row=1, column=0, sticky="ew", padx=10, pady=6)
        send.columnconfigure(1, weight=1)
        tk.Label(send, text="Destinataire").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        tk.Entry(send, textvariable=self.recipient_var).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        tk.Button(send, text="Enregistrer destinataire", command=self.save_recipient).grid(
            row=0, column=2, sticky="ew", padx=8, pady=6
        )
        tk.Label(send, text="Sujet").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        tk.Entry(send, textvariable=self.email_subject_var).grid(row=1, column=1, columnspan=2, sticky="ew", padx=8, pady=6)

        actions = tk.Frame(frame)
        actions.grid(row=2, column=0, sticky="ew", padx=10, pady=4)
        self.send_btn = tk.Button(
            actions,
            text="Envoyer l'email",
            command=self.send_email_from_ui,
            bg="#0F766E",
            fg="white",
            font=("Segoe UI", 10, "bold"),
        )
        self.send_btn.pack(side="left")
        tk.Button(actions, text="Charger depuis message prospect", command=self.load_email_from_prospect).pack(
            side="left", padx=8
        )
        tk.Button(actions, text="Charger depuis message AO", command=self.load_email_from_ao).pack(side="left")
        tk.Button(actions, text="Copier message", command=lambda: self.copy_text(self.email_body)).pack(side="left", padx=8)

        self.email_body = scrolledtext.ScrolledText(frame, height=16, font=("Segoe UI", 10))
        self.email_body.grid(row=3, column=0, sticky="nsew", padx=10, pady=8)

    def _build_files_tab(self) -> None:
        frame = self.tab_files
        files = [
            ("Cockpit AO", OUTPUT_DIR / "AO_CHRUTH.xlsm"),
            ("Base prospects", OUTPUT_DIR / "Base_Prospects_CHRUTH.xlsm"),
            ("Carte prospects", OUTPUT_DIR / "Carte_Prospects_CHRUTH.html"),
            ("CRM", OUTPUT_DIR / "CRM_CHRUTH_CHAUDE.xlsx"),
            ("Messages prospects", OUTPUT_DIR / "Prospects_CHAUDS_messages.xlsx"),
            ("Modele financier", OUTPUT_DIR / "Modele_Financier_CHRUTH.xlsx"),
            ("Sources Power BI", OUTPUT_DIR / "powerbi_sources"),
            ("Import Notion", OUTPUT_DIR / "notion_import_chruth"),
            ("Exports CSV", OUTPUT_DIR / "exports_csv"),
            ("Notice livrables", OUTPUT_DIR / "LIRE_MOI_LIVRABLES.md"),
            ("Manifest JSON", OUTPUT_DIR / "MANIFEST_CHRUTH.json"),
            ("Message AO texte", OUTPUT_DIR / "_message_ao.txt"),
            ("Message prospect texte", OUTPUT_DIR / "_message_prospect_segment.txt"),
            ("Mission CHRUTH", ROOT / "docs" / "MISSION_CHRUTH.md"),
            ("Couverture interface", ROOT / "docs" / "COUVERTURE_INTERFACE_CHRUTH.md"),
            ("Prompts", ROOT / "prompts" / "PROMPTS_CHRUTH.md"),
            ("Guide demarrage", ROOT / "README_DEMARRAGE_NO_CODE.md"),
            ("Notice livraison", ROOT / "README_LIVRAISON.md"),
            ("README projet", ROOT / "README.md"),
            ("Guide AO HTML", ROOT / "GUIDE_AO_CHRUTH.html"),
            ("README HTML", ROOT / "README.html"),
            ("Notebook unique", ROOT / "CHRUTH_Pipeline_Unique.ipynb"),
            ("Notebook prompts", ROOT / "CHRUTH_Prompt_Playground.ipynb"),
            ("Notebook messages AO", ROOT / "CHRUTH_Messages_AO.ipynb"),
            ("Notebook messages prospects", ROOT / "CHRUTH_Messages_Prospects.ipynb"),
            ("Notebook alertes AO", ROOT / "CHRUTH_Alertes.ipynb"),
            ("Notebook moteur IA", ROOT / "CHRUTH_Moteur_IA.ipynb"),
            ("Docs techniques", ROOT / "docs"),
            ("DCE PDF", ROOT / "dce_auto"),
            ("Logs", ROOT / "logs"),
            ("Dossier portable", PACK_DIR),
        ]
        grid = tk.Frame(frame)
        grid.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        for col in range(3):
            grid.columnconfigure(col, weight=1)
        for i, (label, path) in enumerate(files):
            tk.Button(grid, text=label, width=24, command=lambda p=path: self.open_file(p)).grid(
                row=i // 3, column=i % 3, sticky="ew", padx=6, pady=5
            )
        actions = tk.Frame(frame)
        actions.grid(row=1, column=0, sticky="ew", padx=16, pady=8)
        tk.Button(actions, text="Ouvrir le dossier output", command=self.open_output, height=2, width=24).pack(side="left")
        tk.Button(actions, text="Ouvrir le dossier projet", command=lambda: self.open_file(ROOT), height=2, width=24).pack(
            side="left", padx=8
        )
        tk.Button(actions, text="Ouvrir la fiche de poste", command=self.open_source_pdf, height=2, width=24).pack(
            side="left"
        )
        tk.Button(actions, text="Ancienne app messages", command=self.launch_streamlit_messages, height=2, width=24).pack(
            side="left", padx=8
        )

    def _build_log_tab(self) -> None:
        self.log = scrolledtext.ScrolledText(self.tab_log, height=24, font=("Consolas", 9))
        self.log.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.tab_log.rowconfigure(0, weight=1)

    def _entry(self, parent: tk.Widget, label: str, var: tk.StringVar, column: int) -> None:
        tk.Label(parent, text=label).grid(row=0, column=column, sticky="w", padx=8, pady=(6, 0))
        tk.Entry(parent, textvariable=var).grid(row=1, column=column, sticky="ew", padx=8, pady=(0, 8))

    # --------------------------------------------------------------- helpers ---
    def safe(self, fn, *args) -> None:
        self.after(0, lambda: fn(*args))

    def append(self, text: str) -> None:
        self.log.insert("end", text)
        self.log.see("end")

    def set_status(self, text: str) -> None:
        self.status.config(text=text)

    def set_running(self, running: bool) -> None:
        self.running = running
        state = "disabled" if running else "normal"
        self.generate_btn.config(state=state)
        self.prospect_msg_btn.config(state=state)
        self.ao_msg_btn.config(state=state)
        self.send_btn.config(state=state)

    def run_thread(self, label: str, target) -> None:
        if self.running:
            return
        self.set_running(True)
        self.log.delete("1.0", "end")
        self.set_status(label)
        threading.Thread(target=target, daemon=True).start()

    def run_process(self, cmd: list[str], label: str, success_message: str) -> None:
        def worker() -> None:
            self.safe(self.append, "Commande: " + " ".join(cmd) + "\n\n")
            try:
                process = subprocess.Popen(
                    cmd,
                    cwd=ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                assert process.stdout is not None
                for line in process.stdout:
                    self.safe(self.append, line)
                code = process.wait()
                if code == 0:
                    self.safe(self.set_status, "Termine.")
                    self.safe(messagebox.showinfo, "CHRUTH", success_message)
                else:
                    self.safe(self.set_status, f"Erreur code {code}.")
                    self.safe(messagebox.showerror, "CHRUTH", "Action echouee. Consultez le journal.")
            except Exception as exc:  # noqa: BLE001
                self.safe(self.append, f"\nERREUR: {exc}\n")
                self.safe(self.set_status, "Erreur.")
                self.safe(messagebox.showerror, "CHRUTH", str(exc))
            finally:
                self.safe(self.set_running, False)

        self.run_thread(label, worker)

    def pipeline_command(self) -> list[str]:
        cmd = [sys.executable, "CHRUTH_PIPELINE_UNIQUE.py"]
        if self.collect_ao.get():
            cmd.append("--collect-ao")
        if self.collect_prospects.get():
            cmd.extend(["--collect-prospects", "--scope", "france"])
        if self.generer_messages.get():
            cmd.append("--generer-messages")
        if self.creer_pack.get():
            cmd.extend(["--pack", "--package-dir", str(PACK_DIR)])
        return cmd

    # ------------------------------------------------------------- actions ---
    def generate_all(self) -> None:
        if self.collect_prospects.get():
            ok = messagebox.askyesno(
                "Collecte longue",
                "La recollecte prospects peut durer plusieurs dizaines de minutes. Continuer ?",
            )
            if not ok:
                return
        self.run_process(
            self.pipeline_command(),
            "Generation en cours...",
            "Generation terminee. Les documents sont dans output/.",
        )

    def generate_all_messages(self) -> None:
        cmd = [
            sys.executable,
            "CHRUTH_PIPELINE_UNIQUE.py",
            "--skip-ao",
            "--skip-finance",
            "--generer-messages",
        ]
        if self.creer_pack.get():
            cmd.extend(["--pack", "--package-dir", str(PACK_DIR)])
        self.run_process(
            cmd,
            "Generation des messages prospects...",
            "Messages prospects generes dans le classeur Base_Prospects_CHRUTH.xlsm.",
        )

    # --------------------------------------------------------------- email ---
    def load_email_config(self, silent: bool = False) -> None:
        try:
            import chruth_email

            data = chruth_email.read_secrets()
            user = str(data.get("smtp_user") or "")
            if user:
                self.smtp_user_var.set(user)
            if data.get("smtp_password"):
                self.smtp_password_var.set("__DEJA_CONFIGURE__")
            recipients = chruth_email.read_recipients()
            if recipients:
                self.recipient_var.set(recipients[0])
            ok, msg = chruth_email.config_ready()
            self.set_status("Email configure." if ok else msg)
            if not silent:
                messagebox.showinfo("Configuration email", "Configuration rechargee." if ok else msg)
        except Exception as exc:  # noqa: BLE001
            if not silent:
                messagebox.showerror("Configuration email", str(exc))

    def save_email_config(self) -> None:
        try:
            import chruth_email

            current = chruth_email.read_secrets()
            password = self.smtp_password_var.get().strip()
            if password == "__DEJA_CONFIGURE__":
                password = str(current.get("smtp_password") or "")
            chruth_email.save_secrets(self.smtp_user_var.get(), password)
            if self.recipient_var.get().strip():
                chruth_email.save_recipients(self.recipient_var.get())
            self.smtp_password_var.set("__DEJA_CONFIGURE__")
            self.set_status("Configuration email enregistree.")
            messagebox.showinfo("Configuration email", "Configuration enregistree localement.")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Configuration email", str(exc))

    def save_recipient(self) -> None:
        try:
            import chruth_email

            emails = chruth_email.save_recipients(self.recipient_var.get())
            self.recipient_var.set(emails[0])
            self.set_status("Destinataire enregistre.")
            messagebox.showinfo("Destinataire", "Destinataire enregistre.")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Destinataire", str(exc))

    def split_subject_body(self, text: str, fallback: str) -> tuple[str, str]:
        lines = [line.rstrip() for line in str(text or "").splitlines()]
        if lines and lines[0].lower().startswith("objet"):
            subject = lines[0].split(":", 1)[1].strip() if ":" in lines[0] else fallback
            body = "\n".join(lines[1:]).strip()
            return subject or fallback, body or text
        return fallback, str(text or "").strip()

    def load_email_from_prospect(self) -> None:
        text = self.prospect_email.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Email", "Aucun message prospect affiche.")
            return
        subject, body = self.split_subject_body(text, "CHRUTH - Entretien et proprete de vos locaux")
        self.email_subject_var.set(subject)
        self.set_text(self.email_body, body)
        self.tabs.select(self.tab_email)

    def load_email_from_ao(self) -> None:
        text = self.ao_email.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Email", "Aucun message AO affiche.")
            return
        subject, body = self.split_subject_body(text, "CHRUTH - Appel d'offres nettoyage")
        self.email_subject_var.set(subject)
        self.set_text(self.email_body, body)
        self.tabs.select(self.tab_email)

    def send_email_from_ui(self) -> None:
        recipient = self.recipient_var.get().strip()
        subject = self.email_subject_var.get().strip()
        body = self.email_body.get("1.0", "end").strip()
        if not body:
            messagebox.showwarning("Email", "Le message est vide.")
            return
        ok = messagebox.askyesno("Envoyer l'email", f"Envoyer cet email a {recipient} ?")
        if not ok:
            return

        def worker() -> None:
            try:
                import chruth_email

                self.safe(self.append, f"Envoi email a {recipient}...\n")
                chruth_email.send_email(recipient, subject, body)
                self.safe(self.append, "Email envoye.\n")
                self.safe(self.set_status, "Email envoye.")
                self.safe(messagebox.showinfo, "Email", "Email envoye.")
            except Exception as exc:  # noqa: BLE001
                self.safe(self.append, f"ERREUR EMAIL: {exc}\n")
                self.safe(self.set_status, "Erreur email.")
                self.safe(messagebox.showerror, "Email", str(exc))
            finally:
                self.safe(self.set_running, False)

        self.run_thread("Envoi email...", worker)

    def load_segments(self) -> None:
        try:
            import pandas as pd

            path = OUTPUT_DIR / "powerbi_sources" / "Prospects.csv"
            if not path.exists():
                path = OUTPUT_DIR / "prospects_enrichis.csv"
            if not path.exists():
                raise FileNotFoundError("Aucune source prospects trouvee dans output/.")
            try:
                df = pd.read_csv(path, dtype=str, sep=";").fillna("")
                if len(df.columns) <= 1:
                    df = pd.read_csv(path, dtype=str).fillna("")
            except Exception:
                df = pd.read_csv(path, dtype=str).fillna("")

            if "priorite" not in df.columns:
                raise ValueError("La source prospects ne contient pas encore la colonne priorite.")
            if "categorie_chruth" not in df.columns:
                raise ValueError("La source prospects ne contient pas categorie_chruth.")

            work = df[df["priorite"].astype(str).str.upper().isin(["CHAUDE", "TIEDE"])].copy()
            values = []
            rows = {}
            for _, row in work.iterrows():
                cat = str(row.get("categorie_chruth") or "").strip()
                prio = str(row.get("priorite") or "").strip().upper()
                if not cat or not prio:
                    continue
                key = f"{cat}|{prio}"
                if key not in rows:
                    rows[key] = row.to_dict()
                    values.append(key)
            values.sort()
            if not values:
                raise ValueError("Aucun segment CHAUDE/TIEDE trouve.")
            self.segment_values = values
            self.segment_rows = rows
            self.segment_combo.config(values=values)
            self.segment_var.set(values[0])
            self.fill_segment_example()
            self.append(f"{len(values)} segments prospects charges depuis {path.name}.\n")
            self.tabs.select(self.tab_log)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Segments prospects", str(exc))

    def fill_segment_example(self) -> None:
        key = self.segment_var.get()
        row = self.segment_rows.get(key, {})
        if row:
            self.denomination_var.set(str(row.get("denomination") or ""))
            self.ville_var.set(str(row.get("libelle_commune") or row.get("ville") or ""))
            self.effectif_var.set(str(row.get("effectif_label") or row.get("effectif_nombre") or ""))

    def generate_prospect_message(self) -> None:
        key = self.segment_var.get().strip()
        if not key or "|" not in key:
            messagebox.showwarning("Message prospect", "Charge ou selectionne d'abord un segment.")
            return
        cat, prio = key.split("|", 1)

        def worker() -> None:
            try:
                import prospect_messages as pm

                self.safe(self.append, f"Generation segment {cat} / {prio}...\n")
                templates = pm.generer_templates([(cat, prio)], refresh=True)
                tpl = templates[f"{cat}|{prio}"]
                row = {
                    "denomination": self.denomination_var.get(),
                    "libelle_commune": self.ville_var.get(),
                    "effectif_label": self.effectif_var.get(),
                }
                email = pm.rendre(tpl["email"], row)
                script = pm.rendre(tpl["script"], row)
                out = OUTPUT_DIR / "_message_prospect_segment.txt"
                out.parent.mkdir(exist_ok=True)
                out.write_text(
                    f"SEGMENT : {cat} / {prio}\nSOURCE : {tpl.get('source', '')}\n\n"
                    f"===== EMAIL =====\n{email}\n\n===== SCRIPT D'APPEL =====\n{script}\n",
                    encoding="utf-8",
                )
                self.safe(self.set_text, self.prospect_email, email)
                self.safe(self.set_text, self.prospect_script, script)
                subject, body = self.split_subject_body(email, "CHRUTH - Entretien et proprete de vos locaux")
                self.safe(self.email_subject_var.set, subject)
                self.safe(self.set_text, self.email_body, body)
                self.safe(self.append, f"Message prospect ecrit : {out}\n")
                self.safe(self.set_status, "Message prospect genere.")
            except Exception as exc:  # noqa: BLE001
                self.safe(messagebox.showerror, "Message prospect", str(exc))
                self.safe(self.append, f"ERREUR: {exc}\n")
            finally:
                self.safe(self.set_running, False)

        self.run_thread("Generation message prospect...", worker)

    def load_aos(self) -> None:
        try:
            from ao_config import AO_DB_PATH
            from ao_db import connect

            with connect(AO_DB_PATH) as conn:
                rows = conn.execute(
                    "SELECT * FROM ao_records WHERE priorite IN ('CHAUD','TIEDE') "
                    "ORDER BY CAST(score_chruth AS INTEGER) DESC LIMIT 200"
                ).fetchall()
            records = [dict(row) for row in rows]
            if not records:
                raise ValueError("Aucun AO CHAUD/TIEDE trouve. Lance d'abord la generation AO.")
            labels = []
            mapping = {}
            for rec in records:
                label = (
                    f"{rec.get('priorite','')} | {rec.get('score_chruth','')} | "
                    f"{str(rec.get('objet') or '')[:70]} | {str(rec.get('acheteur') or '')[:35]}"
                )
                labels.append(label)
                mapping[label] = rec
            self.ao_labels = labels
            self.ao_records = mapping
            self.ao_combo.config(values=labels)
            self.ao_var.set(labels[0])
            self.show_ao_details()
            self.append(f"{len(labels)} AO charges depuis la base SQLite.\n")
            self.tabs.select(self.tab_log)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Appels d'offres", str(exc))

    def show_ao_details(self) -> None:
        rec = self.ao_records.get(self.ao_var.get(), {})
        keys = ["id_ao", "priorite", "score_chruth", "objet", "acheteur", "ville", "date_limite", "budget_annuel_eur", "url_avis"]
        text = "\n".join(f"{k}: {rec.get(k, '')}" for k in keys)
        self.set_text(self.ao_details, text)

    def generate_ao_message(self) -> None:
        rec = self.ao_records.get(self.ao_var.get())
        if not rec:
            messagebox.showwarning("Message AO", "Charge ou selectionne d'abord un AO.")
            return

        def worker() -> None:
            try:
                import ao_messages
                from outils.generer_message_ao import formater

                self.safe(self.append, f"Generation message AO {rec.get('id_ao', '')}...\n")
                msg = ao_messages.generer_message_ao(rec)
                out = OUTPUT_DIR / "_message_ao.txt"
                out.parent.mkdir(exist_ok=True)
                out.write_text(formater(rec, msg), encoding="utf-8")
                self.safe(self.set_text, self.ao_email, msg.get("email", ""))
                self.safe(self.set_text, self.ao_script, msg.get("script", ""))
                subject, body = self.split_subject_body(msg.get("email", ""), "CHRUTH - Appel d'offres nettoyage")
                self.safe(self.email_subject_var.set, subject)
                self.safe(self.set_text, self.email_body, body)
                self.safe(self.append, f"Message AO ecrit : {out}\n")
                self.safe(self.set_status, "Message AO genere.")
            except Exception as exc:  # noqa: BLE001
                self.safe(messagebox.showerror, "Message AO", str(exc))
                self.safe(self.append, f"ERREUR: {exc}\n")
            finally:
                self.safe(self.set_running, False)

        self.run_thread("Generation message AO...", worker)

    # --------------------------------------------------------------- files ---
    def set_text(self, widget: scrolledtext.ScrolledText, text: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", text)

    def copy_text(self, widget: scrolledtext.ScrolledText) -> None:
        text = widget.get("1.0", "end").strip()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.set_status("Texte copie.")

    def open_output(self) -> None:
        OUTPUT_DIR.mkdir(exist_ok=True)
        subprocess.Popen(["explorer", str(OUTPUT_DIR)])

    def open_file(self, path: Path) -> None:
        if not path.exists():
            messagebox.showwarning("Fichier introuvable", str(path))
            return
        if path.is_dir():
            subprocess.Popen(["explorer", str(path)])
            return
        try:
            subprocess.Popen(["cmd", "/c", "start", "", str(path)], cwd=ROOT, shell=False)
        except Exception:
            subprocess.Popen(["explorer", str(path.parent)])

    def open_source_pdf(self) -> None:
        candidates = [
            ROOT / "docs" / "source" / "Fiche de poste CHRUTH.pdf",
            ROOT.parent / "Fiche de poste CHRUTH.pdf",
            Path(__file__).resolve().parent / "docs" / "source" / "Fiche de poste CHRUTH.pdf",
        ]
        for path in candidates:
            if path.exists():
                self.open_file(path)
                return
        messagebox.showwarning("Fiche de poste", "Fiche de poste CHRUTH.pdf introuvable.")

    def launch_streamlit_messages(self) -> None:
        # Point d'entree unique : veille + messages sont deux pages de la meme app.
        app = ROOT / "CHRUTH_APP.py"
        if not app.exists():
            messagebox.showwarning("App CHRUTH", "CHRUTH_APP.py introuvable.")
            return
        try:
            subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", str(app)],
                cwd=ROOT,
                creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
            )
            self.set_status("Application CHRUTH lancee (veille + messages).")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("App messages", str(exc))


if __name__ == "__main__":
    App().mainloop()
