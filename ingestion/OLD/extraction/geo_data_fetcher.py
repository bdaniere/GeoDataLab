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
import tempfile
import zipfile
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path, PurePosixPath, PureWindowsPath

import geopandas as gpd
import py7zr
import pyogrio
from sqlalchemy import create_engine, text
from util import (
    DEFAULT_OUTPUT_DIR,
    FetchError,
    default_connection_string,
    download,
    guess_filename,
    validate_url,
)

logger = logging.getLogger(__name__)


TARGET_CRS = 2154  # Lambert-93

Check = Callable[["GeoDataset"], list]


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
    geographic_extensions: tuple[str, ...] = ()

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
    geographic_extensions = extensions
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
        if not isinstance(data, dict):
            raise FetchError("GeoJSON invalide : un objet JSON est attendu")

        geojson_type = data.get("type")
        if geojson_type == "FeatureCollection":
            valid = isinstance(data.get("features"), list)
        elif geojson_type == "Feature":
            valid = (
                "geometry" in data
                and (data["geometry"] is None or isinstance(data["geometry"], dict))
                and "properties" in data
                and (data["properties"] is None or isinstance(data["properties"], dict))
            )
        elif geojson_type == "GeometryCollection":
            valid = isinstance(data.get("geometries"), list)
        else:
            valid = (
                geojson_type
                in {
                    "Point",
                    "MultiPoint",
                    "LineString",
                    "MultiLineString",
                    "Polygon",
                    "MultiPolygon",
                }
                and "coordinates" in data
            )

        if not valid:
            raise FetchError(
                f"GeoJSON invalide : type ou structure incorrecte ({geojson_type})"
            )


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


class GeoPackageFormat(DataFormat):
    name = "gpkg"
    extensions = (".gpkg",)
    geographic_extensions = extensions
    content_types = ("application/geopackage+sqlite3",)

    def validate(self, content: bytes) -> None:
        if not content.startswith(b"SQLite format 3\x00"):
            raise FetchError("Fichier GeoPackage invalide")


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
                        "Les archives 7z protégées par mot de passe ne sont pas "
                        "prises en charge"
                    )
                archive.getnames()
        except (py7zr.Bad7zFile, EOFError, OSError, ValueError) as exc:
            raise FetchError(f"Archive 7z invalide : {exc}") from exc


class ShapefileFormat(ZipFormat):
    """A ZIP archive containing one or more complete Shapefiles."""

    name = "shapefile"
    geographic_extensions = (".shp",)

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


