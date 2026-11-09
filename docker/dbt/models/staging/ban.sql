{{
    config(
        materialized='table',
        contract={'enforced': true},
        post_hook=[
            "CREATE INDEX IF NOT EXISTS idx_ban_geometry
             ON {{ this }} USING GIST (geometry)"
        ]
    )
}}

SELECT
    CAST(id AS VARCHAR(24)) AS id,
    CAST(id_fantoir AS VARCHAR(10)) AS id_fantoir,
    CAST(numero AS TEXT) AS numero,
    CAST(rep AS TEXT) AS rep,
    CAST(nom_voie AS TEXT) AS nom_voie,
    CAST(cp AS VARCHAR(5)) AS code_postal,
    CAST(commune AS TEXT) AS commune,
    CAST(commune_id AS VARCHAR(5)) AS commune_id,
    CAST(parcelle_id AS TEXT) AS parcelle_id,
    CAST(adresse AS TEXT) AS adresse,
    CAST(ST_Multi(ST_Transform(geometry, 2154)) AS geometry(MultiPoint, 2154)) AS geometry
FROM {{ source('raw_data', 'imope_ban') }}
