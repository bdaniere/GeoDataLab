import argparse
import json
import sys
from pathlib import Path

from core.ingestion_report import IngestionReport
from core.ingestion_runner import IngestionRunner
from core.models import DestinationConfig, SourceData


def load_configuration(config_path: Path) -> dict:
    """Load ingestion configuration from a JSON file."""
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        return json.load(file)


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

        source_config = configuration["source"]
        destination_config = configuration["destination"]

        source_path = Path(source_config["path"]).expanduser()

        if not source_path.is_file():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        source = SourceData(
            source_name=source_path.name,
            source_type=source_config.get("type"),
            content=str(source_path),
            metadata={},
        )

        destination_options = {
            "mode": destination_config.get("mode", "create"),
        }

        target_crs = destination_config.get("target_crs")
        if target_crs is not None:
            destination_options["target_crs"] = target_crs

        destination = DestinationConfig(
            destination_type=destination_config.get("type", "postgis"),
            schema=destination_config.get("schema", "raw_data"),
            table=None,
            options=destination_options,
        )

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
