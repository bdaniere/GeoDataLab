{{
    config(
        materialized='table',
        contract={'enforced': true},
        post_hook=[
            "CREATE INDEX IF NOT EXISTS idx_communes_geom
             ON {{ this }} USING GIST (geom)"
        ]
    )
}}


WITH source_data AS (
    SELECT * FROM {{ source('raw_data', 'communes_france') }}
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
    ORDER BY geometry, code
),

corrected AS (
    SELECT
        CAST(code AS VARCHAR(5)) AS code_insee,
        nom,
        CAST(departement AS VARCHAR(3)) AS departement,
        CAST(region AS VARCHAR(3)) AS region,
        commune,
        plm,
        CAST(epci AS VARCHAR(9)) AS epci,
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
