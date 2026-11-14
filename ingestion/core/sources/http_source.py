from pathlib import Path
from urllib.parse import unquote, urlparse

from ingestion.core.download_manager import DownloadManager
from ingestion.core.models import SourceConfig, SourceData
from ingestion.core.sources.base import BaseSource


class HttpSource(BaseSource):
    """Extract data from an HTTP source."""

    def __init__(self, download_manager: DownloadManager | None = None):
        self.download_manager = download_manager or DownloadManager()

    def extract(self, config: SourceConfig) -> SourceData:
        """Download data from an HTTP source.

        Args:
            config: Configuration describing the HTTP source.

        Returns:
            SourceData: Downloaded file and associated metadata.

        Raises:
            ValueError: If the source configuration is invalid.
        """

        if config.source_type != "http":
            raise ValueError(f"Unsupported source type: {config.source_type}")

        if not config.location:
            raise ValueError("HTTP source URL is missing.")

        download_dir = Path(config.options.get("download_dir", "data/downloads"))

        filename = config.options.get("filename")

        if not filename:
            filename = Path(unquote(urlparse(config.location).path)).name

        if not filename:
            filename = config.name

        if Path(filename).name != filename or filename in {".", ".."}:
            raise ValueError("Invalid download filename.")

        destination = download_dir / filename

        downloaded_file = self.download_manager.download(
            url=config.location,
            destination=destination,
        )

        return SourceData(
            source_name=config.name,
            source_type=config.source_type,
            content=downloaded_file,
            format=downloaded_file.suffix.lstrip(".").lower() or None,
            metadata={
                "url": config.location,
                "file_path": str(downloaded_file),
                "file_size": downloaded_file.stat().st_size,
            },
        )
