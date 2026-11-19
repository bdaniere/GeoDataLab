WITH source AS (
    SELECT id, fournisseur, annee, filiere, iris, adresse, commune, conso, pdl,
           commune_id, iris_id, ban_id, created_at, updated_at, updated_by
    FROM {{ ref('stg_electricite') }}
),
intermediate AS (
    SELECT id, fournisseur, annee, filiere, iris, adresse, commune, conso, pdl,
           source_commune_id, source_iris_id, source_ban_id,
           created_at, updated_at, updated_by
    FROM {{ ref('int_electricite') }}
),
differences AS (
    (SELECT * FROM source EXCEPT SELECT * FROM intermediate)
    UNION ALL
    (SELECT * FROM intermediate EXCEPT SELECT * FROM source)
)
SELECT id FROM differences
UNION ALL
SELECT e.id
FROM {{ ref('int_electricite') }} AS e
WHERE e.commune_id IS DISTINCT FROM (
    SELECT c.id FROM {{ ref('int_communes') }} AS c WHERE c.id = e.source_commune_id
)
   OR e.iris_id IS DISTINCT FROM (
    SELECT i.id FROM {{ ref('int_iris') }} AS i WHERE i.id = e.source_iris_id
)
   OR e.ban_id IS DISTINCT FROM (
    SELECT b.id FROM {{ ref('int_ban') }} AS b WHERE b.id = e.source_ban_id
)
