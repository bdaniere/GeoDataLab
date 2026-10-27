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
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import unquote, urlparse

import geopandas as gpd
import py7zr
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


class SevenZipFormat(DataFormat):
    name = "7z"
    extensions = (".7z",)
    content_types = ("application/x-7z-compressed",)

    @classmethod
    def matches(cls, filename: str, content_type: str, content: bytes) -> bool:
        return super().matches(filename, content_type, content) or content.startswith(
            b"7z\xbc\xaf'\x1c"
        )

    def validate(self, content: bytes) -> None:
        try:
            with py7zr.SevenZipFile(BytesIO(content), mode="r") as archive:
                if archive.needs_password():
                    raise FetchError(
                        "Les archives 7z protégées par mot de passe ne sont pas prises en charge"
                    )
                archive.getnames()
        except (py7zr.Bad7zFile, EOFError, OSError, ValueError) as exc:
            raise FetchError(f"Archive 7z invalide : {exc}") from exc


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
FORMATS: list = [ShapefileFormat, SevenZipFormat, ZipFormat, GeoJSONFormat]


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

    @property
    def is_7z(self) -> bool:
        return isinstance(self.format, SevenZipFormat)

    @property
    def is_archive(self) -> bool:
        return self.is_zip or self.is_7z

    def _zip(self) -> zipfile.ZipFile:
        if not self.is_zip:
            raise FetchError("The dataset is not a ZIP archive")
        return zipfile.ZipFile(BytesIO(self.content))

    def _seven_zip(self) -> py7zr.SevenZipFile:
        if not self.is_7z:
            raise FetchError("The dataset is not a 7z archive")
        return py7zr.SevenZipFile(BytesIO(self.content), mode="r")

    @staticmethod
    def _safe_member_path(name: str, root: Path) -> Path:
        normalized = name.replace("\\", "/")
        member = PurePosixPath(normalized)
        if (
            member.is_absolute()
            or PureWindowsPath(normalized).is_absolute()
            or PureWindowsPath(normalized).drive
            or ".." in member.parts
        ):
            raise FetchError(f"Unsafe path in archive: {name}")
        dest = (root / Path(*member.parts)).resolve()
        if not dest.is_relative_to(root):
            raise FetchError(f"Unsafe path in archive: {name}")
        return dest

    def list_members(self) -> list[str]:
        """List the files contained in the archive (directories excluded)."""
        if self.is_7z:
            with self._seven_zip() as archive:
                return [
                    name
                    for name in archive.getnames()
                    if not archive.getinfo(name).is_directory
                ]
        with self._zip() as archive:
            return [i.filename for i in archive.infolist() if not i.is_dir()]

    def read_member(self, name: str) -> bytes:
        """Read a file from the archive in memory."""
        if self.is_7z:
            if name not in self.list_members():
                raise FetchError(f"{name} not found in archive")
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                member_path = self._safe_member_path(name, root)
                normalized = name.replace("\\", "/")
                parts = PurePosixPath(normalized).parts
                targets = ["/".join(parts[:i]) for i in range(1, len(parts))]
                targets.append(name)
                with self._seven_zip() as archive:
                    archive.extract(path=root, targets=targets)
                if not member_path.is_file():
                    raise FetchError(f"{name} is not a readable file in the archive")
                return member_path.read_bytes()

        with self._zip() as zf:
            try:
                return zf.read(name)
            except KeyError as exc:
                raise FetchError(f"{name} not found in archive") from exc

    def extract(self, output_dir: Path | str | None = None) -> list[Path]:
        """Extract the archive (default: data/raw_data/<archive name>/).

        Returns the extracted file paths.
        """
        target = Path(output_dir or DEFAULT_OUTPUT_DIR / Path(self.filename).stem)
        target.mkdir(parents=True, exist_ok=True)
        root = target.resolve()
        extracted = []
        if self.is_7z:
            with self._seven_zip() as archive:
                members = archive.getnames()
                for name in members:
                    self._safe_member_path(name, root)
                    if archive.getinfo(name).is_symlink:
                        raise FetchError(f"Symbolic links are not supported: {name}")
                archive.extractall(path=root)
                extracted = [
                    self._safe_member_path(name, root)
                    for name in members
                    if not archive.getinfo(name).is_directory
                ]
            logger.info("Extracted %d file(s) to %s", len(extracted), target)
            return extracted

        with self._zip() as zf:
            for info in zf.infolist():
                dest = self._safe_member_path(info.filename, root)
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
        if not self.is_archive:
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
        An archive with several layers produces one table per layer: <table>_<layer>.
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
    # url_iris_france = "https://data.geopf.fr/telechargement/download/CONTOURS-IRIS/CONTOURS-IRIS_3-0__SHP_LAMB93_FXX_2024-01-01/CONTOURS-IRIS_3-0__SHP_LAMB93_FXX_2024-01-01.7z"
    url_communes_france = "https://contours-administratifs.s3.rbx.io.cloud.ovh.net/2026/geojson/communes-5m.geojson"

    # GeoDataFetcher(sys.argv[1]).fetch().export()
    geodata_fetecher = (
        GeoDataFetcher(url_communes_france)
        .fetch()
        .to_postgis(table="communes_france", schema="raw_data")
    )
