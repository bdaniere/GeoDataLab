WITH nb_iris_per_commune AS (
    SELECT
        c.code,
        c.nom,
        COUNT(i.id) AS nb_iris
    FROM raw_data.communes_france c
    JOIN raw_data.iris_france i
        ON i.INSEE_COM = c.code
    WHERE c.departement = '69'
    GROUP BY c.code, c.nom
)

SELECT
    COUNT(*) FILTER (WHERE nb_iris = 1) AS communes_un_iris,
    COUNT(*) AS total_communes,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE nb_iris = 1) / COUNT(*),
        2
    ) AS pourcentage_communes_un_iris
FROM nb_iris_per_commune;