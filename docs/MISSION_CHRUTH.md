# Missions CHRUTH - correspondance pipeline

Source : `Fiche de poste CHRUTH.pdf`.

## Mission 1 - Data Foundation

Objectif : construire une base prospects B2B reutilisable.

Livrables :
- `output/Base_Prospects_CHRUTH.xlsm`
- `output/prospects_nettoyes.csv`
- `output/prospects_enrichis.csv`
- `output/Carte_Prospects_CHRUTH.html`

## Mission 2 - Segmentation et scoring

Objectif : ne plus prospecter a l'aveugle.

Livrables :
- scoring `signal_besoin` et `priorite`
- `output/KPI_CHRUTH.csv`
- `output/CONTROLE_QUALITE_CHRUTH.csv`
- `output/powerbi_sources/`

## Mission 3 - AI-Driven Sales

Objectif : generer des brouillons de prospection personnalises par segment.

Livrables :
- `output/Prospects_CHAUDS_messages.xlsx` : feuilles Messages + Suivi_Envois (saisie statut) + Perf_Messages (taux par variante A/B, variante recommandee)
- `output/segments_messages.json`
- `prompts/PROMPTS_CHRUTH.md`
- `suivi/suivi_envois.csv` : source de verite du suivi (prive, hors pack)

Boucle d'optimisation : 2 variantes par segment, suivi des resultats saisi a la main, bascule automatique sur la meilleure variante au-dela de 20 resultats.

Note A/B : par defaut les templates A et B sont deterministes et genuinement distincts (A = accroche directe, B = benefice prospect) — aucun appel LLM. La generation IA est opt-in via `generate_messages(utiliser_ia=True)` ; en mode IA les deux variantes partagent actuellement le meme prompt (a affiner dans une prochaine iteration).

## Mission 4 - CRM et rentabilite

Objectif : piloter l'activite avec les donnees.

Livrables :
- `output/CRM_CHRUTH_CHAUDE.xlsx`
- `output/Modele_Financier_CHRUTH.xlsx`
- `output/notion_import_chruth/`

## Extension utile - Appels d'offres

Le projet ajoute un cockpit AO pour detecter les marches publics pertinents, alerter
par email, et rediger un message structure par AO (style SEKOIA : profil CHRUTH injecte).

Livrables :
- `output/AO_CHRUTH.xlsm` : cockpit (AO chauds/tiedes, scoring, brouillons email/script)
- `config_chruth/fiche_chruth.md` : fiche CHRUTH a remplir (faits reels injectes dans l'IA)
- `CHRUTH_Messages_AO.ipynb` : notebook de redaction par AO, sortie sectionnee editable
  (`output/messages_ao/AO_<id>.md`)
- mail d'alerte : chaque nouvel AO chaud/tiede arrive avec son brouillon (email + script)

Moteur IA automatique : une cle cloud dans `.env` (anthropic > mistral > groq, une seule
suffit) sinon Ollama local sinon brouillon deterministe. La fiche CHRUTH rend les messages
precis et evite l'invention (garde-fous anti-hallucination).
