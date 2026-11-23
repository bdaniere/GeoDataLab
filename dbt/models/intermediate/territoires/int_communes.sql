{{ config(indexes=[{'columns': ['geom'], 'type': 'gist'}]) }}

SELECT * FROM {{ ref('stg_communes') }}
