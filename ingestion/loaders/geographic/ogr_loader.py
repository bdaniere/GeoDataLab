import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

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

        options = destination.options

        mode = options.get("mode", "create")

        if mode not in {"create", "overwrite", "append"}:
            raise ValueError(f"Unsupported loading mode: {mode}")

        target_crs = options.get("target_crs")

        ogr_command = [
            "ogr2ogr",
            "-f",
            "PostgreSQL",
            "PG:",
            str(source_path),
            "-nln",
            destination.table,
            "-lco",
            f"SCHEMA={destination.schema}",
        ]

        if mode == "overwrite":
            ogr_command.append("-overwrite")

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
                    "destination_schema": destination.schema,
                    "destination_table": destination.table,
                    "loading_mode": mode,
                },
            )

    def _get_database_environment(self) -> dict[str, str]:
        """Load PostgreSQL connection settings from the Docker environment file."""

        env_path = Path(__file__).resolve().parents[3] / "docker" / ".env"

        # if not env_path.is_file():
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
