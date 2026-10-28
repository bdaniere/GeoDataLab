import json
import zipfile
from io import BytesIO

import geopandas as gpd
import pytest
from shapely.geometry import Point


@pytest.fixture
def zip_bytes():
    def create_zip(files):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        return buffer.getvalue()

    return create_zip


@pytest.fixture
def feature_collection_bytes():
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "Paris"},
                    "geometry": {"type": "Point", "coordinates": [2.35, 48.85]},
                }
            ],
        }
    ).encode()


@pytest.fixture
def valid_shapefile_archive(zip_bytes):
    return zip_bytes(
        {
            "communes.shp": b"shape",
            "communes.shx": b"index",
            "communes.dbf": b"attributes",
        }
    )


@pytest.fixture
def geo_dataframe_with_empty_geometry():
    return gpd.GeoDataFrame(
        {"name": ["Paris", "empty"]},
        geometry=[Point(2.35, 48.85), Point()],
    )


@pytest.fixture
def geo_dataframe_without_crs():
    return gpd.GeoDataFrame({"name": ["Paris"]}, geometry=[Point(2.35, 48.85)])


@pytest.fixture
def geo_dataframe_without_valid_geometry():
    return gpd.GeoDataFrame(
        {"name": ["Paris"], "geometry": [None]}, geometry="geometry"
    )
