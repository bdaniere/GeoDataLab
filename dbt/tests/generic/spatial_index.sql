{% test spatial_index(model, column_name) %}

SELECT {{ dbt.string_literal(column_name) }} AS missing_spatial_index
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_index AS i
    JOIN pg_class AS idx ON idx.oid = i.indexrelid
    JOIN pg_am AS am ON am.oid = idx.relam
    JOIN pg_attribute AS a ON a.attrelid = i.indrelid AND a.attnum = i.indkey[0]
    WHERE i.indrelid = '{{ model }}'::regclass
      AND a.attname = {{ dbt.string_literal(column_name) }}
      AND am.amname = 'gist'
      AND i.indisvalid
      AND i.indisready
      AND i.indpred IS NULL
)

{% endtest %}
