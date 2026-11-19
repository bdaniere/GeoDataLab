{{
    config(
        materialized='table',
        contract={'enforced': true},
        indexes=[
            {'columns': ['iris_id']},
            {'columns': ['commune_id']}
        ]
    )
}}

SELECT
    s.id,
    s.operateur,
    s.code_eic,
    s.nom_commune,
    s.annee,
    s.filiere,
    s.code_iris,
    s.conso,
    s.created_at,
    s.updated_at,
    s.updated_by,
    i.id AS iris_id,
    c.id AS commune_id
FROM {{ ref('stg_consommation_electricite_iris_2025') }} AS s
LEFT JOIN {{ ref('int_iris') }} AS i ON i.id = s.code_iris
LEFT JOIN {{ ref('int_communes') }} AS c
    ON length(s.code_iris) >= 5 AND c.id = left(s.code_iris, 5)
