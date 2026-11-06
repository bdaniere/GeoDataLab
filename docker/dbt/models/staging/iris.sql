{{
    config(
        materialized='table',
        contract={'enforced': true},
        post_hook=[
            "CREATE INDEX IF NOT EXISTS idx_iris_geom
             ON {{ this }} USING GIST (geom)",

             "CREATE OR REPLACE FUNCTION update_updated_at()
             RETURNS TRIGGER AS $$
             BEGIN
                 NEW.updated_at = NOW();
                 RETURN NEW;
             END;
             $$ LANGUAGE plpgsql",

            "DROP TRIGGER IF EXISTS trg_iris_updated_at ON {{ this }}",

            "CREATE TRIGGER trg_iris_updated_at
             BEFORE UPDATE ON {{ this }}
             FOR EACH ROW
             EXECUTE FUNCTION update_updated_at()"
        ]
    )
}}


WITH source_data AS (
    SELECT * FROM {{ source('raw_data', 'imope_iris') }}
),


filtered AS (
    SELECT *
    FROM source_data
    WHERE NOT ST_IsEmpty(geometry)
      AND id IS NOT NULL
),

deduplicated AS (
    SELECT DISTINCT ON (geometry) *
    FROM filtered
    ORDER BY
        geometry DESC NULLS LAST
),



corrected AS (
    SELECT

        CAST(id AS VARCHAR(9)) AS id,
        CAST(nom AS TEXT) AS nom,
        CAST(type AS VARCHAR(1)) AS type,
        CAST(commune AS TEXT) AS commune,
        CAST(commune_id AS VARCHAR(5)) AS commune_id,
        CAST(NOW() AS TIMESTAMP) AS created_at,
        CAST(NOW() AS TIMESTAMP) AS updated_at,
        CAST(
            ST_Transform(
                ST_Multi(
                    CASE
                        WHEN ST_IsValid(geometry) THEN geometry
                        ELSE ST_CollectionExtract(ST_MakeValid(geometry), 3)
                    END
                ),
                2154
            ) AS geometry(MULTIPOLYGON, 2154)
        ) AS geom

    FROM deduplicated
)

SELECT *
FROM corrected
