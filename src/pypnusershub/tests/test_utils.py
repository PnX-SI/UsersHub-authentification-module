import datetime

import pytest
from flask import Response
from werkzeug.http import parse_cookie

from pypnusershub.utils import get_cookie_path, set_cookie, delete_cookie


class TestUtils:
    @pytest.mark.parametrize(
        "url,expected_cookie_path",
        [
            ("https://domain.com/geonature", "/geonature"),
            ("https://domain.com/", "/"),
            (None, "/"),
        ],
    )
    def test_get_cookie_path(self, url, expected_cookie_path):
        cookie_path = get_cookie_path(application_url=url)

        assert cookie_path == expected_cookie_path

    def test_set_cookie(self):
        application_url = "https://domain.com/geonature"
        response = Response("{test: 'test'}")
        key, value = "key", "value"
        cookie_exp = datetime.datetime.utcnow() + datetime.timedelta(days=1)
        response = set_cookie(
            response=response,
            application_url=application_url,
            key=key,
            value=value,
            expires=cookie_exp,
        )

        cookie = response.headers.getlist("Set-Cookie")[0]
        cookie_attrs = parse_cookie(cookie)
        assert cookie_attrs[key] == value
        assert cookie_attrs["Path"] == "/geonature"
        assert cookie_attrs["Expires"] != ""

        logout_response = delete_cookie(
            response, key=key, application_url=application_url
        )
        cookie = logout_response.headers.getlist("Set-Cookie")[1]
        cookie_attrs = parse_cookie(cookie)

        assert cookie_attrs[key] == ""
        assert cookie_attrs["Path"] == "/geonature"
        assert True
