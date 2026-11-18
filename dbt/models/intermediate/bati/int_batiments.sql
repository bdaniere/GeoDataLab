{{
    config(
        materialized='table',
        contract={'enforced': true},
        indexes=[
            {'columns': ['geom'], 'type': 'gist'},
            {'columns': ['commune_id']},
            {'columns': ['iris_id']},
            {'columns': ['parcelle_id']}
        ]
    )
}}

-- Le point sur la surface est calculé une seule fois par bâtiment.
WITH bat AS (
    SELECT
        b.id,
        b.type,
        b.nom,
        b.created_at,
        b.updated_at,
        b.updated_by,
        b.geom,
        ST_PointOnSurface(b.geom) AS pt
    FROM {{ ref('stg_batiments') }} AS b
)

-- LEFT JOIN LATERAL ... LIMIT 1 : un bâtiment reste une seule ligne même si
-- plusieurs polygones le touchent (limite commune), et il n'est pas perdu
-- s'il n'est dans aucune commune / IRIS / parcelle (clé étrangère NULL).
SELECT
    bat.id,
    bat.type,
    bat.nom,
    bat.created_at,
    bat.updated_at,
    bat.updated_by,
    bat.geom,
    CAST(com.id AS varchar(9)) AS commune_id,
    CAST(iris.id AS varchar(9)) AS iris_id,
    CAST(parc.id AS text) AS parcelle_id
FROM bat
LEFT JOIN LATERAL (
    SELECT c.id
    FROM {{ ref('stg_communes') }} AS c
    WHERE ST_Within(bat.pt, c.geom)
    ORDER BY c.id
    LIMIT 1
) AS com ON TRUE
LEFT JOIN LATERAL (
    SELECT i.id
    FROM {{ ref('stg_iris') }} AS i
    WHERE ST_Within(bat.pt, i.geom)
    ORDER BY i.id
    LIMIT 1
) AS iris ON TRUE
LEFT JOIN LATERAL (
    SELECT p.id
    FROM {{ ref('stg_parcelles') }} AS p
    WHERE ST_Within(bat.pt, p.geom)
    ORDER BY p.id
    LIMIT 1
) AS parc ON TRUE
