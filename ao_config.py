from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"

AO_DB_PATH = DATA_DIR / "ao_chruth.sqlite"
AO_RAW_DIR = DATA_DIR / "ao_raw"
AO_OUTPUT_XLSX = OUTPUT_DIR / "AO_CHRUTH.xlsx"

ASSETS_DIR = BASE_DIR / "assets"
AO_TEMPLATE_XLSM = ASSETS_DIR / "AO_CHRUTH_TEMPLATE.xlsm"
AO_OUTPUT_XLSM = OUTPUT_DIR / "AO_CHRUTH.xlsm"

# Dossier partage (OneDrive/SharePoint synchronise localement) ou publier les
# livrables. Vide = etape de publication ignoree. Surcharge par l'environnement
# CHRUTH_DOSSIER_PARTAGE (utile en CI / tache planifiee).
DOSSIER_PARTAGE = ""

BOAMP_API_URL = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records"
REQUEST_TIMEOUT_SECONDS = 30
REQUEST_USER_AGENT = "CHRUTH-AO-Pipeline/1.0"

# Le budget est rarement disponible dans un champ propre. On garde les AO sans
# montant explicite, mais ils seront marques A_VERIFIER_BUDGET.
AO_BUDGET_MIN_EUR = 100_000
AO_KEEP_UNKNOWN_BUDGET = True

# Limites par defaut pour eviter de surcharger l'IA et le fichier Excel.
AO_API_PAGE_LIMIT = 100
AO_MAX_PAGES = 100          # plafond securite (API: offset + limit <= 10000)
AO_MAX_EXPORT_ROWS = 100    # cap export releve (les 100 meilleurs AO de la fenetre)
AO_LOOKBACK_DAYS = 14       # fenetre de collecte (jours, rolling)
AO_API_OFFSET_CAP = 10000   # plafond dur de l'API Opendatasoft

# Zone de scoring principale demandee pour CHRUTH.
IDF_DEPARTEMENTS = ["75", "77", "78", "91", "92", "93", "94", "95"]
PRIORITY_DEPARTEMENTS = IDF_DEPARTEMENTS
NEAR_IDF_DEPARTEMENTS = ["02", "27", "28", "45", "51", "60", "76", "89"]

# Zone IDF activee par defaut (le client ne veut que l'Ile-de-France).
AO_IDF_ONLY = True

# Mots-cles resserres sur le nettoyage (suppression des termes trop larges).
AO_KEYWORDS_CORE = [
    "nettoyage",
    "proprete",
    "entretien des locaux",
    "entretien locaux",
    "nettoyage de vitres",
    "bionettoyage",
    "menage",
    "hygiene des locaux",
]

AO_KEYWORDS_SECONDARY = [
    "entretien menager",
    "proprete des locaux",
    "desinfection",
]

# Seuils budget ANNUALISE (EUR) : score strictement decroissant.
# (montant, points) — la borne est un plafond "<=".
AO_BUDGET_SCORE_BANDS = [
    (50_000, 25),
    (100_000, 20),
    (200_000, 5),
    (500_000, -10),
]
AO_BUDGET_SCORE_ABOVE = -20      # au-dela de la derniere borne
AO_BUDGET_SCORE_UNKNOWN = 10     # budget non affiche (frequent en MAPA), non penalisant

# Categorisation nettoyage demandee par le client.
AO_CATEGORIE_VITRES = ["vitre", "vitrerie", "vitree", "vitres"]
AO_CATEGORIE_BUREAUX = ["bureau", "bureaux"]
AO_CATEGORIE_BATIMENTS = ["batiment", "locaux", "immeuble", "site", "ecole", "gymnase"]

# Secteurs cibles (bonus de score, jamais un filtre).
AO_SECTEURS = {
    "Ecole": ["ecole", "college", "lycee", "groupe scolaire", "scolaire", "creche"],
    "Mairie": ["mairie", "commune de", "ville de", "communaute de communes", "ccas"],
    "Batiment administratif": ["prefecture", "administration", "services techniques", "ministere", "tresorerie"],
    "Gymnase": ["gymnase", "complexe sportif", "salle de sport", "stade"],
    "Mediatheque": ["mediatheque", "bibliotheque", "ludotheque"],
}

