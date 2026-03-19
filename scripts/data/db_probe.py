"""
Quick Postgres data probe for Bank Advisor datasets.

- Loads environment variables from `envs/.env` without using `source` (skips bad lines).
- Runs a handful of sanity queries to check coverage and totals for key tables:
  * monthly_kpis (core datamart)
  * metricas_cartera_segmentada (tarjetas)
  * hip_cartera_vivienda_marginales (hipotecarios raw)

Usage:
    python scripts/data/db_probe.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Tuple

import polars as pl
import psycopg


def load_env(path: Path) -> Dict[str, str]:
    """
    Minimal .env loader that tolerates malformed lines.
    Skips comments/blank lines and any line without '='.
    """
    env: Dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            continue
        env[key] = value
    return env


def get_conn_args(env: Dict[str, str]) -> Tuple[str, int, str, str, str]:
    try:
        host = env["POSTGRES_HOST"]
        port = int(env["POSTGRES_PORT"])
        user = env["POSTGRES_USER"]
        password = env["POSTGRES_PASSWORD"]
        dbname = env["POSTGRES_DB"]
    except KeyError as exc:
        missing = [k for k in ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB") if k not in env]
        raise SystemExit(f"Missing required env keys: {missing}") from exc
    return host, port, user, password, dbname


def run_query(conn_args: Tuple[str, int, str, str, str], sql: str, label: str) -> None:
    host, port, user, password, dbname = conn_args
    print(f"\n[{label}]")
    try:
        with psycopg.connect(host=host, port=port, user=user, password=password, dbname=dbname) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                cols = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                df = pl.DataFrame(rows, schema=cols)
                print(df)
    except Exception as exc:  # noqa: BLE001 - we want to surface any connection/query error
        print(f"ERROR: {exc}")


def main() -> None:
    env_path = Path("envs/.env")
    if not env_path.exists():
        raise SystemExit("envs/.env not found")

    env = load_env(env_path)
    conn_args = get_conn_args(env)

    queries = [
        (
            "monthly_kpis coverage",
            """
            select count(*) as rows, min(fecha) as min_fecha, max(fecha) as max_fecha
            from monthly_kpis;
            """,
        ),
        (
            "cartera_vivienda_total by year (monthly_kpis)",
            """
            select date_part('year', fecha)::int as year,
                   count(*) as rows,
                   count(distinct banco_norm) as banks,
                   sum(cartera_vivienda_total) as saldo_total
            from monthly_kpis
            where cartera_vivienda_total is not null
            group by 1
            order by 1;
            """,
        ),
        (
            "metricas_cartera_segmentada tarjetas",
            """
            select substr(fecha_corte,1,4) as year,
                   count(*) as rows,
                   count(distinct institucion) as banks,
                   sum(cartera_total) as saldo_total
            from metricas_cartera_segmentada
            where lower(segmento_nombre) like '%tarjeta%'
            group by 1
            order by 1;
            """,
        ),
        (
            "hip_cartera_vivienda_marginales coverage",
            """
            select min(periodo)::text as min_periodo,
                   max(periodo)::text as max_periodo,
                   count(*) as rows,
                   count(distinct institucion) as banks
            from hip_cartera_vivienda_marginales;
            """,
        ),
        (
            "hipotecarios top bancos latest year",
            """
            with years as (
                select max(substr(periodo::text,1,4)) as y from hip_cartera_vivienda_marginales
            )
            select h.institucion,
                   sum(h.saldo_insoluto_al_final_periodo) as saldo_total
            from hip_cartera_vivienda_marginales h, years
            where substr(h.periodo::text,1,4) = years.y
            group by h.institucion
            order by saldo_total desc
            limit 5;
            """,
        ),
    ]

    for label, sql in queries:
        run_query(conn_args, sql, label)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
