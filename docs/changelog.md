# CHANGELOG

## 3.2.1 (2026-03-XX)

**🚀 Nouveautés**

- Ajout d'un paramètre is_secondary aux fournisseurs d'identité (#144 par @IdrissaD)


**🐛 Corrections**

- Correction de la réconciliation dans le connecteur OpenID (#152 par @jacquesfize)
- Arrêt de l'utilisation de `pkg_resources` (#149 par @christophe-ramet)

## 3.2.0 (2026-02-18)

**🚀 Nouveautés**

- Compatibilité avec Debian 13 (#131 par @Pierre-Narcisi)
- Ajout de contraintes d'unicités sur les colonnes `t_roles.identifiant`, `t_roles.uuid_role` et `bib_organismes.nom_organisme` (#141 par @jacquesfize)
- Création de la classe `UserManager` qui reprend les méthodes déclarées dans `subscribe.py` et intègre de nouvelles méthodes pour vérifier la validité d'un mot de passe (nombre min. de caractère, présence de majuscule, etc.) (#126 par @christophe-ramet)
- Ajout de méthodes dédiées à l'ajout, la modification et la suppression d'organismes (#130 par @VincentCauchois)
- Ajout d'un paramètre `CODE_CHALLENGE_METHOD` dans le _provider_ OpenIDConnect (#133 par @christophe-ramet)
- Ajout d'une méthode permettant de changer le mot de passe d'un utilisateur (#132 par @christophe-ramet)
- Ajout des colonnes `api_key` et `api_secret` dans la table `t_roles` (par @christophe-ramet et @jacquesfize)

**🐛 Corrections**

- Correction de la prise en compte du paramètre `PASS_METHOD` et `FILL_MD5_PASS` permettant de désactiver l'utilisation du MD5 (#145 par @jacquesfize)
- Dans le _provider_ pour OpenID, l'identifiant s'appuie sur une variable de configuration (par défaut, `preferred_username`) (#138 @edelclaux)

## 3.1.0 (2025-11-14)

**🚨 Breaking Changes**

- La route `/post_usershub` a été supprimée. Pour utiliser l'API de UsersHub, il est maintenant nécessaire d'utiliser les routes directement accessibles depuis cette dernière (#125 par @jacquesfize)

**🚀 Nouveautés**

- Ajout de méthodes dédiées à la création utilisateur et la modification du mot de passe disponible dans `pypnusershub.auth.subscribe` (#125 par @jacquesfize)
- Ajout des derniers modèles SQLAlchemy manquant des tables dans schéma `utilisateurs` (#125 par @jacquesfize)

## 3.0.4 (2025-11-12)

**🐛 Corrections**

- Renforcement de la sécurité de la route d'interaction avec UsersHub (#124 par @christophe-ramet)

## 3.0.3 (2025-03-07)

**🐛 Corrections**

- [Commande Flask] Complétion de la commande `user add` permettant d'indiquer le nom et le prénom de l'utilisateur (par @jacquesfize)
- [Commande Flask] Suppression d'un import qui faisait disfonctionner UsersHub 2.4.5.(par @jacquesfize)
- [Utilisateur] Correction du la suppression d'un utilisateur avec une entrée dans `cor_role_provider` (#119 par @jacquesfize)

## 3.0.2 (2025-02-10)

**🚀 Nouveautés**

- Ajout des champs `meta_create_date` et `meta_update_date` à la table `bib_organismes` (#96 par @lpofredc).
- Ajout de commandes `flask` pour ajouter/modifier des utilisateurs et changer leur mot de passe (#53 par @jacquesfize)

## 3.0.1 (2024-11-29)

**🐛 Corrections**

- Correction d'un problème de redirection lors de la déconnexion
- Utilisation du schéma marshmallow pour le retour de la route `/auth/public_login`
- Ajout du décorateur `@serializable` sur la classe `Provider`

## 3.0.0 (2024-08-07)

**🚀 Nouveautés**

- Enrichissement des modes de connexions avec l'implémentation de `AuthManager` (#93). Plusieurs protocoles
  de connexions sont disponibles : par défaut, OpenID, OpenIDConnect, UsersHub-authentification-module externe.

**⚠️ Notes de version**

- Remplacer l'initialisation du `login_manager` par celle du `auth_manager` lors de l'initialisation de votre
  application Flask comme dans l'exemple ci-dessous :

```python
from pypnusershub.auth import auth_manager
providers_config = [
  {
    "module" : "pypnusershub.auth.providers.default.LocalProvider",
    "id_provider":"local_provider"
  },
]
auth_manager.init_app(app,providers_declaration=providers_config)
```

## 2.1.5 (2024-05-23)

**🚀 Nouveautés**

- Mise à jour de dépendances critiques : `requests`, `jinja2`, `werkzeug` (#102)
  2.1.4 (2024-04-23)

---

**🐛 Corrections**

- Synchronisation de l'expiration des token JWT et du cookie de session généré par `flask-login` (#94)

## 2.1.3 (2024-02-22)

**🐛 Corrections**

- Debug de l'inscription d'un utilisateur depuis GeoNature (#92)

## 2.1.2 (2024-02-16)

**🐛 Corrections**

- Debug de la route utilisée pour l'accès public dans GeoNature (#89)

## 2.1.1 (2024-01-30)

**🚀 Nouveautés**

- Mise à jour de Utils-Flask-SQLAlchemy en version 0.4.1

**🐛 Corrections**

- Modification de l'instanciation du UserSchema dans la route `/auth/login` pour retourner `max_level_profil`

## 2.1.0 (2024-01-29)

**🚀 Nouveautés**

- Mise à jour de Flask version 2 à 3 (#81)
- Mise à jour de SQLAlchemy version 1.3 à 1.4 (#81)
- Arrêt du support de Debian 10 (#81)
- Ajout de Debian 12 dans les tests automatisés (#81)
- Mise à jour du linter black en version 24 (#86)
- Ajout de l'organisme au modèle (#83)
- Ajout du contexte `logged_user` (#84)

**🐛 Corrections**

- Correction de la route de test de connexion à UsersHub (#82)
- Ajout de la propriété `max_level_profil` aux colonnes exclues par défaut (#80)

## 2.0.0 (2023-10-18)

**🚀 Nouveautés**

- Utilisation de la librairie Flask-Login pour la génération et la manipulation du cookie
- Ajout de la possibilité de s'authentifier via un JWT dans les headers HTTP

**⚠️ Notes de version**

Le décorateur `@check_auth` change de signature, les paramètres suivants sont obsolètes :

- `get_role` : l'utilisateur connecté est disponible via `flask_login.current_user`
- `redirect_on_expiration` , `redirect_on_invalid_token` : l'utilisateur sera redirigé vers la vue définie par `login_manager.login_view` (à modifier dans l'application utilisant le sous-module)
- `redirect_on_insufficient_right` : le paramètre applicatif `REDIRECT_ON_FORBIDDEN` contrôle la route de redirection si les droits pour accéder à la ressource sont insuffisants. Lève une 403 si ce paramètre n'est pas défini.
- Le retour de la route `/auth/login` change. L'attribut id_droit_max utilisé pour contrôler les droits côté frontend devient `max_level_profil`

## 1.6.11 (2023-09-19)

**🐛 Corrections**

- Correction de la suppression du cookie sur des sous-domaines lors du logout

## 1.6.10 (2023-09-14)

**🐛 Corrections**

- Correction d'une mauvaise utilisation de la redirection sur la route de `logout`

## 1.6.9 (2023-08-08)

**🐛 Corrections**

- Correction de l'encodage des dates dans le JWT (#62 - par @mvergez)
- Augmentation de la taille du champs `utilisateurs.temp_users.organisme` de 30 à 250 caractères (#73)

## 1.6.8 (2023-06-26)

**🐛 Corrections**

- Meilleur contrôle du cookie (mis uniquement sur le domaine ou le path de l'application) #69 @mvergez

## 1.6.7 (2023-06-07)

**🐛 Corrections**

- Correction de l'import du répertoire `tests`

## 1.6.6 (2023-06-06)

**🚀 Nouveautés**

- Ajout du champs `champs_addi` dans le model `User` #58
- Ajout d'une fonction query `filter_by_app` sur le model `User`
- Amélioration de la méthode `__str__` du model `User`

## 1.6.5 (2023-03-04)

**🚀 Nouveautés**

- Compatibilité authlib 1.1
- Compatibliité SQLAlchemy 1.4
- Mise à jour Utils-Flask-SQLAlchemy 0.3.2

## 1.6.4 (2022-12-16)

**🚀 Nouveautés**

- Ajout d’une propriété `is_public` sur le modèle `User` qui vaut vraie quand il s’agit de l’utilisateur public

## 1.6.3 (2022-12-13)

**🚀 Nouveautés**

- Ajout d’une route `/public_login` permettant de se connecter sans mot de passe avec l’utilisateur ayant pour identifiant celui précisé dans le paramètre de configuration `PUBLIC_ACCESS_USERNAME`. La route renvoie une erreur 403 (Fobidden) si le paramètre de configuration n’est pas défini.

## 1.6.2 (2022-11-22)

**🐛 Corrections**

- Correction d’une inclusion circulaire

## 1.6.1 (2022-11-15)

**🚀 Nouveautés**

- Ajout du paramètre configuration `CODE_APPLICATION` permettant de récupérer l’identifiant de l’application courante en l’absence du paramètre `ID_APP`.

**🐛 Corrections**

- Ajout / correction de relationships dans les modèles

## 1.6.0 (2022-08-31)

**🚀 Nouveautés**

- Ajout d’une contrainte d’unicité sur la colonn `uuid_role` de la table `t_roles`.
- Ajout des modèles `UserList` et `cor_role_liste` correspondants aux tables existantes.
- Compatibilité Flask 2
  - Génération du cookie d’authentification avec `authlib` à la place de `itsdangerous`

- Mise à jour des dépendances
  - Utils-Flask-SQLAlchemy 0.3.0

**🐛 Corrections**

- Correction du format du cookie généré par la fonction `logged_user_headers`

## 1.5.10 (2022-08-03)

**🚀 Nouveautés**

- Github Action de publication automatique du paquet sur pypi
- Ajout de fonctions utilitaires pour les tests
- Amélioration des modèles (`Application.profils` & `Profils.applications`)

**🐛 Corrections**

- Correction d’une dépréciation dans un schéma Marshmallow
- Correction des versions des dépendances requises

## 1.5.9 (2022-01-12)

**🚀 Nouveautés**

- Ajout des fonctions `insert_or_update_organism` et `insert_or_update_role`
- Ajout de tests automatisés
- Intégration continue du module pour exécuter automatiquement les tests et la couverture de code avec GitHub Actions, à chaque commit ou pull request dans les branches `develop` ou `master`

## 1.5.8 (2022-01-03)

**🚀 Nouveautés**

- L’affichage d’un organisme renvoit son nom
- Les schémas Marshmallow des modèles User et Organisme utilise `SmartRelationshipsMixin`
- Ajout de `User.identifiant` aux données sérialisées avec Marshmallow

**🐛 Corrections**

- L’`ID_APP` peut ne pas être présent dans la configuration.
- Suppression du calcul du nom complet dans le schéma Marshmallow de l’utilisateur pour utiliser la fonction du modèle

## 1.5.7 (2021-10-17)

**🐛 Corrections**

- Correction d’un fichier de migration Alembic

## 1.5.6 (2021-10-18)

**🐛 Corrections**

- Correction d’un fichier de migration Alembic

## 1.5.5 (2021-10-13)

**🚀 Nouveautés**

- La route de login est désormais capable de récupèrer l’`id_app` depuis la configuration Flask

**🐛 Corrections**

- Correction d’un fichier de migration Alembic (suppression d’une vue avant sa création)

## 1.5.4 (2021-10-06)

**🐛 Corrections**

- Suppression des `id_organisme` en dur dans les données d’exemple

## 1.5.3 (2021-09-29)

**🐛 Corrections**

- Ajout d’un fichier `__init__.py` dont l’absence excluait les révisions Alembic lors du paquetage du module

## 1.5.2 (2021-09-29)

**🚀 Nouveautés**

- Ajout d’un champs JSONB `additional_data` à la table `bib_organismes`
- Ajout d’une contrainte d’unicité sur `bib_organismes.uuid_organisme` (permet d’utiliser `ON CONFLICT UPDATE`)
- Possibilité d’installer le schéma `utilisateurs` avec Alembic sans passer par une application Flask telle que UsersHub (voir documentation)
- Utilisation d’un dictionnaire `REGISTER_POST_ACTION_FCT` pour déclarer les callbacks de post-actions plutôt que l’entrée `after_USERSHUB_request` dans la config de Flask

**🐛 Corrections**

- Correction de la vue `v_roleslist_forall_applications` (`LEFT JOIN`)
- Correction des SQL d’installation : les évolutions sont amenées par les migrations Alembic

## 1.5.1 (2021-09-07)

**🐛 Corrections**

- Corrections du packaging des migrations

## 1.5.0 (2021-09-06)

**🚀 Nouveautés**

- Gestion du schéma `utilisateurs` avec Alembic par ce module (et non plus dans UsersHub)

**🐛 Corrections**

- Corrections mineurs des modèles

## 1.4.7 (2021-07-22)

**🚀 Nouveautés**

- Amélioration des messages et e-mails utilisateurs

**🐛 Corrections**

- Corrections de 2 bugs mineurs

## 1.4.6 (2021-06-03)

**🚀 Nouveautés**

- Ajout du modèle Organisme et de la table de correspondance `cor_role`
- Support de la méthode de mot de passe `hash` via l’attribut du modèle
- Amélioration des relationships
- Utilisation de @serializable sur les modèles
- Ajout des schémas Marshmallow

**🐛 Corrections**

- Correction du nom d’un n° de séquence

## 1.4.5 (2021-02-24)

**🚀 Nouveautés**

- Passage de l'instance de SQLAlchemy du module parent via une variable d'environnement

**🐛 Corrections**

- Les dépendances du fichier `requirements.txt` ne sont plus fixées à une version

## 1.4.4 (2020-10-17)

**Nouveautés**

- Ajout du nom complet dans le modèle `User` en tant que propriété hybride
- Mise à jour des dépendances (psycopg2 et SQLAlchemy)
- Ajout de l'url de confirmation dans le modèle `TempUser`

## 1.4.3 (2019-12-18)

**Corrections**

- Adaptation des méthodes `as_dict()` pour compatibilité avec la lib utils-flask-sqla (paramètres `relationships` et `depth`)

## 1.4.2 (2019-10-08)

**Corrections**

- Echappement des balises HTML sur le retour de la route "/login" pour corriger une faille XSS (fausse faille car inexploitable)

## 1.4.1 (2019-09-17)

**Corrections**

- Correction de la serialisation du modèle TempUser

## 1.4.0 (2019-09-16)

**Nouveautés**

- Ajout de routes permettant d'utiliser les actions de gestion de compte de l'API de UsersHub (création d'utilisateurs temporaires, ajout de droits à un utilisateur, récupération des droits d'un utilisateur...) #23
- Ajout d'un mécanisme de proxy permettant d'effectuer des "post_actions" sur chacune des routes de gestion de compte (envoi d'email, gestion applicative)
- Documentation de l'API (https://github.com/PnX-SI/UsersHub-authentification-module/blob/master/README.md#utilisation-de-lapi)
- Mise à jour de Flask (1.0.2 vers 1.1.1)

**Corrections**

- Corrections, optimisations, nettoyage et refactorisations diverses

## 1.3.3 (2019-05-29)

**Nouveautés**

- Mise à jour de SQLAlchemy 1.1.13 vers 1.3.3

## 1.3.2 (2019-02-27)

**Nouveautés**

- Ajout d'un callback de redirection lorsque les droits sont insuffisants sur le décorateur `check_auth` (`redirect_on_insufficient_right`)

**Corrections**

- Correction de conflit d'authentification et de permissions entre les différentes applications utilisant le sous-module sur le même domaine (vérification que le token correspond à l'application courante).

Note pour les développeurs : ce conflit est corrigé en ajoutant un paramètre `ID_APP` dans la configuration des applications utilisant ce sous-module (`config.py`). La vérification que le token correspond bien à l'application courante n'est pas assuré si ce paramètre n'est pas passé, pour des raisons de rétro-compatibilité.

## 1.3.1 (2019-01-15)

**Corrections**

- Ajout de la classe `AppRole` au modèle
- Redirection si les droits de l'utilisateur sont insuffisants

## 1.3.0 (2019-01-14)

**Nouveautés**

- Compatibilité avec la version 2 UsersHub
- Suppression des routes et objets du modèle lié au CRUVED qui a été retiré de UsersHub pour le basculer dans GeoNature
- Optimisation des accès à la BDD en utilisant l'instance `DB` de l'application dans laquelle est utilisée ce sous-module

**Corrections**

- Précisions dans la documentation (README) sur le script SQL à utiliser depuis le dépôt de UsersHub
- Suppression des scripts SQL locaux pour se n'utiliser que ceux à jour dans le dépôt de UsersHub

## 1.2.1 (2018-10-08)

**Corrections**

- Ajout d'un test sur la fonction `fn_check_password` pour vérifier si le mot de passe existe

## 1.2.0 (2018-09-19)

- Modification de la route de login pour se connecter sans passer par la table `cor_role_droit_application` lorsqu'on fonctionne avec le CRUVED
- Mise à jour des dépendances (`requirements.txt`)
- Mise à jour de Flask (0.12.2 à 1.0.2)

**Corrections**

- Correction des droits des applications filles retournées lors du login
- Correction de la redirection après logout

## 1.1.1 (2018-06-18)

- Version corrective lié à la récupération du CRUVED des sous-modules

## 1.1.0 (2018-05-17)

**Nouveautés**

- Répercussion du changement du modèle de UsersHub. Le sous-module permet maintenant l'authentification en utilisant une des deux méthode de cryptage de mot de passe (MD5 et HASH). Ajout du paramètre `PASS_METHOD` (valeur possible : 'hash' ou 'md5') qui contrôle ce comportement.
- Prise en compte des évolutions de la version 1.3.1 de UsersHub intégrant la gestion des droits utilisateurs via des 'tags'.
- Ajout de fonctionnalités nécessaires à GeoNature v2 (gestion des droits avec le CRUVED) :
  - Ajout du décorateur `@check_auth_cruved` pour protéger les routes en passant paramètre une action du CRUVED et une application ou un module.
  - Fonction `cruved_for_user_in_app` permettant de récupérer le CRUVED d'un utilisateur

- Corrections diverses

**⚠️ Notes de version**

Cette release n'est compatible avec UsersHub 1.3.1 minimum, qui inclut d'importantes évolutions de la BDD (https://github.com/PnEcrins/UsersHub/blob/develop/data/update_1.3.0to1.3.1.sql).

## 1.0.2 (2017-12-15)

**Nouveautés**

Intégration des pull request de @ksamuel

- Ajout des paramètres :
  - redirect_on_invalid_token
  - redirect_on_expiration

- Diverses petites améliorations

## 1.0.1 (2017-03-10)

**Nouveautés**

Intégration de la pull request de @ksamuel.

### Models:

- nouvelles classes pour mapper les tables `bib_droits` et `cor_role_droit_application`
- la classe User utilise md5 pour hasher son password au lieu de sha256. Il faudrait alerter UsersHub de changer le hashing de leur password pour un algo plus robuste et avec un salt. Mais en attendant on doit utiliser le leur.
- `__repr__` pour faciliter le debuggage
- AppUser n'a plus de setter sur le password puisque c'est une vue en lecture seule

### Auth workflow:

- exceptions plus granulaires et exceptions personnalisées
- obtenir un objet User depuis un token est maintenant une fonction indépendante
- ajout d'une vue pour le log out
- pas de renouvellement de cookie si le token est vide ou en cours d'écriture
- redirection optionnelle sur check_auth
- usage optionnel des codes HTTP standards pour les erreurs
- le modèle user est maintenant attaché à Flask.g
- COOKIE_AUTORENEW passe sur True par défaut pour éviter d'avoir à setter la valeur pour les projets existant. Une erreur de ma part dans la première PR.

## 1.0.0 (2017-03-03)

Première version stable du sous-module d'authentification.

Le module peut désormais être intégré de façon indépendante (merci @ksamuel).

## 0.1.0 (2016-07-07)

Première version du sous-module d'authentification de UsersHub (https://github.com/PnEcrins/UsersHub/).

Il permet d'intégrer une authentification dans une application tiers en se basant sur la base de données centralisée de UsersHub.
