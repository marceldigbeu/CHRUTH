import math

CODES_NAF = {
    "84.11Z": {"label": "Administration publique générale", "cible": "PUB_MAIRIE", "priorite": 3},
    "85.10Z": {"label": "Enseignement pré-primaire", "cible": "PUB_ECOLE", "priorite": 3},
    "85.20Z": {"label": "Enseignement primaire", "cible": "PUB_ECOLE", "priorite": 3},
    "86.10Z": {"label": "Activités hospitalières", "cible": "PUB_HOPITAL", "priorite": 3},
    "86.21Z": {"label": "Pratique médicale générale", "cible": "PRIV_SANTE_CABINET", "priorite": 2},
    "86.22Z": {"label": "Pratique médicale spécialisée", "cible": "PRIV_SANTE_CABINET", "priorite": 2},
    "86.90F": {"label": "Autres activités santé", "cible": "PRIV_SANTE_CENTRE", "priorite": 2},
    "91.01Z": {"label": "Gestion des bibliothèques", "cible": "PUB_MUSEE", "priorite": 2},
    "91.02Z": {"label": "Gestion des musées", "cible": "PUB_MUSEE", "priorite": 2},
    "93.29Z": {"label": "Activités récréatives", "cible": "PRIV_LOISIRS", "priorite": 2},
    "68.20A": {"label": "Location de logements", "cible": "IMMO_LOCATION", "priorite": 2},
    "68.31Z": {"label": "Agences immobilières", "cible": "IMMO_AGENCE", "priorite": 2},
    "82.11Z": {"label": "Services administratifs combinés", "cible": "PRIV_BUREAU", "priorite": 2},
    "56.10A": {"label": "Restauration traditionnelle", "cible": "PRIV_RESTAURANT", "priorite": 1},
    "47.11D": {"label": "Centres commerciaux", "cible": "PRIV_COMMERCE", "priorite": 2},
}

NAF_EXCLUS = {"81.21Z", "81.22Z", "81.29Z"}

# Classification robuste par PREFIXE NAF (4 premiers caracteres significatifs).
# L'API renvoie souvent des sous-codes ou d'anciens codes NAF au niveau
# etablissement (85.1C, 86.22C, 86.90D...) qui ne matchent pas le code recherche.
# On classe sur la FAMILLE NAF -> categorie CHRUTH stable.
NAF_PREFIX_MAP = {
    "84.1": ("PUB_MAIRIE", "Administration publique"),
    "85.1": ("PUB_ECOLE", "Enseignement primaire/maternelle"),
    "85.2": ("PUB_ECOLE", "Enseignement primaire"),
    "86.1": ("PUB_HOPITAL", "Activités hospitalières"),
    "86.2": ("PRIV_SANTE_CABINET", "Pratique médicale"),
    "86.9": ("PRIV_SANTE_CENTRE", "Autres activités santé"),
    "91.0": ("PUB_MUSEE", "Bibliothèques / musées"),
    "93.2": ("PRIV_LOISIRS", "Activités récréatives"),
    "68.2": ("IMMO_LOCATION", "Location de logements"),
    "68.3": ("IMMO_AGENCE", "Agences immobilières"),
    "82.1": ("PRIV_BUREAU", "Services administratifs / bureaux"),
    "56.1": ("PRIV_RESTAURANT", "Restauration"),
    "47.1": ("PRIV_COMMERCE", "Commerce / centres commerciaux"),
}

# Codes tranche effectif INSEE -> (libelle lisible, effectif representatif).
# C'est le format REEL renvoye par l'API (et non les libelles).
# "NN" = non renseigne / non employeur.
TRANCHE_EFFECTIF = {
    "NN": ("Non renseigné", -1),
    "00": ("0 salarié", 0),
    "01": ("1 à 2 salariés", 2),
    "02": ("3 à 5 salariés", 5),
    "03": ("6 à 9 salariés", 9),
    "11": ("10 à 19 salariés", 19),
    "12": ("20 à 49 salariés", 49),
    "21": ("50 à 99 salariés", 99),
    "22": ("100 à 199 salariés", 199),
    "31": ("200 à 249 salariés", 249),
    "32": ("250 à 499 salariés", 499),
    "41": ("500 à 999 salariés", 999),
    "42": ("1000 à 1999 salariés", 1999),
    "51": ("2000 à 4999 salariés", 4999),
    "52": ("5000 à 9999 salariés", 9999),
    "53": ("10000 salariés et plus", 10000),
}

EXCLUSION_KEYWORDS = [
    r"désinfect", r"desinfect",
    r"désinsectis", r"desinsectis",
    r"dératis", r"deratis",
    r"crime", r"sinistre",
    r"funéraire", r"pompes funèbres",
]

