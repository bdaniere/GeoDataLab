import os
import shutil
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest
from core.models import SourceData
from loaders.geographic.ogr_loader import OgrLoader
from psycopg2 import sql
from psycopg2.extensions import parse_dsn


@pytest.fixture
def geopackage():
    path = Path(__file__).parent / "testdata" / "test.gpkg"
    assert path.is_file(), f"Missing test GeoPackage: {path}"
    return path


@pytest.fixture
def source(geopackage):
    return SourceData(
        "test_geopackage",
        "local",
        geopackage,
        format="gpkg",
        metadata={"source_layer": "villes"},
    )


@pytest.fixture
def ogrinfo():
    if not shutil.which("ogrinfo"):
        if os.environ.get("TEST_POSTGIS_DSN"):
            pytest.fail("ogrinfo is required for PostGIS integration tests")
        pytest.skip("ogrinfo is required to inspect the GeoPackage")


@pytest.fixture
def postgis(monkeypatch, ogrinfo):
    dsn = os.environ.get("TEST_POSTGIS_DSN")
    if not dsn:
        pytest.skip("Set TEST_POSTGIS_DSN to run PostGIS integration tests")
    if not shutil.which("ogr2ogr"):
        pytest.fail("ogr2ogr is required for PostGIS integration tests")

    settings = parse_dsn(dsn)
    required = ("host", "port", "dbname", "user", "password")
    missing = [key for key in required if not settings.get(key)]
    if missing:
        pytest.fail(f"TEST_POSTGIS_DSN is missing: {', '.join(missing)}")

    environment = os.environ.copy()
    environment.update(
        {
            "PGHOST": settings["host"],
            "PGPORT": settings["port"],
            "PGDATABASE": settings["dbname"],
            "PGUSER": settings["user"],
            "PGPASSWORD": settings["password"],
        }
    )
    monkeypatch.setattr(OgrLoader, "_get_database_environment", lambda self: environment)

    connection = psycopg2.connect(dsn)
    connection.autocommit = True
    schema = f"test_ogr_{uuid4().hex}"
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:
        yield connection, schema
    finally:
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
            )
        connection.close()
