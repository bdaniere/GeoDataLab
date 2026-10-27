-- Sub request with CTE 
WITH iris_par_commune AS (
	SELECT 
		INSEE_COM AS commune,
		COUNT(*) AS nb_iris
	FROM raw_data.iris_france
	GROUP BY INSEE_COM
), 
parcelles_par_commune AS (
	SELECT 
		commune,
		COUNT(*) as nb_parcelles
	FROM raw_data.parcelles_69
	GROUP BY commune
),
batiments_par_commune AS (
	SELECT 
		commune,
		COUNT(*) as nb_batiments
	FROM raw_data.batiments_69
	GROUP BY commune
)

-- count iris / parcelles / batiments per communes
SELECT
    c.code,
    c.nom,
    COALESCE(i.nb_iris, 0) AS nb_iris,
    COALESCE(p.nb_parcelles, 0) AS nb_parcelles,
    COALESCE(b.nb_batiments, 0) AS nb_batiments
FROM raw_data.communes_france c
LEFT JOIN iris_par_commune i
    ON i.commune = c.code
LEFT JOIN parcelles_par_commune p
    ON p.commune = c.code
LEFT JOIN batiments_par_commune b
    ON b.commune = c.code
WHERE c.departement = '69'
ORDER BY
    nb_iris DESC,
    nb_parcelles DESC;



	

