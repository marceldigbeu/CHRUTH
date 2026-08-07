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

Une seule adresse, dix pages : accueil, veille appels d'offres, collecte, base de
donnees, acheteurs de la semaine, carte, messages et CRM, pilotage, reglages et
mode developpeur lie a `AO_CHRUTH.xlsm`.

L'**Accueil** ouvre l'application : chiffres cles, echeances les plus proches avec
code couleur d'urgence, et AO retenus par le tri, chacun avec un lien vers l'avis
d'origine. La page **Collecte** lance les AO, les prospects ou les deux et affiche
le journal en direct. C'est la surface principale, et la seule consultable en ligne
depuis un telephone (voir `docs/DEPLOIEMENT_APP_VEILLE.md` et `docs/SURFACES_CHRUTH.md`).

### Trier les appels d'offres

Le score va a la decimale (71,4 et non 71) : le bareme compte en continu le budget,
le delai restant, la densite de termes metier et la completude du dossier. Avant, il
ne prenait que 17 valeurs, toutes multiples de 5, et des dizaines de marches se
retrouvaient a egalite.

La page **Veille** expose une jauge **Score minimum** au pas de 0,5 et un classement
par score decroissant. Le bouton **Rediger un message** bascule sur la page Messages
avec le marche deja selectionne.

### Maitriser le cout des messages

La page **Messages et CRM** plafonne la longueur des reponses (256 a 2048 tokens) et
affiche, avant chaque redaction, les tokens envoyes et le total au pire. Sur une API
facturee au token, rien d'autre n'arrete une reponse qui part en boucle.

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

Les secrets restent locaux et ne doivent pas etre envoyes sur GitHub :

- `.env`
- `alertes_secrets.json`
- `destinataires.txt`
- `.streamlit/secrets.toml`

**Destinataires** — depuis `output/AO_CHRUTH.xlsm`, onglet `Parametres`, saisir les
adresses en colonne B a partir de `B5`, puis cliquer sur `Enregistrer_Destinataires`.
Le script met a jour `destinataires.txt` et le champ `destinataire` de
`alertes_secrets.json`. Il ne modifie pas l'expediteur.

**Adresse d'envoi et mot de passe d'application** — page **Reglages** de
l'application, bloc *Expediteur*. Les deux se saisissent ensemble : ils forment une
paire, et les changer separement casse tous les envois. Le mot de passe n'est jamais
reaffiche, et un champ laisse vide conserve celui deja enregistre. Il est ecrit dans
`alertes_secrets.json`, jamais dans les reglages partages — ceux-ci sont publies en
ligne avec l'etat de la veille.

## Acces a l'application

Une page de connexion peut proteger l'application. Tant que rien n'est configure,
elle demarre sans connexion : c'est le mode poste local.

Aucun mot de passe n'est stocke ni envoye : l'identification est deleguee a Google.
La liste des adresses autorisees vit dans `.streamlit/secrets.toml`, hors de
l'application — un droit d'acces modifiable depuis l'application protegee ne
protegerait rien.

Mise en service : `docs/GUIDE_CONNEXION.md`.

## Fichiers gardes vs nettoyes

Conserves pour l'exploitation : scripts metier, cockpit no-code, templates Excel, guides, prompts, config CHRUTH, base SQLite utile, fiche de poste et livrables.

Supprimes car regenerables ou non utiles a l'entreprise : historique Git local, tests, logs, caches Python, donnees brutes volumineuses/corrompues, sauvegardes anciennes et doublons Excel.

## Guides utiles

- `README_DEMARRAGE_NO_CODE.md` : guide utilisateur.
- `README_LIVRAISON.md` : guide de livraison.
- `output/LIRE_MOI_LIVRABLES.md` : correspondance missions -> livrables.
- `docs/MISSION_CHRUTH.md` : couverture des missions de la fiche de poste.
- `docs/GUIDE_CONNEXION.md` : activer la page de connexion.
- `docs/GUIDE_PUBLICATION.md` : quoi publier, et ce qu'il faut vérifier avant.
- `docs/GUIDE_CHANGER_LES_REGLAGES.md` : ou se changent les reglages.
- `prompts/PROMPTS_CHRUTH.md` : prompts et logique IA.
