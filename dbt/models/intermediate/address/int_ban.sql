{{
    config(
        materialized='table',
        contract={'enforced': true},
        indexes=[
            {'columns': ['geom'], 'type': 'gist'},
            {'columns': ['parcelle_id']}
        ]
    )
}}

WITH source AS (
    SELECT
        b.id,
        b.id_fantoir,
        b.numero,
        b.rep,
        b.nom_voie,
        b.code_postal,
        b.commune,
        b.commune_id,
        b.parcelle_id,
        b.adresse,
        b.created_at,
        b.updated_at,
        b.updated_by,
        b.geom
    FROM {{ ref('stg_ban') }} AS b
),

flagged AS (
    SELECT
        d.*,
        EXISTS (
            SELECT 1
            FROM {{ ref('stg_parcelles') }} AS p
            WHERE p.id = d.parcelle_id
        ) AS parcelle_valide
    FROM source AS d
),

valid_addresses AS (
    SELECT
        id,
        id_fantoir,
        numero,
        rep,
        nom_voie,
        code_postal,
        commune,
        commune_id,
        parcelle_id,
        adresse,
        created_at,
        updated_at,
        updated_by,
        geom
    FROM flagged
    WHERE parcelle_valide
),

invalid_addresses AS (
    SELECT *
    FROM flagged
    WHERE NOT parcelle_valide
),

corrected_addresses AS (
    SELECT
        d.id,
        d.id_fantoir,
        d.numero,
        d.rep,
        d.nom_voie,
        d.code_postal,
        d.commune,
        d.commune_id,
        n.id AS parcelle_id,
        d.adresse,
        d.created_at,
        d.updated_at,
        d.updated_by,
        d.geom
    FROM invalid_addresses AS d
    LEFT JOIN LATERAL (
        SELECT p.id
        FROM {{ ref('stg_parcelles') }} AS p
        WHERE ST_DWithin(d.geom, p.geom, 50)
        ORDER BY d.geom <-> p.geom
        LIMIT 1
    ) AS n ON TRUE
)

SELECT * FROM valid_addresses

UNION ALL

SELECT * FROM corrected_addresses