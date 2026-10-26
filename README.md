# GeoDataLab
Laboratoire de data engineering et d'analyse géospatiale des territoires français

## Présentation

GeoDataLab est un projet personnel et pédagogique visant à explorer les technologies du data engineering et de la géomatique à travers l'intégration, le traitement et la visualisation de données territoriales françaises.

L'objectif est de construire progressivement une plateforme capable de collecter des données issues de sources publiques, de les stocker dans une base géographique, d'en contrôler la qualité, de les transformer et de produire des analyses territoriales.

Ce projet sert également de laboratoire pour expérimenter différentes technologies et comparer leurs usages dans un contexte concret.

## Objectifs

- Découvrir et mettre en pratique les outils du data engineering.
- Automatiser l'ingestion de données issues de sources hétérogènes.
- Expérimenter l'intégration de données géographiques et non géographiques.
- Concevoir une base de données PostgreSQL/PostGIS.
- Développer des traitements de données en Python et SQL.
- Mettre en place des contrôles de qualité et des tests automatisés.
- Découvrir l'orchestration de pipelines avec Apache Airflow.
- Explorer les outils de publication cartographique et de visualisation.
- Documenter les expérimentations, les difficultés rencontrées et les choix techniques.

## Sources de données envisagées

### Bâtiments et énergie

- IMOPE — Observatoire national des bâtiments.
- Diagnostics de performance énergétique (DPE) — ADEME.
- Données de consommation d'énergie par IRIS — SDES.
 
### Référentiels géographiques

- Cadastre.
- Limites communales.
- IRIS.
- Géoportail de l'Urbanisme (GPU).

### Données socio-économiques et équipements

- Base permanente des équipements (BPE) — INSEE.
- Filosofi — INSEE.
- Données relatives aux risques d'inondation.
- Données DFCI.

Cette liste est indicative et sera affinée en fonction de la disponibilité des données, de leurs licences, de leur qualité et des possibilités d'intégration.

## Architecture technique envisagée

### Infrastructure

- Docker Compose.
- PostgreSQL.
- PostGIS.

### Ingestion

- Python.
- Airbyte.

### Transformation et qualité

- Python.
- SQL.
- GeoPandas.
- Pytest.
- dbt, à explorer.

### Orchestration

- Apache Airflow.

### Visualisation

- GeoServer.
- OpenLayers ou une autre bibliothèque cartographique.
- Power BI.

### Technologies complémentaires

- Databricks et Spark, dans une phase exploratoire ultérieure.