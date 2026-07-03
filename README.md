# CHRUTH — Outils data & prospection

Projet data-driven pour CHRUTH : il **collecte, structure, score et visualise** des opportunités commerciales, et produit des **tableaux Excel** + une **carte interactive** exploitables sans coder.

Dossier de référence unique : **`CHRUTH_Data`**.

---

## 1. Ce que ça fait (vue d'ensemble)

Il y a **deux pipelines indépendants** :

| Pipeline | Source de données | Produit |
|---|---|---|
| **AO — Appels d'offres** | API **BOAMP** (marchés publics) | `output/AO_CHRUTH.xlsm` (cockpit appels d'offres) |
| **Prospects — Entreprises** | API **Recherche Entreprises** (data.gouv) | `output/Base_Prospects_CHRUTH.xlsm` + `output/Carte_Prospects_CHRUTH.html` |

Les deux sont **séparés** (données et logiques différentes) mais vivent dans le même projet.

---

## 2. Les fichiers produits (dans `output/`)

- **`AO_CHRUTH.xlsm`** — cockpit appels d'offres. Onglets : `Pilotage` (bandeau + KPI + Top 20 de la semaine), `AO_CHAUDS`, `AO_A_VERIFIER`, `DCE_A_RECUPERER`, `CRM_Suivi`, `Agent_IA`, `Scoring`, etc. Contient un **bouton macro** « Mettre à jour ».
- **`Base_Prospects_CHRUTH.xlsm`** — base des sociétés (SIRET, catégorie, priorité CHAUDE/TIEDE/FROIDE, coordonnées…), avec **bouton « Mettre à jour »** (macro). *Nom fixe, écrasé à chaque run.*
- **`Carte_Prospects_CHRUTH.html`** — carte interactive des sociétés (voir §5).
- Annexes prospects : `CRM_CHRUTH_CHAUDE.xlsx`, `Prospects_CHAUDS_messages.xlsx`, `KPI_CHRUTH.csv`, `CONTROLE_QUALITE_CHRUTH.csv`, exports Notion/Power BI.

---

## 3. Comment lancer une mise à jour

> ⚠️ **Avant toute mise à jour : ferme les fichiers Excel** (`AO_CHRUTH.xlsm`, `Base_Prospects…xlsx`). Un fichier ouvert dans Excel est **verrouillé** → la pipeline ne peut pas le réécrire et **rien ne se met à jour**.

### Le plus simple — le cockpit web (non-codeur)
Double-clic sur **`COCKPIT_CHRUTH.bat`** : le navigateur s'ouvre sur l'**interface unique** du projet
(état des missions de la fiche de poste, génération des livrables, messages prospects/AO,
envoi email, accès à tous les fichiers). Laisser la fenêtre noire ouverte pendant l'utilisation.
L'interface Tkinter historique reste disponible via `OUVRIR_MOI_CHRUTH.bat`.

### Le notebook de pilotage (si tu travailles déjà dans Jupyter / VS Code)
`CHRUTH_Pipeline_Unique.ipynb` : ouvre-le (Jupyter / VS Code) puis **Exécuter ▸ Exécuter tout**. Il lance la pipeline (`CHRUTH_PIPELINE_UNIQUE.py`) et produit les deux Excel + la carte. Réglages dans la section « Régler les options » :
- `COLLECTE_AO` (défaut `False`) : collecte BOAMP (~2 min).
- `COLLECTE_PROSPECTS` (défaut `False`) : `True` = recollecter toute la France (long).
- `GENERER_MESSAGES` / `CREER_PACK` : brouillons IA par segment / dossier portable prêt à envoyer.

*Ce notebook pilote les modules `.py` du dossier (il ne les remplace pas).*

### En ligne de commande (les deux pipelines séparément)
```bat
:: Appels d'offres -> AO_CHRUTH.xlsm
python ao_weekly_update.py
:: ou : double-clic LANCER_UPDATE_AO_CHRUTH.bat

:: Prospects + carte -> Base_Prospects...xlsx + Carte_Prospects_CHRUTH.html
python chruth_pipeline_master.py            :: retraite les données existantes
python chruth_pipeline_master.py --collect  :: + recollecte toute la France (long)
```

### Les boutons dans Excel (le plus pratique au quotidien)
Chaque tableur a un **bouton « Mettre à jour »**. Au clic, le tableur **se ferme, lance la collecte/MAJ, puis se rouvre tout seul à jour** (via `outils/refresh_runner.py`, qui attend que le fichier soit libéré). **Tu n'as donc PAS besoin de fermer le fichier toi-même** avant — le bouton s'en charge.
- **`AO_CHRUTH.xlsm`** → bouton « Mettre a jour les AO » : collecte BOAMP + DCE (~2 min) puis rouvre.
- **`Base_Prospects_CHRUTH.xlsm`** → bouton « Mettre a jour les prospects » : **popup** au clic — *Oui* = rafraîchir vite (retraite, rapide) ; *Non* = tout recollecter la France (long).
- Les deux tableurs ont aussi un bouton **Activer / Desactiver collecte**. Etat **OFF** = pas d'appel reseau BOAMP / API Entreprises / DCE ; les boutons retraitent seulement les donnees locales et regenerent les exports.