SEUILS_SCORE = {"CHAUDE": 70, "TIEDE": 40, "FROIDE": 0}

# Poids effectif base sur l'effectif representatif (decode depuis le code INSEE).
# Remplace l'ancien dict par libelles, qui ne matchait jamais les codes API.
def poids_effectif(n: int) -> int:
    if n >= 50:
        return 30
    if n >= 20:
        return 25
    if n >= 10:
        return 20
    if n >= 6:
        return 15
    if n >= 3:
        return 10
    if n >= 1:
        return 5
    return 0  # 0 salarie ou non renseigne (-1)

POIDS_CATEGORIE = {
    "PUB_MAIRIE": 25,
    "PUB_ECOLE": 25,
    "PUB_HOPITAL": 30,
    "PUB_MUSEE": 20,
    "PRIV_SANTE_CENTRE": 25,
    "PRIV_SANTE_CABINET": 20,
    "PRIV_BUREAU": 15,
    "PRIV_COMMERCE": 15,
    "PRIV_LOISIRS": 12,
    "PRIV_RESTAURANT": 10,
    "IMMO_AGENCE": 10,
    "IMMO_LOCATION": 15,
    "AUTRE": 5,
}

REGIONS_BONUS = [
    "Île-de-France",
    "Auvergne-Rhône-Alpes",
    "Provence-Alpes-Côte d'Azur",
    "Nouvelle-Aquitaine",
    "Occitanie",
]

DEPARTEMENTS_TEST = ["69"]

DEPARTEMENTS_FRANCE = [
    "01","02","03","04","05","06","07","08","09","10","11","12","13","14","15","16","17","18","19",
    "2A","2B","21","22","23","24","25","26","27","28","29","30","31","32","33","34","35","36","37",
    "38","39","40","41","42","43","44","45","46","47","48","49","50","51","52","53","54","55","56",
    "57","58","59","60","61","62","63","64","65","66","67","68","69","70","71","72","73","74","75",
    "76","77","78","79","80","81","82","83","84","85","86","87","88","89","90","91","92","93","94",
    "95","971","972","973","974","975","976",
]

API_BASE_URL = "https://recherche-entreprises.api.gouv.fr/search"
API_PER_PAGE = 25
REQUEST_DELAY_SECONDS = 0.15
REQUEST_USER_AGENT = "CHRUTH-DataPipeline/1.0 (internship-project)"
REQUEST_MAX_RETRIES = 3
REQUEST_RETRY_BACKOFF_SECONDS = 1.5

REGION_MAPPING = {
    "11": "Île-de-France",
    "84": "Auvergne-Rhône-Alpes",
    "93": "Provence-Alpes-Côte d'Azur",
    "75": "Nouvelle-Aquitaine",
    "76": "Occitanie",
    "32": "Hauts-de-France",
    "44": "Grand Est",
    "52": "Pays de la Loire",
    "53": "Bretagne",
    "24": "Centre-Val de Loire",
    "28": "Normandie",
    "27": "Bourgogne-Franche-Comté",
    "94": "Corse",
    "01": "Guadeloupe",
    "02": "Martinique",
    "03": "Guyane",
    "04": "La Réunion",
    "06": "Mayotte",
}

# Region (nom) -> liste de departements. Permet une collecte "par zone" lisible
# pour un non-codeur : --scope region --regions "Île-de-France".
# Les accents sont normalises a la selection (voir normaliser_region).
REGIONS_DEPARTEMENTS = {
    "Île-de-France": ["75", "77", "78", "91", "92", "93", "94", "95"],
    "Auvergne-Rhône-Alpes": ["01", "03", "07", "15", "26", "38", "42", "43", "63", "69", "73", "74"],
    "Provence-Alpes-Côte d'Azur": ["04", "05", "06", "13", "83", "84"],
    "Nouvelle-Aquitaine": ["16", "17", "19", "23", "24", "33", "40", "47", "64", "79", "86", "87"],
    "Occitanie": ["09", "11", "12", "30", "31", "32", "34", "46", "48", "65", "66", "81", "82"],
    "Hauts-de-France": ["02", "59", "60", "62", "80"],
    "Grand Est": ["08", "10", "51", "52", "54", "55", "57", "67", "68", "88"],
    "Pays de la Loire": ["44", "49", "53", "72", "85"],
    "Bretagne": ["22", "29", "35", "56"],
    "Centre-Val de Loire": ["18", "28", "36", "37", "41", "45"],
    "Normandie": ["14", "27", "50", "61", "76"],
    "Bourgogne-Franche-Comté": ["21", "25", "39", "58", "70", "71", "89", "90"],
    "Corse": ["2A", "2B"],
    "Guadeloupe": ["971"],
    "Martinique": ["972"],
    "Guyane": ["973"],
    "La Réunion": ["974"],
    "Mayotte": ["976"],
}


