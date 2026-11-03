-- id : voir pour utiliser un uuid
-- type : varchar(2)
-- nom : text
-- commune : varchar(5)
-- created : TIMESTAMP
-- updated : TIMESTAMP avec contrain on update
-- GEOMETRY : MULTIPOLYGON 2154


{{
    config(
        materialized='table',
        contract={'enforced': true},
        post_hook=[
            "CREATE INDEX IF NOT EXISTS idx_batiments_geom
             ON {{ this }} USING GIST (geom)",

            "CREATE OR REPLACE FUNCTION update_updated_at()
             RETURNS TRIGGER AS $$
             BEGIN
                 NEW.updated_at = NOW();
                 RETURN NEW;
             END;
             $$ LANGUAGE plpgsql",

            "DROP TRIGGER IF EXISTS trg_batiments_updated_at ON {{ this }}",

            "CREATE TRIGGER trg_batiments_updated_at
             BEFORE UPDATE ON {{ this }}
             FOR EACH ROW
             EXECUTE FUNCTION update_updated_at()"
        ]
    )
}}


WITH source_data AS (
    SELECT * FROM {{ source('raw_data', 'batiments') }}
),

filtered AS (
    SELECT *
    FROM source_data
    WHERE geometry IS NOT NULL
      AND NOT ST_IsEmpty(geometry)
),

deduplicated AS (
    SELECT DISTINCT ON (geometry) *
    FROM filtered
    ORDER BY
        geometry,
        created DESC NULLS LAST
),

corrected AS (
    SELECT
        gen_random_uuid() AS id,
        CAST(type AS VARCHAR(2)) AS type,
        nom,
        CAST(commune AS VARCHAR(5)) AS commune,
        created,
        updated,
        CAST(
            ST_Transform(
                ST_Multi(
                    CASE
                        WHEN ST_IsValid(geometry) THEN geometry
                        ELSE ST_CollectionExtract(ST_MakeValid(geometry), 3)
                    END
                ),
                2154
            ) AS geometry(MULTIPOLYGON, 2154)
        ) AS geom

    FROM deduplicated
)

SELECT *
FROM corrected
