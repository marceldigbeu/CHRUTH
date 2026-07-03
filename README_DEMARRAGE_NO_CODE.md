# CHRUTH - Demarrage no-code

## Ce qu'il faut faire

1. Double-cliquer sur `COCKPIT_CHRUTH.bat` : le navigateur s'ouvre sur le **cockpit web CHRUTH**,
   l'interface unique du projet (etat des missions, generation, messages, email, livrables).
   Laisser la fenetre noire ouverte pendant l'utilisation.
2. Alternative : `OUVRIR_MOI_CHRUTH.bat` ouvre l'ancienne interface Tkinter (memes actions).
3. Dans les deux cas, les sections sont les memes :
   - `1. Generer` pour recreer tous les documents.
   - `2. Messages prospects` pour generer un email + script par segment.
   - `3. Messages AO` pour generer un email + script pour un appel d'offres.
   - `4. Email` pour configurer Gmail et envoyer le message affiche.
   - `5. Livrables` pour ouvrir directement les fichiers, dossiers, guides, notebooks, logs et exports.
3. Cliquer sur `Ouvrir le dossier output` si besoin.

## Mode recommande

Ne coche rien au premier lancement.

La pipeline utilisera les donnees deja presentes et regenerera les documents sans collecte internet.

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

L'onglet `Livrables` donne aussi acces a Power BI, Notion, DCE PDF, logs, prompts, notebooks, guides HTML et fiche de poste.

## En cas de probleme

Ouvre le dernier fichier dans `logs/`.

Les fichiers Excel ouverts peuvent bloquer la regeneration. Ferme Excel puis relance.

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

Pour retravailler un AO en detail : notebook `CHRUTH_Messages_AO.ipynb` (choix de l'AO,
message sectionne, ecrit aussi un fichier editable `output/messages_ao/AO_<id>.md`).
Chaque nouvel AO chaud/tiede arrive aussi avec son brouillon directement dans le mail d'alerte.

### Rendre les messages precis (fiche CHRUTH)

Remplir une fois `config_chruth/fiche_chruth.md` avec des faits VRAIS (activite, zone IDF,
prestations, points forts, et ce qu'il ne faut PAS pretendre). L'IA n'utilise que cette fiche
pour parler de CHRUTH : messages plus justes partout (cockpit, mail d'alerte, notebook).
Tant que la fiche est vide, les messages restent volontairement generiques.

Le moteur se regle tout seul : une cle cloud dans `.env` (ANTHROPIC/MISTRAL/GROQ, une seule
suffit) sinon Ollama local sinon brouillon type. Aucun reglage a faire.

## Envoi email depuis l'interface

1. Onglet `Email`.
2. Renseigner l'email expediteur Gmail.
3. Renseigner le mot de passe d'application Gmail.
4. Renseigner le destinataire.
5. Cliquer sur `Enregistrer config`.
6. Depuis `Messages prospects` ou `Messages AO`, generer un message.
7. Revenir dans `Email` et cliquer sur `Envoyer l'email`.

La configuration est stockee localement dans `alertes_secrets.json` et `destinataires.txt`.
Ces fichiers ne sont pas copies dans les packs envoyes.

Pour Gmail, il faut un mot de passe d'application, pas le mot de passe normal du compte.
