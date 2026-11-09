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
    SELECT * FROM {{ source('raw_data', 'imope_commune') }}
),


filtered AS (
    SELECT *
    FROM source_data
    WHERE geometry IS NOT NULL
      AND NOT ST_IsEmpty(geometry)
),



corrected AS (
    SELECT
        CAST(id AS VARCHAR(9)) AS id,
        CAST(insee AS VARCHAR(5)) AS code_insee,
        nom,
        nom_unaccent,
        CAST(cp AS VARCHAR(5)) AS code_postal,
        CAST(superficie AS FLOAT) AS superficie,
        CAST(population AS INTEGER) AS population,
        CAST(epci_id AS VARCHAR(9)) AS epci_id,
        CAST(epci AS VARCHAR(9)) AS epci,
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

    FROM filtered
)

SELECT *
FROM corrected
