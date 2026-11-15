import logging
from dataclasses import replace
from datetime import UTC, datetime

from core.models import (
    DestinationConfig,
    IngestionResult,
    MultiLayerIngestionResult,
    SourceData,
)
from core.table_naming import generate_table_names
from extraction.layer_discovery import LayerDiscovery
from loaders.geographic.ogr_loader import OgrLoader

logger = logging.getLogger(__name__)


class IngestionRunner:
    """Orchestrate the ingestion of multi-layer source files."""

    def __init__(
        self,
        loader: OgrLoader | None = None,
        layer_discovery: LayerDiscovery | None = None,
    ):
        self.loader = loader or OgrLoader()
        self.layer_discovery = layer_discovery or LayerDiscovery()

    def run(
        self,
        source: SourceData,
        destination: DestinationConfig,
    ) -> MultiLayerIngestionResult:
        """Discover and load all layers from a source file.

        Args:
            source: Extracted source data.
            destination: Destination configuration.

        Returns:
            MultiLayerIngestionResult: Global and per-layer results.
        """

        started_at = datetime.now(UTC)

        if destination.destination_type != "postgis":
            raise NotImplementedError(
                f"Unsupported destination type: {destination.destination_type}"
            )

        if destination.table is not None:
            raise ValueError(
                "Destination table must not be specified for multi-layer ingestion."
            )

        layers = self.layer_discovery.discover(source.content)

        logger.info(
            "Ingestion started | source=%s | layers=%d | schema=%s | mode=%s",
            source.source_name,
            len(layers),
            destination.schema,
            destination.options.get("mode", "create"),
        )

        layers = self.layer_discovery.discover(source.content)

        table_names = generate_table_names(
            source_path=source.content,
            layer_names=[layer.name for layer in layers],
        )

        layer_results = {}

        for layer in layers:
            table_name = table_names[layer.name]

            layer_source = replace(
                source,
                metadata={
                    **source.metadata,
                    "source_layer": layer.name,
                },
            )

            layer_destination = DestinationConfig(
                destination_type=destination.destination_type,
                schema=destination.schema,
                table=table_name,
                options=destination.options.copy(),
            )

            logger.info(
                "Layer ingestion started | source=%s | layer=%s | table=%s",
                source.source_name,
                layer.name,
                table_name,
            )

            try:
                result = self.loader.load(
                    source=layer_source,
                    destination=layer_destination,
                )

                if result.success:
                    logger.info(
                        "Layer ingestion completed | layer=%s | source_features=%s "
                        "| destination_records=%s | records_inserted=%s | duration=%.2fs",
                        layer.name,
                        result.source_feature_count,
                        result.destination_record_count,
                        result.records_inserted,
                        result.duration_seconds or 0,
                    )
                else:
                    logger.warning(
                        "Layer ingestion failed | layer=%s | error=%s",
                        layer.name,
                        result.error,
                    )

            except Exception as error:
                result = IngestionResult(
                    source_name=source.source_name,
                    success=False,
                    started_at=datetime.now(UTC),
                    finished_at=datetime.now(UTC),
                    error=str(error),
                    metadata={
                        "source_layer": layer.name,
                        "destination_schema": destination.schema,
                        "destination_table": table_name,
                    },
                )

                logger.exception(
                    "Unexpected error during layer ingestion | layer=%s",
                    layer.name,
                )

            layer_results[layer.name] = result

        finished_at = datetime.now(UTC)

        logger.info(
            "Ingestion completed | source=%s | success=%s "
            "| successful_layers=%d | failed_layers=%d | duration=%.2fs",
            source.source_name,
            all(result.success for result in layer_results.values()),
            sum(result.success for result in layer_results.values()),
            sum(not result.success for result in layer_results.values()),
            (finished_at - started_at).total_seconds(),
        )

        return MultiLayerIngestionResult(
            source_name=source.source_name,
            success=all(result.success for result in layer_results.values()),
            started_at=started_at,
            finished_at=finished_at,
            layer_results=layer_results,
        )
