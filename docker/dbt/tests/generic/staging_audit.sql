{% test staging_audit(model) %}

WITH relation AS (
    SELECT '{{ model }}'::regclass AS oid
),
columns AS (
    SELECT array_agg(a.attname::text ORDER BY a.attnum) AS names
    FROM pg_attribute a
    JOIN relation r ON r.oid = a.attrelid
    WHERE a.attnum > 0 AND NOT a.attisdropped
),
expected AS (
    SELECT CASE
        WHEN 'geom' = ANY(names) THEN ARRAY['created_at', 'updated_at', 'updated_by', 'geom']
        WHEN 'geometry' = ANY(names) THEN ARRAY['created_at', 'updated_at', 'updated_by', 'geometry']
        ELSE ARRAY['created_at', 'updated_at', 'updated_by']
    END AS names
    FROM columns
)
SELECT 'ordre des colonnes audit' AS probleme
FROM columns, expected
WHERE columns.names[cardinality(columns.names) - cardinality(expected.names) + 1:] IS DISTINCT FROM expected.names

UNION ALL

SELECT 'valeurs par defaut audit'
WHERE (
    SELECT count(*)
    FROM pg_attribute a
    JOIN relation r ON r.oid = a.attrelid
    JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
    WHERE (a.attname IN ('created_at', 'updated_at') AND pg_get_expr(d.adbin, d.adrelid) = 'CURRENT_TIMESTAMP')
       OR (a.attname = 'updated_by' AND pg_get_expr(d.adbin, d.adrelid) = 'CURRENT_USER')
) <> 3

UNION ALL

SELECT 'declencheur audit'
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_trigger t
    JOIN relation r ON r.oid = t.tgrelid
    JOIN pg_proc p ON p.oid = t.tgfoid
    WHERE t.tgname = 'trg_staging_audit'
      AND NOT t.tgisinternal
      AND t.tgenabled IN ('O', 'A')
      AND t.tgtype = 19
      AND p.proname = 'audit_' || {{ dbt.string_literal(model.identifier) }}
      AND pg_get_triggerdef(t.oid) ILIKE '%IS DISTINCT FROM%'
)

{% endtest %}
