"""Point d'entrée de l'ingestion : télécharge les sources de data_source.json
et les charge dans PostgreSQL (schéma raw_data).

Usage :
    python run_ingestion.py                # toutes les sources
    python run_ingestion.py geographic     # uniquement les données géographiques
    python run_ingestion.py non_geographic # uniquement les données non géographiques
    python run_ingestion.py --only imope communes_france
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from data_fetcher import DataFetcher
from geo_data_fetcher import GeoDataFetcher

logger = logging.getLogger(__name__)

SOURCES_FILE = Path(__file__).parent / "data_source.json"
SCHEMA = "raw_data"


def load_sources(path: Path = SOURCES_FILE) -> dict[str, dict[str, str]]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_geographic(sources: dict[str, str]) -> None:
    for table_name, url in sources.items():
        logger.info("Ingestion géographique : %s", table_name)
        GeoDataFetcher(url).fetch().to_postgis(table=table_name, schema=SCHEMA)


def run_non_geographic(sources: dict[str, str]) -> None:
    for table_name, url in sources.items():
        logger.info("Ingestion non géographique : %s", table_name)
        DataFetcher(url).fetch().to_postgres(table=table_name, schema=SCHEMA)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "kind",
        nargs="?",
        choices=["all", "geographic", "non_geographic"],
        default="all",
        help="type de données à ingérer (défaut : all)",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="NAME",
        help="limiter à certaines sources (clés de data_source.json)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    sources = load_sources()
    geo = sources.get("geographic_data", {})
    non_geo = sources.get("non_geographic_data", {})

    if args.only:
        wanted = set(args.only)
        unknown = wanted - geo.keys() - non_geo.keys()
        if unknown:
            parser.error(f"sources inconnues : {', '.join(sorted(unknown))}")
        geo = {k: v for k, v in geo.items() if k in wanted}
        non_geo = {k: v for k, v in non_geo.items() if k in wanted}

    if args.kind in ("all", "geographic"):
        run_geographic(geo)
    if args.kind in ("all", "non_geographic"):
        run_non_geographic(non_geo)


if __name__ == "__main__":
    main()
