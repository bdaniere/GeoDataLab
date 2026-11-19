WITH source AS (
    SELECT id, fournisseur, annee, filiere, iris, conso, pdl,
           iris_id, ban_id, created_at, updated_at, updated_by
    FROM {{ ref('stg_chaleur_urbaine') }}
),
intermediate AS (
    SELECT id, fournisseur, annee, filiere, iris, conso, pdl,
           source_iris_id, source_ban_id, created_at, updated_at, updated_by
    FROM {{ ref('int_chaleur_urbaine') }}
),
differences AS (
    (SELECT * FROM source EXCEPT SELECT * FROM intermediate)
    UNION ALL
    (SELECT * FROM intermediate EXCEPT SELECT * FROM source)
)
SELECT id FROM differences
UNION ALL
SELECT c.id
FROM {{ ref('int_chaleur_urbaine') }} AS c
WHERE c.iris_id IS DISTINCT FROM (
    SELECT i.id FROM {{ ref('int_iris') }} AS i WHERE i.id = c.source_iris_id
)
   OR c.ban_id IS DISTINCT FROM (
    SELECT b.id FROM {{ ref('int_ban') }} AS b WHERE b.id = c.source_ban_id
)
