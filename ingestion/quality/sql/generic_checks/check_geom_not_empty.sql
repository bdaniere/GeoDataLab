SELECT *
FROM {schema_name}.{table_name}
WHERE ST_IsEmpty({geometry_column})
;
