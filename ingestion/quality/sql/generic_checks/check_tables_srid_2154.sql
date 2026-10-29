SELECT *
FROM raw_data.batiments
WHERE NOT ST_SRID(geometry) = '2154'
