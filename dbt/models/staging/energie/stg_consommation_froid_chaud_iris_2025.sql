{{
    config(
        materialized='table',
        contract={'enforced': true}
    )
}}

SELECT
    gen_random_uuid() AS id,
    CAST("ID" AS VARCHAR(5)) AS id_source,
    CAST("OPERATEUR" AS TEXT) AS operateur,
    CAST("ANNEE" AS BIGINT) AS annee,
    CAST("FILIERE" AS VARCHAR(1)) AS filiere,
    CAST(LPAD(CAST("IRIS" AS TEXT), 9, '0') AS VARCHAR(9)) AS code_iris,
    CAST("CONSO" AS TEXT) AS conso,
    CAST(NOW() AS TIMESTAMP) AS created_at,
    CAST(NOW() AS TIMESTAMP) AS updated_at,
    CAST(CURRENT_USER AS TEXT) AS updated_by
FROM {{ source('raw_data', 'consommation_froid_chaud_iris_2025') }}