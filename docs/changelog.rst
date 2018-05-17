CHANGELOG
*********


1.1.0
-----

**Nouveautés**

- Repercussion du changement du modèle de UsersHub. Le sous-module permet maintenant l'authentification en utilisant une des deux méthode de cryptage de mot de passe (MD5 et HASH). Ajout du paramètre PASS_METHOD (valeur possible: 'hash' ou 'md5') qui contrôle ce comportement.

- Prise en compte des évolutions de la version 1.3.1 de Usershub intégrant la gestions des droits utilisateurs via des 'Tags'.

- Ajout de fonctionnalités necessaire à GeoNature v2 (gestion des droits avec le CRUVED)

  - Ajout du décorateur ``@check_auth_cruved`` pour protéger les routes en passant paramètre une action du CRUVED et une application ou un module.

  - Fonction ``cruved_for_user_in_app`` permettant de récupérer le CRUVED d'un utilisateur

- Corrections diverses


**Notes de version**

Cette release n'est compatible qu'avec UsersHub 1.3.1 (Voir les changement à réaliser si vous êtes sur la version 1.3.0 : https://github.com/PnEcrins/UsersHub/blob/develop/data/update_1.3.0to1.3.1.sql)
