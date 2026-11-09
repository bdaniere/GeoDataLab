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
    CAST(conso AS FLOAT) AS conso,
    CAST(pdl AS FLOAT) AS pdl,
    CAST(iris_id AS VARCHAR(9)) AS iris_id,
    CAST(ban_id AS VARCHAR(18)) AS ban_id
FROM {{ source('raw_data', 'imope_chaleur_urbaine') }}
