SELECT {id_column} AS id
FROM {schema_name}.{table_name}
WHERE ST_IsEmpty({geometry_column})
;