### Automatique (chaque lundi)
Deux **tâches planifiées Windows** déjà installées :
- **« CHRUTH AO - Mise a jour hebdomadaire »** — lundi **08:00** → `ao_weekly_update.py`.
- **« CHRUTH Prospects - hebdo (carte) »** — lundi **08:30** → `chruth_pipeline_master.py --collect --scope france`.

---

## 4. Comment ça marche (flux de données)

### Pipeline AO (`ao_weekly_update.py`)
1. **Collecte** (`ao_collect_boamp.py`) : requête ciblée à l'API BOAMP (mots-clés nettoyage/propreté + fenêtre **14 jours**), filtrage de pertinence, **dédup** dans une base **SQLite** (`data/ao_chruth.sqlite`).
2. **Scoring** (`ao_scoring.py`) : note /100 (métier + zone IDF + budget + infos + délai) → priorité **CHAUD / TIEDE / FROID / À VÉRIFIER**.
3. **DCE** (`ao_dce.py`, `ao_dce_process.py`) : extrait le lien du dossier de consultation, télécharge les PDF directs (sans CAPTCHA) ou consomme les PDF déposés dans `dce_manuel/<id_ao>.pdf`, en extrait budget/contact (complète sans écraser).
4. **Export** (`ao_export_excel.py`) : assemble `AO_CHRUTH.xlsm` dans le gabarit macro `assets/AO_CHRUTH_TEMPLATE.xlsm` (conserve le bouton).

### Pipeline Prospects (`chruth_pipeline_master.py` → `full_update`)
1. **Collecte** (`collect_api_entreprises.py`) : sociétés cibles via l'API Recherche Entreprises (par NAF × département) — coordonnées **lat/lon incluses**.
2. **Nettoyage + classification** (`clean_classify.py`) → `enrichissement FINESS` (`enrich_finess.py`, téléphones) → **scoring + export** (`scoring_export.py`) → `Base_Prospects…xlsx`.
3. **Carte** (`prospects_carte.py`) : génère `Carte_Prospects_CHRUTH.html`.
4. Annexes : contrôle qualité, KPI, CRM, messages, exports Notion/Power BI.

---

## 5. La carte interactive (`Carte_Prospects_CHRUTH.html`)

Centrée sur **60 rue François Ier, 75008 Paris**. Fonctionnalités :
- **Cercles de rayon** togglables : 5 / 10 / 20 / 30 / 50 km.
- **Couche proximité** (sociétés ≤ rayon) + **couche France entière** (30k, en clusters).
- **Recherche** : par adresse (géocodeur) et par **nom de société**.
- **Itinéraire** routier entre 2 adresses (distance + durée).
- **Filtre par priorité** (Chaudes / Tièdes / Froides) — sur la proximité **et** la France.
- **Tri ✅ Retenir / ❌ Écarter** par société (mémorisé dans le navigateur) + **export CSV** de la sélection.
- **Distance** à votre adresse affichée dans chaque popup.

Tout est **gratuit, sans clé** (OpenStreetMap / Nominatim / OSRM). Internet requis à l'ouverture.

---

## 6. Prérequis & installation

- **Python 3.10+** ; dépendances : `pip install -r requirements.txt` (requests, pandas, openpyxl, pdfplumber, pymupdf, folium).
- **Internet** (collecte des données, fonds de carte, itinéraire).
- **Excel** (ou compatible) pour ouvrir le `.xlsm` ; macros à autoriser pour le bouton.

---

## 7. Pièges & bonnes pratiques

- **Ferme les fichiers Excel avant toute mise à jour** (sinon écriture bloquée → « rien ne se passe »).
- La pipeline **régénère entièrement** les Excel à chaque run : les saisies manuelles dans `AO_CHRUTH.xlsm` (ex. CRM) **sont écrasées** au run suivant.
- La carte HTML peut rester ouverte (pas de verrou en écriture) ; fais juste **Ctrl+F5** pour voir la nouvelle version.
- Le tableur prospects a maintenant un **nom fixe** (`Base_Prospects_CHRUTH.xlsm`), écrasé à chaque run.
- **Bouton « Mettre à jour »** dans chaque tableur : pas besoin de fermer le fichier avant — le bouton ferme, met à jour, et rouvre tout seul.
- La collecte France des prospects est **longue** (~dizaines de minutes, ~43k établissements).

---

## 8. Structure du projet

```
CHRUTH_Data/
├── CHRUTH_Pipeline_Unique.ipynb    ← notebook de pilotage (lance la pipeline)
├── ao_*.py                         ← pipeline Appels d'offres (12 modules)
├── collect_api_entreprises.py, clean_classify.py, enrich_finess.py,
│   scoring_export.py, config.py, chruth_pipeline_master.py, prospects_carte.py
│                                   ← pipeline Prospects + carte
├── assets/AO_CHRUTH_TEMPLATE.xlsm  ← gabarit macro (bouton)
├── data/ao_chruth.sqlite           ← base AO (dédupliquée)  + data/raw_*.json (brut prospects)
├── output/                         ← fichiers produits (Excel, carte, CSV)
├── outils/                         ← vérificateur, générateurs
├── tests/                          ← suite pytest
└── docs/superpowers/               ← specs & plans de conception
```

---

*Toute la collecte s'appuie sur des sources publiques gratuites (BOAMP, API Entreprises, FINESS, OpenStreetMap). Aucune clé d'API payante n'est requise.*
