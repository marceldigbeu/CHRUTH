# CHRUTH - Demarrage no-code

## L'application CHRUTH (recommandee)

Double-cliquer sur `LANCER_APP_CHRUTH.bat` : le navigateur ouvre l'application, une
seule adresse pour dix pages dans le menu de gauche :

- **Accueil** : ce qui est urgent, si le systeme tourne, ou aller ensuite. Les
  echeances les plus proches avec un code couleur, et les AO retenus par le tri.
- **Veille appels d'offres** : consulter les AO, corriger le tri, suivre. Une
  jauge **Score minimum** et un classement par score y filtrent la liste, et le
  bouton **Rediger un message** bascule vers la redaction sur le marche choisi.
- **Collecte** : lancer les collectes AO/prospects, choisir le périmètre et suivre le journal.
- **Base de donnees** : consulter les AO Excel, filtrer les 132 000 prospects et telecharger les fichiers importants.
- **Acheteurs de la semaine** : qui a publie ces sept derniers jours.
- **Carte** : utiliser directement `output/Carte_Prospects_CHRUTH.html`.
- **Messages et CRM** : generer les messages (AO et prospects) et suivre le
  commercial. La longueur des reponses est plafonnee et le cout en tokens
  affiche avant chaque redaction.
- **Pilotage** : ce qui attend, ce que la collecte a filtre, et ou sont les marches.
- **Reglages** : destinataires, adresse d'envoi, interrupteurs, fiche CHRUTH —
  vus par toutes les surfaces.
- **Developpeur** : inspecter et ouvrir `output/AO_CHRUTH.xlsm`, puis lancer sa mise a jour apres fermeture d'Excel.

C'est la seule surface qui peut aussi s'ouvrir en ligne, depuis un telephone, sans
PC allume : voir `docs/DEPLOIEMENT_APP_VEILLE.md`. Une page de connexion peut alors
la proteger (`docs/GUIDE_CONNEXION.md`) ; en local, aucune connexion n'est demandee.
La carte de toutes les surfaces et leur role est dans `docs/SURFACES_CHRUTH.md`.

## Les interfaces de traitement (alternatives)

1. Double-cliquer sur `COCKPIT_CHRUTH.bat` : le navigateur s'ouvre sur le cockpit web CHRUTH.
2. Laisser la fenetre noire ouverte pendant l'utilisation.
3. Alternative : `OUVRIR_MOI_CHRUTH.bat` ouvre l'interface Tkinter historique.
4. Dans les deux cas, les sections couvrent : generation, messages prospects, messages AO, email et livrables.

## Mode recommande

Ne coche rien au premier lancement. La pipeline utilisera les donnees deja presentes et regenerera les documents sans collecte internet.

## Options

- `Recollecter les appels d'offres BOAMP/DCE` : met a jour le cockpit AO avec internet.
- `Recollecter les prospects API Entreprises` : relance une collecte France, longue.
- `Generer les brouillons IA` : utilise un LLM local/cloud si configure.
- `Creer le dossier portable` : cree une copie prete a envoyer.

## Documents generes

- `output/AO_CHRUTH.xlsm`
- `output/Base_Prospects_CHRUTH.xlsm`
- `output/Carte_Prospects_CHRUTH.html`
- `output/CRM_CHRUTH_CHAUDE.xlsx`
- `output/Prospects_CHAUDS_messages.xlsx`
- `output/Modele_Financier_CHRUTH.xlsx`
- `output/powerbi_sources/`
- `output/notion_import_chruth/`

La fiche de poste source est dans `docs/source/Fiche de poste CHRUTH.pdf`.

## En cas de probleme

Les logs ne sont pas conserves dans la version allegee. Ils seront recrees automatiquement dans `logs/` au prochain lancement.

Les fichiers Excel ouverts peuvent bloquer la regeneration. Ferme Excel puis relance, sauf si tu utilises le bouton de mise a jour integre au classeur.

## Messages automatises

### Prospects

1. Onglet `Messages prospects`.
2. Cliquer sur `Charger les segments`.
3. Choisir un segment.
4. Cliquer sur `Generer email + script`.

Le resultat est aussi ecrit dans `output/_message_prospect_segment.txt`.

### Appels d'offres

1. Onglet `Messages AO`.
2. Cliquer sur `Charger les AO chauds/tiedes`.
3. Choisir un AO.
4. Cliquer sur `Generer email + script AO`.

Le resultat est aussi ecrit dans `output/_message_ao.txt`.

## Rendre les messages precis

Remplir une fois la fiche CHRUTH avec des faits vrais : activite, zone IDF,
prestations, points forts, et ce qu'il ne faut pas pretendre. L'IA n'utilise que
cette fiche pour parler de CHRUTH, et refuse d'inventer ce qui n'y figure pas.

Deux endroits au choix, le meme contenu : la page **Reglages** de l'application,
ou le fichier `config_chruth/fiche_chruth.md`. La saisie de l'application prime ;
le fichier sert quand elle est vide.

**La signature est un cas a part.** Elle n'est pas redigee par l'IA — un modele
inventerait un numero plausible et faux — mais recopiee telle quelle depuis une
section dont le titre commence par « Coordonnees » :

```markdown
## Coordonnées
- Site : chruth.fr
- Email : contact@chruth.fr
- Téléphone : 01 23 45 67 89
```

Un titre different, `## Contact` par exemple, ne produit aucune signature. Un
seul champ suffit a la declencher. Laisser vide plutot qu'approximer : un lien
faux coute plus cher que pas de lien.

Le moteur se regle tout seul : une cle cloud dans `.env` si disponible, sinon Ollama local, sinon brouillon type.

## Envoi email depuis l'interface

1. Onglet `Email`.
2. Renseigner l'email expediteur Gmail.
3. Renseigner le mot de passe d'application Gmail.
4. Renseigner le destinataire.
5. Cliquer sur `Enregistrer config`.
6. Generer un message depuis `Messages prospects` ou `Messages AO`.
7. Revenir dans `Email` et cliquer sur `Envoyer l'email`.

La configuration reste locale dans `alertes_secrets.json` et `destinataires.txt`. Ces fichiers ne sont pas copies dans les packs envoyes et ne doivent pas etre publies sur GitHub.

## Destinataires depuis Excel

Dans `output/AO_CHRUTH.xlsm`, onglet `Parametres`, ajouter les destinataires en colonne B a partir de `B5`, une adresse par ligne, puis cliquer sur `Enregistrer_Destinataires`.

Cette action met a jour `destinataires.txt` et le champ `destinataire` de `alertes_secrets.json`, sans modifier le compte expediteur Gmail.
