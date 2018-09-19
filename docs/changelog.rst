CHANGELOG
*********

1.2.1 (unreleased)
------------------

**Corrections**

* 

1.2.0 (2018-09-19)
------------------

* Modification de la route de login pour se connecter sans passer par la table ``cor_role_droit_application`` lorsqu'on fonctionne avec le CRUVED
* Mise à jour des dépendances (``requirements.txt``)
* Mise à jour de Flask (0.12.2 à 1.0.2)

**Corrections**

* Correction des droits des applications filles retournées lors du login
* Correction de la redirection après logout

1.1.1 (2018-06-18)
------------------

* Version corrective lié à la récupération du CRUVED des sous-modules

1.1.0 (2018-05-17)
------------------

**Nouveautés**

* Répercussion du changement du modèle de UsersHub. Le sous-module permet maintenant l'authentification en utilisant une des deux méthode de cryptage de mot de passe (MD5 et HASH). Ajout du paramètre ``PASS_METHOD`` (valeur possible : 'hash' ou 'md5') qui contrôle ce comportement.
* Prise en compte des évolutions de la version 1.3.1 de UsersHub intégrant la gestion des droits utilisateurs via des 'tags'.
* Ajout de fonctionnalités nécessaires à GeoNature v2 (gestion des droits avec le CRUVED) :

  * Ajout du décorateur ``@check_auth_cruved`` pour protéger les routes en passant paramètre une action du CRUVED et une application ou un module.
  * Fonction ``cruved_for_user_in_app`` permettant de récupérer le CRUVED d'un utilisateur
* Corrections diverses

**Notes de version**

Cette release n'est compatible avec UsersHub 1.3.1 minimum, qui inclut d'importantes évolutions de la BDD (https://github.com/PnEcrins/UsersHub/blob/develop/data/update_1.3.0to1.3.1.sql).


1.0.2 (2017-12-15)
------------------

**Nouveautés**

Intégration des pull request de @ksamuel 

* Ajout des paramètres : 

  * redirect_on_invalid_token 
  * redirect_on_expiration

* Diverse petites améliorations

1.0.1 (2017-03-10)
------------------

**Nouveautés**

Intégration de la pull request de @ksamuel.

###  Models:

* nouvelles classes pour mapper les tables `bib_droits` et `cor_role_droit_application`
* la classe User utilise md5 pour hasher son password au lieu de sha256. Il faudrait alerter UsersHub de changer le hashing de leur password pour un algo plus robuste et avec un salt. Mais en attendant on doit utiliser le leur.
* `__repr__` pour faciliter le debuggage
* AppUser n'a plus de setter sur le password puisque c'est une vue en lecture seule

###  Auth workflow:

* exceptions plus granulaires et exceptions personnalisées
* obtenir un objet User depuis un token est maintenant une fonction indépendante
* ajout d'une vue pour le log out
* pas de renouvellement de cookie si le token est vide ou en cours d'écriture
* redirection optionnelle sur check_auth
* usage optionnel des codes HTTP standards pour les erreurs
* le modèle user est maintenant attaché à Flask.g
* COOKIE_AUTORENEW passe sur True par défaut pour éviter d'avoir à setter la valeur pour les projets existant. Une erreur de ma part dans la première PR.

1.0.0 (2017-03-03)
------------------

Première version stable du sous-module d'authentification.

Le module peut désormais être intégré de façon indépendante (merci @ksamuel).

0.1.0 (2016-07-07)
------------------

Première version du sous-module d'authentification de UsersHub (https://github.com/PnEcrins/UsersHub/). 

Il permet d'intégrer une authentification dans une application tiers en se basant sur la base de données centralisée de UsersHub.
