# Acheteurs actifs de la semaine — nouveau livrable Prospects

Date : 2026-07-27

## Problème

Le pipeline Prospects actuel collecte **toutes les entreprises d'Île-de-France**
par code d'activité (≈132 000 sociétés via l'API Recherche Entreprises), puis les
score et les cartographie. C'est lourd, large, et déconnecté du besoin réel : la
plupart de ces sociétés n'ont aucun marché en cours.

Décision de l'utilisateur : **à chaque mise à jour hebdomadaire, le livrable
Prospects ne doit contenir que les acheteurs ayant publié un appel d'offres de
propreté dans les 7 derniers jours.** Ce sont des cibles chaudes, avec un besoin
présent, dérivées directement du flux de veille — pas d'une collecte France.

## Objectif

Produire chaque semaine la liste des **acheteurs actifs** (organisations ayant
publié un AO propreté pertinent sur 7 jours glissants), dédoublonnés, **classés
public / privé-droit**, **enrichis** (adresse, contact, effectif) via leur SIRET,
et exposés à la fois comme **page de la plateforme** et comme **fichier exporté**.
Ce livrable **remplace** l'ancienne logique « toutes les entreprises IDF » comme
source de prospection ; l'ancien pipeline est **mis en sommeil** (code et livrables
conservés, plus déclenché comme mise à jour Prospects).

## Décisions (validées)

