"""Run the quality checks described in check_plan.yml and collect the results."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd
import yaml
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "extraction"))
from util import default_connection_string

logger = logging.getLogger(__name__)

QUALITY_DIR = Path(__file__).resolve().parent
DEFAULT_PLAN = QUALITY_DIR / "check_plan.yml"
SQL_DIR = QUALITY_DIR / "sql" / "generic_checks"

SQL_CORRECTION_DIR = QUALITY_DIR / "sql" / "correction"

# failed check -> correction script, applied in this order
CORRECTIONS = {
    "check_geometry_not_null": "drop_null_geometries",
    "check_geom_not_empty": "drop_empty_geometry",
    "check_geometry_validity": "fix_invalid_geometry",
    "check_tables_srid_2154": "fix_srid_2154",
}

RESULT_COLUMNS = [
    "schema_name",
    "table_name",
    "check",
    "status",
    "nb_rows",
    "error",
]

QUALITY_ERROR_COLUMNS = ["schema", "table", "check_name", "id"]


def load_plan(plan_path: Path = DEFAULT_PLAN) -> list[dict]:
    with open(plan_path, encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("tables", [])


def render_sql(check: str, table: dict, sql_dir: Path = SQL_DIR) -> str:
    """Load the SQL and replace the {placeholders} with the table's values."""
    sql = (sql_dir / f"{check}.sql").read_text(encoding="utf-8")
    for key, value in table.items():
        if not isinstance(value, (list, dict)):
            sql = sql.replace("{" + key + "}", str(value))
    return sql.strip().rstrip(";")


def _run_table_checks(conn, table: dict) -> tuple[list[dict], list[dict]]:
    """Run all checks of one table; return (result rows, offending ids)."""
    results = []
    quality_errors = []
    logger.info(
        f"Running checks for table {table.get('schema_name')}.{table.get('table_name')}"
    )
    for check in table.get("checks", []):
        row = {
            "schema_name": table.get("schema_name"),
            "table_name": table.get("table_name"),
            "check": check,
            "status": None,
            "nb_rows": None,
            "error": None,
        }
        try:
            sql = render_sql(check, table)
            rows = conn.execute(text(sql)).mappings().all()
            nb_rows = len(rows)
            row["nb_rows"] = nb_rows
            row["status"] = "OK" if nb_rows == 0 else "KO"
            quality_errors.extend(
                {
                    "schema": table["schema_name"],
                    "table": table["table_name"],
                    "check_name": check,
                    "id": result["id"],
                }
                for result in rows
            )
        except Exception as exc:
            conn.rollback()
            logger.exception("Check %s failed", check)
            row["status"] = "ERROR"
            row["error"] = str(exc)
        results.append(row)
    return results, quality_errors


def _apply_corrections(conn, table: dict, failed_checks: set[str]) -> bool:
    """Run the correction scripts mapped to the failed checks; True if any was applied."""
    applied = False
    for check, correction in CORRECTIONS.items():
        if check not in failed_checks:
            continue
        try:
            sql = render_sql(correction, table, SQL_CORRECTION_DIR)
            result = conn.execute(text(sql))
            conn.commit()
            applied = True
            logger.info(
                "Correction %s applied on %s.%s (%s rows affected)",
                correction,
                table.get("schema_name"),
                table.get("table_name"),
                result.rowcount,
            )
        except Exception:
            conn.rollback()
            logger.exception("Correction %s failed", correction)
    return applied


def run_checks(
    plan_path: Path = DEFAULT_PLAN,
    connection_string: str | None = None,
    apply_corrections: bool = False,
) -> pd.DataFrame:
    """
    Run every check of every table; one result row per (table, check).
    nb_rows is the number of offending rows returned by the check query.

    With apply_corrections, the corrections mapped in CORRECTIONS are run for the
    failed checks, then all checks are re-run on the corrected tables only; their
    new results replace the previous ones.
    """
    engine = create_engine(connection_string or default_connection_string())
    results = []
    quality_errors = []

    with engine.connect() as conn:
        for table in load_plan(plan_path):
            table_results, table_errors = _run_table_checks(conn, table)

            if apply_corrections:
                failed = {r["check"] for r in table_results if r["status"] == "KO"}
                if _apply_corrections(conn, table, failed):
                    table_results, table_errors = _run_table_checks(conn, table)

            results.extend(table_results)
            quality_errors.extend(table_errors)

    pd.DataFrame(quality_errors, columns=QUALITY_ERROR_COLUMNS).to_sql(
        name="quality_error",
        con=engine,
        schema="raw_data",
        if_exists="replace",
        index=False,
    )

    return pd.DataFrame(results, columns=RESULT_COLUMNS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df_results = run_checks(apply_corrections=True)
    print(df_results[df_results["status"] != "OK"].to_string(index=False))
