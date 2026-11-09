{{
    config(
        materialized='table',
        contract={'enforced': true},
        post_hook=[
            "CREATE INDEX IF NOT EXISTS idx_epci_geom
             ON {{ this }} USING GIST (geom)"
        ]
    )
}}

SELECT
    CAST(id AS VARCHAR(9)) AS id,
    CAST(nom AS TEXT) AS nom,
    CAST(type AS VARCHAR(26)) AS type,
    CAST(
        ST_Transform(
            ST_Multi(
                CASE
                    WHEN ST_IsValid(geometry) THEN geometry
                    ELSE ST_CollectionExtract(ST_MakeValid(geometry), 3)
                END
            ),
            2154
        ) AS geometry(MultiPolygon, 2154)
    ) AS geom
FROM {{ source('raw_data', 'imope_epci') }}
