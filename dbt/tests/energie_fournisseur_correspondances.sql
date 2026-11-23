WITH fournisseurs_manquants_ou_modifies AS (
    (SELECT * FROM {{ ref('stg_energie_fournisseur') }}
     EXCEPT
     SELECT * FROM {{ ref('int_energie_fournisseur') }})
    UNION ALL
    (SELECT * FROM {{ ref('int_energie_fournisseur') }}
     EXCEPT
     SELECT * FROM {{ ref('stg_energie_fournisseur') }})
),
liens_attendus AS (
    SELECT f.id AS energie_fournisseur_id, a.id AS adresse_id
    FROM {{ ref('int_energie_fournisseur') }} AS f
    JOIN {{ ref('int_adresses') }} AS a ON f.adresse_id = a.source_id
),
liens_incorrects AS (
    (SELECT * FROM liens_attendus
     EXCEPT
     SELECT * FROM {{ ref('int_energie_fournisseur_adresses') }})
    UNION ALL
    (SELECT * FROM {{ ref('int_energie_fournisseur_adresses') }}
     EXCEPT
     SELECT * FROM liens_attendus)
)
SELECT 'fournisseur manquant ou modifié' AS probleme
FROM fournisseurs_manquants_ou_modifies
UNION ALL
SELECT 'lien manquant ou incorrect' AS probleme
FROM liens_incorrects
