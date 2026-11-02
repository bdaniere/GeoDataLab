SELECT {id_column} AS id
FROM {schema_name}.{table_name}
GROUP BY {id_column}
HAVING COUNT(*) > 1;