{{
    config(
        materialized='table',
        contract={'enforced': true},
        indexes=[{'columns': ['geom'], 'type': 'gist'}]
    )
}}

SELECT
    CAST(id AS VARCHAR(9)) AS id,
    CAST(nom AS TEXT) AS nom,
    CAST(type AS VARCHAR(26)) AS type,
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
        ) AS geometry(MultiPolygon, 2154)
    ) AS geom
    
FROM {{ source('raw_data', 'imope_epci') }}
