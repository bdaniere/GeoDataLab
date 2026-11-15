from contextlib import contextmanager
from typing import Any

import psycopg2
from psycopg2.extras import Json


class IngestionHistory:
    """Manages persistent ingestion history in PostgreSQL."""

    SCHEMA = "ingestion_meta"

    def __init__(self, environment: dict[str, str]):
        self.environment = environment

    @contextmanager
    def _connection(self):
        """Open and close a PostgreSQL connection."""

        connection = psycopg2.connect(
            host=self.environment["PGHOST"],
            port=self.environment["PGPORT"],
            dbname=self.environment["PGDATABASE"],
            user=self.environment["PGUSER"],
            password=self.environment["PGPASSWORD"],
        )

        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create history schema and tables if they do not exist."""

        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                    CREATE SCHEMA IF NOT EXISTS ingestion_meta;
                    """
            )

            cursor.execute(
                """
                    CREATE TABLE IF NOT EXISTS ingestion_meta.ingestions (
                        id BIGSERIAL PRIMARY KEY,
                        source_name TEXT NOT NULL,
                        source_path TEXT,
                        destination_schema TEXT NOT NULL,
                        loading_mode TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'running',
                        started_at TIMESTAMPTZ NOT NULL,
                        finished_at TIMESTAMPTZ,
                        duration_seconds DOUBLE PRECISION,
                        source_feature_count BIGINT,
                        destination_record_count BIGINT,
                        records_inserted BIGINT,
                        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                        CHECK (
                            status IN (
                                'running',
                                'success',
                                'partial',
                                'failed'
                            )
                        )
                    );
                    """
            )

            cursor.execute(
                """
                    CREATE TABLE IF NOT EXISTS ingestion_meta.layer_ingestions (
                        id BIGSERIAL PRIMARY KEY,
                        ingestion_id BIGINT NOT NULL
                            REFERENCES ingestion_meta.ingestions(id)
                            ON DELETE CASCADE,
                        layer_name TEXT NOT NULL,
                        destination_table TEXT NOT NULL,
                        status TEXT NOT NULL,
                        started_at TIMESTAMPTZ,
                        finished_at TIMESTAMPTZ,
                        duration_seconds DOUBLE PRECISION,
                        source_feature_count BIGINT,
                        destination_record_count BIGINT,
                        records_inserted BIGINT,
                        error TEXT,
                        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                        CHECK (
                            status IN ('success', 'failed')
                        ),
                        UNIQUE (ingestion_id, layer_name)
                    );
                    """
            )

            cursor.execute(
                """
                    CREATE INDEX IF NOT EXISTS
                    idx_layer_ingestions_ingestion_id
                    ON ingestion_meta.layer_ingestions (ingestion_id);
                    """
            )

    def start_ingestion(
        self,
        source_name: str,
        source_path: str | None,
        destination_schema: str,
        loading_mode: str,
        started_at,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Create a new ingestion history entry."""

        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                    INSERT INTO ingestion_meta.ingestions (
                        source_name,
                        source_path,
                        destination_schema,
                        loading_mode,
                        started_at,
                        metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                (
                    source_name,
                    source_path,
                    destination_schema,
                    loading_mode,
                    started_at,
                    Json(metadata or {}),
                ),
            )

            return cursor.fetchone()[0]

    def record_layer_result(
        self,
        ingestion_id: int,
        layer_name: str,
        destination_table: str,
        result,
    ) -> None:
        """Persist the result of an individual layer ingestion."""

        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                    INSERT INTO ingestion_meta.layer_ingestions (
                        ingestion_id,
                        layer_name,
                        destination_table,
                        status,
                        started_at,
                        finished_at,
                        duration_seconds,
                        source_feature_count,
                        destination_record_count,
                        records_inserted,
                        error,
                        metadata
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (ingestion_id, layer_name)
                    DO UPDATE SET
                        destination_table = EXCLUDED.destination_table,
                        status = EXCLUDED.status,
                        started_at = EXCLUDED.started_at,
                        finished_at = EXCLUDED.finished_at,
                        duration_seconds = EXCLUDED.duration_seconds,
                        source_feature_count = EXCLUDED.source_feature_count,
                        destination_record_count =
                            EXCLUDED.destination_record_count,
                        records_inserted = EXCLUDED.records_inserted,
                        error = EXCLUDED.error,
                        metadata = EXCLUDED.metadata;
                    """,
                (
                    ingestion_id,
                    layer_name,
                    destination_table,
                    "success" if result.success else "failed",
                    result.started_at,
                    result.finished_at,
                    result.duration_seconds,
                    result.source_feature_count,
                    result.destination_record_count,
                    result.records_inserted,
                    result.error,
                    Json(result.metadata),
                ),
            )

    def finish_ingestion(
        self,
        ingestion_id: int,
        status: str,
        finished_at,
        duration_seconds: float,
        source_feature_count: int | None,
        destination_record_count: int | None,
        records_inserted: int | None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Finalize a global ingestion history entry."""

        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                    UPDATE ingestion_meta.ingestions
                    SET
                        status = %s,
                        finished_at = %s,
                        duration_seconds = %s,
                        source_feature_count = %s,
                        destination_record_count = %s,
                        records_inserted = %s,
                        metadata = metadata || %s
                    WHERE id = %s;
                    """,
                (
                    status,
                    finished_at,
                    duration_seconds,
                    source_feature_count,
                    destination_record_count,
                    records_inserted,
                    Json(metadata or {}),
                    ingestion_id,
                ),
            )