def normaliser_region(nom: str) -> str:
    """Rend la saisie d'une region tolerante aux accents/casse/tirets.
    Renvoie le nom canonique (cle de REGIONS_DEPARTEMENTS) ou "" si inconnu."""
    def _clef(s: str) -> str:
        s = (s or "").strip().lower()
        accents = "àâäáãéèêëíìîïóòôöõúùûüç'’- "
        nus =     "aaaaaeeeeiiiiooooouuuuc      "
        table = {ord(a): n for a, n in zip(accents, nus)}
        return s.translate(table).replace(" ", "")
    cible = _clef(nom)
    for canonique in REGIONS_DEPARTEMENTS:
        if _clef(canonique) == cible:
            return canonique
    return ""


def departements_des_regions(noms: list[str]) -> list[str]:
    """Aplati une liste de noms de regions en liste de departements (dedupliquee, ordonnee)."""
    vus: list[str] = []
    inconnues: list[str] = []
    for nom in noms:
        canonique = normaliser_region(nom)
        if not canonique:
            inconnues.append(nom)
            continue
        for dept in REGIONS_DEPARTEMENTS[canonique]:
            if dept not in vus:
                vus.append(dept)
    if inconnues:
        valides = ", ".join(REGIONS_DEPARTEMENTS.keys())
        raise ValueError(
            f"Region(s) inconnue(s) : {', '.join(inconnues)}. Valeurs possibles : {valides}"
        )
    return vus


# --- Filtre de prospection (catégories ciblées) ---
# Le client cible : agences immo, centres de santé, cabinets médicaux, écoles,
# bureaux, musées, restaurants, commerces, loisirs, hôpitaux, mairies.
# On retire la location immobilière (volume énorme, hors cible) et les non classés.
CATEGORIES_EXCLUES_PROSPECTION = {"IMMO_LOCATION", "AUTRE"}


