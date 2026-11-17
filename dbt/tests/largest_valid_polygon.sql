WITH fixtures AS (
    SELECT
        'valid' AS name,
        ST_GeomFromText('POLYGON((4 45, 4.01 45, 4.01 45.01, 4 45.01, 4 45))', 4326) AS geom
    UNION ALL
    SELECT
        'split',
        ST_GeomFromText('POLYGON((0 0, 4 4, 0 4, 2 0, 0 0))', 2154)
    UNION ALL
    SELECT
        'collapsed',
        ST_GeomFromText('POLYGON((0 0, 1 0, 2 0, 0 0))', 2154)
),

results AS (
    SELECT
        name,
        geom AS original_geom,
        {{ largest_valid_polygon('geom') }} AS geom
    FROM fixtures
)

SELECT name
FROM results
WHERE
    (name = 'collapsed' AND geom IS NOT NULL)
    OR (
        name <> 'collapsed'
        AND (
            geom IS NULL
            OR ST_GeometryType(geom) <> 'ST_Polygon'
            OR ST_SRID(geom) <> 2154
            OR ST_IsEmpty(geom)
            OR NOT ST_IsValid(geom)
        )
    )
    OR (name = 'valid' AND NOT ST_Equals(geom, ST_Transform(original_geom, 2154)))
    OR (
        name = 'split'
        AND (
            abs(ST_Area(geom) - 16.0 / 3.0) > 0.000001
            OR NOT ST_Contains(geom, ST_SetSRID(ST_Point(1, 3), 2154))
        )
    )
