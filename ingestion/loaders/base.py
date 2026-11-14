from abc import ABC, abstractmethod

from ingestion.core.models import (
    DestinationConfig,
    IngestionResult,
    SourceData,
)


class BaseLoader(ABC):
    """Define the common interface for all data loaders."""

    @abstractmethod
    def load(
        self,
        source: SourceData,
        destination: DestinationConfig,
    ) -> IngestionResult:
        """Load extracted data into the configured destination.

        Args:
            source: Data extracted from a source.
            destination: Configuration describing the destination.

        Returns:
            IngestionResult: Result and metadata of the loading operation.
        """
        raise NotImplementedError
