{{
    config(
        materialized='table',
        contract={'enforced': true},
        indexes=[{'columns': ['adresse_id']}]
    )
}}

SELECT
    numero_dpe,
    fraisannuelsenergie,
    ges,
    dpe,
    date_dpe,
    nges,
    adresse_id,
    created_at,
    updated_at,
    updated_by
FROM {{ ref('stg_dpe') }}
