{{
    config(
        materialized='table',
        contract={'enforced': true}
    )
}}

SELECT
    gen_random_uuid() AS id,
    CAST(id AS TEXT) AS id_source,
    CAST(operateur AS TEXT) AS operateur,
    CAST(annee AS BIGINT) AS annee,
    CAST(filiere AS TEXT) AS filiere,
    CAST(iris AS TEXT) AS code_iris,
    CAST(conso AS TEXT) AS conso
FROM {{ source('raw_data', 'consommation_froid_chaud_iris_2025') }}