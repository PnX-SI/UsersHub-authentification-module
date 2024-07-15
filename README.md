# UsersHub-authentification-module

[![pytest](https://github.com/PnX-SI/UsersHub-authentification-module/actions/workflows/pytest.yml/badge.svg)](https://github.com/PnX-SI/UsersHub-authentification-module/actions/workflows/pytest.yml)
[![codecov](https://codecov.io/gh/PnX-SI/UsersHub-authentification-module/branch/master/graph/badge.svg?token=O57GQEH494)](https://codecov.io/gh/PnX-SI/UsersHub-authentification-module)

Module Flask (Python) permettant de gérer l'authentification suivant le modèle de [UsersHub](https://github.com/PnX-SI/UsersHub/).

Prévu pour être utilisé comme un submodule git.

Nécessite le schéma `utilisateurs` de UsersHub dans la BDD de l'application l'utilisant. Pour cela installez UsersHub dans la même BDD ou uniquement son schéma : https://github.com/PnX-SI/UsersHub/blob/master/data/usershub.sql

Par défaut le sous-module utilise le mot de passe "pass_plus" (méthode de hashage bcrypt) pour s'authentifier. Si vous souhaitez utiliser le champ "pass" (en md5), il faut passer le paramètre `PASS_METHOD = 'md5'` à la configuration Flask de l'application parent qui utilise le sous-module.

## Flask Login

Le sous-module utilise la librairie Flask-Login pour la gestion de l'authentification (https://flask-login.readthedocs.io/en/latest/).  
Cette librairie offre une méthode standard de gestion de l'authentification via un cookie de session. Le sous-module ajoute la possibilité de s'authentifier via un JWT si notre application utilise une API.  
Il est possible de surcoucher les vues de redirection ainsi que les callbacks renvoyés suite à une erreur 401. Voir https://flask-login.readthedocs.io/en/latest/#customizing-the-login-process.

## Routes

- `login/` :
  - parametres : login, password, id_application
  - return : token

## Fonction de décoration

- `@check_auth`
  - parametres : level = niveau de droit
  - utilise le token passé en cookie de la requête

## Exemple d'usage

Pour disposer des routes de connexions/deconnexions avec le protocole de connexion par défaut, le code minimal d'une application Flask est le suivant:

```python
from flask import Flask
from pypnusershub.auth import auth_manager

app = Flask(__name__) # Instantiate a Flask application
app.config["URL_APPLICATION"] = "/" # Home page of your application
providers_config = # Declare identity providers used to log into your app
    [
      # Default identity provider (comes with UH-AM)
      {
        "module" : "pypnusershub.auth.providers.default.DefaultConfiguration",
        "id_provider":"local_provider"
      },
      # you can add other identity providers that works with OpenID protocol (and many others !)
    ]
auth_manager.init_app(app,providers_config)

if __name__ == "__main__":
  app.run(host="0.0.0.0",port=5200)
```

Pour protéger une route, utiliser le décorateur `check_auth(niveau_profil)`:

```python
  # Import the decorator from
  from pypnusershub.decorators import check_auth

  @adresses.route('/', methods=['POST', 'PUT'])
  @check_auth(4) # Decorate the Flask route
  def insertUpdate_bibtaxons(id_taxon=None):
    pass
```

Pour utiliser les routes de UsersHub, ajouter les paramètres suivants dans la configuration de l'application :

- `URL_USERSHUB` : Url de votre UsersHub
- `ADMIN_APPLICATION_LOGIN` , `ADMIN_APPLICATION_PASSWORD`, `ADMIN_APPLICATION_MAIL` : identifiant de l'administrateur de votre UsersHub

```python
app.config["URL_USERSHUB"]="http://usershub-url.ext"

# Administrateur de mon application
app.config["ADMIN_APPLICATION_LOGIN"]="admin-monapplication"
app.config["ADMIN_APPLICATION_PASSWORD"]="monpassword"
app.config["ADMIN_APPLICATION_MAIL"]="admin-monapplication@mail.ext"
```

## Installation

### Pré-requis

- Python 3.9 ou ultérieur
- Paquets systèmes suivant: `sudo apt install python3-dev build-essential postgresql-server-dev`

### Installer `UsersHub-authentification-module`

Cloner le repository ou télécharger une archive, puis dans le dossier :

```
pip install .
```

### Configuration de la base de données

La manière la plus courante pour se connecter à la base de données en ayant les droits super-utilisateur est de se logger avec l'utilisateur 'postgres'. Par exemple sous Ubuntu :

```
sudo su postgres
```

**Création de la base de données**
Assurez-vous d'avoir au moins créé une base de données. Par exemple sous Ubuntu :

```sh
createdb ma_db
psql -d ma_db -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
```

**Création d'un utilisateur**
Il faut ensuite créer un utilisateur. Par exemple :

```
createuser -P parcnational
```

Puis donner les droits à cet utilisateur sur la base de données :

```sh
psql
```

Puis, entrez la requête suivante:

```sql
GRANT ALL PRIVILEGES ON DATABASE ma_db TO parcnational;
```

**Accédez à votre base de données**
SQLAlchemy vous permettra de vous connecter à la base de données avec une URL
de type :

```
postgresql://nom_utilisateur:mot_de_passe@host:port/db_name
```

**Création des tables et schémas nécessaires**

UsersHub-authentification-module s'appuit sur un schéma PostgreSQL nommée `utilisateurs`. Pour créer ce dernier et l'ensemble des tables nécessaires, on utilise `alembic`. Alembic est une librairie python de versionnage de base de données. Chaque modification sur la base de données est décrite par un révision (e.g. `/src/pypnusershub/migrations/versions/fa35dfe5ff27_create_utilisateurs_schema.py`). Cette dernière indique quelles sont les actions sur la base de données à effectuer pour passer à la révision suivante (fonction `upgrade()`) mais aussi pour revenir à la précédente (fonction `downgrade()`).

Dans un premier temps, indiquer la nouvelle url de connexion à votre BDD dans la variable `sqlalchemy.url` dans le fichier `alembic.ini`.

```ini
sqlalchemy.url = postgresql://parcnational:<mot_de_passe>@localhost:5432/db_name
```

Une fois modifié, lancer la commande suivante pour remplir la base de données:

```sh
alembic upgrade utilisateurs@head
```

### (Optionnel) Interface de gestion utilisateurs

Si vous souhaitez une interface permettant de modifier les données utilisateurs décritent dans `UsersHub-authentification-module`, il est conseillé d'utiliser [UsersHub](https://github.com/PnX-SI/UsersHub).

## Utilisation de l'API

### Routes définies par UsersHub-authentification module

Les routes suivantes sont implémentés dans `UsersHub-authentification-module` :

| Route URI           | Action                                                                                                                                         | Paramètres                 | Retourne                         |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | -------------------------------- |
| `/providers`        | Retourne l'ensemble des fournisseurs d'identités activés                                                                                       | NA                         |                                  |
| `/get_current_user` | Retourne les informations de l'utilisateur connecté                                                                                            | NA                         | {user,expires,token}             |
| `/login/<provider>` | Connecte un utilisateur avec le provider <provider>                                                                                            | Optionnel({user,password}) | {user,expires,token} ou redirect |
| `/public_login`     | Connecte l'utilisateur permettant l'accès public à votre application                                                                           | NA                         | {user,expires,token}             |
| `/logout`           | Déconnecte l'utilisateur courant                                                                                                               | NA                         | redirect                         |
| `/authorize`        | Connecte un utilisateur à l'aide des infos retournées par le fournisseurs d'identités (Si redirection vers un portail de connexion par /login) | {data}                     | redirect                         |

### Routes définies dans UsersHub

Les routes utilisées dans le `UsersHub-authentification-module` proviennent du module `UsersHub`. Les routes sont les suivantes :

| Route URI                   | Action                                                                                                           | Paramètres                               | Retourne                                   |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------- | ---------------------------------------- | ------------------------------------------ |
| `/create_tmp_user`          | Création d'un utilisateur temporaire en base                                                                     | {données sur l'utilisateur}              | {token}                                    |
| `/valid_temp_user`          | Création utilisateur en base dans la table t_role et ajout d'un profil avec code 1 pour une l’application donnée | {token, application_id}                  | {role}                                     |
| `/create_cor_role_token`    | Génère un token pour utilisateur ayant l’email indiqué et stoque le token dans cor_role_token                    | {email}                                  | {role}                                     |
| `/change_password`          | Mise à jour du mot de passe de l’utilisateur et suppression du token en base                                     | {token, password, password_confirmation} | {role}                                     |
| `/change_application_right` | Modifie le profil de l’utilisateur pour l’application                                                            | {id_application, id_profil, id_role}     | {id_role, id_profil, id_application, role} |
| `/update_user`              | Mise à jour d'un rôle                                                                                            | {id_role, données utilisateur}           | {role}                                     |

### Méthodes définies dans le module

- `connect_admin()` : décorateur pour la connexion d’un utilisateur type admin a une appli ici usershub. Paramètres à renseigner dans config.py
- `post_usershub()` :
  - route générique pour appeler les route usershub en tant qu'administrateur de l'appli en cours

### Configuration

Paramètres à rajouter dans le fichier de configuration (`config.py`)

Les paramètre concernant la gestion du cookie sont gérés par flask-admin : https://flask-login.readthedocs.io/en/latest/#cookie-settings

`REDIRECT_ON_FORBIDDEN` : paramètre de redirection utilisé par le décorateur `check_auth` lorsque les droits d'accès à une ressource/page sont insuffisants (par défaut lève une erreur 403)

### Changement du prefix d'accès aux routes de UsersHub-authentification-modules

Par défaut, les routes sont acesibles depuis le prefix `/auth/`. Si vous voulez changez cela, il suffit de modifier le paramètre `prefix` de l'appel de la méthode `AuthManager.init_app()`:

```python
auth_manager.init_app(app, prefix="/authentification", providers_declaration=providers_config)
```

### Configuration des actions post request

Rajouter le paramètre `after_USERSHUB_request` à la configuration. Ce paramètre est un tableau qui définit, pour chaque action, un ensemble d'opérations à réaliser ensuite. Comme par exemple envoyer un email.

```
function_dict = {
    'create_cor_role_token': create_cor_role_token,
    'create_temp_user': create_temp_user,
    'valid_temp_user': valid_temp_user,
    'change_application_right': change_application_right
}
```

Chaque fonction prend un paramètre en argument qui correspond aux données retournées par la route de UsersHub.

## Connexion à l'aide de fournisseurs d'identités extérieurs
