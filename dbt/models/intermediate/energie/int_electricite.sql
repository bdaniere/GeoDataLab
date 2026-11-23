{{
    config(
        materialized='table',
        contract={'enforced': true},
        indexes=[
            {'columns': ['commune_id']},
            {'columns': ['iris_id']},
            {'columns': ['ban_id']}
        ]
    )
}}

SELECT
    e.id,
    e.fournisseur,
    e.annee,
    e.filiere,
    e.iris,
    e.adresse,
    e.commune,
    e.conso,
    e.pdl,
    e.commune_id AS source_commune_id,
    e.iris_id AS source_iris_id,
    e.ban_id AS source_ban_id,
    CAST(c.id AS varchar(5)) AS commune_id,
    CAST(i.id AS varchar(9)) AS iris_id,
    CAST(b.id AS varchar(22)) AS ban_id,
    e.created_at,
    e.updated_at,
    e.updated_by
FROM {{ ref('stg_electricite') }} AS e
LEFT JOIN {{ ref('int_communes') }} AS c ON c.id = e.commune_id
LEFT JOIN {{ ref('int_iris') }} AS i ON i.id = e.iris_id
LEFT JOIN {{ ref('int_ban') }} AS b ON b.id = e.ban_id
