{{
    config(
        materialized='table',
        contract={'enforced': true},
        indexes=[
            {'columns': ['geom'], 'type': 'gist'},
            {'columns': ['source_id']},
            {'columns': ['parcelle_id']}
        ]
    )
}}

-- 1. Atomisation des MultiPoint : une ligne par point.
-- L'id est un UUID déterministe (source + rang du point) pour que le build soit reproductible.
WITH dumped AS (
    SELECT
        a.id AS source_id,
        d.path[1] AS point_rank,
        a.adresse,
        a.commune,
        a.iris,
        a.nlogh,
        a.cp,
        a.altitude,
        a.bailleursoc,
        a.batihist,
        a.chauffage,
        a.consochauff,
        a.consochurb,
        a.consoelec,
        a.consoelecm,
        a.consogaz,
        a.consogazm,
        a.consotou,
        a.consotoum,
        a.consochurbm,
        a.diffprixpct,
        a.energie,
        a.mur,
        a.nbpdlelec,
        a.nbpdlgaz,
        a.nivtot,
        a.nlogsoc,
        a.pgaz,
        a.prix,
        a.surfacemurs,
        a.surfaceplanchersbas,
        a.surfaceplanchershauts,
        a.surfacetot,
        a.toit,
        a.typehab,
        a.typobati,
        a.zoneargile,
        a.zonehist,
        a.zoneinond,
        a.zoneqpv,
        a.zonezsp,
        a.pmr,
        a.commune_id,
        a.epci_id,
        a.iris_id,
        a.parcelle_id,
        a.created_at,
        a.updated_at,
        a.updated_by,
        CAST(d.geom AS geometry(Point, 2154)) AS geom
    FROM {{ ref('stg_adresses') }} AS a
    CROSS JOIN LATERAL ST_Dump(a.geom) AS d
),

-- 2. Points dont le parcelle_id est manquant ou absent de la table des parcelles
invalid AS (
    SELECT d.source_id, d.point_rank, d.geom
    FROM dumped AS d
    WHERE NOT EXISTS (
        SELECT 1
        FROM {{ ref('int_parcelles') }} AS p
        WHERE p.id = d.parcelle_id
    )
),

-- 3. Rattachement par intersection spatiale
by_intersection AS (
    SELECT i.source_id, i.point_rank, p.id AS parcelle_id
    FROM invalid AS i
    CROSS JOIN LATERAL (
        SELECT p.id
        FROM {{ ref('int_parcelles') }} AS p
        WHERE ST_Intersects(i.geom, p.geom)
        ORDER BY p.id
        LIMIT 1
    ) AS p
),

-- 4. Rattachement au plus proche voisin (rayon max 50 m) pour les points restants.
-- Approche discutable (risque de faux rattachement), mais l'objectif du projet
-- est de pratiquer, pas nécessairement de fournir un résultat parfait.
by_nearest AS (
    SELECT i.source_id, i.point_rank, p.id AS parcelle_id
    FROM invalid AS i
    CROSS JOIN LATERAL (
        SELECT p.id
        FROM {{ ref('int_parcelles') }} AS p
        WHERE ST_DWithin(i.geom, p.geom, 50)
        ORDER BY i.geom <-> p.geom
        LIMIT 1
    ) AS p
    WHERE NOT EXISTS (
        SELECT 1
        FROM by_intersection AS bi
        WHERE bi.source_id = i.source_id
          AND bi.point_rank = i.point_rank
    )
)

SELECT
    CAST(md5(d.source_id || '-' || d.point_rank) AS uuid) AS id,
    d.source_id,
    d.adresse,
    d.commune,
    d.iris,
    d.nlogh,
    d.cp,
    d.altitude,
    d.bailleursoc,
    d.batihist,
    d.chauffage,
    d.consochauff,
    d.consochurb,
    d.consoelec,
    d.consoelecm,
    d.consogaz,
    d.consogazm,
    d.consotou,
    d.consotoum,
    d.consochurbm,
    d.diffprixpct,
    d.energie,
    d.mur,
    d.nbpdlelec,
    d.nbpdlgaz,
    d.nivtot,
    d.nlogsoc,
    d.pgaz,
    d.prix,
    d.surfacemurs,
    d.surfaceplanchersbas,
    d.surfaceplanchershauts,
    d.surfacetot,
    d.toit,
    d.typehab,
    d.typobati,
    d.zoneargile,
    d.zonehist,
    d.zoneinond,
    d.zoneqpv,
    d.zonezsp,
    d.pmr,
    d.commune_id,
    d.epci_id,
    d.iris_id,
    CAST(
        COALESCE(
            bi.parcelle_id,
            bn.parcelle_id,
            CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM {{ ref('int_parcelles') }} AS p
                    WHERE p.id = d.parcelle_id
                ) THEN d.parcelle_id
            END
        )
        AS varchar(14)
    ) AS parcelle_id,
    d.created_at,
    d.updated_at,
    d.updated_by,
    d.geom
FROM dumped AS d
LEFT JOIN by_intersection AS bi
    ON bi.source_id = d.source_id AND bi.point_rank = d.point_rank
LEFT JOIN by_nearest AS bn
    ON bn.source_id = d.source_id AND bn.point_rank = d.point_rank
