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
    schema: str
    table: str
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionResult:
    """Contains information related to an ingestion operation."""

    source_name: str
    success: bool

    started_at: datetime
    finished_at: datetime | None = None

    records_processed: int | None = None
    error: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float | None:
        """Calculates the duration of the ingestion in seconds."""

        if self.finished_at is None:
            return None

        return (self.finished_at - self.started_at).total_seconds()
