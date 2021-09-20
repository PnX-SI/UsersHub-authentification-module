Installation du schéma `utilisateurs` avec alembic
--------------------------------------------------

1. Créer un virtualenv (nécessite le paquet ``python3-venv``) :

.. code-block::

    $ python3 -m venv venv


2. Entrer dans le virtualenv :

.. code-block::

    $ source venv/bin/activate

3. Installer alembic et le module UsersHub-authentication-module :

.. code-block::

    $ pip install alembic -e .

4. Éditer le ficher ``alembic.ini`` et définir correctement la variable ``sqlalchemy.url``.

5. Lancer la création du schéma `utilisateurs` avec alembic :

.. code-block::

    $ alembic upgrade utilisateurs@head

6. (Optionnel) Installer les données d’exemples :

.. code-block::

    $ alembic upgrade utilisateurs-samples@head
