{{
    config(
        materialized='table',
        contract={'enforced': true},
        post_hook=[
            "CREATE INDEX IF NOT EXISTS idx_parcelles_geom
             ON {{ this }} USING GIST (geom)"
        ]
    )
}}


WITH source_data AS (
    SELECT * FROM {{ source('raw_data', 'parcelles') }}
),


filtered AS (
    SELECT *
    FROM source_data
    WHERE NOT ST_IsEmpty(geometry)
      AND id IS NOT NULL
),


 

corrected AS (
    SELECT
        CAST(id AS TEXT) AS id,
        CAST(commune AS TEXT) AS commune,
        CAST(prefixe AS VARCHAR(3)) AS prefixe,
        CAST(section AS VARCHAR(2)) AS section,
        CAST(numero AS VARCHAR(4)) AS numero,
        CAST(contenance AS INTEGER) AS contenance,
        CAST(ST_Area(geometry) AS FLOAT) AS superficie,
        CAST(created AS TIMESTAMP) AS created_at,
        CAST(updated AS TIMESTAMP) AS updated_at,
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
