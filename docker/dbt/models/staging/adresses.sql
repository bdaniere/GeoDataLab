{{
    config(
        materialized='table',
        contract={'enforced': true},
        post_hook=[
            "CREATE INDEX IF NOT EXISTS idx_adresses_geometry
             ON {{ this }} USING GIST (geometry)"
        ]
    )
}}

WITH source_data AS (
    SELECT
        id,
        adresse,
        commune,
        iris,
        nlogh,
        cp,
        altitude,
        bailleursoc,
        batihist,
        chauffage,
        consochauff,
        consochurb,
        consoelec,
        consoelecm,
        consogaz,
        consogazm,
        consotou,
        consotoum,
        consochurbm,
        diffprixpct,
        energie,
        mur,
        nbpdlelec,
        nbpdlgaz,
        nivtot,
        nlogsoc,
        pgaz,
        prix,
        surfacemurs,
        surfaceplanchersbas,
        surfaceplanchershauts,
        surfacetot,
        toit,
        typehab,
        typobati,
        zoneargile,
        zonehist,
        zoneinond,
        zoneqpv,
        zonezsp,
        pmr,
        commune_id,
        epci_id,
        iris_id,
        parcelle_id,
        geometry
    FROM {{ source('raw_data', 'imope_adresse') }}
),

filtered AS (
    SELECT *
    FROM source_data
    WHERE id IS NOT NULL
      AND geometry IS NOT NULL
      AND NOT ST_IsEmpty(geometry)
),

deduplicated AS (
    SELECT DISTINCT ON (id) *
    FROM filtered
    ORDER BY id
),

corrected AS (
    SELECT
        CAST(id AS text) AS id,
        CAST(adresse AS text) AS adresse,
        CAST(commune AS text) AS commune,
        CAST(iris AS text) AS iris,
        CAST(nlogh AS integer) AS nlogh,
        CAST(cp AS varchar(9)) AS cp,
        CAST(altitude AS integer) AS altitude,
        CASE
            WHEN bailleursoc = 1 THEN TRUE
            WHEN bailleursoc = 0 THEN FALSE
            ELSE NULL
        END AS bailleursoc,
        CASE
            WHEN batihist = 1 THEN TRUE
            WHEN batihist = 0 THEN FALSE
            ELSE NULL
        END AS batihist,
        CAST(chauffage AS varchar(10)) AS chauffage,
        CAST(consochauff AS integer) AS consochauff,
        CAST(consochurb AS integer) AS consochurb,
        CAST(consoelec AS integer) AS consoelec,
        CAST(consoelecm AS integer) AS consoelecm,
        CAST(consogaz AS integer) AS consogaz,
        CAST(consogazm AS integer) AS consogazm,
        CAST(consotou AS integer) AS consotou,
        CAST(consotoum AS integer) AS consotoum,
        CAST(consochurbm AS integer) AS consochurbm,
        CAST(diffprixpct AS integer) AS diffprixpct,
        CAST(energie AS varchar(16)) AS energie,
        CAST(mur AS varchar(20)) AS mur,
        CAST(nbpdlelec AS integer) AS nbpdlelec,
        CAST(nbpdlgaz AS integer) AS nbpdlgaz,
        CAST(nivtot AS integer) AS nivtot,
        CAST(nlogsoc AS integer) AS nlogsoc,
        CASE
            WHEN pgaz = 'oui' THEN TRUE
            WHEN pgaz = 'non' THEN FALSE
            ELSE NULL
        END AS pgaz,
        CAST(prix AS float) AS prix,
        CAST(surfacemurs AS float) AS surfacemurs,
        CAST(surfaceplanchersbas AS float) AS surfaceplanchersbas,
        CAST(surfaceplanchershauts AS float) AS surfaceplanchershauts,
        CAST(surfacetot AS float) AS surfacetot,
        CAST(toit AS varchar(25)) AS toit,
        CAST(typehab AS varchar(11)) AS typehab,
        CAST(typobati AS varchar(22)) AS typobati,
        CAST(zoneargile AS varchar(6)) AS zoneargile,
        CASE
            WHEN zonehist = 1 THEN TRUE
            WHEN zonehist = 0 THEN FALSE
            ELSE NULL
        END AS zonehist,
        CASE
            WHEN zoneinond = 'true' THEN TRUE
            WHEN zoneinond = 'false' THEN FALSE
            ELSE NULL
        END AS zoneinond,
        CASE
            WHEN zoneqpv = 1 THEN TRUE
            WHEN zoneqpv = 0 THEN FALSE
            ELSE NULL
        END AS zoneqpv,
        CASE
            WHEN zonezsp = 1 THEN TRUE
            WHEN zonezsp = 0 THEN FALSE
            ELSE NULL
        END AS zonezsp,
        CAST(pmr AS varchar(2)) AS pmr,
        CAST(commune_id AS varchar(5)) AS commune_id,
        CAST(epci_id AS varchar(9)) AS epci_id,
        CAST(iris_id AS varchar(9)) AS iris_id,
        CAST(parcelle_id AS varchar(14)) AS parcelle_id,
        CAST(
            ST_Transform(geometry, 2154)
            AS geometry(MultiPoint, 2154)
        ) AS geometry
    FROM deduplicated
)

SELECT
    id,
    adresse,
    commune,
    iris,
    nlogh,
    cp,
    altitude,
    bailleursoc,
    batihist,
    chauffage,
    consochauff,
    consochurb,
    consoelec,
    consoelecm,
    consogaz,
    consogazm,
    consotou,
    consotoum,
    consochurbm,
    diffprixpct,
    energie,
    mur,
    nbpdlelec,
    nbpdlgaz,
    nivtot,
    nlogsoc,
    pgaz,
    prix,
    surfacemurs,
    surfaceplanchersbas,
    surfaceplanchershauts,
    surfacetot,
    toit,
    typehab,
    typobati,
    zoneargile,
    zonehist,
    zoneinond,
    zoneqpv,
    zonezsp,
    pmr,
    commune_id,
    epci_id,
    iris_id,
    parcelle_id,
    geometry
FROM corrected
