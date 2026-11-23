{{
    config(
        materialized='table',
        contract={'enforced': true},
        indexes=[
            {'columns': ['commune_id']},
            {'columns': ['adresse_id']}
        ]
    )
}}

SELECT
    id,
    adresse,
    annee,
    conso,
    consomean,
    adresse_id,
    commune_id,
    created_at,
    updated_at,
    updated_by
FROM {{ ref('stg_energie_fournisseur') }}
