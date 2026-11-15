from core.sources.base import BaseSource
from core.sources.http_source import HttpSource
from core.sources.local_source import LocalSource


class SourceFactory:
    """Create source handlers based on the configured source type."""

    @staticmethod
    def create(source_type: str) -> BaseSource:
        """Create the appropriate source handler."""

        sources = {
            "local": LocalSource,
            "http": HttpSource,
        }

        source_class = sources.get(source_type.lower())

        if source_class is None:
            raise ValueError(
                f"Unsupported source type: {source_type}. "
                f"Supported types: {', '.join(sources)}"
            )

        return source_class()
