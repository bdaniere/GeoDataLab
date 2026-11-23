{{
    config(
        materialized='table',
        contract={'enforced': true}
    )
}}

SELECT
    gen_random_uuid() AS id,
    CAST("OPERATEUR" AS TEXT) AS operateur,
    CAST("CODE_EIC" AS VARCHAR(16)) AS code_eic,
    CAST("NOM_COMMUNE" AS TEXT) AS nom_commune,
    CAST("ANNEE" AS BIGINT) AS annee,
    CAST("FILIERE" AS TEXT) AS filiere,
    CAST("CODE_IRIS" AS VARCHAR(9)) AS code_iris,
    CAST("CONSO" AS TEXT) AS conso,
    CAST(NOW() AS TIMESTAMP) AS created_at,
    CAST(NOW() AS TIMESTAMP) AS updated_at,
    CAST(CURRENT_USER AS TEXT) AS updated_by
FROM {{ source('raw_data', 'consommation_electricite_iris_2025') }}