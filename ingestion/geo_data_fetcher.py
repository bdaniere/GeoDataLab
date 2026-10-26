"""Récupération de données géographiques depuis une URL (Zip, GeoJSON, ...).

Exemple :
    fetcher = GeoDataFetcher("https://example.com/communes.geojson")
    dataset = fetcher.fetch()
    dataset.export()  # -> data/raw_data/communes.geojson
"""

from __future__ import annotations

import json
import logging
import mimetypes
import zipfile
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw_data"

Check = Callable[["GeoDataset"], list]


class FetchError(Exception):
    "Error while downloading or reading the data"


# ███████╗ ██████╗ ██████╗ ███╗   ███╗ █████╗ ████████╗
# ██╔════╝██╔═══██╗██╔══██╗████╗ ████║██╔══██╗╚══██╔══╝
# █████╗  ██║   ██║██████╔╝██╔████╔██║███████║   ██║
# ██╔══╝  ██║   ██║██╔══██╗██║╚██╔╝██║██╔══██║   ██║
# ██║     ╚██████╔╝██║  ██║██║ ╚═╝ ██║██║  ██║   ██║
# ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝


class DataFormat(ABC):
    """
    A data format: detection and validation.
    To be extended to other formats.
    """

    name: str = ""
    extensions: tuple = ()
    content_types: tuple = ()

    @classmethod
    def matches(cls, filename: str, content_type: str, content: bytes) -> bool:
        filename = filename.lower()
        if any(filename.endswith(ext) for ext in cls.extensions):
            return True
        return content_type in cls.content_types

    @abstractmethod
    def validate(self, content: bytes) -> None:
        """Raise FetchError if the content is invalid."""


class GeoJSONFormat(DataFormat):
    name = "geojson"
    extensions = (".geojson", ".json")
    content_types = ("application/geo+json", "application/json")

    def validate(self, content: bytes) -> None:
        try:
            data = json.loads(content)
        except ValueError as exc:
            raise FetchError(f"GeoJSON invalide : {exc}") from exc
        if not isinstance(data, dict) or "type" not in data:
            raise FetchError("GeoJSON invalide : clé 'type' manquante")


class ZipFormat(DataFormat):
    name = "zip"
    extensions = (".zip",)
    content_types = ("application/zip", "application/x-zip-compressed")

    @classmethod
    def matches(cls, filename, content_type, content):
        return (
            super().matches(filename, content_type, content)
            or content[:4] == b"PK\x03\x04"
        )

    def validate(self, content: bytes) -> None:
        if not zipfile.is_zipfile(BytesIO(content)):
            raise FetchError("Archive ZIP invalide")


# Ajouter ici les nouveaux formats (ex: GeoPackage, CSV, ...).
FORMATS: list = [ZipFormat, GeoJSONFormat]


# ██████╗  █████╗ ████████╗ █████╗ ███████╗███████╗████████╗███████╗
# ██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔════╝
# ██║  ██║███████║   ██║   ███████║███████╗█████╗     ██║   ███████╗
# ██║  ██║██╔══██║   ██║   ██╔══██║╚════██║██╔══╝     ██║   ╚════██║
# ██████╔╝██║  ██║   ██║   ██║  ██║███████║███████╗   ██║   ███████║
# ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚══════╝   ╚═╝   ╚══════╝


