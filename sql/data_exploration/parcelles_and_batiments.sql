-- nb batiment / surface_batie / surface_parcelle par parcelles
SELECT
    p.id,
    p.commune,
    COUNT(b.id) AS nb_batiments,
    ST_Area(p.geometry) AS surface_parcelle,
    COALESCE(SUM(ST_Area(b.geometry)), 0) AS surface_batie
FROM raw_data.parcelles_69 p
LEFT JOIN raw_data.batiments_69 b
    ON ST_COVERS(p.geometry, b.geometry)
GROUP BY
    p.id,
    p.commune,
    p.geometry
ORDER BY
	nb_batiments DESC,
	surface_batie DESC,
    surface_parcelle DESC
;
    