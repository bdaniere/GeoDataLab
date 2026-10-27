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
import os
import tempfile
import zipfile
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

import geopandas as gpd
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw_data"

TARGET_CRS = 2154  # Lambert-93
VECTOR_EXTENSIONS = (".shp", ".geojson", ".json", ".gpkg")


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
    content_types = (
        "application/geo+json",
        "application/vnd.geo+json",
        "application/json",
    )

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


class ShapefileFormat(ZipFormat):
    """A ZIP archive containing one or more complete Shapefiles."""

    name = "shapefile"

    @classmethod
    def matches(cls, filename: str, content_type: str, content: bytes) -> bool:
        if not super().matches(filename, content_type, content):
            return False
        if not zipfile.is_zipfile(BytesIO(content)):
            return False
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                return any(
                    not name.endswith("/")
                    and PurePosixPath(name).suffix.lower() == ".shp"
                    for name in archive.namelist()
                )
        except zipfile.BadZipFile:
            return False

    def validate(self, content: bytes) -> None:
        super().validate(content)
        with zipfile.ZipFile(BytesIO(content)) as archive:
            files: dict[tuple[str, str], set[str]] = {}
            shapefiles = []
            for name in archive.namelist():
                path = PurePosixPath(name)
                if name.endswith("/") or not path.suffix:
                    continue
                key = (str(path.parent).casefold(), path.stem.casefold())
                files.setdefault(key, set()).add(path.suffix.lower())
                if path.suffix.lower() == ".shp":
                    shapefiles.append((name, key))

        for name, key in shapefiles:
            missing = {".shx", ".dbf"} - files[key]
            if missing:
                raise FetchError(
                    f"Shapefile incomplet '{name}' : fichiers manquants "
                    f"{', '.join(sorted(missing))}"
                )


# Ajouter ici les nouveaux formats (ex: GeoPackage, CSV, ...).
FORMATS: list = [ShapefileFormat, ZipFormat, GeoJSONFormat]


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

    def to_geodataframes(
        self, target_crs: int = TARGET_CRS, source_crs: int | None = None
    ) -> dict[str, gpd.GeoDataFrame]:
        """Read the data as GeoDataFrames reprojected to target_crs (default 2154).

        Returns one GeoDataFrame per layer, keyed by file stem. `source_crs` is only
        used for layers that have no CRS defined.
        """
        if not self.is_zip:
            layers = {Path(self.filename).stem: gpd.read_file(BytesIO(self.content))}
        else:
            layers = {}
            with tempfile.TemporaryDirectory() as tmp:
                for path in self.extract(tmp):
                    if path.suffix.lower() in VECTOR_EXTENSIONS:
                        layers[path.stem] = gpd.read_file(path)
            if not layers:
                raise FetchError("No readable vector file found in the archive")

        for name, gdf in layers.items():
            if gdf.crs is None:
                if source_crs is None:
                    raise FetchError(f"Layer '{name}' has no CRS, provide source_crs")
                gdf = gdf.set_crs(source_crs)
            layers[name] = gdf.to_crs(target_crs)
        return layers

    def to_postgis(
        self,
        table: str,
        schema: str = "public",
        connection_string: str | None = None,
        if_exists: str = "replace",
        target_crs: int = TARGET_CRS,
        source_crs: int | None = None,
    ) -> list[str]:
        """Send the data to PostGIS, reprojected to target_crs (default Lambert-93).

        Defaults to the docker-compose instance (POSTGRES_* environment variables).
        A ZIP with several layers produces one table per layer: <table>_<layer>.
        Returns the created table names.
        """
        layers = self.to_geodataframes(target_crs, source_crs)
        engine = create_engine(connection_string or default_connection_string())
        names = []
        try:
            with engine.begin() as conn:
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
                for layer, gdf in layers.items():
                    name = table if len(layers) == 1 else f"{table}_{layer}"
                    gdf.to_postgis(name, conn, schema=schema, if_exists=if_exists)
                    names.append(name)
                    logger.info("%d rows sent to %s.%s", len(gdf), schema, name)
        finally:
            engine.dispose()
        return names


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
            resp = requests.get(self.url, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            content = resp.content
            content_type = (
                resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
            )
        except requests.RequestException as exc:
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

    url_parcelles_69 = "https://cadastre.data.gouv.fr/bundler/cadastre-etalab/departements/69/geojson/parcelles"
    url_batiments_69 = "https://cadastre.data.gouv.fr/bundler/cadastre-etalab/departements/69/geojson/batiments"
    url_iris_france = "https://data.geopf.fr/telechargement/download/CONTOURS-IRIS/CONTOURS-IRIS_3-0__SHP_LAMB93_FXX_2024-01-01/CONTOURS-IRIS_3-0__SHP_LAMB93_FXX_2024-01-01.7z"

    # GeoDataFetcher(sys.argv[1]).fetch().export()
    geodata_fetecher = (
        GeoDataFetcher(url_iris_france)
        .fetch()
        .to_postgis(table="iris_france", schema="raw_data")
    )