| Sujet | Choix |
|---|---|
| Fenêtre | AO publiés dans les **7 derniers jours** (glissants) |
| Pertinence | Seuls les AO jugés **PERTINENT** (propreté), rejetés exclus |
| Sources | **BOAMP** (`ao_db`) + **Maximilien** (`veille_depot`) ; JOUE/TED quand la source existera |
| Dédoublonnage | par **SIRET** si présent, sinon nom d'acheteur normalisé + département |
| Enrichissement | **oui**, par SIRET → adresse, contact, effectif, nature juridique |
| Classification | **public / privé-droit**, déduite de la catégorie juridique (issue de l'enrichissement) |
| Livraison | **page plateforme** (Streamlit + HTML) **+ export** Excel/CSV |
| Cadence | **hebdomadaire**, tâche planifiée Windows (lundi matin) |
| Ancien pipeline | **en sommeil** (non supprimé) |

## Architecture

Un module métier pur, une page de surface, un export, une planification. Le module
ne connaît ni Streamlit ni le réseau au-delà de l'enrichissement isolé.

| Unité | Fichier | Rôle |
|---|---|---|
| Cœur métier | `acheteurs_semaine.py` *(nouveau)* | collecte AO récents → acheteurs dédoublonnés → enrichis → classés → DataFrame |
| Enrichissement SIRET | `collect_api_entreprises.py` *(étendu)* | `fetch_by_siret(siret)` : une fiche entreprise via l'API Recherche Entreprises |
| Export fichier | `acheteurs_semaine.py` | `exporter(df, xlsx_path, csv_path)` |
| Page Streamlit | `pages_acheteurs.py` *(nouveau)* + `CHRUTH_APP.py` | page « Acheteurs de la semaine » |
| Page HTML | `CHRUTH_PLATEFORME.html` *(étendu)* | même vue dans la copie HTML |
| Planification | `outils/installer_tache_acheteurs.ps1` *(nouveau)* | tâche hebdo lundi 08:45 |

### Modèle de données (une ligne = un acheteur)

```
acheteur, siret, siren, type (public|prive), categorie_juridique, nature_juridique_libelle,
adresse, code_postal, ville, departement, effectif,
nb_ao_semaine, aos (liste: objet, date_publication, priorite, url), source, enrichi (bool)
```

### 1. Collecte des AO récents (`acheteurs_semaine.collecter_aos_recents`)

```python
def collecter_aos_recents(jours: int = 7, aujourd_hui: date | None = None) -> list[dict]:
    """AO PERTINENT publiés dans la fenêtre, depuis BOAMP + Maximilien."""
```

- BOAMP : `ao_db.fetch_records()` → filtrer `priorite` pertinente et
  `date_publication >= aujourd_hui - jours`. Champs : acheteur, siret_acheteur,
  siren_acheteur, ville, departement, date_publication, url_avis, priorite, objet.
- Maximilien : `veille_depot.lire()` → `aos` dont `veille_etat.verdict_effectif(e)
  == "PERTINENT"` et `date_publication` dans la fenêtre. Pas de SIRET (nom seul).
- Date manquante : **exclue** de ce livrable (la fenêtre est le cœur du besoin) —
  contrairement au tri, où le doute profite à l'AO.
- Fenêtre par défaut 7 jours ; paramétrable (constante `FENETRE_JOURS = 7`).

### 2. Extraction des acheteurs (`extraire_acheteurs`)

```python
def extraire_acheteurs(aos: list[dict]) -> list[dict]:
    """Dédoublonne par SIRET (sinon nom normalisé + dept) et agrège les AO."""
```

- Clé : `siret` s'il existe, sinon `f"{normalize_text(acheteur)}|{departement}"`.
- Agrège : `nb_ao_semaine`, liste `aos` (objet, date, priorité, url), meilleure
  priorité (CHAUD > TIÈDE).

### 3. Enrichissement par SIRET (`collect_api_entreprises.fetch_by_siret`)

```python
def fetch_by_siret(siret: str) -> dict | None:
    """Une fiche entreprise via l'API Recherche Entreprises (q=<siret>). None si absente/réseau KO."""
```

- Renvoie adresse, code postal, ville, `tranche_effectif_salarie`,
  **`nature_juridique`** (code catégorie juridique INSEE) + libellé.
- `enrichir(acheteur)` best-effort : un échec réseau laisse l'acheteur non enrichi
  (`enrichi=False`) sans casser le livrable ; un délai `REQUEST_DELAY_SECONDS`
  entre appels (comme la collecte existante).
- Acheteurs sans SIRET (Maximilien) : non enrichis, gardés avec leurs infos d'AO.

### 4. Classification public / privé-droit (`classer`)

```python
def classer(nature_juridique: str) -> str:
    """'public' si personne morale de droit public, sinon 'prive'."""
```

- Règle : catégorie juridique INSEE de **niveau I = « 7 »** (administrations,
  collectivités, établissements publics) → **public** ; sinon → **privé-droit**.
- Cas notables assumés : **SEM** (catégorie 5385) et **bailleurs ESH** (SA, 57xx)
  = **privé-droit** — cohérent avec la maquette validée. Sans nature juridique
  (acheteur non enrichi), repli heuristique sur le nom (« mairie », « commune »,
  « département », « préfecture », « hôpital », « CCAS » → public ; défaut privé-droit),
  avec `type_incertain=True` pour signaler à l'utilisateur.

### 5. Export (`exporter`)

```python
def exporter(df, xlsx_path: Path, csv_path: Path) -> None:
```

- `output/Acheteurs_Semaine_CHRUTH.xlsx` (mise en forme légère, colonnes lisibles)
  + `output/Acheteurs_Semaine_CHRUTH.csv`. Écrase à chaque run (nom fixe).

### 6. Page « Acheteurs de la semaine »

- **Streamlit** `pages_acheteurs.py` : entrée de navigation dans `CHRUTH_APP.py`,
  tableau des acheteurs (type coloré public/privé-droit, effectif, nb AO, liens),
  filtre par type, bouton d'export. Réutilise le thème `theme_chruth`.
- **HTML** `CHRUTH_PLATEFORME.html` : même vue (données d'exemple), page ajoutée à
  la navigation à 8 pages (→ 9).

### 7. Planification hebdomadaire

- `outils/installer_tache_acheteurs.ps1` crée la tâche Windows
  « CHRUTH Acheteurs - hebdo » (lundi 08:45) → `python -m acheteurs_semaine`
  (point d'entrée `main()` : collecte → extraction → enrichissement → export).
- Voir [[feedback-local-automation]] : Task Scheduler + script local, pas `/schedule`.

### 8. Mise en sommeil de l'ancien pipeline

- `chruth_pipeline_master.full_update` **n'est plus** la mise à jour Prospects de
  référence. On **ne supprime rien** ; on documente dans `docs/SURFACES_CHRUTH.md`
  que la prospection passe désormais par « Acheteurs de la semaine ».
- La tâche planifiée « CHRUTH Prospects - hebdo (carte) » est **désactivée**
  (`schtasks /Change /DISABLE`), non supprimée.

## Invariants

- Le livrable ne contient **que** des acheteurs d'AO pertinents publiés dans la
  fenêtre : jamais de rejeté, jamais hors fenêtre.
- L'enrichissement est **best-effort** : le réseau KO n'empêche jamais la production
  du livrable (acheteurs non enrichis, marqués).
- Aucun secret ; aucune donnée personnelle au-delà des contacts publics de l'avis.
- L'ancien pipeline reste **réversible** (rien supprimé).

## Tests (TDD)

`acheteurs_semaine` (données injectées, zéro réseau) :
- `collecter_aos_recents` : garde un AO PERTINENT dans la fenêtre, écarte un rejeté,
  un hors-fenêtre, un sans date ; fusionne BOAMP + Maximilien.
- `extraire_acheteurs` : dédoublonne par SIRET ; deux AO du même acheteur → une
  ligne, `nb_ao_semaine == 2`, priorité = la plus chaude.
- `classer` : « 7220 » → public ; « 5710 » (ESH) → privé-droit ; « 5385 » (SEM) →
  privé-droit ; vide + nom « Mairie de X » → public incertain.
- `enrichir` : client d'enrichissement factice → champs adresse/effectif remplis ;
  client qui lève → `enrichi=False`, ligne conservée.
- `exporter` : xlsx + csv écrits, colonnes attendues présentes.

`collect_api_entreprises.fetch_by_siret` : réponse API simulée → fiche ; 404/erreur
→ `None` (pas d'exception).

`pages_acheteurs` (AppTest) : la page démarre, le tableau s'affiche sur un jeu
injecté, le filtre public/privé fonctionne, l'app à N pages reste navigable.

## Hors périmètre (YAGNI)

- Pas de carte pour ce livrable (l'ancienne carte 132k reste, en sommeil).
- Pas de scoring complexe : l'ordre = priorité de l'AO puis fraîcheur.
- Pas de collecte d'entreprises par NAF (c'est justement ce qu'on remplace).
- Pas de JOUE tant que la source d'avis européens n'est pas branchée (extension
  naturelle : ajouter une 3ᵉ source dans `collecter_aos_recents`).
