{{
    config(
        materialized='table',
        contract={'enforced': true},
        indexes=[
            {'columns': ['iris_id']},
            {'columns': ['ban_id']}
        ]
    )
}}

SELECT
    c.id,
    c.fournisseur,
    c.annee,
    c.filiere,
    c.iris,
    c.conso,
    c.pdl,
    c.iris_id AS source_iris_id,
    c.ban_id AS source_ban_id,
    CAST(i.id AS varchar(9)) AS iris_id,
    CAST(b.id AS varchar(18)) AS ban_id,
    c.created_at,
    c.updated_at,
    c.updated_by
FROM {{ ref('stg_chaleur_urbaine') }} AS c
LEFT JOIN {{ ref('int_iris') }} AS i ON i.id = c.iris_id
LEFT JOIN {{ ref('int_ban') }} AS b ON b.id = c.ban_id
