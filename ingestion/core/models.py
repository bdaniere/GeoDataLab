from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SourceConfig:
    """Describes a data source, regardless of its origin."""

    name: str
    source_type: str
    location: str | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class DestinationConfig:
    """Describes the destination of the data."""

    destination_type: str
    schema: str = "raw_data"
    table: str | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionResult:
    """Contains information related to an ingestion operation."""

    source_name: str
    success: bool

    started_at: datetime
    finished_at: datetime | None = None

    records_processed: int | None = None
    source_feature_count: int | None = None
    destination_record_count: int | None = None
    records_inserted: int | None = None

    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float | None:
        """Calculates the duration of the ingestion in seconds."""

        if self.finished_at is None:
            return None

        return (self.finished_at - self.started_at).total_seconds()


@dataclass
class MultiLayerIngestionResult:
    """Contains the results of a multi-layer ingestion operation."""

    source_name: str
    success: bool
    started_at: datetime
    finished_at: datetime | None = None

    layer_results: dict[str, IngestionResult] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float | None:
        """Calculate the duration of the ingestion."""

        if self.finished_at is None:
            return None

        return (self.finished_at - self.started_at).total_seconds()

    @property
    def successful_layers(self) -> int:
        """Return the number of successfully loaded layers."""

        return sum(result.success for result in self.layer_results.values())

    @property
    def failed_layers(self) -> int:
        """Return the number of failed layers."""

        return sum(not result.success for result in self.layer_results.values())

    @property
    def source_feature_count(self) -> int | None:
        """Return the total number of source features across all layers."""

        counts = [result.source_feature_count for result in self.layer_results.values()]

        if not counts or any(count is None for count in counts):
            return None

        return sum(counts)

    @property
    def destination_record_count(self) -> int | None:
        """Return the total number of destination records across all layers."""

        counts = [
            result.destination_record_count for result in self.layer_results.values()
        ]

        if not counts or any(count is None for count in counts):
            return None

        return sum(counts)

    @property
    def records_inserted(self) -> int | None:
        """Return the total number of records inserted across all layers."""

        counts = [result.records_inserted for result in self.layer_results.values()]

        if not counts or any(count is None for count in counts):
            return None

        return sum(counts)


@dataclass
class SourceData:
    """Represent data extracted from a source."""

    source_name: str
    source_type: str
    content: Any

    format: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
