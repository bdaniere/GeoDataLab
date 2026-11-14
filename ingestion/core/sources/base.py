from abc import ABC, abstractmethod

from ingestion.core.models import SourceConfig, SourceData


class BaseSource(ABC):
    """Define the common interface for all data sources."""

    @abstractmethod
    def extract(self, config: SourceConfig) -> SourceData:
        """Extract data from the configured source.

        Args:
            config: Configuration describing the data source.

        Returns:
            SourceData: Extracted data and associated metadata.
        """
        raise NotImplementedError
