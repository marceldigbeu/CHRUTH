# CHRUTH - Demarrage no-code

## Ce qu'il faut faire

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

Remplir une fois `config_chruth/fiche_chruth.md` avec des faits vrais : activite, zone IDF, prestations, points forts, et ce qu'il ne faut pas pretendre. L'IA n'utilise que cette fiche pour parler de CHRUTH.

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