FORMATS: list[type[DataFormat]] = [
    ShapefileFormat,
    SevenZipFormat,
    ZipFormat,
    GeoJSONFormat,
    GeoPackageFormat,
]
VECTOR_EXTENSIONS = tuple(
    dict.fromkeys(
        extension
        for format_type in FORMATS
        for extension in format_type.geographic_extensions
    )
)


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

    def export(self, output_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Path | list[Path]:
        """Export geographic data, extracting only supported files from archives.

        For archives, extracted files are written below a subdirectory named after the
        archive, and the returned paths identify the geographic data files.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if self.is_archive:
            data_members, archive_members = self._geographic_archive_members()
            if not data_members:
                raise FetchError("No supported geographic file found in the archive")
            return self._extract_selected_members(
                archive_members, data_members, output_dir / Path(self.filename).stem
            )
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

    def _geographic_archive_members(self) -> tuple[list[str], list[str]]:
        """Find geographic files and required Shapefile sidecars in an archive."""
        members = self.list_members()
        data_members = []
        for name in members:
            extension = PurePosixPath(name).suffix.lower()
            if extension not in VECTOR_EXTENSIONS:
                continue
            if extension in {".geojson", ".json"}:
                try:
                    GeoJSONFormat().validate(self.read_member(name))
                except FetchError:
                    if extension == ".json":
                        continue
                    raise
            elif extension == ".gpkg":
                GeoPackageFormat().validate(self.read_member(name))
            data_members.append(name)
        archive_members = set(data_members)
        shapefiles = [
            name
            for name in data_members
            if PurePosixPath(name).suffix.lower() == ".shp"
        ]
        files_by_stem: dict[tuple[str, str], set[str]] = {}
        members_by_stem: dict[tuple[str, str], list[str]] = {}
        for name in members:
            path = PurePosixPath(name)
            key = (str(path.parent).casefold(), path.stem.casefold())
            files_by_stem.setdefault(key, set()).add(path.suffix.lower())
            members_by_stem.setdefault(key, []).append(name)

        for name in shapefiles:
            path = PurePosixPath(name)
            key = (str(path.parent).casefold(), path.stem.casefold())
            missing = {".shx", ".dbf"} - files_by_stem[key]
            if missing:
                raise FetchError(
                    f"Shapefile incomplet '{name}' : fichiers manquants "
                    f"{', '.join(sorted(missing))}"
                )
            archive_members.update(
                member
                for member in members_by_stem[key]
                if PurePosixPath(member).suffix.lower()
                in {".shx", ".dbf", ".prj", ".cpg"}
            )
        return data_members, [name for name in members if name in archive_members]

    def _extract_selected_members(
        self, members: list[str], data_members: list[str], output_dir: Path
    ) -> list[Path]:
        """Extract only selected geographic files and their required sidecars."""
        output_dir.mkdir(parents=True, exist_ok=True)
        root = output_dir.resolve()
        destinations = {name: self._safe_member_path(name, root) for name in members}

        if self.is_7z:
            with self._seven_zip() as archive:
                targets = []
                for name in members:
                    info = archive.getinfo(name)
                    if info.is_symlink:
                        raise FetchError(f"Symbolic links are not supported: {name}")
                    parts = PurePosixPath(name).parts
                    targets.extend(
                        "/".join(parts[:index]) for index in range(1, len(parts))
                    )
                    targets.append(name)
                archive.extract(path=root, targets=list(dict.fromkeys(targets)))
        else:
            with self._zip() as archive:
                for name in members:
                    destination = destinations[name]
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(archive.read(name))

        extracted = [destinations[name] for name in data_members]
        logger.info("Exported %d geographic file(s) to %s", len(extracted), output_dir)
        return extracted

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

    @staticmethod
    def _read_file_layers(path: Path, stem: str, single_source: bool) -> dict:
        """Read every layer of a file (a GeoPackage can hold several)."""
        if path.suffix.lower() != ".gpkg":
            return {stem: gpd.read_file(path)}
        names = [str(name) for name in pyogrio.list_layers(path)[:, 0]]
        result = {}
        for layer in names:
            key = layer if single_source else f"{stem}_{layer}"
            result[key] = gpd.read_file(path, layer=layer)
        return result

    def _read_layers(self) -> tuple[dict, list[str]]:
        """Return all layers (with or without geometry) keyed by name."""
        layers: dict = {}
        with tempfile.TemporaryDirectory() as tmp:
            if not self.is_archive:
                if isinstance(self.format, GeoPackageFormat):
                    path = Path(tmp) / self.filename
                    path.write_bytes(self.content)
                    layers = self._read_file_layers(
                        path, Path(self.filename).stem, True
                    )
                else:
                    layers = {
                        Path(self.filename).stem: gpd.read_file(BytesIO(self.content))
                    }
            else:
                data_members, archive_members = self._geographic_archive_members()
                if not data_members:
                    raise FetchError(
                        "No supported geographic file found in the archive"
                    )
                paths = self._extract_selected_members(
                    archive_members, data_members, Path(tmp)
                )
                for path in paths:
                    layers.update(
                        self._read_file_layers(path, path.stem, len(paths) == 1)
                    )
        return layers, list(layers)

    def to_geodataframes(
        self, target_crs: int = TARGET_CRS, source_crs: int | None = None
    ) -> dict[str, gpd.GeoDataFrame]:
        """Read the data as GeoDataFrames reprojected to target_crs (default 2154).

        Returns one GeoDataFrame per layer, keyed by file stem. `source_crs` is only
        used for layers that have no CRS defined. A sequential `id` field is added to
        layers where no field name contains "id" (case-insensitive).
        """
        return self._prepare_geo_layers(self._read_layers()[0], target_crs, source_crs)

    @staticmethod
    def _prepare_geo_layers(
        layers: dict, target_crs: int, source_crs: int | None
    ) -> dict[str, gpd.GeoDataFrame]:
        layers_with_geometry = {}
        for name, gdf in layers.items():
            if not isinstance(gdf, gpd.GeoDataFrame):
                continue
            geometry = gdf.geometry

            gdf = gdf.loc[geometry.notna() & ~geometry.is_empty].copy()
            if gdf.empty:
                logger.warning("Skipping layer '%s': no non-empty geometries", name)
                continue

            if gdf.crs is None:
                if source_crs is None:
                    raise FetchError(f"Layer '{name}' has no CRS, provide source_crs")
                gdf = gdf.set_crs(source_crs)
            gdf = gdf.to_crs(target_crs)

            geometry_name = gdf.geometry.name
            if not any(
                "id" in str(column).lower()
                for column in gdf.columns
                if column != geometry_name
            ):
                gdf.insert(0, "id", range(1, len(gdf) + 1))
            layers_with_geometry[name] = gdf

        if not layers_with_geometry:
            raise FetchError("No geographic features with geometry found")
        return layers_with_geometry

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
        raw_layers, _ = self._read_layers()
        layers = self._prepare_geo_layers(raw_layers, target_crs, source_crs)
        tables = {
            name: frame
            for name, frame in raw_layers.items()
            if not isinstance(frame, gpd.GeoDataFrame)
        }
        engine = create_engine(connection_string or default_connection_string())
        names = []
        try:
            with engine.begin() as conn:
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
                for layer, gdf in layers.items():
                    name = (
                        table if len(layers) + len(tables) == 1 else f"{table}_{layer}"
                    )
                    geometry_column = str(gdf.geometry.name).lower()
                    gdf = gdf.rename(columns=lambda column: str(column).lower())
                    if not gdf.columns.is_unique:
                        raise FetchError(
                            f"Layer '{layer}' has duplicate field names after "
                            "converting them to lowercase"
                        )
                    gdf = gdf.set_geometry(geometry_column)
                    gdf.to_postgis(name, conn, schema=schema, if_exists="replace")
                    names.append(name)
                    logger.info("%d rows sent to %s.%s", len(gdf), schema, name)
                for layer, frame in tables.items():
                    frame = frame.rename(columns=lambda column: str(column).lower())
                    if not frame.columns.is_unique:
                        raise FetchError(
                            f"Layer '{layer}' has duplicate field names after "
                            "converting them to lowercase"
                        )
                    name = f"{table}_{layer}"
                    frame.to_sql(
                        name, conn, schema=schema, if_exists=if_exists, index=False
                    )
                    names.append(name)
                    logger.info("%d rows sent to %s.%s", len(frame), schema, name)
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
        validate_url(url)
        self.url = url
        self.timeout = timeout
        self.headers = headers

    def fetch(self) -> GeoDataset:
        """Download, detect the format, and validate the content."""
        content, content_type = download(self.url, self.timeout, self.headers)

        filename = self._guess_filename()
        fmt = self._detect_format(filename, content_type, content)
        fmt.validate(content)

        if not Path(filename).suffix:
            filename += mimetypes.guess_extension(content_type) or f".{fmt.name}"
        return GeoDataset(self.url, filename, content, fmt)

    def _guess_filename(self) -> str:
        return guess_filename(self.url)

    @staticmethod
    def _detect_format(filename: str, content_type: str, content: bytes) -> DataFormat:
        for fmt_cls in FORMATS:
            if fmt_cls.matches(filename, content_type, content):
                return fmt_cls()
        raise FetchError(f"Unsupported format ({filename}, {content_type})")
