{{
    config(
        materialized='table',
        contract={'enforced': true},
        indexes=[
            {'columns': ['commune_id']},
            {'columns': ['ban_id']}
        ]
    )
}}

-- ban_id source parfois absent ou sans correspondance : il est mis à NULL
-- quand il n'existe pas dans int_ban, pour que la clé étrangère soit valide.
SELECT
    r.id,
    r.adresse,
    r.code_postal,
    r.commune,
    r.etage,
    r.npiece,
    r.surfhab,
    r.annee_construction,
    r.dpe,
    r.date_dpe,
    r.commune_id,
    CAST(b.id AS varchar(22)) AS ban_id,
    r.created_at,
    r.updated_at,
    r.updated_by
FROM {{ ref('stg_rpls') }} AS r
LEFT JOIN {{ ref('int_ban') }} AS b
    ON b.id = r.ban_id
