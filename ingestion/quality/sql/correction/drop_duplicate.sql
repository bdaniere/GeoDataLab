WITH doublons AS (
    SELECT
        {id_column},
        {geometry_column},
        ROW_NUMBER() OVER (
            PARTITION BY {geometry_column}
            ORDER BY {id_column}
        ) AS numero
    FROM {schema_name}.{table_name}
)

-- Pour vérifier les doublons avant suppression
-- SELECT *
-- FROM doublons
-- WHERE numero > 1;

DELETE FROM {schema_name}.{table_name}
WHERE {id_column} IN (
    SELECT {id_column}  
    FROM doublons
    WHERE numero > 1
);