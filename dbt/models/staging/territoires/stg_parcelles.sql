{{
    config(
        materialized='table',
        contract={'enforced': true},
        indexes=[{'columns': ['geom'], 'type': 'gist'}]
    )
}}


WITH source_data AS (
    SELECT * FROM {{ source('raw_data', 'parcelles_69') }}
),


filtered AS (
    SELECT *
    FROM source_data
    WHERE NOT ST_IsEmpty(wkb_geometry)
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
        CAST(ST_Area(wkb_geometry) AS FLOAT) AS superficie,
        CAST(created AS TIMESTAMP) AS created_at,
        CAST(updated AS TIMESTAMP) AS updated_at,
        CAST(CURRENT_USER AS TEXT) AS updated_by,
        CAST(
            {{ largest_valid_polygon('wkb_geometry') }}
            AS geometry(POLYGON, 2154)
        ) AS geom

    FROM filtered
)

SELECT *
FROM corrected
