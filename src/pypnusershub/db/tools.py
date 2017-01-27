# coding: utf8

from __future__ import (unicode_literals, print_function,
                        absolute_import, division)
"""
    DB tools not related to any model in particular.
"""

from sqlalchemy import create_engine

from pypnusershub.utils import text_resource_stream


def init_schema(con_uri):

    with text_resource_stream('schema.sql', 'pypnusershub.db') as sql_file:
        sql = sql_file.read()

    engine = create_engine(con_uri)
    with engine.connect():
        engine.execute(sql)
        engine.execute("COMMIT")


def delete_schema(con_uri):

    engine = create_engine(con_uri)
    with engine.connect():
        engine.execute("DROP SCHEMA IF EXISTS utilisateurs CASCADE")
        engine.execute("COMMIT")


def reset_schema(con_uri):
    delete_schema(con_uri)
    init_schema(con_uri)


def load_fixtures(con_uri):
    with text_resource_stream('fixtures.sql', 'pypnusershub.db') as sql_file:

        engine = create_engine(con_uri)
        with engine.connect():
            for line in sql_file:
                if line.strip():
                    engine.execute(line)
            engine.execute("COMMIT")
