DO $$
DECLARE
    col_type text;
    col_srid integer;
BEGIN
    SELECT type, srid INTO col_type, col_srid
    FROM geometry_columns
    WHERE f_table_schema = '{schema_name}'
      AND f_table_name = '{table_name}'
      AND f_geometry_column = '{geometry_column}';

    IF col_type = 'POLYGON' AND EXISTS (
        SELECT 1
        FROM {schema_name}.{table_name}
        WHERE NOT ST_IsValid({geometry_column})
          AND ST_NumGeometries(ST_CollectionExtract(ST_MakeValid({geometry_column}), 3)) > 1
    ) THEN
        EXECUTE format(
            'ALTER TABLE {schema_name}.{table_name} ALTER COLUMN {geometry_column} TYPE geometry(MultiPolygon, %s) USING ST_Multi({geometry_column})',
            col_srid
        );
        col_type := 'MULTIPOLYGON';
    END IF;

    IF col_type = 'MULTIPOLYGON' THEN
        UPDATE {schema_name}.{table_name}
        SET {geometry_column} = ST_Multi(ST_CollectionExtract(ST_MakeValid({geometry_column}), 3))
        WHERE NOT ST_IsValid({geometry_column});
    ELSE
        UPDATE {schema_name}.{table_name}
        SET {geometry_column} = ST_GeometryN(ST_CollectionExtract(ST_MakeValid({geometry_column}), 3), 1)
        WHERE NOT ST_IsValid({geometry_column});
    END IF;
END $$;
