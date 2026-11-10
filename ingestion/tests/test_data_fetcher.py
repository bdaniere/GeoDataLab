import data_fetcher
import pytest
from data_fetcher import DataFetcher, DataSet, _is_csv, _sanitize, read_csv
from util import FetchError


def test_read_csv_detects_semicolon_separator():
    frame = read_csv(b"code;population\n75056;2161000\n")

    assert frame.to_dict(orient="records") == [{"code": 75056, "population": 2161000}]


def test_read_csv_supports_windows_1252():
    frame = read_csv("nom;ville\n1;Café".encode("cp1252"))

    assert frame.loc[0, "ville"] == "Café"


def test_read_csv_rejects_empty_content():
    with pytest.raises(FetchError, match="Invalid CSV"):
        read_csv(b"")


def test_sanitize_normalizes_identifiers():
    assert _sanitize("Énergie finale (kWh)") == "energie_finale_kwh"
    assert _sanitize("!!!") == "col"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("data.csv", True),
        ("nested/DATA.CSV", True),
        ("__MACOSX/._data.csv", False),
        ("nested/.hidden.csv", False),
        ("folder/", False),
        ("data.json", False),
    ],
)
def test_is_csv(name, expected):
    assert _is_csv(name) is expected


def test_dataset_reads_single_csv():
    dataset = DataSet("https://example.com/data.csv", "data.csv", b"a,b\n1,2\n")

    frames = dataset.to_dataframes()

    assert list(frames) == ["data"]
    assert frames["data"].to_dict(orient="records") == [{"a": 1, "b": 2}]


def test_dataset_reads_csv_files_from_zip(zip_bytes):
    content = zip_bytes(
        {
            "tables/communes.csv": b"code;nom\n75056;Paris\n",
            "tables/iris.csv": b"code,nom\n7510101,Paris\n",
            "__MACOSX/._ignored.csv": b"ignored\n1\n",
            "readme.txt": b"documentation",
        }
    )
    dataset = DataSet("https://example.com/data.zip", "data.zip", content)

    frames = dataset.to_dataframes()

    assert set(frames) == {"communes", "iris"}
    assert frames["communes"].loc[0, "nom"] == "Paris"


def test_dataset_rejects_duplicate_csv_stems_in_zip(zip_bytes):
    content = zip_bytes(
        {"one/communes.csv": b"id\n1\n", "two/communes.csv": b"id\n2\n"}
    )
    dataset = DataSet("https://example.com/data.zip", "data.zip", content)

    with pytest.raises(FetchError, match="Duplicate CSV name"):
        dataset.to_dataframes()


def test_dataset_rejects_zip_without_csv_files(zip_bytes):
    dataset = DataSet(
        "https://example.com/data.zip", "data.zip", zip_bytes({"readme.txt": b"text"})
    )

    with pytest.raises(FetchError, match="No CSV file"):
        dataset.to_dataframes()


def test_fetch_rejects_unsupported_content_type(monkeypatch):
    monkeypatch.setattr(
        data_fetcher, "download", lambda *args: (b"payload", "text/html")
    )

    with pytest.raises(FetchError, match="Unsupported format"):
        DataFetcher("https://example.com/file").fetch()


def test_fetch_accepts_csv_content_type_without_csv_extension(monkeypatch):
    monkeypatch.setattr(
        data_fetcher, "download", lambda *args: (b"id,value\n1,ok\n", "text/csv")
    )

    dataset = DataFetcher("https://example.com/resource").fetch()

    assert dataset.filename == "resource"
    assert dataset.to_dataframes()["resource"].loc[0, "value"] == "ok"
