SELECT id
FROM {schema_name}.{table_name}
WHERE NOT ST_SRID({geometry_column}) = '2154'