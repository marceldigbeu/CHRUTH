# Plan d'implémentation — Espace utilisateur personnel CHRUTH

Document de travail : il décide, avant le code, le stockage, les frontières entre
données communes et données personnelles, et les compromis assumés.

## 1. Décisions de stockage (questions de la section 9)

| Question | Décision | Conséquence |
|---|---|---|
| Base hébergée | **Branche GitHub dédiée** (reprise de l'architecture `veille_depot`), pas de base hébergée au lancement | Aucun compte Supabase/Neon à ouvrir maintenant ; l'abstraction du dépôt reste le point de branchement futur |
| Qui ouvre le compte | Le dépôt GitHub existe déjà (repos + jeton) | Rien à créer |
| Nombre d'utilisateurs | 3 ou moins | Un fichier par membre, un écrit par action : largement sous les limites de l'API GitHub |
| Comptes sans Google | **Oui, inscription locale** (mot de passe haché) | Justifié : des membres sans compte Google doivent entrer. Voir section 4 |
| Photo + téléphone | **Uniquement en local** | Exception documentée au critère de persistance en ligne. Voir section 5 |
| Départ d'un salarié | **Suppression complète** | Geste administrateur : suppression du fichier membre |

## 2. Le conflit « données personnelles sur GitHub »

Le critère d'acceptation interdit de publier des données personnelles sur la branche
d'état, et le document interdit tout secret dans un fichier versionné. Les réponses
choisissent pourtant le stockage GitHub. Le plan résout la contradiction en changeant
les deux termes :

- **Pas la branche d'état.** Les données personnelles vont sur une branche dédiée
  `espace-membres`, dans un chemin dédié `etat/espace_membres/<email>.enc`. La branche
  `ao-state` et le fichier `veille.json` restent ce qu'ils sont : des données
  communes, non personnelles.
- **Chiffré au repos.** Chaque fichier membre est chiffré (Fernet, bibliothèque
  `cryptography`). La clé vit dans les secrets Streamlit (en ligne) ou dans un fichier
  local ignoré par git (poste). Un lecteur du dépôt ne voit que du chiffré : le
  contenu n'est pas « publié » au sens utile du terme.

L'écriture sur GitHub reste une requête HTTP par action. Pour 3 utilisateurs, c'est
acceptable ; c'est d'ailleurs le comportement déjà accepté pour l'état de la veille.

## 3. Ce qui reste commun, ce qui devient personnel

**Reste commun (inchangé, aucune régression) :**
- `data/ao_chruth.sqlite` : appels d'offres, scores, verdicts de tri ;
- `reglages.py` + état partagé : destinataires, interrupteurs, fiche entreprise ;
- `etat/veille.json` sur `ao-state` : état de la veille, corrections humaines ;
- `crm/` et `suivi/` : suivi commercial et envois, déjà hors git.

**Devient personnel (fichiers `espace/membres/<email>.enc`) :**
- profil : nom affiché, rôle, téléphone, signature d'email ; photo de profil ;
- préférences d'affichage : filtres par défaut de la veille, page d'accueil, densité ;
- appels d'offres suivis / mis de côté, notes privées ;
- messages générés et retouchés, conservés pour réutilisation ;
- journal d'activité personnel.

## 4. Inscription locale (comptes sans Google)

Le document autorise la réintroduction de mots de passe si des personnes sans compte
Google doivent entrer, en exigeant de le dire et de le justifier. C'est le cas : la
réponse à la question 3 est « oui ».

- Hachage `hashlib.scrypt` (bibliothèque standard, paramètres stockés avec le haché) —
  pas de `werkzeug` : même garantie, zéro dépendance nouvelle.
- Le haché est stocké dans le fichier membre, lui-même chiffré.
- Le compte local respecte la même garde que Google : l'adresse doit figurer dans
  `[acces]` pour entrer. L'administrateur ouvre et ferme toujours cet accès dans les
  secrets ; l'écran Administration ne déplace pas le secret.
- L'identité finale est l'adresse email, quelle que soit la porte d'entrée (Google ou
  locale). Un même email ne peut pas avoir deux espaces.

## 5. Exception assumée au critère de persistance

« Les données personnelles survivent à un redémarrage en ligne » est couvert pour :
préférences, notes, AO suivis, messages, journal, attribution, profil texte.

Photo et téléphone ont été décidés « uniquement en local » : sur le poste, ils vivent
dans le fichier membre local ; en ligne, la photo affichée est celle de Google
(`st.user.picture`) et le téléphone n'est pas éditable. Cette exception est assumée
par le choix de la question 5 et documentée ici.

## 6. Mode poste local

Sans fournisseur d'identité (`[auth]` absent), la connexion reste exigée : c'est
le compte local qui protège l'entrée. Chaque membre crée son compte depuis
l'écran de connexion et se connecte ; le travail est rattaché à SON adresse, pas
à un utilisateur partagé. Le défaut `CHRUTH_UTILISATEUR_LOCAL` (`local@chruth`)
ne sert plus qu'au repli hors session (pages ouvertes seules, tests).

Le poste local est traité comme administrateur par défaut : tout compte local
connecté administre, sauf si une liste `[acces].admins` est définie — elle fait
alors foi, avec ou sans fournisseur.

## 7. Modules nouveaux

| Module | Responsabilité | Mi roir de |
|---|---|---|
| `espace_depot.py` | Lire/écrire/liste/supprime les fichiers membres chiffrés, local ou GitHub | `veille_depot.py` |
| `espace.py` | Opérations par membre : profil, préférences, AO, notes, messages, journal, comptes | `veille_etat.py` |
| `comptes.py` | Identité courante, mot de passe scrypt, utilisateur local par défaut | `connexion.py` |

## 8. Écrans

1. **Connexion** (modifiée) : bouton Google existant + formulaire compte local
   (connexion et création).
2. **Mon espace** : identité en lecture (email, nom Google), champs éditables (nom
   affiché, rôle, téléphone, signature), photo (Google en ligne, fichier local sur le
   poste), préférences d'affichage avec enregistrement explicite, aperçu du journal.
3. **Mes appels d'offres** : AO marqués (à voir, favori, mis de côté) et notes privées,
   distincts du verdict de tri commun.
4. **Mes messages** : messages conservés (email + script), réutilisables.
5. **Administration** : liste des membres, état (actif/désactivé), suppression complète,
   réinitialisation de mot de passe ; l'accès `[acces]` reste dans les secrets et
   l'écran se contente de l'afficher et de l'expliquer.

## 9. Tests (TDD)

- `tests/test_espace_depot.py` : chiffrement/déchiffrement, deux membres isolés,
  persistance après relecture, refus d'écriture sans clé ni jeton, source github
  (API simulée).
- `tests/test_espace.py` : isolation des données entre deux utilisateurs, persistance,
  suppression complète.
- `tests/test_comptes.py` : hachage/vérification du mot de passe, refus d'un mauvais
  mot de passe, utilisateur local par défaut en mode sans authentification.
- `tests/test_connexion.py` : refus d'une adresse non autorisée, autorisation d'une
  adresse connue, mode local ouvert.
