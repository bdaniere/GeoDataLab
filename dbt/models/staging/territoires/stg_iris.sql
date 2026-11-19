{{
    config(
        materialized='table',
        contract={'enforced': true},
        indexes=[{'columns': ['geom'], 'type': 'gist'}]
    )
}}


WITH source_data AS (
    SELECT * FROM {{ source('raw_data', 'imope_iris') }}
),


filtered AS (
    SELECT *
    FROM source_data
    WHERE NOT ST_IsEmpty(geom)
      AND id IS NOT NULL
),

deduplicated AS (
    SELECT DISTINCT ON (geom) *
    FROM filtered
    ORDER BY
        geom DESC NULLS LAST
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
                        WHEN ST_IsValid(geom) THEN geom
                        ELSE ST_CollectionExtract(ST_MakeValid(geom), 3)
                    END
                ),
                2154
            ) AS geometry(MULTIPOLYGON, 2154)
        ) AS geom

    FROM deduplicated
)

SELECT *
FROM corrected
