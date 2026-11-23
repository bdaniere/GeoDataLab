{{ config(severity='warn') }}

SELECT d.numero_dpe, d.adresse_id
FROM {{ ref('int_dpe') }} AS d
WHERE d.adresse_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM {{ ref('int_dpe_adresses') }} AS lien
      WHERE lien.numero_dpe = d.numero_dpe
  )
