import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

MAX_DOWNLOAD_ATTEMPTS = 3


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

    def download(
        self,
        url: str,
        destination: Path,
        headers: dict[str, str] | None = None,
    ) -> Path:
        """Download a file, restarting up to twice after transient connection failures."""

        destination = Path(destination)
        temporary_path = destination.with_name(destination.name + ".part")

        destination.parent.mkdir(parents=True, exist_ok=True)

        for attempt in range(1, MAX_DOWNLOAD_ATTEMPTS + 1):
            try:
                self._download_once(url, temporary_path, headers)
                temporary_path.replace(destination)
                return destination
            except (
                requests.ConnectionError,
                requests.Timeout,
                requests.exceptions.ChunkedEncodingError,
            ) as error:
                temporary_path.unlink(missing_ok=True)
                if isinstance(error, requests.exceptions.SSLError) or (
                    attempt == MAX_DOWNLOAD_ATTEMPTS
                ):
                    raise DownloadError(f"Failed to download {url}: {error}") from error

                delay = 2 ** (attempt - 1)
                logger.warning(
                    "Download interrupted (%s); restarting from the beginning in %s "
                    "seconds (attempt %s/%s).",
                    error,
                    delay,
                    attempt + 1,
                    MAX_DOWNLOAD_ATTEMPTS,
                )
                time.sleep(delay)
            except (requests.RequestException, OSError, ValueError, DownloadError) as error:
                temporary_path.unlink(missing_ok=True)
                if isinstance(error, DownloadError):
                    raise
                raise DownloadError(f"Failed to download {url}: {error}") from error

        raise DownloadError(f"Failed to download {url}: no attempts were made.")

    def _download_once(
        self,
        url: str,
        temporary_path: Path,
        headers: dict[str, str] | None,
    ) -> None:
        with self.session.get(
            url,
            headers=headers,
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
                    f"Incomplete download: expected {expected_size} bytes, "
                    f"received {downloaded_size} bytes."
                )
