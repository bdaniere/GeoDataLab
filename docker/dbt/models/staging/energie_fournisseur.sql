{{
    config(
        materialized='table',
        contract={'enforced': true}
    )
}}

SELECT
    CAST(id AS TEXT) AS id,
    CAST(adresse AS TEXT) AS adresse,
    CAST(annee AS INTEGER) AS annee,
    CAST(conso AS FLOAT) AS conso,
    CAST(consomean AS FLOAT) AS consomean,
    CAST(adresse_id AS VARCHAR(26)) AS adresse_id,
    CAST(commune_id AS VARCHAR(5)) AS commune_id
FROM {{ source('raw_data', 'imope_energie_fournisseur') }}
