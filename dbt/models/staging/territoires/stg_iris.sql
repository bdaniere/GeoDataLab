{{
    config(
        materialized='table',
        contract={'enforced': true},
        post_hook=[
            "CREATE INDEX IF NOT EXISTS idx_iris_geom
             ON {{ this }} USING GIST (geom)"
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
        CAST(CURRENT_USER AS TEXT) AS updated_by,
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
