# Mettre la plateforme de veille en ligne

L'app se lance en local sans rien configurer. La mise en ligne sert à la consulter
depuis un téléphone, sans PC allumé.

## En local, tout de suite

Double-clic sur `LANCER_APP_CHRUTH.bat`, ou :

```
python -m streamlit run CHRUTH_APP.py
```

L'application s'ouvre sur la veille ; la page « Messages et CRM » est dans le
menu de gauche.

Elle lit `etat/veille.json` dans le dossier du projet. Sans veille cloud encore en
service, ce fichier se remplit avec :

```
python ao_maximilien_veille.py
```

## En ligne, sur Streamlit Community Cloud

### 1. Connecter le dépôt

share.streamlit.io > **New app** > le dépôt `CHRUTH`, branche `main`,
fichier principal `CHRUTH_APP.py`.

### 2. Renseigner les secrets de l'app

**Settings > Secrets** de l'app, au format TOML :

```toml
CHRUTH_VEILLE_SOURCE = "github"
CHRUTH_GITHUB_REPO = "<compte>/CHRUTH"
CHRUTH_GITHUB_TOKEN = "<jeton a portee fine>"
```

Le jeton se crée dans GitHub > Settings > Developer settings >
**Fine-grained tokens**, limité à ce **seul dépôt**, avec exactement deux
permissions :

| Permission | Pourquoi |
|---|---|
| `Contents: Read and write` | lire et réécrire `etat/veille.json` sur `ao-state` |
| `Actions: Read and write` | le bouton « Vérifier maintenant » |

Conséquence assumée : ce jeton permet d'écrire dans le dépôt. Il est limité à un
dépôt, à deux permissions, et révocable en un clic.

Sans jeton, l'app fonctionne en **lecture seule** : le fil s'affiche, les boutons
de correction refusent poliment d'écrire.

### 3. Le point à vérifier : qui peut ouvrir le lien

Sur le palier gratuit, la restriction d'accès repose sur le partage du lien.
La conception en tient compte :

- **Ce que l'app affiche par défaut** : uniquement des données d'appels d'offres,
  qui sont **publiques** (ce sont des avis de marchés publics).
- **Ce qu'elle n'affiche pas** : le guide des messages, qui est de l'information
  d'entreprise. Il reste masqué tant que `CHRUTH_VEILLE_GUIDE` n'est pas mis à `1`.
  Ne l'activer qu'une fois l'accès réellement restreint — ou l'éditer en local.
- Le CRM et les données commerciales ne sont pas dans cette app.

### 4. Vérifier

- Le fil affiche les AO, du plus récent au plus ancien.
- « Afficher les AO rejetés par le tri » les fait apparaître avec leur motif.
- Un clic sur **Pas pertinent** survit à un rechargement de la page.
- La correction est reprise par le prochain run de veille comme exemple de tri.

## Comment l'app et la veille se partagent le fichier

Les deux écrivent `etat/veille.json` sur la branche `ao-state` : le workflow par
`git`, l'app par l'API GitHub. L'app relit avant d'écrire et réessaie une fois en
cas de conflit — un run de veille qui écrit entre-temps ne fait donc rien perdre.
