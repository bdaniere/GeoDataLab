CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS raw_data;
COMMENT ON SCHEMA raw_data IS
'Data imported without changes';

CREATE SCHEMA IF NOT EXISTS staging;
COMMENT ON SCHEMA staging IS
'Cleaned and normalized data';

CREATE SCHEMA IF NOT EXISTS staging;
COMMENT ON SCHEMA intermediate IS
'Intermediate transformations combining and enriching data from staging models, including spatial operations and business logic';
