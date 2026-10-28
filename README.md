# GeoDataLab
Laboratoire de data engineering et d'analyse géospatiale des territoires français

## Présentation

GeoDataLab est un projet personnel et pédagogique visant à explorer les technologies du data engineering et de la géomatique à travers l'intégration, le traitement et la visualisation de données territoriales françaises.

L'objectif est de construire progressivement une plateforme capable de collecter des données issues de sources publiques, de les stocker dans une base géographique, d'en contrôler la qualité, de les transformer et de produire des analyses territoriales.

Ce projet sert également de laboratoire pour expérimenter différentes technologies et comparer leurs usages dans un contexte concret.

## Objectifs

- Découvrir et mettre en pratique les outils du data engineering.
- Automatiser l'ingestion de données issues de sources hétérogènes.
- Expérimenter l'intégration de données géographiques et non géographiques.
- Concevoir une base de données PostgreSQL/PostGIS.
- Développer des traitements de données en Python et SQL.
- Mettre en place des contrôles de qualité et des tests automatisés.
- Découvrir l'orchestration de pipelines avec Apache Airflow.
- Explorer les outils de publication cartographique et de visualisation.
- Documenter les expérimentations, les difficultés rencontrées et les choix techniques.

## Sources de données envisagées

### Bâtiments et énergie

- IMOPE — Observatoire national des bâtiments.
- Diagnostics de performance énergétique (DPE) — ADEME.
- Données de consommation d'énergie par IRIS — SDES.
 
### Référentiels géographiques

- Cadastre.
- Limites communales.
- IRIS.
- Géoportail de l'Urbanisme (GPU).

### Données socio-économiques et équipements

- Base permanente des équipements (BPE) — INSEE.
- Filosofi — INSEE.
- Données relatives aux risques d'inondation.
- Données DFCI.

Cette liste est indicative et sera affinée en fonction de la disponibilité des données, de leurs licences, de leur qualité et des possibilités d'intégration.

## Architecture technique envisagée

### Infrastructure

- Docker Compose.
- PostgreSQL.
- PostGIS.

### Ingestion

- Python.
- Airbyte.

### Transformation et qualité

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

### Technologies complémentaires

- Databricks et Spark, dans une phase exploratoire ultérieure.

## Feuille de route

### Étape 1 — Infrastructure et stockage

- [x] Mettre en place l'environnement Docker.
- [x] Déployer PostgreSQL et PostGIS.
- [x] Importer un premier jeu de données géographiques.
- [x] Réaliser les premières requêtes spatiales.

### Étape 2 — Découverte d'Airbyte

- [x] Installer Airbyte.
- [x] Configurer une première source et une destination.
- [x] Réaliser une synchronisation.
- [x] Comparer l'utilisation d'Airbyte et d'un script Python.
- [x] Developpement d'un outil python pour les données non geographique
- [x] Exclusion de Airbyte du projet

### Étape 3 — Qualité et transformations

- [x] Mettre en place des tests automatisés.
- [ ] Contrôler la qualité des données.
- [ ] Structurer les transformations SQL et Python.
- [ ] Évaluer l'intérêt de dbt.

### Étape 4 — Premier pipeline de données

- [ ] Sélectionner un périmètre géographique restreint.
- [ ] Intégrer des données territoriales et des données métier.
- [ ] Réaliser les premiers traitements.
- [ ] Produire des indicateurs simples.

### Étape 5 — Orchestration

- [ ] Découvrir Apache Airflow.
- [ ] Orchestrer plusieurs étapes du pipeline.
- [ ] Gérer les erreurs, les logs et les nouvelles tentatives.

### Étape 6 — Visualisation

- [ ] Publier des données géographiques.
- [ ] Construire une première interface cartographique.
- [ ] Produire un tableau de bord analytique.

### Étape 7 — Technologies avancées

- [ ] Étudier les architectures de traitement distribué.
- [ ] Explorer Spark et Databricks.
- [ ] Documenter les avantages et les limites des différentes approches.

## Principes du projet

- Privilégier des expérimentations concrètes et reproductibles.
- Documenter les choix techniques.
- Séparer les données brutes des données transformées.
- Ne pas versionner les gros fichiers de données dans Git.
- Contrôler la qualité des données avant leur exploitation.
- Introduire les technologies progressivement.
- Vérifier les licences et les conditions de réutilisation des sources.

## Tests

Les tests unitaires de l'ingestion se trouvent dans `ingestion/tests`. Ils utilisent des
jeux de données générés pendant les tests et simulent les téléchargements : ils ne
nécessitent ni accès réseau ni base PostgreSQL/PostGIS.

Avec Poetry, depuis le dossier `ingestion` :

```bash
poetry install --with dev
poetry run pytest
```

La suite est également exécutée automatiquement par GitHub Actions lors des push et des
pull requests.

## Statut

Projet en cours de définition. Les choix techniques et la feuille de route évolueront au fil des expérimentations.