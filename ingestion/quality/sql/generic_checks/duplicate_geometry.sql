WITH duplicated_geometries AS (
    SELECT ST_AsEWKB({geometry_column}) AS geom_key
    FROM {schema_name}.{table_name}
    WHERE {geometry_column} IS NOT NULL
    GROUP BY ST_AsEWKB({geometry_column})
    HAVING COUNT(*) > 1
)
SELECT
    b.id
FROM {schema_name}.{table_name} AS b
JOIN duplicated_geometries AS d
    ON ST_AsEWKB(b.{geometry_column}) = d.geom_key
ORDER BY b.id
;