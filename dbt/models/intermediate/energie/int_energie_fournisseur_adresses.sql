{{
    config(
        materialized='table',
        contract={'enforced': true},
        indexes=[{'columns': ['adresse_id']}]
    )
}}

SELECT
    fournisseur.id AS energie_fournisseur_id,
    adresse.id AS adresse_id
FROM {{ ref('int_energie_fournisseur') }} AS fournisseur
JOIN {{ ref('int_adresses') }} AS adresse
    ON fournisseur.adresse_id = adresse.source_id
