{{ config(
    store_failures = true
) }}

SELECT *
FROM {{ source('raw_data', 'communes_france') }}
WHERE geometry IS NULL
   OR ST_IsEmpty(geometry)
   OR NOT ST_IsValid(geometry)