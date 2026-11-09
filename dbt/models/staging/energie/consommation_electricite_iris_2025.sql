{{
    config(
        materialized='table',
        contract={'enforced': true}
    )
}}

SELECT
    gen_random_uuid() AS id,
    CAST(operateur AS TEXT) AS operateur,
    CAST(code_eic AS VARCHAR(16)) AS code_eic,
    CAST(nom_commune AS TEXT) AS nom_commune,
    CAST(annee AS BIGINT) AS annee,
    CAST(filiere AS TEXT) AS filiere,
    CAST(code_iris AS VARCHAR(9)) AS code_iris,
    CAST(conso AS TEXT) AS conso,
    CAST(NOW() AS TIMESTAMP) AS created_at,
    CAST(NOW() AS TIMESTAMP) AS updated_at,
    CAST(CURRENT_USER AS TEXT) AS updated_by
FROM {{ source('raw_data', 'consommation_electricite_iris_2025') }}