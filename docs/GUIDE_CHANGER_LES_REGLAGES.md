# Changer les réglages de la veille CHRUTH

Qui reçoit les alertes, depuis quelle adresse elles partent, et comment agir
directement sur la base ou sur le tableur.

Tout ce qui suit se passe dans le **dossier de production** :

```
%USERPROFILE%\Downloads\CHRUTH_LIVRAISON_NO_CODE
```

C'est lui que les tâches Windows exécutent. Le dossier `%USERPROFILE%\CHRUTH`
est le dépôt de code : on y développe, on n'y règle rien.

---

## 1. Changer les destinataires

Trois façons, du plus simple au plus technique. Elles écrivent toutes au même
endroit : `destinataires.txt`, une adresse par ligne.

**Aujourd'hui** : `destinataire1@exemple.fr` et `maintainers@users.noreply.github.com`.

### Depuis le tableur (recommandé)

1. Ouvrir `output\AO_CHRUTH.xlsm`, onglet **Parametres**
2. Colonne **B, à partir de la ligne 5** : une adresse par cellule
3. Cliquer le bouton **Enregistrer destinataires**

Le bouton écrit la colonne dans `destinataires.txt`. Un message confirme, ou
signale qu'aucune adresse valide n'a été trouvée. C'est ce fichier qui compte —
la colonne du tableur n'en est que le reflet, repeuplée à chaque régénération.

### Depuis le fichier

Ouvrir `destinataires.txt` dans le Bloc-notes :

```
# Destinataires CHRUTH - une adresse email par ligne.
destinataire1@exemple.fr
maintainers@users.noreply.github.com
```

Une adresse par ligne. Les lignes vides et celles commençant par `#` sont
ignorées. Enregistrer suffit — aucune commande à lancer.

Les destinataires sont mis en **copie cachée** : ils ne se voient pas entre eux.

### Pour la veille cloud (Maximilien)

Le cloud ne lit pas ce fichier : il lit un secret GitHub.
`Settings > Secrets and variables > Actions` → **`CHRUTH_ALERTE_DEST`**,
plusieurs adresses séparées par des virgules.

> **Les deux listes sont indépendantes.** Ajouter quelqu'un dans le tableur ne
> lui donne pas les alertes Maximilien, et inversement. Pour qu'une personne
> reçoive tout, l'inscrire aux deux endroits.

---

## 2. Changer l'expéditeur

**Aujourd'hui** : `maintainers@users.noreply.github.com`.

L'envoi passe par Gmail, qui exige un **mot de passe d'application** — pas le mot
de passe du compte. Il se crée sur https://myaccount.google.com/apppasswords
(la validation en deux étapes doit être active sur le compte).

### En local

Éditer `alertes_secrets.json` :

```json
{
  "smtp_user": "nouvelle.adresse@gmail.com",
  "smtp_password": "les 16 caracteres du mot de passe d application",
  "destinataire": "adresse.de.secours@gmail.com"
}
```

- `smtp_user` : l'adresse d'envoi. Elle se reçoit aussi une copie de chaque alerte.
- `smtp_password` : le mot de passe d'application. Les espaces sont tolérés.
- `destinataire` : utilisé **uniquement** si `destinataires.txt` est vide ou absent.

Ce fichier n'est jamais versionné et ne part jamais dans le tableur partagé.

### Pour la veille cloud

Les deux secrets GitHub **`CHRUTH_SMTP_USER`** et **`CHRUTH_SMTP_PASSWORD`**.

### Règle de priorité, si tu changes au mauvais endroit

Les variables d'environnement **écrasent** le fichier :

```
CHRUTH_SMTP_USER / CHRUTH_SMTP_PASSWORD   →  sinon alertes_secrets.json
destinataires.txt  →  sinon CHRUTH_ALERTE_DEST  →  sinon "destinataire" des secrets
```

Si une modification « ne prend pas », c'est presque toujours qu'une variable
d'environnement plus prioritaire est encore posée.

### Changer de fournisseur (autre que Gmail)

`ao_config.py`, deux lignes :

```python
ALERTE_SMTP_HOST = "smtp.gmail.com"
ALERTE_SMTP_PORT = 587
```

Le protocole utilisé est STARTTLS. Un serveur en SSL direct (port 465) demanderait
une modification du code.

---

## 3. Agir depuis le tableur Excel

Cockpit : `output\AO_CHRUTH.xlsm`. Les boutons sont sur l'onglet **Parametres**,
sauf celui des messages qui est sur `AO_Nettoyage_IDF`.

| Bouton | Ce qu'il fait |
|---|---|
| **Mettre a jour les AO** | Relance la collecte et régénère le tableur |
| **Notifications ON/OFF** | Coupe les emails. La collecte, elle, continue |
| **Collecte ON/OFF** | Coupe les appels réseau (BOAMP, Maximilien) |
| **Enregistrer destinataires** | Écrit la colonne B dans `destinataires.txt` |
| **Generer le message IA** | Sur la ligne d'AO sélectionnée → onglet `Message_IA` |

