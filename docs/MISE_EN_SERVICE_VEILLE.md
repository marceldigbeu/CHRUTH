# Mise en service de la veille Maximilien

Cinq actions à faire une fois, sur GitHub. Le code est prêt sans elles, mais
rien ne tournera tant qu'elles ne sont pas faites.

## 1. Fusionner sur la branche par défaut

Les crons ne s'exécutent QUE depuis la branche par défaut (`main`).
Tant que le workflow est sur `feat/veille-maximilien`, il ne se déclenchera jamais.

## 2. Créer les secrets du dépôt

`Settings > Secrets and variables > Actions > New repository secret` :

| Nom | Valeur |
|---|---|
| `CHRUTH_SMTP_USER` | `expediteur@gmail.com` |
| `CHRUTH_SMTP_PASSWORD` | le mot de passe d'application Gmail (16 caractères) |
| `CHRUTH_ALERTE_DEST` | les destinataires, séparés par des virgules |

Optionnel, pour activer l'arbitrage IA (sinon le tri reste déterministe) :
`GROQ_API_KEY` ou `MISTRAL_API_KEY`.

## 3. Autoriser le workflow à écrire

`Settings > Actions > General > Workflow permissions` : cocher
**Read and write permissions**. Sans ça, le `git push` de l'état échoue.

## 4. Vérifier que la branche d'état existe

`ao-state` existe déjà. Le workflow y écrira `etat/veille.json`.

## 5. Premier essai

`Actions > Veille Maximilien > Run workflow`. Attendu : un email par AO
pertinent inconnu, puis un commit `etat veille ...` sur `ao-state`.
Au second lancement : aucun email (l'état fait son travail).

## Suspendre sans désinstaller

`Settings > Secrets and variables > Actions > Variables` :
`CHRUTH_NOTIFICATIONS` = `OFF`. Remettre `ON` pour reprendre.
