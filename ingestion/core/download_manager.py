from pathlib import Path

import requests


class DownloadError(Exception):
    """Raise when a file download fails."""


class DownloadManager:
    """Handle HTTP file downloads with limited memory usage."""

    def __init__(
        self,
        timeout: tuple[int, int] = (10, 300),
        chunk_size: int = 1024 * 1024,
    ):
        self.timeout = timeout
        self.chunk_size = chunk_size
        self.session = requests.Session()

    def download(self, url: str, destination: Path) -> Path:
        """Download a file progressively to the local filesystem.

        Args:
            url: URL of the file to download.
            destination: Local path where the file will be stored.

        Returns:
            Path: Path to the downloaded file.

        Raises:
            DownloadError: If the download fails.
        """

        destination = Path(destination)
        temporary_path = destination.with_name(destination.name + ".part")

        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            with self.session.get(
                url,
                stream=True,
                timeout=self.timeout,
            ) as response:
                response.raise_for_status()

                content_length = response.headers.get("Content-Length")
                content_encoding = response.headers.get(
                    "Content-Encoding", "identity"
                ).lower()

                expected_size = None

                if content_length and content_encoding == "identity":
                    expected_size = int(content_length)

                downloaded_size = 0

                with temporary_path.open("wb") as file:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            file.write(chunk)
                            downloaded_size += len(chunk)

                if expected_size is not None and downloaded_size != expected_size:
                    raise DownloadError(
                        f"Incomplete download: expected "
                        f"{expected_size} bytes, received "
                        f"{downloaded_size} bytes."
                    )

            temporary_path.replace(destination)

            return destination

        except (requests.RequestException, OSError, ValueError) as error:
            temporary_path.unlink(missing_ok=True)

            if isinstance(error, DownloadError):
                raise

            raise DownloadError(f"Failed to download {url}: {error}") from error
