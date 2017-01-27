# UsersHub-authentification-module

Module Flask (Python) permettant de gérer l'authentification suivant le modèle de [UsersHub](https://github.com/PnEcrins/UsersHub/).

Prévu pour être utilisé comme un submodule git


## Routes :

* login :
  * parametres : login, password, id_application
  * return : token


## Fonction de décoration :
* check_auth
  * parametres : level = niveau de droit
  * utilise le token passé en cookie de la requête

## Exemple d'usage

```
  #Import de la librairie
  fnauth = importlib.import_module("apptax.UsersHub-authentification-module.routes")

  #Ajout d'un test d'authentification avec niveau de droit
  @adresses.route('/', methods=['POST', 'PUT'])
  @fnauth.check_auth(4)
  def insertUpdate_bibtaxons(id_taxon=None):
    ...
```

## Installation:

Cloner le repository, puis dans le dossier :

```
python setup.py install
```

Le driver postgres Python, "psycopg2", peut avoir besoin d'être compilé. Si
à l'installation vous obtenez un message d'erreur décrivant un fichier de
header manquant (xxxx.h), comme par exemple:


```
fatal error: Python.h: Aucun fichier ou dossier de ce type
```

Alors il faudra installer au préalable les headers de votre version de Python,
votre version de postgres et un compilateur.

Par exemple, sur Ubuntu avec Python 3.5 et postgresql 9.5:

```
sudo apt install python3.5-dev build-essential postgresql-server-dev-9.5
```

Il faut ensuite configurere la base de données en étant administrateur.

La manière la plus courante pour se connecter à la base de données en ayant les droits admin est de se logger en tant qu'utilisateur 'postgres'. Par exemple sous Ubuntu:

```
sudo su postgres
```

Assurez-vous d'avoir au moins créé une base de données. Par exemple sous Ubuntu:


```
createdb ma_db
```

Il faut ensuite créer un utilisateur. Par exemple:

```
createuser -P parcnational
```

Puis donner les droits à cet utilisateur sur la base de données:

```
$ psql
postgres=# GRANT ALL PRIVILEGES ON DATABASE ma_db TO parcnational;
```

SQLAlchemy vous permettra de vous connecter à la base de données avec une URL
de type:

```
postgresql://nom_utilisateur:mot_de_passe@host:port/db_name
```

Par exemple:

```
postgresql://parcnational:secret@127.0.0.1:5432/ma_db
```

Il vous faudra créer un schema nommé 'utilisteurs' qui contient toutes les tables nécessaires. Ce module contient le sql pour le faire dans le fichier db/schema.sql. Néanmoins une commande vous permet de le faire automatiquement:

```
python -m pypnusershub init_schema url_de_la_db
```

Ex:

```
python -m pypnusershub init_schema postgresql://parcnational:secret@127.0.0.1:5432/ma_db
```

`python -m pypnusershub` permet aussi de supprimer le schema (`delete_schema`), remettre à zéro (`reset_schema`) et charger des données de test (`load_fixtures`). Pour plus d'informations:

```
python -m pypnusershub --help
```

Please note that you can only load the fixtures once, as they have UNIQUE constraints.
