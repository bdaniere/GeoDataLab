{{
    config(
        materialized='table',
        contract={'enforced': true},
        post_hook=[
            "CREATE INDEX IF NOT EXISTS idx_batiments_geom
             ON {{ this }} USING GIST (geom)"
        ]
    )
}}


WITH source_data AS (
    SELECT * FROM {{ source('raw_data', 'batiments') }}
),

filtered AS (
    SELECT *
    FROM source_data
    WHERE geometry IS NOT NULL
      AND NOT ST_IsEmpty(geometry)
),

deduplicated AS (
    SELECT DISTINCT ON (geometry) *
    FROM filtered
    ORDER BY
        geometry,
        created DESC NULLS LAST
),

corrected AS (
    SELECT
        gen_random_uuid() AS id,
        CAST(type AS VARCHAR(2)) AS type,
        nom,
        created AS created_at,
        updated AS updated_at,
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
