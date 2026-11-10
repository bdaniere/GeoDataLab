{% macro audit_staging() %}
    {% set function_name = adapter.quote('audit_' ~ this.identifier) %}
    {% set function_schema = adapter.quote(this.schema) %}

    ALTER TABLE {{ this }}
        ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP,
        ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP,
        ALTER COLUMN updated_by SET DEFAULT CURRENT_USER;

    CREATE OR REPLACE FUNCTION {{ function_schema }}.{{ function_name }}()
    RETURNS trigger AS $$
    BEGIN
        NEW.updated_at = statement_timestamp();
        NEW.updated_by = CURRENT_USER;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS trg_staging_audit ON {{ this }};
    CREATE TRIGGER trg_staging_audit
        BEFORE UPDATE ON {{ this }}
        FOR EACH ROW
        WHEN (OLD.* IS DISTINCT FROM NEW.*)
        EXECUTE FUNCTION {{ function_schema }}.{{ function_name }}();
{% endmacro %}
