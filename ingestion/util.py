"""Helpers shared by the ingestion scripts (geo_data_fetcher, data_fetcher)."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw_data"
USER_AGENT = "GeoDataLab/0.1"


class FetchError(Exception):
    "Error while downloading or reading the data"


def default_connection_string() -> str:
    """Connection string of the docker-compose PostGIS (POSTGRES_* env variables)."""

    current_dir = Path(__file__).resolve().parent
    dotenv_path = current_dir / ".." / "docker" / ".env"

    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)
    else:
        logger.warning(".env file not found : %s", dotenv_path)

    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGIS_PORT", "5432")
    db = os.environ["POSTGRES_DB"]

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def validate_url(url: str) -> None:
    if urlparse(url).scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL (http/https expected) : {url}")


def guess_filename(url: str) -> str:
    name = Path(unquote(urlparse(url).path)).name
    return name or "download"


def download(
    url: str, timeout: int = 60, headers: dict | None = None
) -> tuple[bytes, str]:
    """Download a URL; return (content, lower-cased content type without params)."""
    logger.info("Downloading: %s", url)
    try:
        resp = requests.get(
            url, headers={"User-Agent": USER_AGENT, **(headers or {})}, timeout=timeout
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise FetchError(f"Failed to download {url} : {exc}") from exc
    content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
    return resp.content, content_type
