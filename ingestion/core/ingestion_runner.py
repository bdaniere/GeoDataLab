import logging
from dataclasses import replace
from datetime import UTC, datetime

from core.ingestion_history import IngestionHistory
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

    def _initialize_history(self) -> IngestionHistory | None:
        """Initialize persistent ingestion history.

        Returns:
            IngestionHistory | None: History manager if available.
        """

        try:
            environment = self.loader._get_database_environment()

            history = IngestionHistory(environment)
            history.initialize()

            return history

        except Exception:
            logger.exception(
                "Unable to initialize ingestion history. "
                "The ingestion will continue without history."
            )
            return None

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

        table_names = generate_table_names(
            source_path=source.content,
            layer_names=[layer.name for layer in layers],
        )

        loading_mode = destination.options.get("mode", "create")

        logger.info(
            "Ingestion started | source=%s | layers=%d | schema=%s | mode=%s",
            source.source_name,
            len(layers),
            destination.schema,
            loading_mode,
        )

        # Initialize persistent history.
        history = self._initialize_history()
        ingestion_id = None

        if history is not None:
            try:
                ingestion_id = history.start_ingestion(
                    source_name=source.source_name,
                    source_path=str(source.content),
                    destination_schema=destination.schema,
                    loading_mode=loading_mode,
                    started_at=started_at,
                    metadata=source.metadata,
                )

                logger.info(
                    "Ingestion history created | ingestion_id=%s",
                    ingestion_id,
                )

            except Exception:
                logger.exception("Unable to create global ingestion history entry.")
                history = None

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

            except Exception as error:
                logger.exception(
                    "Unexpected error during layer ingestion | layer=%s",
                    layer.name,
                )

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

            layer_results[layer.name] = result

            if result.success:
                logger.info(
                    "Layer ingestion completed | layer=%s | duration=%s",
                    layer.name,
                    result.duration_seconds,
                )
            else:
                logger.warning(
                    "Layer ingestion failed | layer=%s | error=%s",
                    layer.name,
                    result.error,
                )

            # Persist individual layer result.
            if history is not None and ingestion_id is not None:
                try:
                    history.record_layer_result(
                        ingestion_id=ingestion_id,
                        layer_name=layer.name,
                        destination_table=table_name,
                        result=result,
                    )

                except Exception:
                    logger.exception(
                        "Unable to persist layer history | layer=%s",
                        layer.name,
                    )

        finished_at = datetime.now(UTC)

        success = all(result.success for result in layer_results.values())

        successful_layers = sum(result.success for result in layer_results.values())

        failed_layers = sum(not result.success for result in layer_results.values())

        # Calculate global counters.
        def total_count(attribute: str) -> int | None:
            values = [
                getattr(result, attribute, None) for result in layer_results.values()
            ]

            if not values or any(value is None for value in values):
                return None

            return sum(values)

        source_count = total_count("source_feature_count")
        destination_count = total_count("destination_record_count")
        inserted_count = total_count("records_inserted")

        if successful_layers == len(layer_results):
            status = "success"
        elif successful_layers > 0:
            status = "partial"
        else:
            status = "failed"

        duration = (finished_at - started_at).total_seconds()

        logger.info(
            "Ingestion completed | source=%s | status=%s "
            "| successful_layers=%d | failed_layers=%d | duration=%.2fs",
            source.source_name,
            status,
            successful_layers,
            failed_layers,
            duration,
        )

        # Finalize global history.
        if history is not None and ingestion_id is not None:
            try:
                history.finish_ingestion(
                    ingestion_id=ingestion_id,
                    status=status,
                    finished_at=finished_at,
                    duration_seconds=duration,
                    source_feature_count=source_count,
                    destination_record_count=destination_count,
                    records_inserted=inserted_count,
                    metadata={
                        "successful_layers": successful_layers,
                        "failed_layers": failed_layers,
                    },
                )

            except Exception:
                logger.exception(
                    "Unable to finalize global ingestion history | id=%s",
                    ingestion_id,
                )

        return MultiLayerIngestionResult(
            source_name=source.source_name,
            success=success,
            started_at=started_at,
            finished_at=finished_at,
            layer_results=layer_results,
        )
