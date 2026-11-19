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
    g.id,
    g.fournisseur,
    g.annee,
    g.filiere,
    g.iris,
    g.adresse,
    g.commune,
    g.conso,
    g.pdl,
    g.commune_id AS source_commune_id,
    g.iris_id AS source_iris_id,
    g.ban_id AS source_ban_id,
    CAST(c.id AS varchar(5)) AS commune_id,
    CAST(i.id AS varchar(9)) AS iris_id,
    CAST(b.id AS varchar(22)) AS ban_id,
    g.created_at,
    g.updated_at,
    g.updated_by
FROM {{ ref('stg_gaz') }} AS g
LEFT JOIN {{ ref('int_communes') }} AS c ON c.id = g.commune_id
LEFT JOIN {{ ref('int_iris') }} AS i ON i.id = g.iris_id
LEFT JOIN {{ ref('int_ban') }} AS b ON b.id = g.ban_id
