WITH source AS (
    SELECT id, id_source, operateur, annee, filiere, code_iris, conso,
           created_at, updated_at, updated_by
    FROM {{ ref('stg_consommation_froid_chaud_iris_2025') }}
),
intermediate AS (
    SELECT id, id_source, operateur, annee, filiere, code_iris, conso,
           created_at, updated_at, updated_by
    FROM {{ ref('int_consommation_froid_chaud_iris_2025') }}
),
differences AS (
    (SELECT * FROM source EXCEPT SELECT * FROM intermediate)
    UNION ALL
    (SELECT * FROM intermediate EXCEPT SELECT * FROM source)
)
SELECT id FROM differences
UNION ALL
SELECT s.id
FROM {{ ref('int_consommation_froid_chaud_iris_2025') }} AS s
WHERE s.iris_id IS DISTINCT FROM (
    SELECT i.id FROM {{ ref('int_iris') }} AS i WHERE i.id = s.code_iris
)
   OR s.commune_id IS DISTINCT FROM (
    SELECT c.id FROM {{ ref('int_communes') }} AS c
    WHERE length(s.code_iris) >= 5 AND c.id = left(s.code_iris, 5)
)
