from core.models import IngestionResult, MultiLayerIngestionResult


class IngestionReport:
    """Formats ingestion results into human-readable reports."""

    @staticmethod
    def _format_duration(duration: float | None) -> str:
        """Format a duration in seconds."""
        if duration is None:
            return "N/A"

        return f"{duration:.2f} s"

    @staticmethod
    def _format_count(count: int | None) -> str:
        """Format a record count."""
        if count is None:
            return "N/A"

        return f"{count:,}".replace(",", " ")

    @staticmethod
    def _format_layer_result(
        layer_name: str,
        result: IngestionResult,
    ) -> list[str]:
        """Format the result of a single layer ingestion."""
        status = "SUCCESS" if result.success else "FAILED"

        metadata = result.metadata or {}
        schema = metadata.get("schema")
        table = metadata.get("table")

        destination = f"{schema}.{table}" if schema and table else table or "N/A"

        lines = [
            f"  Layer: {layer_name}",
            f"    Status: {status}",
            f"    Destination: {destination}",
            (
                "    Source features: "
                f"{IngestionReport._format_count(result.source_feature_count)}"
            ),
            (
                "    Destination records: "
                f"{IngestionReport._format_count(result.destination_record_count)}"
            ),
            (
                "    Records inserted: "
                f"{IngestionReport._format_count(result.records_inserted)}"
            ),
            (
                "    Duration: "
                f"{IngestionReport._format_duration(result.duration_seconds)}"
            ),
        ]

        if result.error:
            lines.append(f"    Error: {result.error}")

        return lines

    @classmethod
    def format_result(
        cls,
        result: MultiLayerIngestionResult,
    ) -> str:
        """Generate a human-readable report for a multi-layer ingestion."""
        status = "SUCCESS" if result.success else "FAILED"

        lines = [
            "=" * 65,
            "INGESTION REPORT",
            "=" * 65,
            f"Source: {result.source_name}",
            f"Status: {status}",
            f"Duration: {cls._format_duration(result.duration_seconds)}",
            "",
            "GLOBAL SUMMARY",
            "-" * 65,
            f"Successful layers: {result.successful_layers}",
            f"Failed layers: {result.failed_layers}",
            (f"Source features: {cls._format_count(result.source_feature_count)}"),
            (
                "Destination records: "
                f"{cls._format_count(result.destination_record_count)}"
            ),
            (f"Records inserted: {cls._format_count(result.records_inserted)}"),
            "",
            "LAYER DETAILS",
            "-" * 65,
        ]

        if not result.layer_results:
            lines.append("No layer results available.")
        else:
            for layer_name, layer_result in result.layer_results.items():
                lines.extend(cls._format_layer_result(layer_name, layer_result))
                lines.append("")

        lines.append("=" * 65)

        return "\n".join(lines)
