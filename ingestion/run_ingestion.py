import argparse
import json
import sys
from pathlib import Path

from core.ingestion_report import IngestionReport
from core.ingestion_runner import IngestionRunner
from core.models import DestinationConfig, SourceConfig
from core.sources.factory import SourceFactory


def load_configuration(config_path: Path) -> dict:
    """Load ingestion configuration from a JSON file."""

    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_source(source_configuration: dict):
    """Build and extract a source from its configuration."""

    source_type = source_configuration.get("type")
    location = source_configuration.get("location")

    if not source_type:
        raise ValueError("Source type is missing from configuration.")

    if not location:
        raise ValueError("Source location is missing from configuration.")

    source_config = SourceConfig(
        name=source_configuration.get("name") or Path(location).stem,
        source_type=source_type,
        location=location,
        options=source_configuration.get("options", {}),
    )

    source_handler = SourceFactory.create(source_config.source_type)

    return source_handler.extract(source_config)


def build_destination(destination_configuration: dict) -> DestinationConfig:
    """Build a destination configuration."""

    destination_options = destination_configuration.get("options", {}).copy()

    destination_options["mode"] = destination_configuration.get(
        "mode",
        destination_options.get("mode", "create"),
    )

    target_crs = destination_configuration.get("target_crs")

    if target_crs is not None:
        destination_options["target_crs"] = target_crs

    return DestinationConfig(
        destination_type=destination_configuration.get("type", "postgis"),
        schema=destination_configuration.get("schema", "raw_data"),
        table=None,
        options=destination_options,
    )


def main() -> int:
    """Run the ingestion process from a configuration file."""

    parser = argparse.ArgumentParser(description="GeoDataLab - Geospatial ingestion")

    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "config" / "ingestion.json",
        help="Path to the ingestion configuration file.",
    )

    args = parser.parse_args()

    try:
        configuration = load_configuration(args.config)

        source = build_source(configuration["source"])
        destination = build_destination(configuration["destination"])

        runner = IngestionRunner()

        result = runner.run(
            source=source,
            destination=destination,
        )

        print(IngestionReport.format_result(result))

        return 0 if result.success else 1

    except Exception as error:
        print(f"Ingestion failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
