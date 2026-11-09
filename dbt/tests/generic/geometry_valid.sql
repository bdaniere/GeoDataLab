{% test geometry_valid(model, column_name) %}

SELECT *
FROM {{ model }}
WHERE {{ column_name }} IS NULL
   OR ST_IsEmpty({{ column_name }})
   OR NOT ST_IsValid({{ column_name }})

{% endtest %}