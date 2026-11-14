import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from pyproj import CRS
from pyproj.exceptions import CRSError

from ingestion.core.models import (
    DestinationConfig,
    IngestionResult,
    SourceData,
)
from ingestion.loaders.base import BaseLoader


class OgrLoader(BaseLoader):
    """Load geographic files into PostGIS using ogr2ogr."""

    def load(
        self,
        source: SourceData,
        destination: DestinationConfig,
    ) -> IngestionResult:
        """Load a geographic file into a PostGIS table.

        Args:
            source: Extracted data containing a local file path.
            destination: Configuration describing the PostGIS destination.

        Returns:
            IngestionResult: Result and metadata of the loading operation.
        """

        started_at = datetime.now(UTC)

        if destination.destination_type != "postgis":
            raise ValueError(
                f"Unsupported destination type: {destination.destination_type}"
            )

        if not isinstance(source.content, (str, Path)):
            raise TypeError("OgrLoader expects a local file path.")

        source_path = Path(source.content)

        if not source_path.is_file():
            raise FileNotFoundError(f"Source file does not exist: {source_path}")

        source_layer = source.metadata.get("source_layer")
        self._validate_source_layer(
            source_path=source_path,
            source_layer=source_layer,
        )

        options = destination.options

        mode = options.get("mode", "create")

        if mode not in {"create", "overwrite", "append"}:
            raise ValueError(f"Unsupported loading mode: {mode}")

        target_crs = options.get("target_crs")
        self._validate_target_crs(target_crs)

        source_layer = source.metadata.get("source_layer")

        ogr_command = [
            "ogr2ogr",
            "-f",
            "PostgreSQL",
            "PG:",
            str(source_path),
        ]

        if source_layer:
            ogr_command.append(source_layer)

        ogr_command.extend(
            [
                "-nln",
                f"{destination.schema}.{destination.table}",
            ]
        )

        if mode == "overwrite":
            ogr_command.extend(
                [
                    "-lco",
                    "OVERWRITE=YES",
                ]
            )

        elif mode == "append":
            ogr_command.append("-append")

        if target_crs:
            ogr_command.extend(
                [
                    "-t_srs",
                    f"EPSG:{target_crs}",
                ]
            )

        environment = self._get_database_environment()

        try:
            print(f"Running command: {' '.join(ogr_command)}")
            process = subprocess.run(
                ogr_command,
                capture_output=True,
                text=True,
                check=True,
                env=environment,
            )

            return IngestionResult(
                source_name=source.source_name,
                success=True,
                started_at=started_at,
                finished_at=datetime.now(UTC),
                metadata={
                    "source_file": str(source_path.resolve()),
                    "source_layer": source_layer,
                    "destination_schema": destination.schema,
                    "destination_table": destination.table,
                    "loading_mode": mode,
                    "target_crs": target_crs,
                    "command_output": process.stdout,
                },
            )

        except subprocess.CalledProcessError as error:
            return IngestionResult(
                source_name=source.source_name,
                success=False,
                started_at=started_at,
                finished_at=datetime.now(UTC),
                error=error.stderr or str(error),
                metadata={
                    "source_file": str(source_path.resolve()),
                    "source_layer": source_layer,
                    "destination_schema": destination.schema,
                    "destination_table": destination.table,
                    "loading_mode": mode,
                },
            )

    def _get_database_environment(self) -> dict[str, str]:
        """Load PostgreSQL connection settings from the Docker environment file."""

        env_path = Path(__file__).resolve().parents[3] / "docker" / ".env"

        # if not env_path.is_file():  # TMP - Reactivation at the end of the development phase for use with Docker
        load_dotenv(dotenv_path=env_path)

        environment = os.environ.copy()
        config = {
            "POSTGRES_HOST": environment.get("POSTGRES_HOST", "localhost"),
            "POSTGIS_PORT": environment.get("POSTGIS_PORT", "5432"),
            "POSTGRES_DB": environment.get("POSTGRES_DB", ""),
            "POSTGRES_USER": environment.get("POSTGRES_USER", ""),
            "POSTGRES_PASSWORD": environment.get("POSTGRES_PASSWORD", ""),
        }

        missing_variables = [
            variable for variable, value in config.items() if not value
        ]

        if missing_variables:
            raise ValueError(
                f"Missing or empty PostgreSQL variables in environment or {env_path}: "
                f"{', '.join(missing_variables)}"
            )

        environment.update(
            {
                "PGHOST": config["POSTGRES_HOST"],
                "PGPORT": config["POSTGIS_PORT"],
                "PGDATABASE": config["POSTGRES_DB"],
                "PGUSER": config["POSTGRES_USER"],
                "PGPASSWORD": config["POSTGRES_PASSWORD"],
            }
        )

        return environment

    @staticmethod
    def _validate_target_crs(target_crs: int | str | None) -> None:
        """Validate the target EPSG code.

        Args:
            target_crs: Target EPSG code.

        Raises:
            ValueError: If the EPSG code is invalid.
        """

        if target_crs is None:
            return

        if isinstance(target_crs, bool) or not str(target_crs).isdigit():
            raise ValueError(
                f"Invalid target CRS: {target_crs}. Expected a valid EPSG code."
            )

        try:
            CRS.from_epsg(int(target_crs))
        except (CRSError, ValueError) as error:
            raise ValueError(
                f"Invalid target CRS: {target_crs}. Expected a valid EPSG code."
            ) from error

    @staticmethod
    def _validate_source_layer(
        source_path: Path,
        source_layer: str | None,
    ) -> None:
        """Validate that the requested layer exists in the source file.

        Args:
            source_path: Path to the geographic source file.
            source_layer: Name of the requested source layer.

        Raises:
            ValueError: If the requested layer does not exist.
        """

        if source_layer is None:
            return

        command = [
            "ogrinfo",
            "-ro",
            "-q",
            str(source_path),
        ]

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as error:
            raise ValueError(f"Unable to inspect source file: {source_path}") from error

        available_layers = [
            line.strip().split(": ", 1)[1].split(" ", 1)[0]
            for line in process.stdout.splitlines()
            if ": " in line
        ]

        if source_layer not in available_layers:
            raise ValueError(
                f"Source layer '{source_layer}' does not exist. "
                f"Available layers: {', '.join(available_layers)}"
            )
