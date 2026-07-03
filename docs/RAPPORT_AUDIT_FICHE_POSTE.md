# Rapport d'audit — objectifs de la fiche de poste CHRUTH

Date : 03/07/2026.
Source : `docs/source/Fiche de poste CHRUTH.pdf`.
Methode : verification de la presence et de la fraicheur de chaque livrable,
lecture des logs du dernier run pipeline (02/07/2026, code retour 0),
execution de la suite de tests automatises (222 fonctions de test),
et test fonctionnel des actions no-code (segments, messages prospects, messages AO, statut).

## Verdict global

Les 4 missions de la fiche de poste sont couvertes par des livrables concrets,
regenerables par une pipeline unique, et exploitables sans coder.
Le projet ajoute une extension appels d'offres publics (BOAMP) non demandee mais
directement alignee avec l'objectif d'acquisition de clients.
Trois points d'attention restent a traiter avant de considerer le projet finalise
(voir "Ecarts et actions" en bas).

## Mission 1 — Data Foundation

Objectif fiche de poste : base de prospects B2B structuree, collectee, enrichie, exploitable.

Realisation : la pipeline collecte les societes cibles via l'API Recherche Entreprises
(data.gouv, par NAF x departement, coordonnees GPS incluses), les nettoie et les classifie
(`clean_classify.py`), les enrichit via FINESS (`enrich_finess.py`), et produit une base de
132 502 prospects. Livrables verifies presents et dates du 02/07/2026 :
`output/Base_Prospects_CHRUTH.xlsm` (82 Mo, 13 onglets), `output/prospects_nettoyes.csv`,
`output/prospects_enrichis.csv`, `output/Carte_Prospects_CHRUTH.html` (carte interactive
avec rayons, recherche, itineraire, filtres, tri retenir/ecarter).
Statut : ATTEINT. L'actif data est reutilisable et se regenere en un clic.

## Mission 2 — Segmentation et scoring

Objectif fiche de poste : segments, scoring simple, zones et secteurs rentables, priorisation.

Realisation : scoring /100 avec priorites CHAUDE (2 606), TIEDE (64 898), FROIDE (64 998) ;
segments par categorie metier x priorite ; analyses par villes et zones dans les onglets
`Top_Cibles`, `Villes`, `Stats` du classeur ; `output/KPI_CHRUTH.csv` et
`output/CONTROLE_QUALITE_CHRUTH.csv` presents ; 13 sources Power BI exportees.
Statut : ATTEINT. La prospection est priorisee par score, plus a l'aveugle.

## Mission 3 — AI-Driven Sales

Objectif fiche de poste : messages personnalises par IA, templates email + scripts d'appel,
test/optimisation, automatisation partielle du contact initial.

Realisation : generation d'email + script d'appel par segment (48 segments CHAUDE/TIEDE testes
fonctionnels), variantes A/B deterministes distinctes avec bascule automatique sur la meilleure
variante au-dela de 20 resultats saisis (`suivi/suivi_envois.csv`, feuille `Perf_Messages`) ;
moteur IA auto-configurable (cle cloud > Ollama local > template deterministe) avec garde-fous
anti-hallucination via `config_chruth/fiche_chruth.md` ; alertes email automatiques des nouveaux
AO avec brouillon inclus (tache Windows + workflow GitHub Actions horaire).
Statut : ATTEINT dans son perimetre. Deux limites assumees et documentees : en mode IA les
variantes A/B partagent le meme prompt, et l'envoi reste declenche manuellement (choix prudent).

## Mission 4 — Data Insights (CRM et rentabilite)

Objectif fiche de poste : CRM simple, rentabilite par client/prestation, segments profitables,
patterns de retention/churn.

Realisation : `output/CRM_CHRUTH_CHAUDE.xlsx` (CRM simple), import Notion pret
(`output/notion_import_chruth/`, 10 fichiers + notice), `output/Modele_Financier_CHRUTH.xlsx`
(5 onglets : previsionnel global, charges fixes, hypotheses marche, marches, synthese
rentabilite) alimente par `previsions.py`, `rentabilite.py`, `rentabilite_marche.py`.
Statut : ATTEINT sur l'outillage. Nuance honnete : la retention et le churn ne pourront etre
reellement mesures qu'avec de vraies donnees clients saisies dans le CRM — l'outillage est
pret, les donnees d'usage restent a accumuler.

## Extension — Appels d'offres publics (hors fiche de poste)

Cockpit `output/AO_CHRUTH.xlsm` (scoring /100, priorites, DCE telecharges et analyses,
CRM de suivi), base SQLite anti-doublons, alertes email horaires via GitHub Actions,
redaction structuree de reponses par AO. Valeur ajoutee claire pour l'acquisition.

## Qualite logicielle

Suite de 222 fonctions de test (pytest) couvrant scoring, exports Excel, messages, carte,
alertes, CRM, previsions, migration de base.

Resultat pytest du 03/07/2026 : 222 reussites, 0 echec.

Correction apportee pendant l'audit : `ao_alertes.py` utilisait une f-string avec backslash,
syntaxe acceptee seulement a partir de Python 3.12. Le code a ete reecrit en equivalent
strict (memes liens HTML generes) pour etre compatible Python 3.10+ — utile pour GitHub
Actions et tout poste qui n'aurait pas la derniere version de Python.

## Ecarts et actions recommandees

1. `config_chruth/fiche_chruth.md` est vide. Tant qu'elle n'est pas remplie avec des faits
   vrais (activite, zone, prestations, points forts, ce qu'il ne faut pas pretendre), tous
   les messages IA restent volontairement generiques. Action : la remplir (5 minutes) —
   accessible depuis l'onglet Livrables du cockpit.
2. Aucune cle IA n'est renseignee dans `.env` : le moteur retombe sur les templates
   deterministes (ou Ollama si installe). Acceptable, mais la personnalisation IA promise
   en mission 3 n'est active qu'avec une cle (Anthropic, Mistral ou Groq — une seule suffit).
3. Pertinence du scoring AO : l'AO le mieux score (95/100, CHAUD) au moment de l'audit est
   un marche de formation contre la discrimination — hors metier nettoyage. Le filtre de
   pertinence (`is_relevant` / mots-cles BOAMP) laisse passer des faux positifs bien scores.
   Action suggeree : renforcer le filtre metier (exclusions "formation", "conseil", etc.)
   ou ponderer negativement les objets hors lexique proprete.
4. Interface unique : ajoutee le 03/07/2026 — `COCKPIT_CHRUTH.bat` ouvre le cockpit web
   (etat des missions en temps reel, generation, messages, email, tous les livrables).
   L'interface Tkinter reste disponible en secours (`OUVRIR_MOI_CHRUTH.bat`).

## Comment verifier soi-meme (sans coder)

Double-cliquer sur `COCKPIT_CHRUTH.bat` : la section "Etat des missions" affiche en vert/rouge
chaque livrable de chaque mission avec sa date et sa taille, et se met a jour apres chaque
generation.
