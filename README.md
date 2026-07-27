# CHRUTH - Outils data, IA et prospection

Projet no-code/data pour realiser les missions de la fiche de poste CHRUTH :

1. Construire une base de donnees prospects B2B.
2. Segmenter et scorer les prospects.
3. Generer des messages de prospection avec l'IA.
4. Structurer le CRM et analyser la rentabilite.
5. Suivre en bonus les appels d'offres nettoyage.

Le dossier local est allege : les tests, logs, caches, donnees brutes massives et historique Git local ont ete retires. Les scripts metier, templates, guides, prompts, configurations utiles et livrables sont conserves.

## Demarrage rapide

Pour une personne no-code, ouvrir l'application CHRUTH :

```bat
LANCER_APP_CHRUTH.bat
```

Une seule adresse, huit pages : veille appels d'offres, collecte, base de donnees,
carte, messages et CRM, pilotage, reglages et mode developpeur lie a `AO_CHRUTH.xlsm`.
La page **Collecte** lance les AO, les prospects ou les deux et affiche le journal en direct.
C'est la surface principale, et la seule consultable en ligne depuis un
telephone (voir `docs/DEPLOIEMENT_APP_VEILLE.md` et `docs/SURFACES_CHRUTH.md`).

Pour lancer les traitements par lots :

```bat
COCKPIT_CHRUTH.bat
```

Alternative :

```bat
OUVRIR_MOI_CHRUTH.bat
```

Ces interfaces permettent de generer les livrables, produire les messages prospects/AO et configurer l'envoi email.

## Lancement en ligne de commande

Regenerer les documents depuis les donnees locales :

```bat
python CHRUTH_PIPELINE_UNIQUE.py
```

Recollecter les appels d'offres et les prospects avec internet :

```bat
python CHRUTH_PIPELINE_UNIQUE.py --collect-ao --collect-prospects
```

Creer un dossier portable pret a envoyer :

```bat
python CHRUTH_PIPELINE_UNIQUE.py --pack
```

## Livrables principaux

Les livrables sont generes dans `output/` :

- `AO_CHRUTH.xlsm` : cockpit appels d'offres.
- `Base_Prospects_CHRUTH.xlsm` : base prospects, segmentation et scoring.
- `Carte_Prospects_CHRUTH.html` : carte interactive.
- `CRM_CHRUTH_CHAUDE.xlsx` : CRM simple.
- `Prospects_CHAUDS_messages.xlsx` : messages de prospection.
- `Modele_Financier_CHRUTH.xlsx` : rentabilite et modele financier.
- `powerbi_sources/` : sources Power BI.
- `notion_import_chruth/` : fichiers CSV pour Notion.

La fiche de poste source est conservee ici :

```text
docs/source/Fiche de poste CHRUTH.pdf
```

## Email et destinataires

Les secrets Gmail restent locaux et ne doivent pas etre envoyes sur GitHub :

- `.env`
- `alertes_secrets.json`
- `destinataires.txt`

Depuis `output/AO_CHRUTH.xlsm`, onglet `Parametres`, saisir les destinataires en colonne B a partir de `B5`, puis cliquer sur `Enregistrer_Destinataires`.

Le script met a jour :

- `destinataires.txt`
- le champ `destinataire` de `alertes_secrets.json`

Il ne modifie pas `smtp_user` ni `smtp_password`.

## Fichiers gardes vs nettoyes

Conserves pour l'exploitation : scripts metier, cockpit no-code, templates Excel, guides, prompts, config CHRUTH, base SQLite utile, fiche de poste et livrables.

Supprimes car regenerables ou non utiles a l'entreprise : historique Git local, tests, logs, caches Python, donnees brutes volumineuses/corrompues, sauvegardes anciennes et doublons Excel.

## Guides utiles

- `README_DEMARRAGE_NO_CODE.md` : guide utilisateur.
- `README_LIVRAISON.md` : guide de livraison.
- `output/LIRE_MOI_LIVRABLES.md` : correspondance missions -> livrables.
- `docs/MISSION_CHRUTH.md` : couverture des missions de la fiche de poste.
- `prompts/PROMPTS_CHRUTH.md` : prompts et logique IA.
