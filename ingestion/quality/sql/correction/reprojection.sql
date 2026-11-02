ALTER TABLE {schema_name}.{table_name} 
ALTER COLUMN {geometry_column} TYPE geometry({expected_type}, {expected_srid})
USING ST_Transform({geometry_column}, {expected_srid});