{{
    config(
        materialized='table',
        contract={'enforced': true}
    )
}}

SELECT
    CAST(id AS VARCHAR(36)) AS id,
    CAST(adresse AS TEXT) AS adresse,
    CAST(cp AS TEXT) AS code_postal,
    CAST(commune AS TEXT) AS commune,
    CAST(etage AS TEXT) AS etage,
    CAST(npiece AS INTEGER) AS npiece,
    CAST(surfhab AS INTEGER) AS surfhab,
    CAST(annee_construction AS INTEGER) AS annee_construction,
    CAST(dpe AS VARCHAR(1)) AS dpe,
    CAST((datedpe || '-01')::DATE AS DATE) AS date_dpe,
    CAST(commune_id AS VARCHAR(5)) AS commune_id,
    CAST(ban_id AS VARCHAR(22)) AS ban_id
FROM {{ source('raw_data', 'imope_rpls') }}
