from unittest.mock import Mock

import pytest
import requests
import util
from util import FetchError


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com/data.csv?download=1", "data.csv"),
        ("https://example.com/territoires%20fr.csv", "territoires fr.csv"),
        ("https://example.com/", "download"),
    ],
)
def test_guess_filename(url, expected):
    assert util.guess_filename(url) == expected


@pytest.mark.parametrize("url", ["ftp://example.com/data.csv", "file:///tmp/data.csv"])
def test_validate_url_rejects_non_http_schemes(url):
    with pytest.raises(ValueError, match="http/https expected"):
        util.validate_url(url)


@pytest.mark.parametrize("url", ["http://example.com/data.csv", "https://example.com"])
def test_validate_url_accepts_http_schemes(url):
    util.validate_url(url)


def test_download_returns_bytes_and_normalized_content_type(monkeypatch):
    response = Mock()
    response.headers = {"Content-Type": "TEXT/CSV; charset=utf-8"}
    response.content = b"value\n1\n"
    monkeypatch.setattr(util.requests, "get", Mock(return_value=response))

    content, content_type = util.download("https://example.com/data.csv")

    assert content == b"value\n1\n"
    assert content_type == "text/csv"
    response.raise_for_status.assert_called_once_with()


def test_download_wraps_request_errors(monkeypatch):
    monkeypatch.setattr(
        util.requests,
        "get",
        Mock(side_effect=requests.Timeout("connection timed out")),
    )

    with pytest.raises(FetchError, match="Failed to download"):
        util.download("https://example.com/data.csv")


def test_default_connection_string_reads_environment(monkeypatch):
    monkeypatch.setattr(util.Path, "resolve", lambda path: path)
    monkeypatch.setattr(util.Path, "exists", lambda path: False)
    monkeypatch.setenv("POSTGRES_USER", "geo_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "geo_password")
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGIS_PORT", "5544")
    monkeypatch.setenv("POSTGRES_DB", "geo")

    assert util.default_connection_string() == (
        "postgresql+psycopg2://geo_user:geo_password@db:5544/geo"
    )
