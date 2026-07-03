# Couverture de l'interface CHRUTH

## Exploite directement dans Tkinter

- Generation complete : `CHRUTH_PIPELINE_UNIQUE.py`
- Messages prospects : `prospect_messages.py`, `llm_client.py`
- Messages AO : `ao_messages.py`, `outils/generer_message_ao.py`
- Envoi email : `chruth_email.py`, `alertes_secrets.json`, `destinataires.txt`
- Ouverture livrables : fichiers `output/`
- Ouverture docs : `README_DEMARRAGE_NO_CODE.md`, `README_LIVRAISON.md`, `docs/MISSION_CHRUTH.md`, `prompts/PROMPTS_CHRUTH.md`

## Exploite indirectement par la pipeline

- AO : `ao_weekly_update.py`, `ao_collect_boamp.py`, `ao_dce_process.py`, `ao_export_excel.py`, `ao_publish.py`, `ao_db.py`, `ao_scoring.py`, `ao_pilotage.py`, `ao_style.py`
- Prospects : `chruth_pipeline_master.py`, `collect_api_entreprises.py`, `clean_classify.py`, `enrich_finess.py`, `scoring_export.py`, `prospects_carte.py`
- Finance : `outils/generer_modele_financier.py`, `previsions.py`, `rentabilite.py`, `rentabilite_marche.py`
- CRM / exports : `crm.py`, exports Notion, exports Power BI

## Accessible depuis l'onglet Livrables

- Cockpit AO
- Base prospects
- Carte prospects
- CRM
- Messages prospects
- Modele financier
- Sources Power BI
- Import Notion
- Exports CSV
- DCE PDF
- Logs
- Guides HTML
- Notebooks
- Prompts
- Docs techniques
- Fiche de poste source
- Ancienne app Streamlit messages

## Non exposes comme actions no-code

Ces fichiers sont conserves pour maintenance, tests ou developpement :

- `tests/`
- `docs/superpowers/`
- scripts de creation de templates Excel
- modules internes appeles par la pipeline

Ils ne doivent pas etre manipules par une personne no-code.
