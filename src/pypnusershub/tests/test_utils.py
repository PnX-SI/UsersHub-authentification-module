import pytest

from pypnusershub.utils import get_cookie_path


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
