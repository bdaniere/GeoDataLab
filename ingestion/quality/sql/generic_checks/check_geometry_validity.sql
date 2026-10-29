SELECT
    b.id,
    v.reason AS invalid_reason,
    v.location AS error_location
FROM {schema_name}.{table_name} AS b
CROSS JOIN LATERAL ST_IsValidDetail(b.{geometry_column}) AS v
WHERE b.{geometry_column} IS NOT NULL
  AND NOT v.valid;