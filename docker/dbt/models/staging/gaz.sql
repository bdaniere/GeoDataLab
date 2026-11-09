{{
    config(
        materialized='table',
        contract={'enforced': true}
    )
}}

SELECT
    CAST(id AS VARCHAR(36)) AS id,
    CAST(fournisseur AS TEXT) AS fournisseur,
    CAST(annee AS INTEGER) AS annee,
    CAST(filiere AS VARCHAR(1)) AS filiere,
    CAST(iris AS TEXT) AS iris,
    CAST(adresse AS TEXT) AS adresse,
    CAST(commune AS TEXT) AS commune,
    CAST(conso AS FLOAT) AS conso,
    CAST(pdl AS INTEGER) AS pdl,
    CAST(iris_id AS VARCHAR(9)) AS iris_id,
    CAST(ban_id AS VARCHAR(22)) AS ban_id
FROM {{ source('raw_data', 'imope_gaz') }}
