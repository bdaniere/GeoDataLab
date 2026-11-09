{{
    config(
        materialized='table',
        contract={'enforced': true},
    )
}}


WITH source_data AS (
    SELECT * FROM {{ source('raw_data', 'imope_adresse') }}
),

filtered AS (
    SELECT *
    FROM source_data
    WHERE numero_dpe IS NOT NULL
),

deduplicated AS (
    SELECT DISTINCT ON (numero_dpe) *
    FROM filtered
    ORDER BY
        numero_dpe DESC NULLS LAST
),

corrected AS (
    SELECT

        CAST(numero_dpe AS VARCHAR(13)) AS numero_dpe,
        CAST(fraisannuelsenergie AS FLOAT) AS fraisannuelsenergie,
        CAST(ges AS VARCHAR(1)) AS ges,
        CAST(dpe AS VARCHAR(1)) AS dpe,
        CAST(date_dpe AS DATE) AS date_dpe,
        CAST(nges AS INTEGER) AS nges,
        CAST(id AS TEXT) AS adresse_id,
        CAST(NOW() AS TIMESTAMP) AS created_at,
        CAST(NOW() AS TIMESTAMP) AS updated_at,
        CAST(CURRENT_USER AS TEXT) AS updated_by
    FROM deduplicated
)

SELECT *
FROM corrected
