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
    SELECT * FROM {{ source('raw_data', 'batiments_69') }}
),

filtered AS (
    SELECT *
    FROM source_data
    WHERE wkb_geometry IS NOT NULL
      AND NOT ST_IsEmpty(wkb_geometry)
),

deduplicated AS (
    SELECT DISTINCT ON (wkb_geometry) *
    FROM filtered
    ORDER BY
        wkb_geometry,
        created DESC NULLS LAST
),

corrected AS (
    SELECT
        gen_random_uuid() AS id,
        CAST(type AS VARCHAR(2)) AS type,
        nom,
        CAST(created AS TIMESTAMP) AS created_at,
        CAST(NOW() AS TIMESTAMP) AS updated_at,
        CAST(CURRENT_USER AS TEXT) AS updated_by,
        CAST(
            ST_Transform(
                ST_Multi(
                    CASE
                        WHEN ST_IsValid(wkb_geometry) THEN wkb_geometry
                        ELSE ST_CollectionExtract(ST_MakeValid(wkb_geometry), 3)
                    END
                ),
                2154
            ) AS geometry(MULTIPOLYGON, 2154)
        ) AS geom

    FROM deduplicated
)

SELECT *
FROM corrected
