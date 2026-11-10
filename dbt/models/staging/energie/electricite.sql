{{
    config(
        materialized='table',
        contract={'enforced': true}
    )
}}

SELECT
    CAST(id AS TEXT) AS id,
    CAST(fournisseur AS TEXT) AS fournisseur,
    CAST(annee AS INTEGER) AS annee,
    CAST(filiere AS VARCHAR(1)) AS filiere,
    CAST(iris AS TEXT) AS iris,
    CAST(adresse AS TEXT) AS adresse,
    CAST(commune AS TEXT) AS commune,
    CAST(conso AS FLOAT) AS conso,
    CAST(pdl AS INTEGER) AS pdl,
    CAST(commune_id AS VARCHAR(5)) AS commune_id,
    CAST(iris_id AS VARCHAR(9)) AS iris_id,
    CAST(ban_id AS VARCHAR(22)) AS ban_id,
    CAST(NOW() AS TIMESTAMP) AS created_at,
    CAST(NOW() AS TIMESTAMP) AS updated_at,
    CAST(CURRENT_USER AS TEXT) AS updated_by
FROM {{ source('raw_data', 'imope_electricite') }}
