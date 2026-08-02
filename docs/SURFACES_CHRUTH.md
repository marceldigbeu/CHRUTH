# Les surfaces CHRUTH, et laquelle utiliser

Cinq interfaces coexistent. Aucune n'a été supprimée : elles lisent et écrivent
toutes les mêmes réglages, via `reglages.py`.

| Surface | Usage | Évolue ? |
|---|---|---|
| **Plateforme Streamlit** (`LANCER_APP_CHRUTH.bat`) | Collecte AO/prospects avec journal, veille, base, carte, fichiers, messages, CRM, pilotage, réglages et mode développeur relié à Excel. Seule accessible au téléphone | **Oui** |
| Cockpit Excel `AO_CHRUTH.xlsm` | Consulter, filtrer, annoter. Ses boutons écrivent dans la source unique | Gelé |
| Cockpit web `COCKPIT_CHRUTH.bat` | Lancer les traitements | Gelé |
| Interface Windows `OUVRIR_MOI_CHRUTH.bat` | Lancer les traitements | Gelé |
| Notebooks Jupyter | Inspecter, expérimenter | Gelés |

**Gelé** veut dire : fonctionnel, maintenu, mais sans nouveauté. Toute fonction
nouvelle arrive dans la plateforme Streamlit.

## Prospection : passage aux « Acheteurs de la semaine » (2026-07-27)

Depuis T9, la prospection passe par le cycle **« Acheteurs de la semaine »** dérivé
des appels d'offres (AOs), avec mise à jour hebdomadaire chaque lundi 08:45.
L'ancienne collecte « toutes entreprises IDF » reste dormante : sa carte 132k est
conservée mais n'est plus régénérée. La tâche programmée `CHRUTH Prospects - hebdo
(carte)` a été désactivée (non supprimée) et remplacée par `CHRUTH Acheteurs - hebdo`
(voir `outils/installer_tache_acheteurs.ps1`).

Un réglage changé dans n'importe laquelle est vu par toutes les autres : elles
partagent `etat/veille.json` sur la branche `ao-state`, avec un cache local qui
prend le relais si GitHub est injoignable.

**Ce qui n'est pas partagé** : le mot de passe d'application Gmail, qui reste dans
`alertes_secrets.json` et les secrets GitHub. L'état est versionné.

## Ordre de priorité, quand deux surfaces disent le contraire

`reglages.lire()` empile trois sources, la dernière gagne :

1. les défauts du code (`reglages.DEFAUTS`) ;
2. le cache local `reglages_cache.json` ;
3. l'état partagé sur `ao-state`.

Conséquence pratique : **hors ligne, le cache fait foi et rien ne se perd** — une
saisie est écrite sur disque *avant* le réseau, et repart à la prochaine écriture
réussie. Les anciens leviers locaux (`destinataires.txt`, `alertes_actives.flag`,
`collecte_active.flag`) restent écrits et servent de repli quand l'état partagé
est injoignable.

Les réglages sont relus une fois par processus. Une surface qui tourne longtemps
(la plateforme) reprend les changements venus d'ailleurs au rechargement de la
page, ou via `reglages.rafraichir()`.
