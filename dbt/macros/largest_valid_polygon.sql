{% macro largest_valid_polygon(geometry) %}
(
    SELECT part.geom
    FROM (
        SELECT
            ST_Transform(dumped.geom, 2154) AS geom,
            dumped.path
        FROM ST_Dump(
            ST_CollectionExtract(
                CASE
                    WHEN ST_IsValid({{ geometry }}) THEN {{ geometry }}
                    ELSE ST_MakeValid({{ geometry }})
                END,
                3
            )
        ) AS dumped
    ) AS part
    WHERE NOT ST_IsEmpty(part.geom)
    ORDER BY ST_Area(part.geom) DESC, part.path
    LIMIT 1
)
{% endmacro %}
