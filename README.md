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
