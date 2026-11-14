import sqlite3
from contextlib import closing

import pytest
from core.models import DestinationConfig, SourceData
from loaders.geographic.ogr_loader import OgrLoader
from psycopg2 import sql


def destination(schema, mode="create"):
    return DestinationConfig("postgis", schema, "features", options={"mode": mode})


def imported_rows(connection, schema):
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("SELECT id, nom, ST_SRID(geom) FROM {}.features ORDER BY id, nom").format(
                sql.Identifier(schema)
            )
        )
        return cursor.fetchall()


def expected_rows(geopackage):
    with closing(sqlite3.connect(geopackage)) as connection:
        rows = connection.execute("SELECT id, nom FROM villes ORDER BY id, nom").fetchall()
    return [(feature_id, name, 4326) for feature_id, name in rows]


def test_import_geopackage(postgis, source, geopackage):
    connection, schema = postgis

    result = OgrLoader().load(source, destination(schema))

    assert result.success, result.error
    assert result.records_processed == 2
    assert imported_rows(connection, schema) == expected_rows(geopackage)
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("SELECT ST_X(geom), ST_Y(geom) FROM {}.features ORDER BY id").format(
                sql.Identifier(schema)
            )
        )
        coordinates = cursor.fetchall()
    assert coordinates[0] == pytest.approx((2.3522, 48.8566))
    assert coordinates[1] == pytest.approx((4.8357, 45.764))


def test_create_rejects_existing_table(postgis, source, geopackage):
    connection, schema = postgis
    loader = OgrLoader()
    first = loader.load(source, destination(schema))
    assert first.success, first.error

    with pytest.raises(ValueError, match="Destination table already exists"):
        loader.load(source, destination(schema))

    assert imported_rows(connection, schema) == expected_rows(geopackage)


def test_append_adds_features(postgis, source, geopackage):
    connection, schema = postgis
    loader = OgrLoader()
    first = loader.load(source, destination(schema))
    assert first.success, first.error

    result = loader.load(source, destination(schema, "append"))

    assert result.success, result.error
    assert imported_rows(connection, schema) == sorted(expected_rows(geopackage) * 2)


def test_overwrite_replaces_table(postgis, source, geopackage):
    connection, schema = postgis
    loader = OgrLoader()
    first = loader.load(source, destination(schema))
    assert first.success, first.error
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("ALTER TABLE {}.features ADD COLUMN obsolete text").format(
                sql.Identifier(schema)
            )
        )
        cursor.execute(
            sql.SQL("UPDATE {}.features SET nom = 'obsolete'").format(
                sql.Identifier(schema)
            )
        )

    result = loader.load(source, destination(schema, "overwrite"))

    assert result.success, result.error
    assert imported_rows(connection, schema) == expected_rows(geopackage)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_schema = %s AND table_name = 'features' AND column_name = 'obsolete'
            """,
            (schema,),
        )
        assert cursor.fetchone()[0] == 0


def test_missing_source_layer_raises_error(source, ogrinfo):
    source.metadata["source_layer"] = "missing_layer"

    with pytest.raises(ValueError, match="Source layer 'missing_layer' does not exist"):
        OgrLoader().load(source, destination("unused"))


@pytest.mark.parametrize("target_crs", ["not-an-epsg", 999999, True])
def test_invalid_target_crs_raises_error(geopackage, target_crs):
    source = SourceData("test_geopackage", "local", geopackage, format="gpkg")
    config = destination("unused")
    config.options["target_crs"] = target_crs

    with pytest.raises(ValueError, match="Invalid target CRS"):
        OgrLoader().load(source, config)
