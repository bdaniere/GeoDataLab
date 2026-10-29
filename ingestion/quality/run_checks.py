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

RESULT_COLUMNS = [
    "schema_name",
    "table_name",
    "check",
    "status",
    "nb_rows",
    "error",
]


def load_plan(plan_path: Path = DEFAULT_PLAN) -> list[dict]:
    with open(plan_path, encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("tables", [])


def render_sql(check: str, table: dict) -> str:
    """Load the check SQL and replace the {placeholders} with the table's values."""
    sql = (SQL_DIR / f"{check}.sql").read_text(encoding="utf-8")
    for key, value in table.items():
        if not isinstance(value, (list, dict)):
            sql = sql.replace("{" + key + "}", str(value))
    return sql.strip().rstrip(";")


def run_checks(
    plan_path: Path = DEFAULT_PLAN, connection_string: str | None = None
) -> pd.DataFrame:
    """
    Run every check of every table; one result row per (table, check).
    nb_rows is the number of offending rows returned by the check query.
    """
    engine = create_engine(connection_string or default_connection_string())
    results = []

    with engine.connect() as conn:
        for table in load_plan(plan_path):
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
                    nb_rows = len(conn.execute(text(sql)).fetchall())
                    row["nb_rows"] = nb_rows
                    row["status"] = "OK" if nb_rows == 0 else "KO"

                except Exception as exc:
                    conn.rollback()
                    logger.exception("Check %s failed", check)
                    row["status"] = "ERROR"
                    row["error"] = str(exc)
                results.append(row)

    return pd.DataFrame(results, columns=RESULT_COLUMNS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df_results = run_checks()
    print(df_results.to_string(index=False))