# Exclusions DURES : ecartent l'AO meme si "nettoyage" figure dans l'objet
# (activites hors cible CHRUTH qui contiennent souvent le mot nettoyage :
# voirie, graffitis, CVC, fourniture de produits/materiels...).
AO_EXCLUSION_DURES = [
    "voirie",
    "nettoiement de la voirie",
    "demolition",
    "deratisation",
    "desinsectisation",
    "desinsectation",
    "graffiti",
    "affiches sauvages",
    "meubles meublants",
    "mobilier urbain",
    "materiels sportifs",
    "materiel sportif",
    "acquisition de materiels",
    "cvc",
    "traitement d'air",
    "eau chaude sanitaire",
    "therapie cellulaire",
    "fourniture de produits",
    "fourniture et livraison de produits",
    "equipements de nettoyage",
    "equipement de nettoyage",
    # Faux positifs signales : objet hors-cible (chauffage, reseaux, boitage,
    # restauration, gestion d'etablissement, dechets) avec un mot "nettoyage"
    # incident dans le detail. Termes cibles sur l'ACTIVITE (anti-regression verifiee :
    # n'ecartent pas un vrai AO nettoyage de creche / avec gestion des poubelles).
    "chauffage",
    "vmc",
    "fraisage",
    "eu-ev-ep",
    "pompes de relevage",
    "boitage",
    "adressage",
    "restauration collective",
    "gestion de l'etablissement",
    "sensibilisation",
    "prevention et la gestion des dechets",
]

# Exclusions SOUPLES : ecartent seulement si AUCUN mot-cle nettoyage fort n'est present.
AO_EXCLUSION_KEYWORDS = [
    "travaux routiers",
    "alimentation en eau",
    "reseau d'eau",
    "electricite",
    "construction neuve",
    "liaison froide",
    "repas",
    "denrees alimentaires",
    "restauration collective",
    "fouilles archeologiques",
    "etudes geotechniques",
    "maitrise d'oeuvre",
    "produits d'incontinence",
]

AO_PRIORITY_LABELS = {
    "CHAUD": 65,
    "TIEDE": 40,
    "FROID": 0,
}

CRM_TRACKING_COLUMNS = {
    "statut_contact": "A verifier",
    "responsable": "",
    "date_contact": "",
    "date_relance": "",
    "reponse": "",
    "rdv_obtenu": "",
    "commentaire_humain": "",
}

# --- Alertes email (Phase 2) ---
ALERTE_SMTP_HOST = "smtp.gmail.com"
ALERTE_SMTP_PORT = 587
ALERTE_SECRETS_FILE = BASE_DIR / "alertes_secrets.json"
# Liste des destinataires (une adresse par ligne). Ajouter une ligne = un destinataire de plus.
ALERTE_DESTINATAIRES_FILE = BASE_DIR / "destinataires.txt"
ALERTE_PRIORITES = ("CHAUD", "TIEDE")

# Drapeau ON/OFF des alertes email, pilote par le bouton du cockpit Excel.
# Source de verite PERSISTANTE : ce fichier survit a la regeneration du tableur
# (le tableur est recree depuis le template a chaque refresh, donc la cellule
# Parametres!B2 ne sert que d'affichage / de bouton).
ALERTE_ACTIVE_FILE = BASE_DIR / "alertes_actives.flag"
COLLECTE_ACTIVE_FILE = BASE_DIR / "collecte_active.flag"


def notifications_actives(flag_file: Path = ALERTE_ACTIVE_FILE) -> bool:
    """True si les alertes email sont activees. Defaut : actives si le fichier manque."""
    try:
        return Path(flag_file).read_text(encoding="utf-8").strip().upper() != "OFF"
    except FileNotFoundError:
        return True


def set_notifications(actif: bool, flag_file: Path = ALERTE_ACTIVE_FILE) -> None:
    """Persiste l'etat ON/OFF des alertes email."""
    Path(flag_file).write_text("ON" if actif else "OFF", encoding="utf-8")


def collecte_active(flag_file: Path = COLLECTE_ACTIVE_FILE) -> bool:
    """True si la collecte reseau est activee. Defaut : active si le fichier manque."""
    try:
        return Path(flag_file).read_text(encoding="utf-8").strip().upper() != "OFF"
    except FileNotFoundError:
        return True


def set_collecte(actif: bool, flag_file: Path = COLLECTE_ACTIVE_FILE) -> None:
    """Persiste l'etat ON/OFF de la collecte reseau."""
    Path(flag_file).write_text("ON" if actif else "OFF", encoding="utf-8")


# Emplacement de la liste de destinataires dans l'onglet Parametres du cockpit
# (l'utilisateur saisit une adresse par cellule, le bouton "Enregistrer" persiste
# vers destinataires.txt, et l'export repeuple la colonne au refresh suivant).
PARAM_DEST_COL = "B"
PARAM_DEST_FIRST_ROW = 5
PARAM_DEST_MAX = 50  # garde-fou de lecture / nettoyage de la colonne
