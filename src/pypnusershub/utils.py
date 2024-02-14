# coding: utf8

from __future__ import unicode_literals, print_function, absolute_import, division

"""
    Collections of utilities unrelated to the main module purpose.
"""

import os
import io
from types import ModuleType
from typing import Optional
from urllib.parse import urlsplit

from flask import current_app, Response
from sqlalchemy import select

from pypnusershub.env import db


class RessourceError(EnvironmentError):
    def __init__(self, msg, errors):
        super(RessourceError, self).__init__(msg)
        self.errors = errors


def binary_resource_stream(resource, locations):
    """Return a resource from this path or package"""

    # convert
    errors = []

    # If location is a string or a module, we wrap it in a tuple
    if isinstance(locations, (str, ModuleType)):
        locations = (locations,)

    for location in locations:
        # Assume location is a module and try to load it using pkg_resource
        try:
            import pkg_resources

            module_name = getattr(location, "__name__", location)
            return pkg_resources.resource_stream(module_name, resource)
        except (ImportError, EnvironmentError) as e:
            errors.append(e)

            # Falling back to load it from path.
            try:
                # location is a module
                module_path = __import__(location).__file__
                parent_dir = os.path_dirname(module_path)
            except (AttributeError, ImportError):
                # location is a dir path
                parent_dir = os.path.realpath(location)

            # Now we got a resource full path. Just open it as a regular file.
            canonical_path = os.path.join(parent_dir, resource)
            try:
                return open(os.path.join(canonical_path), mode="rb")
            except EnvironmentError as e:
                errors.append(e)

    msg = (
        'Unable to find resource "%s" in "%s". '
        "Inspect RessourceError.errors for list of encountered errors."
    )
    raise RessourceError(msg % (resource, locations), errors)


def text_resource_stream(
    path, locations, encoding="utf8", errors=None, newline=None, line_buffering=False
):
    """Return a resource from this path or package. Transparently decode the stream."""
    stream = binary_resource_stream(path, locations)
    return io.TextIOWrapper(stream, encoding, errors, newline, line_buffering)


def get_current_app_id():
    if "ID_APP" in current_app.config:
        return current_app.config["ID_APP"]
    elif "CODE_APPLICATION" in current_app.config:
        from pypnusershub.db.models import Application

        return db.session.execute(
            select(Application.id_application).filter_by(
                code_application=current_app.config["CODE_APPLICATION"],
            )
        ).scalar_one()
    else:
        return None


def get_cookie_path(application_url: Optional[str] = None) -> str:
    """
    Returns the cookie path computed from the application_url
    """
    if application_url is None:
        return "/"
    split_url = urlsplit(application_url)
    return split_url.path if split_url.path else "/"


def delete_cookie(response: Response, application_url: Optional[str] = None, **kwargs):
    cookie_path = get_cookie_path(application_url=application_url)
    response.delete_cookie(**kwargs, path=cookie_path)
    return response


def set_cookie(response: Response, application_url: Optional[str] = None, **kwargs):
    """
    Set automatically a Path on a cookie.
    All kwargs are passed to Response.set_cookie()
    """
    cookie_path = get_cookie_path(application_url=application_url)
    response.set_cookie(**kwargs, path=cookie_path)
    return response
