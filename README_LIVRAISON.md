# CHRUTH - Livraison pipeline unique

Pour une personne no-code, le fichier a ouvrir est :

```bat
OUVRIR_MOI_CHRUTH.bat
```

Il ouvre une petite interface avec un bouton `Generer les documents`.
La meme interface permet aussi de generer les messages prospects/AO et de les envoyer par Gmail.

Le dossier contient aussi un notebook de pilotage :

```text
CHRUTH_Pipeline_Unique.ipynb
```

Le notebook est utile si la personne travaille deja avec Jupyter ou VS Code.

Le moteur appele par le notebook est :

```bat
python CHRUTH_PIPELINE_UNIQUE.py
```

Sous Windows, tu peux aussi double-cliquer :

```bat
LANCER_PIPELINE_CHRUTH.bat
```

Par defaut, la pipeline regenere les documents depuis les donnees locales, sans collecte reseau.

## Recollecter les donnees

Pour refaire les collectes internet :

```bat
python CHRUTH_PIPELINE_UNIQUE.py --collect-ao --collect-prospects
```

Pour recollecter seulement les appels d'offres :

```bat
python CHRUTH_PIPELINE_UNIQUE.py --collect-ao
```

Pour recollecter seulement les prospects :

```bat
python CHRUTH_PIPELINE_UNIQUE.py --collect-prospects
```

## Creer un dossier pret a envoyer

```bat
python CHRUTH_PIPELINE_UNIQUE.py --pack
```

Le pack exclut les secrets locaux :
- `alertes_secrets.json`
- `destinataires.txt`

Les fichiers exemples restent inclus.
Les identifiants Gmail et destinataires doivent etre saisis dans l'onglet `Email` de l'interface sur le poste utilisateur.

## Livrables principaux

- `output/AO_CHRUTH.xlsm` : cockpit appels d'offres.
- `output/Base_Prospects_CHRUTH.xlsm` : base prospects, segmentation, scoring.
- `output/Carte_Prospects_CHRUTH.html` : carte interactive.
- `output/CRM_CHRUTH_CHAUDE.xlsx` : CRM simple.
- `output/Prospects_CHAUDS_messages.xlsx` : messages de prospection.
- `output/Modele_Financier_CHRUTH.xlsx` : modele financier et rentabilite.
- `output/powerbi_sources/` : sources Power BI.
- `output/notion_import_chruth/` : fichiers CSV pour Notion.

## Missions couvertes

La correspondance avec la fiche de poste est documentee ici :

```text
docs/MISSION_CHRUTH.md
prompts/PROMPTS_CHRUTH.md
```
