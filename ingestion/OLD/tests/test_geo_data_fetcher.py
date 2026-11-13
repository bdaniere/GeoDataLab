import geo_data_fetcher
import pytest
from geo_data_fetcher import (
    GeoDataFetcher,
    GeoDataset,
    GeoJSONFormat,
    ShapefileFormat,
    ZipFormat,
)
from util import FetchError


def test_geojson_format_accepts_feature_collection(feature_collection_bytes):
    GeoJSONFormat().validate(feature_collection_bytes)


@pytest.mark.parametrize("content", [b"{", b"[]", b'{"type":"Unknown"}'])
def test_geojson_format_rejects_invalid_documents(content):
    with pytest.raises(FetchError, match="GeoJSON invalide"):
        GeoJSONFormat().validate(content)


def test_shapefile_format_requires_sidecar_files(zip_bytes):
    content = zip_bytes({"communes.shp": b"shape"})

    assert ShapefileFormat.matches("communes.zip", "application/zip", content)
    with pytest.raises(FetchError, match="Shapefile incomplet"):
        ShapefileFormat().validate(content)


def test_geo_data_fetcher_detects_shapefile_archive(valid_shapefile_archive):
    content = valid_shapefile_archive

    detected = GeoDataFetcher._detect_format("communes.zip", "application/zip", content)

    assert isinstance(detected, ShapefileFormat)


def test_geo_data_fetcher_fetches_valid_geojson_without_network(
    monkeypatch, feature_collection_bytes
):
    monkeypatch.setattr(
        geo_data_fetcher,
        "download",
        lambda *args: (feature_collection_bytes, "application/geo+json"),
    )

    dataset = GeoDataFetcher("https://example.com/communes").fetch()

    assert dataset.filename.endswith((".geojson", ".json"))
    assert isinstance(dataset.format, GeoJSONFormat)


def test_geo_dataset_exports_only_supported_geographic_files(tmp_path, zip_bytes):
    content = zip_bytes(
        {
            "departement/communes.shp": b"shape",
            "departement/communes.shx": b"index",
            "departement/communes.dbf": b"attributes",
            "departement/notes.txt": b"documentation",
        }
    )
    dataset = GeoDataset(
        "https://example.com/communes.zip",
        "communes.zip",
        content,
        ShapefileFormat(),
    )

    exported = dataset.export(tmp_path)

    assert exported == [tmp_path / "communes" / "departement" / "communes.shp"]
    assert exported[0].read_bytes() == b"shape"
    assert (exported[0].with_suffix(".dbf")).read_bytes() == b"attributes"
    assert not (tmp_path / "communes" / "departement" / "notes.txt").exists()


def test_geo_dataset_rejects_archive_path_traversal(tmp_path, zip_bytes):
    content = zip_bytes(
        {
            "../escape.shp": b"shape",
            "../escape.shx": b"index",
            "../escape.dbf": b"attributes",
        }
    )
    dataset = GeoDataset(
        "https://example.com/communes.zip",
        "communes.zip",
        content,
        ShapefileFormat(),
    )

    with pytest.raises(FetchError, match="Unsafe path"):
        dataset.export(tmp_path)

    assert not (tmp_path.parent / "escape.shp").exists()


def test_prepare_geo_layers_reprojects_and_adds_id(geo_dataframe_with_empty_geometry):
    prepared = GeoDataset._prepare_geo_layers(
        {"communes": geo_dataframe_with_empty_geometry},
        target_crs=2154,
        source_crs=4326,
    )

    assert list(prepared) == ["communes"]
    assert prepared["communes"].crs.to_epsg() == 2154
    assert prepared["communes"]["id"].tolist() == [1]
    assert prepared["communes"]["name"].tolist() == ["Paris"]


def test_prepare_geo_layers_requires_source_crs_when_missing(geo_dataframe_without_crs):
    with pytest.raises(FetchError, match="has no CRS"):
        GeoDataset._prepare_geo_layers(
            {"communes": geo_dataframe_without_crs}, 2154, None
        )


def test_prepare_geo_layers_rejects_layers_without_geometry(
    geo_dataframe_without_valid_geometry,
):
    with pytest.raises(FetchError, match="No geographic features"):
        GeoDataset._prepare_geo_layers(
            {"table": geo_dataframe_without_valid_geometry}, 2154, None
        )


def test_geo_dataset_run_checks_resets_previous_errors(feature_collection_bytes):
    dataset = GeoDataset(
        "https://example.com/communes.geojson",
        "communes.geojson",
        feature_collection_bytes,
        GeoJSONFormat(),
        checks_errors=["old error"],
    )

    success = dataset.run_checks([lambda _: [], lambda _: ["invalid geometry"]])

    assert success is False
    assert dataset.checks_errors == ["invalid geometry"]


def test_zip_format_rejects_invalid_archive():
    with pytest.raises(FetchError, match="Archive ZIP invalide"):
        ZipFormat().validate(b"not a zip")
