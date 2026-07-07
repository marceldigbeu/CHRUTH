# Livrables CHRUTH

Ce dossier de sortie est genere par `CHRUTH_PIPELINE_UNIQUE.py`.

## Correspondance missions -> livrables

### 1_data_foundation

- `output/Base_Prospects_CHRUTH.xlsm`
- `output/prospects_nettoyes.csv`
- `output/prospects_enrichis.csv`
- `output/Carte_Prospects_CHRUTH.html`

### 2_segmentation_scoring

- `output/KPI_CHRUTH.csv`
- `output/CONTROLE_QUALITE_CHRUTH.csv`
- `output/Base_Prospects_CHRUTH.xlsm`
- `output/powerbi_sources/`

### 3_ai_driven_sales

- `output/Prospects_CHAUDS_messages.xlsx`
- `output/segments_messages.json`
- `output/_message_ao.txt`
- `output/_message_prospect_segment.txt`
- `prompts/PROMPTS_CHRUTH.md`

### 4_crm_rentabilite

- `output/CRM_CHRUTH_CHAUDE.xlsx`
- `output/Modele_Financier_CHRUTH.xlsx`
- `output/notion_import_chruth/`

### bonus_appels_offres

- `output/AO_CHRUTH.xlsm`

## Lancement

```bat
python CHRUTH_PIPELINE_UNIQUE.py
```

Par defaut, la collecte reseau est desactivee. Pour recollecter :

```bat
python CHRUTH_PIPELINE_UNIQUE.py --collect-ao --collect-prospects
```

## Version allegee

Les logs, caches, tests, donnees brutes massives et doublons regenerables ont ete retires du dossier de livraison. Les livrables ci-dessus, les scripts metier, les guides et les templates restent conserves.