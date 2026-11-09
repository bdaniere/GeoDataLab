{{
    config(
        materialized='table',
        contract={'enforced': true}
    )
}}

SELECT
    gen_random_uuid() AS id,
    CAST(id AS VARCHAR(5)) AS id_source,
    CAST(operateur AS TEXT) AS operateur,
    CAST(annee AS BIGINT) AS annee,
    CAST(filiere AS VARCHAR(1)) AS filiere,
    CAST(iris AS VARCHAR(9)) AS code_iris,
    CAST(conso AS TEXT) AS conso,
    CAST(NOW() AS TIMESTAMP) AS created_at,
    CAST(NOW() AS TIMESTAMP) AS updated_at,
    CAST(CURRENT_USER AS TEXT) AS updated_by
FROM {{ source('raw_data', 'consommation_froid_chaud_iris_2025') }}