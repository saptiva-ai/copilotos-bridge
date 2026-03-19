"""
Create an aggregated view for mortgage/housing portfolio and (optionally) backfill monthly_kpis.

- View: hip_cartera_vivienda_mensual
    Aggregates hip_cartera_vivienda_marginales by periodo (YYYYMM) and banco_norm,
    computing cartera_vivienda_total.
- Optional: backfill monthly_kpis.cartera_vivienda_total using the aggregated view.

Usage:
    python scripts/data/backfill_hip_cartera_vivienda.py
    python scripts/data/backfill_hip_cartera_vivienda.py --backfill-monthly-kpis
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict

import psycopg


def load_env(path: Path) -> Dict[str, str]:
    """Minimal .env loader that tolerates malformed lines."""
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


def connect(env: Dict[str, str]) -> psycopg.Connection:
    required = ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]
    missing = [k for k in required if not env.get(k)]
    if missing:
        raise SystemExit(f"Missing required env keys: {missing}")

    return psycopg.connect(
        host=env["POSTGRES_HOST"],
        port=int(env["POSTGRES_PORT"]),
        user=env["POSTGRES_USER"],
        password=env["POSTGRES_PASSWORD"],
        dbname=env["POSTGRES_DB"],
    )


def create_view(conn: psycopg.Connection) -> None:
    sql = """
    CREATE OR REPLACE VIEW hip_cartera_vivienda_mensual AS
    SELECT
        to_date(periodo::text || '01', 'YYYYMMDD') AS fecha,
        upper(institucion) AS banco_norm,
        sum(saldo_insoluto_al_final_periodo) AS cartera_vivienda_total
    FROM hip_cartera_vivienda_marginales
    GROUP BY 1, 2;
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        conn.commit()
    print("✓ View hip_cartera_vivienda_mensual created/refreshed.")


def backfill_monthly_kpis(conn: psycopg.Connection) -> None:
    """
    Upsert cartera_vivienda_total into monthly_kpis from the aggregated view.
    - Tries ON CONFLICT if a unique constraint/index exists on (fecha, banco_norm).
    - If not, falls back to delete+insert to avoid errors.
    """
    insert_sql = """
    INSERT INTO monthly_kpis (fecha, banco_norm, cartera_vivienda_total)
    SELECT fecha, banco_norm, cartera_vivienda_total
    FROM hip_cartera_vivienda_mensual
    ON CONFLICT (fecha, banco_norm)
    DO UPDATE SET cartera_vivienda_total = EXCLUDED.cartera_vivienda_total;
    """

    delete_sql = """
    DELETE FROM monthly_kpis m
    USING hip_cartera_vivienda_mensual h
    WHERE m.fecha = h.fecha AND m.banco_norm = h.banco_norm;
    """

    fallback_insert_sql = """
    INSERT INTO monthly_kpis (fecha, banco_norm, cartera_vivienda_total)
    SELECT fecha, banco_norm, cartera_vivienda_total
    FROM hip_cartera_vivienda_mensual;
    """

    with conn.cursor() as cur:
        try:
            cur.execute(insert_sql)
            conn.commit()
            print("✓ monthly_kpis upserted via ON CONFLICT.")
            return
        except psycopg.Error as exc:
            conn.rollback()
            print(f"⚠ ON CONFLICT failed ({exc.__class__.__name__}: {exc}). Falling back to delete+insert.")

        # Fallback path: delete matching rows then insert fresh values
        cur.execute(delete_sql)
        deleted = cur.rowcount
        cur.execute(fallback_insert_sql)
        inserted = cur.rowcount
        conn.commit()
        print(f"✓ monthly_kpis backfilled via delete+insert (deleted={deleted}, inserted={inserted}).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create hip_cartera_vivienda_mensual view and optionally backfill monthly_kpis.")
    parser.add_argument(
        "--backfill-monthly-kpis",
        action="store_true",
        help="Upsert cartera_vivienda_total into monthly_kpis from the aggregated view.",
    )
    args = parser.parse_args()

    env_path = Path("envs/.env")
    if not env_path.exists():
        raise SystemExit("envs/.env not found")

    env = load_env(env_path)
    conn = connect(env)

    try:
        create_view(conn)
        if args.backfill_monthly_kpis:
            backfill_monthly_kpis(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
