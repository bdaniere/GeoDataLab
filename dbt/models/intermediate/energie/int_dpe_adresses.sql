{{
    config(
        materialized='table',
        contract={'enforced': true},
        indexes=[{'columns': ['adresse_id']}]
    )
}}

SELECT
    dpe.numero_dpe,
    adresse.id AS adresse_id
FROM {{ ref('int_dpe') }} AS dpe
JOIN {{ ref('int_adresses') }} AS adresse
    ON dpe.adresse_id = adresse.source_id