# --- Proximite au siege CHRUTH (60 rue François Ier, Paris 8e) ---
# Pour une societe de nettoyage, la distance au siege = capacite a servir le
# client. On l'injecte dans le scoring via des bandes alignees sur les cercles
# de la carte (5/10/20/30/50 km). Coordonnees figees (deterministe, sans reseau).
CHRUTH_SIEGE_LAT = 48.869893
CHRUTH_SIEGE_LON = 2.30194


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p = math.radians
    dlat, dlon = p(lat2 - lat1), p(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p(lat1)) * math.cos(p(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def distance_au_siege(lat, lon) -> float:
    """Distance (km) entre un prospect et le siege CHRUTH. NaN si coords absentes."""
    try:
        latf, lonf = float(lat), float(lon)
    except (TypeError, ValueError):
        return float("nan")
    if math.isnan(latf) or math.isnan(lonf) or (latf == 0 and lonf == 0):
        return float("nan")
    return haversine_km(CHRUTH_SIEGE_LAT, CHRUTH_SIEGE_LON, latf, lonf)


def poids_proximite(km: float) -> int:
    """Bandes de proximite au siege (alignees sur les cercles de la carte).
    Coords absentes (NaN) => 0 (on ne penalise pas, mais aucun bonus)."""
    if km != km:  # NaN
        return 0
    if km <= 5:
        return 30
    if km <= 10:
        return 25
    if km <= 20:
        return 20
    if km <= 30:
        return 12
    if km <= 50:
        return 5
    return 0


# (EFFECTIF_MAPPING supprime : remplace par TRANCHE_EFFECTIF, format reel de l'API.)


# --- Rentabilite estimee par segment (Mission 4 - modele a priori, SANS donnees clients) ---
# HYPOTHESES A AJUSTER avec l'entreprise : cout annuel moyen d'une prestation de
# nettoyage par salarie (EUR), proxy du CA potentiel (le nettoyage croit avec
# l'effectif / la surface occupee). Ce ne sont PAS des donnees reelles.
TARIF_NETTOYAGE_PAR_SALARIE = {
    "PRIV_BUREAU": 600,
    "PRIV_COMMERCE": 500,
    "PRIV_RESTAURANT": 700,
    "PRIV_LOISIRS": 550,
    "PRIV_SANTE_CABINET": 900,
    "PRIV_SANTE_CENTRE": 950,
    "PUB_HOPITAL": 1000,
    "PUB_ECOLE": 500,
    "PUB_MAIRIE": 550,
    "PUB_MUSEE": 650,
    "IMMO_AGENCE": 500,
}
TARIF_NETTOYAGE_DEFAUT = 500
# Marge brute estimee sur une prestation de nettoyage (hypothese a ajuster).
TAUX_MARGE_NETTOYAGE = 0.20


# --- Modele financier previsionnel (HYPOTHESES A VALIDER avec CHRUTH) ---
# Aucune donnee reelle : ce sont des hypotheses ajustables pour la projection.
PREV_HORIZON_MOIS = 12                 # duree de la projection (1 exercice = 12 mois)
PREV_ANNEE_EXERCICE = 2026             # annee civile de l'exercice (Janvier -> Decembre)
PREV_CONTACTS_PAR_MOIS = 100           # prospects reellement travailles / mois
PREV_TAUX_CONVERSION = 0.03            # part des contacts qui deviennent clients (3%)
PREV_PANIER_MOYEN_ANNUEL_EUR = 8000    # CA annuel moyen par client
PREV_COUT_VARIABLE_PCT = 0.75          # couts variables (main d'oeuvre, produits) en % du CA
PREV_COUTS_FIXES_MENSUELS_EUR = 3000   # charges fixes mensuelles (structure)
PREV_CHURN_MENSUEL = 0.02              # clients perdus par mois (2%)

# CAPEX / actualisation / fiscalite (hypotheses a valider)
PREV_CAPEX_INITIAL_EUR = 20000     # investissement de depart (materiel, lancement)
PREV_TAUX_ACTUALISATION = 0.10     # taux d'actualisation annuel (pour la VAN)
PREV_TAUX_IS = 0.25                # taux d'imposition sur les benefices
PREV_AMORT_MOIS = 24               # duree d'amortissement du CAPEX (mois)
# Scenarios : (conversion, panier_annuel, cout_variable_pct, couts_fixes_mensuels)
PREV_SCENARIOS = {
    "Pessimiste": (0.02, 6000, 0.80, 3500),
    "Realiste":   (0.03, 8000, 0.75, 3000),
    "Optimiste":  (0.05, 10000, 0.70, 2800),
}
PREV_SCENARIO_DEFAUT = "Realiste"

# --- Rentabilite par marche (simulateur bottom-up par contrat de nettoyage) ---
# Demande Sonia (2026-06-23). Valeurs PLACEHOLDER de test, a ajuster.
# Charges fixes ENTREPRISE (mensuelles, EUR) — liste exacte demandee.
MARCHE_CHARGES_FIXES = {
    "Logiciel de paie": 40,
    "Service Star": 50,
    "Suite Google": 12,
    "Assurance professionnelle - bureau": 80,
    "Assurance professionnelle - Chruth": 120,
    "Hebergement": 20,
    "Internet": 40,
    "Eco-pepiniere (loyer)": 300,
    "Produits de nettoyage (stock structure)": 150,
    "Salaires (structure / encadrement)": 2500,
}

# Hypotheses de calcul par marche (editables dans le tableur).
MARCHE_TAUX_HORAIRE_JOUR = 18       # cout horaire agent charge, intervention de jour
MARCHE_TAUX_HORAIRE_NUIT = 23       # cout horaire agent charge, intervention de nuit (majore)
MARCHE_SEMAINES_PAR_MOIS = 4.33     # annualisation des jours/semaine -> mensuel
MARCHE_COUT_PRODUITS_DEFAUT = 60    # cout produits/mois si fournis par nous (defaut)
MARCHE_TAUX_MARGE_CIBLE = 0.20      # marge cible de reference (repere)
MARCHE_LIGNES_VIDES = 4             # lignes vides ajoutees sous les exemples

# Marches exemples (valeurs de test ajustables). Prix calibres pour un cout
# horaire charge ~18 EUR jour / 23 EUR nuit : la plupart sont rentables, un
# (Centre commercial Bobigny) est volontairement deficitaire pour illustrer la
# detection (marge rouge) et le point mort.
# (nom, jours_sem, heures_jour, effectif, type, produits, cout_produits_mois, prix_mois, amortissement_mois)
MARCHE_EXEMPLES = [
    ("Bureaux Levallois",         5, 3, 2, "Jour", "Nous",   60,  3000,  50),
    ("Clinique Paris 12 (nuit)",  6, 4, 3, "Nuit", "Client",  0,  8500, 120),
    ("Ecole primaire Montreuil",  4, 2, 2, "Jour", "Nous",    80, 1600,  40),
    ("Centre commercial Bobigny", 7, 5, 4, "Nuit", "Nous",   200, 13000, 150),
    ("Cabinet medical Neuilly",   3, 2, 1, "Jour", "Client",  0,   650,  20),
    ("Mairie annexe Pantin",      5, 3, 2, "Jour", "Nous",    70,  2900,  60),
    ("Restaurant Bastille",       6, 2, 1, "Nuit", "Nous",    50,  1500,  30),
    ("Coworking Republique",      5, 4, 3, "Jour", "Client",  0,  5500,  80),
]
