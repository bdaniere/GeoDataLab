WITH dpe_manquants_ou_modifies AS (
    (SELECT * FROM {{ ref('stg_dpe') }}
     EXCEPT
     SELECT * FROM {{ ref('int_dpe') }})
    UNION ALL
    (SELECT * FROM {{ ref('int_dpe') }}
     EXCEPT
     SELECT * FROM {{ ref('stg_dpe') }})
),
liens_attendus AS (
    SELECT d.numero_dpe, a.id AS adresse_id
    FROM {{ ref('int_dpe') }} AS d
    JOIN {{ ref('int_adresses') }} AS a ON d.adresse_id = a.source_id
),
liens_incorrects AS (
    (SELECT * FROM liens_attendus
     EXCEPT
     SELECT * FROM {{ ref('int_dpe_adresses') }})
    UNION ALL
    (SELECT * FROM {{ ref('int_dpe_adresses') }}
     EXCEPT
     SELECT * FROM liens_attendus)
)
SELECT 'DPE manquant ou modifié' AS probleme
FROM dpe_manquants_ou_modifies
UNION ALL
SELECT 'lien manquant ou incorrect' AS probleme
FROM liens_incorrects
