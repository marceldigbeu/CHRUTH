# CHRUTH - Livraison no-code

Ce dossier est la version allegee de livraison pour realiser les missions de la fiche de poste CHRUTH : base prospects, segmentation/scoring, messages IA, CRM/rentabilite et veille appels d'offres.

## Fichier a ouvrir

Pour une personne no-code, ouvrir en priorite l'application CHRUTH :

```bat
LANCER_APP_CHRUTH.bat
```

Une seule adresse, dix pages : accueil, veille appels d'offres, collecte, base de
donnees, acheteurs de la semaine, carte, messages et CRM, pilotage, reglages et
mode developpeur lie au cockpit Excel.

L'**Accueil** ouvre l'application : echeances les plus proches et AO retenus par
le tri. La page **Veille** filtre par une jauge de score et permet de basculer
vers la redaction sur le marche choisi. La page **Collecte** lance les AO, les
prospects ou les deux et suit leur journal. La page **Reglages** porte les
destinataires, l'adresse d'envoi et la fiche CHRUTH.

C'est la surface principale et la seule consultable en ligne depuis un telephone
(voir `docs/DEPLOIEMENT_APP_VEILLE.md`, protection de l'acces dans
`docs/GUIDE_CONNEXION.md`, carte des surfaces dans `docs/SURFACES_CHRUTH.md`).

Pour lancer les traitements par lots (generation, collectes) :

```bat
COCKPIT_CHRUTH.bat
```

Alternative :

```bat
OUVRIR_MOI_CHRUTH.bat
```

Ces interfaces permettent de generer les documents, les messages prospects/AO et d'envoyer les emails via Gmail.

## Regeneration des documents

Le moteur appele par les interfaces est :

```bat
python CHRUTH_PIPELINE_UNIQUE.py
```

Sous Windows, tu peux aussi double-cliquer :

```bat
LANCER_PIPELINE_CHRUTH.bat
```

Par defaut, la pipeline regenere les documents depuis les donnees locales, sans collecte reseau. Les anciennes donnees brutes, logs, tests et caches ont ete retires du dossier ; ils sont regenerables si une nouvelle collecte est lancee.

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

- `.env`
- `alertes_secrets.json`
- `destinataires.txt`
- `.streamlit/secrets.toml`

Les fichiers exemples restent inclus. Les identifiants Gmail et les destinataires
se saisissent sur le poste utilisateur : page **Reglages** de l'application, ou
onglet `Email` du cockpit.

Pour produire une copie verifiee plutot qu'un simple pack, preferer :

```bat
python outils/preparer_dossier_demo.py
```

Ce script refuse d'ecrire s'il detecte un fichier de secrets, ecarte les
sauvegardes horodatees et masque les adresses recopiees dans la documentation
ou les exports.

## Email et destinataires

Dans le cockpit Excel `output/AO_CHRUTH.xlsm`, l'onglet `Parametres` permet de saisir les destinataires des alertes en colonne B a partir de `B5`. Le bouton `Enregistrer_Destinataires` met a jour `destinataires.txt` et le champ `destinataire` de `alertes_secrets.json`, sans toucher a `smtp_user` ni `smtp_password`.

L'adresse d'envoi et son mot de passe d'application se modifient dans la page
**Reglages** de l'application. Les deux se saisissent ensemble : ils forment une
paire, et les changer separement casse tous les envois. Le mot de passe est ecrit
dans `alertes_secrets.json`, jamais dans les reglages partages, et n'est jamais
reaffiche.

Les interrupteurs (alertes, collecte) et la fiche CHRUTH sont partages entre
toutes les surfaces : les modifier dans l'application, dans le classeur ou dans
le cockpit revient au meme.

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

## Nettoyage realise

Le dossier conserve les fichiers necessaires a l'exploitation et aux livrables. Ont ete supprimes : historique Git local, tests, caches Python, logs, sauvegardes anciennes, donnees brutes volumineuses/corrompues et doublons regenerables. Les livrables `output/`, les scripts metier, les templates, la fiche de poste, les guides, les prompts et les configurations utiles sont conserves.
