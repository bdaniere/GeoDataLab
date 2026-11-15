from pathlib import Path

from core.models import SourceConfig, SourceData
from core.sources.base import BaseSource


class LocalSource(BaseSource):
    """Extract data from a local file."""

    def extract(self, config: SourceConfig) -> SourceData:
        """Return a reference to an existing local file.

        Args:
            config: Configuration describing the local data source.

        Returns:
            SourceData: Local file path and associated metadata.

        Raises:
            ValueError: If the source configuration is invalid.
            FileNotFoundError: If the configured file does not exist.
        """

        if config.source_type != "local":
            raise ValueError(f"Unsupported source type: {config.source_type}")

        if not config.location:
            raise ValueError("Local file path is missing.")

        file_path = Path(config.location).expanduser()

        if not file_path.exists():
            raise FileNotFoundError(f"Local file does not exist: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Expected a file, got a directory: {file_path}")

        file_path = file_path.resolve()

        return SourceData(
            source_name=config.name,
            source_type=config.source_type,
            content=file_path,
            format=file_path.suffix.lstrip(".").lower() or None,
            metadata={
                "file_path": str(file_path),
                "file_size": file_path.stat().st_size,
            },
        )
