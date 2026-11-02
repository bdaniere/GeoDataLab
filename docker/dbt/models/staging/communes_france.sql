{{
    config(
        materialized='table'
    )
}}

WITH source_data AS (

    SELECT
        code,
        geometry
    FROM {{ source('raw_data', 'communes_france') }}

),

corrected AS (

    SELECT
        code,

        CASE
            WHEN geometry IS NULL THEN NULL

            WHEN ST_IsValid(geometry) THEN geometry

            ELSE ST_CollectionExtract(
                ST_MakeValid(geometry),
                3
            )
        END AS geometry

    FROM source_data

)

SELECT
    code,
    geometry
FROM corrected