Les deux interrupteurs écrivent dans des fichiers qui font foi, `alertes_actives.flag`
et `collecte_active.flag` (`ON` / `OFF`). Ils survivent à la régénération du tableur —
tu peux aussi les éditer au Bloc-notes.

> ### Le piège à connaître
>
> **Le tableur est reconstruit à neuf à chaque mise à jour.** Toute saisie faite
> ailleurs que dans la colonne des destinataires est **perdue** : elle n'est pas
> relue avant d'être écrasée.
>
> Pour qu'une information survive, elle doit aller **dans la base** (section 4) :
> c'est elle la source, le tableur n'en est qu'une photo.

Deuxième piège : les `.xlsm` sont associés à **WPS Spreadsheets**, qui **verrouille
le fichier**. Tableur ouvert, la régénération échoue. Fermer WPS avant une mise à jour.

---

## 4. Agir depuis la base de données

Fichier : `data\ao_chruth.sqlite`, table `ao_records`, une ligne par AO, clé `id_ao`
(`26-…` pour BOAMP, `MX-…` pour Maximilien).

Ouvrir avec [DB Browser for SQLite](https://sqlitebrowser.org/) (gratuit), ou en
ligne de commande depuis le dossier de production :

```bash
python -c "import sqlite3;c=sqlite3.connect('data/ao_chruth.sqlite');[print(r) for r in c.execute(\"select id_ao,priorite,substr(objet,1,50) from ao_records limit 10\")]"
```

### Les colonnes qui pilotent le comportement

| Colonne | Effet |
|---|---|
| `alerte_envoyee` | Horodatage. **Non vide = déjà notifié**, ne repartira pas |
| `verdict_tri` | `PERTINENT` ou `REJETE`. `REJETE` = jamais notifié |
| `motif_tri` | La raison, reprise dans l'email et l'app |
| `priorite` | `CHAUD` / `TIEDE` / `FROID`. Seuls les deux premiers sont notifiés |
| `date_publication` | Date de l'avis. Sert au classement et au Top 20 de la semaine |
| `statut_contact`, `commentaire_humain`, `rdv_obtenu` | Ton suivi commercial |

### Renvoyer un AO que tu as raté

Vider son horodatage : il repartira à la prochaine alerte.

```sql
UPDATE ao_records SET alerte_envoyee = '' WHERE id_ao = '26-71675';
```

### Forcer un verdict que le tri a mal jugé

```sql
UPDATE ao_records SET verdict_tri = 'PERTINENT', motif_tri = 'validé à la main'
WHERE id_ao = 'MX-943757';
```

Pour un AO **Maximilien**, préfère les boutons de l'app : la correction y est
gardée **et** réinjectée dans le prompt, donc l'IA apprend. En base, tu corriges
un cas ; dans l'app, tu corriges la règle.

### Faire taire durablement une famille d'AO

Ne bricole pas la base : ajoute le terme dans `ao_config.py`, liste
`AO_EXCLUSION_TRI`. Tous les AO concernés, présents et à venir, seront écartés
avec un motif lisible.

### Voir ce qui partirait au prochain envoi

```bash
python -c "import ao_alertes,sys;sys.stdout.reconfigure(encoding='utf-8',errors='replace');r=ao_alertes.nouveaux_ao_a_alerter();print(len(r),'AO');[print(' ',a['id_ao'],a['priorite'],(a['objet'] or '')[:55]) for a in r]"
```

Aucun email n'est envoyé : cette commande ne fait que lire.

> ### Ne jamais supprimer de lignes
>
> L'anti-doublon repose sur la présence de l'`id_ao`. Un AO supprimé sera
> recollecté, re-scoré, et **re-notifié** comme s'il était nouveau. Pour faire
> disparaître un AO, mets-le à `verdict_tri = 'REJETE'` : il reste en base,
> traçable, et ne dérange plus.
>
> Avant toute modification en masse, copie le fichier `.sqlite` ailleurs. Il fait
> 6 Mo.

---

## 5. Vérifier qu'un changement a bien pris

Depuis le dossier de production :

```bash
python -c "import ao_alertes; c=ao_alertes.charger_config_smtp(); print('expediteur :', c['smtp_user']); print('destinataires :', c['destinataires'])"
```

La commande lit exactement ce que le programme lira au moment d'envoyer, en
appliquant les règles de priorité. Si elle affiche ce que tu attends, c'est bon.

Si elle s'arrête sur une erreur, le message dit lequel des deux manque —
identifiants ou destinataires.

---

## 6. En cas de doute

| Symptôme | Première chose à regarder |
|---|---|
| Plus aucun email | `alertes_actives.flag` est-il à `ON` ? |
| Rien de nouveau ne remonte | `collecte_active.flag` est-il à `ON` ? |
| Le changement d'adresse n'a pas pris | Une variable d'environnement plus prioritaire (section 2) |
| La mise à jour du tableur échoue | WPS Spreadsheets garde le fichier ouvert |
| Un AO hors métier notifié | L'ajouter à `AO_EXCLUSION_TRI` dans `ao_config.py` |
| Un vrai AO jamais notifié | Vérifier `verdict_tri` et `priorite` en base |

Les journaux de chaque exécution sont dans `logs\`, un fichier horodaté par run.
