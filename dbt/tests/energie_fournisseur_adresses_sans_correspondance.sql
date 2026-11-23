{{ config(severity='warn') }}

SELECT f.id, f.adresse_id
FROM {{ ref('int_energie_fournisseur') }} AS f
WHERE f.adresse_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM {{ ref('int_energie_fournisseur_adresses') }} AS lien
      WHERE lien.energie_fournisseur_id = f.id
  )
