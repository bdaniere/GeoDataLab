from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from core.download_manager import DownloadError, DownloadManager
from core.models import SourceConfig
from core.sources.http_source import HttpSource, USER_AGENT


class FakeDownloadManager(DownloadManager):
    def __init__(self) -> None:
        self.headers: dict[str, str] | None = None
        self.url: str | None = None

    def download(
        self,
        url: str,
        destination: Path,
        headers: dict[str, str] | None = None,
    ) -> Path:
        self.headers = headers
        self.url = url
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"data")
        return destination


def test_http_source_uses_default_user_agent_and_configured_headers(
    tmp_path: Path,
) -> None:
    download_manager = FakeDownloadManager()
    source = HttpSource(download_manager=download_manager)
    config = SourceConfig(
        name="parcelles",
        source_type="http",
        location="https://example.test/parcelles.geojson",
        options={
            "download_dir": str(tmp_path),
            "headers": {"X-Api-Key": "test-token", "User-Agent": "CustomAgent/1.0"},
        },
    )

    source.extract(config)

    assert download_manager.url == config.location
    assert download_manager.headers == {
        "User-Agent": "CustomAgent/1.0",
        "X-Api-Key": "test-token",
    }


def test_http_source_adds_default_user_agent_when_headers_are_not_configured(
    tmp_path: Path,
) -> None:
    download_manager = FakeDownloadManager()
    source = HttpSource(download_manager=download_manager)
    config = SourceConfig(
        name="parcelles",
        source_type="http",
        location="https://example.test/parcelles.geojson",
        options={"download_dir": str(tmp_path)},
    )

    source.extract(config)

    assert download_manager.headers == {"User-Agent": USER_AGENT}


def test_download_manager_sends_headers_with_request(tmp_path: Path) -> None:
    response = MagicMock()
    response.__enter__.return_value = response
    response.headers = {"Content-Length": "4"}
    response.iter_content.return_value = [b"data"]
    session = Mock()
    session.get.return_value = response

    download_manager = DownloadManager()
    download_manager.session = session
    headers = {"User-Agent": USER_AGENT, "X-Test": "test-token"}
    destination = tmp_path / "download.bin"

    download_manager.download(
        "https://example.test/download.bin",
        destination,
        headers=headers,
    )

    session.get.assert_called_once_with(
        "https://example.test/download.bin",
        headers=headers,
        stream=True,
        timeout=download_manager.timeout,
    )
    assert destination.read_bytes() == b"data"


def test_download_retries_interrupted_stream(tmp_path: Path) -> None:
    interrupted = MagicMock()
    interrupted.__enter__.return_value = interrupted
    interrupted.headers = {}

    def interrupted_chunks(chunk_size: int):
        assert chunk_size == 1024 * 1024
        yield b"partial"
        raise requests.exceptions.ChunkedEncodingError("reset")

    interrupted.iter_content.side_effect = interrupted_chunks
    complete = MagicMock()
    complete.__enter__.return_value = complete
    complete.headers = {"Content-Length": "4"}
    complete.iter_content.return_value = [b"data"]
    session = Mock()
    session.get.side_effect = [interrupted, complete]
    download_manager = DownloadManager()
    download_manager.session = session
    destination = tmp_path / "download.bin"
    headers = {"User-Agent": USER_AGENT}

    with patch("core.download_manager.time.sleep") as sleep:
        download_manager.download("https://example.test/data", destination, headers=headers)

    assert session.get.call_count == 2
    assert all(call.kwargs["headers"] == headers for call in session.get.call_args_list)
    sleep.assert_called_once()
    assert destination.read_bytes() == b"data"
    assert not (tmp_path / "download.bin.part").exists()


def test_download_gives_up_after_repeated_connection_errors(tmp_path: Path) -> None:
    response = MagicMock()
    response.__enter__.return_value = response
    response.headers = {}

    def interrupted_chunks(chunk_size: int):
        assert chunk_size == 1024 * 1024
        yield b"partial"
        raise requests.ConnectionError("reset")

    response.iter_content.side_effect = interrupted_chunks
    session = Mock()
    session.get.return_value = response
    download_manager = DownloadManager()
    download_manager.session = session
    destination = tmp_path / "download.bin"
    destination.write_bytes(b"existing")

    with patch("core.download_manager.time.sleep"):
        with pytest.raises(DownloadError, match="reset"):
            download_manager.download("https://example.test/data", destination)

    assert session.get.call_count == 3
    assert destination.read_bytes() == b"existing"
    assert not (tmp_path / "download.bin.part").exists()


def test_download_does_not_retry_http_errors(tmp_path: Path) -> None:
    response = MagicMock()
    response.__enter__.return_value = response
    response.raise_for_status.side_effect = requests.HTTPError("404")
    session = Mock()
    session.get.return_value = response
    download_manager = DownloadManager()
    download_manager.session = session

    with pytest.raises(DownloadError, match="404"):
        download_manager.download("https://example.test/data", tmp_path / "download.bin")

    assert session.get.call_count == 1


def test_download_does_not_retry_tls_errors(tmp_path: Path) -> None:
    session = Mock()
    session.get.side_effect = requests.exceptions.SSLError("invalid certificate")
    download_manager = DownloadManager()
    download_manager.session = session

    with pytest.raises(DownloadError, match="invalid certificate"):
        download_manager.download("https://example.test/data", tmp_path / "download.bin")

    assert session.get.call_count == 1