@dataclass
class GeoDataset:
    """Raw downloaded data, with its metadata."""

    url: str
    filename: str
    content: bytes
    format: DataFormat
    checks_errors: list = field(default_factory=list)

    def export(self, output_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Path:
        """Write the raw data locally (default in data/raw_data)."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / self.filename
        path.write_bytes(self.content)
        logger.info("Exported data : %s", path)
        return path

    @property
    def is_zip(self) -> bool:
        return isinstance(self.format, ZipFormat)

    def _zip(self) -> zipfile.ZipFile:
        if not self.is_zip:
            raise FetchError("The dataset is not a ZIP archive")
        return zipfile.ZipFile(BytesIO(self.content))

    def list_members(self) -> list[str]:
        """List the files contained in the ZIP archive (directories excluded)."""
        with self._zip() as zf:
            return [i.filename for i in zf.infolist() if not i.is_dir()]

    def read_member(self, name: str) -> bytes:
        """Read a file of the ZIP archive in memory."""
        with self._zip() as zf:
            try:
                return zf.read(name)
            except KeyError as exc:
                raise FetchError(f"{name} not found in archive") from exc

    def extract(self, output_dir: Path | str | None = None) -> list[Path]:
        """Extract the ZIP archive (default: data/raw_data/<archive name>/).

        Returns the extracted file paths.
        """
        target = Path(output_dir or DEFAULT_OUTPUT_DIR / Path(self.filename).stem)
        target.mkdir(parents=True, exist_ok=True)
        root = target.resolve()
        extracted = []
        with self._zip() as zf:
            for info in zf.infolist():
                dest = (root / info.filename).resolve()
                if not dest.is_relative_to(root):
                    raise FetchError(f"Unsafe path in archive: {info.filename}")
                if info.is_dir():
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(info))
                extracted.append(dest)
        logger.info("Extracted %d file(s) to %s", len(extracted), target)
        return extracted

    def run_checks(self, checks: list) -> bool:
        """Run a series of checks; return True if none fail."""
        self.checks_errors = []
        for check in checks:
            self.checks_errors.extend(check(self))
        return not self.checks_errors

    def to_postgis(
        self, connection_string: str, table: str, schema: str = "public"
    ) -> None:
        """Send to PostGIS (to be implemented)."""
        raise NotImplementedError("PostGIS export not implemented")


# ███████╗██╗██╗     ███████╗███████╗
# ██╔════╝██║██║     ██╔════╝██╔════╝
# █████╗  ██║██║     █████╗  ███████╗
# ██╔══╝  ██║██║     ██╔══╝  ╚════██║
# ██║     ██║███████╗███████╗███████║
# ╚═╝     ╚═╝╚══════╝╚══════╝╚══════╝


class GeoDataFetcher:
    """Download geographic data from a URL."""

    def __init__(self, url: str, timeout: int = 60, headers: dict | None = None):
        if urlparse(url).scheme not in ("http", "https"):
            raise ValueError(f"Invalid URL (http/https expected) : {url}")
        self.url = url
        self.timeout = timeout
        self.headers = {"User-Agent": "GeoDataLab/0.1", **(headers or {})}

    def fetch(self) -> GeoDataset:
        """Download, detect the format, and validate the content."""
        logger.info("Downloading: %s", self.url)
        try:
            with urlopen(
                Request(self.url, headers=self.headers), timeout=self.timeout
            ) as resp:
                content = resp.read()
                content_type = resp.headers.get_content_type()
        except OSError as exc:
            raise FetchError(f"Failed to download {self.url} : {exc}") from exc

        filename = self._guess_filename()
        fmt = self._detect_format(filename, content_type, content)
        fmt.validate(content)

        if not Path(filename).suffix:
            filename += mimetypes.guess_extension(content_type) or f".{fmt.name}"
        return GeoDataset(self.url, filename, content, fmt)

    def _guess_filename(self) -> str:
        name = Path(unquote(urlparse(self.url).path)).name
        return name or "download"

    @staticmethod
    def _detect_format(filename: str, content_type: str, content: bytes) -> DataFormat:
        for fmt_cls in FORMATS:
            if fmt_cls.matches(filename, content_type, content):
                return fmt_cls()
        raise FetchError(f"Unsupported format ({filename}, {content_type})")


# ███╗   ███╗ █████╗ ██╗███╗   ██╗
# ████╗ ████║██╔══██╗██║████╗  ██║
# ██╔████╔██║███████║██║██╔██╗ ██║
# ██║╚██╔╝██║██╔══██║██║██║╚██╗██║
# ██║ ╚═╝ ██║██║  ██║██║██║ ╚████║
# ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # if len(sys.argv) != 2:
    #     sys.exit("Usage : python geo_data_fetcher.py <url>")

    url_test = "https://cadastre.data.gouv.fr/bundler/cadastre-etalab/departements/69/geojson/parcelles"
    # GeoDataFetcher(sys.argv[1]).fetch().export()
    geodata_fetecher = GeoDataFetcher(url_test).fetch().export()
