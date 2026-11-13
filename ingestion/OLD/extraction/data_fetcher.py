"""Récupération de données non-géographiques (CSV, ZIP de CSV) depuis une URL.

Exemple :
    dataset = DataFetcher("https://example.com/data.zip").fetch()
    dataset.to_postgres(table="mydata", schema="raw_data")
"""

from __future__ import annotations

import csv
import logging
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath

import pandas as pd
from sqlalchemy import create_engine, text
from util import (
    FetchError,
    default_connection_string,
    download,
    guess_filename,
    validate_url,
)

logger = logging.getLogger(__name__)

ENCODINGS = ("utf-8-sig", "cp1252")


def _is_csv(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    return (
        path.suffix.lower() == ".csv"
        and not name.endswith("/")
        and "__MACOSX" not in path.parts
        and not path.name.startswith(".")
    )


def _sanitize(name: str) -> str:
    """Lower-case ASCII identifier usable as a PostgreSQL table/column name."""
    ascii_name = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore")
    cleaned = re.sub(r"\W+", "_", ascii_name.decode().lower()).strip("_")
    return cleaned or "col"


def read_csv(content: bytes) -> pd.DataFrame:
    """Read CSV bytes, guessing the separator and trying common encodings."""
    last_error: Exception | None = None
    for encoding in ENCODINGS:
        try:
            return pd.read_csv(
                BytesIO(content), sep=None, engine="python", encoding=encoding
            )
        except UnicodeDecodeError as exc:
            last_error = exc
        except csv.Error as exc:
            raise FetchError(f"Invalid CSV : {exc}") from exc
        except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
            raise FetchError(f"Invalid CSV : {exc}") from exc
    raise FetchError(f"Unable to decode CSV : {last_error}")


@dataclass
class DataSet:
    """Raw downloaded tabular data (CSV or ZIP of CSV)."""

    url: str
    filename: str
    content: bytes

    @property
    def is_zip(self) -> bool:
        return zipfile.is_zipfile(BytesIO(self.content))

    def to_dataframes(self) -> dict[str, pd.DataFrame]:
        """One DataFrame per CSV, keyed by file stem (a ZIP may contain several)."""
        if not self.is_zip:
            return {PurePosixPath(self.filename).stem: read_csv(self.content)}

        frames: dict[str, pd.DataFrame] = {}
        with zipfile.ZipFile(BytesIO(self.content)) as archive:
            for name in archive.namelist():
                if not _is_csv(name):
                    continue
                stem = PurePosixPath(name.replace("\\", "/")).stem
                if stem in frames:
                    raise FetchError(f"Duplicate CSV name in archive: {stem}")
                frames[stem] = read_csv(archive.read(name))
        if not frames:
            raise FetchError("No CSV file found in the archive")
        return frames

    def to_postgres(
        self,
        table: str,
        schema: str = "public",
        connection_string: str | None = None,
        if_exists: str = "replace",
    ) -> list[str]:
        """Send each CSV to PostgreSQL (docker-compose instance by default).

        A single CSV goes to <table>; each CSV of a ZIP goes to <table>_<csv name>.
        Returns the created table names.
        """
        frames = self.to_dataframes()
        engine = create_engine(connection_string or default_connection_string())
        names = []
        try:
            with engine.begin() as conn:
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
                for stem, df in frames.items():
                    name = table if len(frames) == 1 else f"{table}_{_sanitize(stem)}"
                    df = df.rename(columns=_sanitize)
                    if not df.columns.is_unique:
                        raise FetchError(
                            f"CSV '{stem}' has duplicate column names after cleaning"
                        )
                    df.to_sql(
                        name,
                        conn,
                        schema=schema,
                        if_exists="replace",
                        index=False,
                        chunksize=10_000,
                    )
                    names.append(name)
                    logger.info("%d rows sent to %s.%s", len(df), schema, name)
        finally:
            engine.dispose()
        return names


class DataFetcher:
    """Download non-geographic data (CSV or ZIP of CSV) from a URL."""

    def __init__(self, url: str, timeout: int = 60, headers: dict | None = None):
        validate_url(url)
        self.url = url
        self.timeout = timeout
        self.headers = headers

    def fetch(self) -> DataSet:
        content, content_type = download(self.url, self.timeout, self.headers)
        filename = guess_filename(self.url)
        dataset = DataSet(self.url, filename, content)
        if not dataset.is_zip and not (
            filename.lower().endswith(".csv") or "csv" in content_type
        ):
            raise FetchError(f"Unsupported format ({filename}, {content_type})")
        return dataset
