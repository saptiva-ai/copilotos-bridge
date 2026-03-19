# /// script
# requires-python = ">=3.11"
# dependencies = ["psycopg[binary]>=3.1"]
# ///
"""
Sync bank_dim_institucion: normalize names, set activo/inactivo, add comments.

Updates:
1. Normalize nombre_corto to match banco_norm canonical (no accents)
2. Set activo=false + fecha_baja for revoked/merged banks
3. Add nombre_completo (comments) for banks with history
4. Insert missing institutions from Instituciones.xlsx

Usage:
    DATABASE_URL='postgresql://...' uv run scripts/data/sync_dim_institucion.py --dry-run
    DATABASE_URL='postgresql://...' uv run scripts/data/sync_dim_institucion.py
"""
from __future__ import annotations

import argparse
import psycopg
import os
import sys
from datetime import date


# =============================================================================
# NAME NORMALIZATIONS: dim nombre_corto → canonical banco_norm
# =============================================================================
# These fix accent/case mismatches between dim table and KPI table.
NAME_FIXES = {
    "BANSÍ": "BANSI",
    "VE POR MÁS": "VE POR MAS",
    "BANCA MIFEL": "MIFEL",
}

# =============================================================================
# INACTIVE BANKS: code → (fecha_baja, comentario)
# =============================================================================
INACTIVE_BANKS = {
    "0000040131": (date(2020, 6, 30), "Licencia revocada por CNBV jun 2020. Banco Ahorro Famsa"),
    "0000040102": (date(2022, 12, 1), "Accendo Banco — licencia revocada dic 2022"),
    "0000040126": (date(2023, 6, 12), "Credit Suisse — adquirido por UBS jun 2023"),
    "0000040129": (date(2016, 1, 1), "Barclays México — operaciones transferidas ~2016"),
    "0000040037": (date(2018, 7, 1), "Interacciones — fusionado con Banorte jul 2018"),
    "0000040139": (date(2020, 1, 1), "BIAfirme — fusionado con Afirme ~2020"),
    "0000040147": (date(2024, 1, 1), "Bankaool — licencia revocada, en proceso de liquidación"),
    "0000040149": (date(2023, 6, 1), "Forjadores — licencia revocada jun 2023"),
}

# =============================================================================
# COMMENTS for active banks with notable history
# =============================================================================
BANK_COMMENTS = {
    "0000040002": "Citibanamex — en proceso de venta por Citigroup (anunciado 2022)",
    "0000040138": "Antes ABC Capital. Adquirido por Ualá (2024). Licencia bancaria argentina/mexicana",
    "0000040154": "Antes Finterra. Rebrandeo a Covalto ~2023",
    "0000040042": "Banca Mifel — banco comercial mediano. banco_norm canónico: MIFEL",
    "0000040128": "Antes Autofin, ahora opera como Kapital",
    "0000040151": "Dondé Banco — banco de empeño y préstamos personales",
    "0000040160": "Banco S3 — banco digital de reciente creación (~2024)",
    "0000040162": "KEB Hana México — subsidiaria de Hana Financial Group (Corea del Sur)",
    "0000040164": "BNP Paribas México — banca corporativa francesa",
    "0000040155": "ICBC — Industrial and Commercial Bank of China",
    "0000040157": "Shinhan — subsidiaria de Shinhan Financial Group (Corea del Sur)",
    "0000040159": "Bank of China — subsidiaria en México",
    "0000040158": "Mizuho Bank — banco japonés, banca corporativa",
    "0000040108": "MUFG Bank (antes Bank of Tokyo-Mitsubishi UFJ)",
    "0000040150": "Inmobiliario Mexicano — créditos hipotecarios",
    "0000040136": "Intercam Banco — banca patrimonial y servicios financieros",
    "0000040152": "Bancrea — banca empresarial y comercial",
    "0000040060": "Bansí — banca comercial. banco_norm canónico: BANSI (sin acento)",
    "0000040113": "Ve por Más (BX+) — banca comercial. banco_norm canónico: VE POR MAS",
}

# =============================================================================
# MISSING INSTITUTIONS to insert (from Instituciones.xlsx, not yet in dim)
# =============================================================================
# Only banks from XLSX that don't exist in dim at all.
# Format: (clave_cnbv, nombre_corto, tipo_institucion, activo, comentario)
MISSING_INSTITUTIONS = [
    ("0000040003", "SERFIN", "Banca Multiple", False, "Serfín — absorbido por Santander (~2001)"),
    ("0000040004", "ATLANTICO", "Banca Multiple", False, "Atlántico — desaparecido ~2002"),
    ("0000040007", "CITIBANK", "Banca Multiple", False, "Citibank México — operaciones migradas a Banamex"),
    ("0000040017", "BBVA BANCOMER SERVICIOS", "Banca Multiple", False, "Subsidiaria de BBVA, operaciones consolidadas"),
    ("0000040022", "GE MONEY", "Banca Multiple", False, "GE Money — salió de México ~2009"),
    ("0000040032", "IXE", "Banca Multiple", False, "IXE Banco — fusionado con Banorte (2013)"),
    ("0000040071", "BANPAIS", "Banca Multiple", False, "Banpaís — absorbido por Banorte (~1997)"),
    ("0000040086", "BANCEN", "Banca Multiple", False, "Bancen — banco histórico desaparecido"),
    ("0000040103", "AMERICAN EXPRESS", "Banca Multiple", True, "American Express Bank (México)"),
    ("0000040107", "BANKBOSTON", "Banca Multiple", False, "BankBoston — adquirido por Bank of America, salió de México"),
    ("0000040114", "BANK ONE", "Banca Multiple", False, "Bank One — fusionado con JP Morgan Chase (2004)"),
    ("0000040116", "ING", "Banca Multiple", False, "ING Bank — salió del retail mexicano"),
    ("0000040117", "JP MORGAN", "Banca Multiple", True, "J.P. Morgan México — banca de inversión"),
    ("0000040119", "HSBC BANK", "Banca Multiple", False, "HSBC Bank — consolidado bajo HSBC México (040021)"),
    ("0000040124", "DEUTSCHE BANK", "Banca Multiple", True, "Deutsche Bank México — banca corporativa"),
    ("0000040134", "BANCO WAL-MART", "Banca Multiple", True, "Banco Walmart de México Adelante"),
    ("0000040142", "DEUNO", "Banca Multiple", False, "Deuno — operaciones cesadas"),
    ("0000040144", "BNY MELLON", "Banca Multiple", True, "The Bank of New York Mellon — custodia y servicios"),
    ("0000040146", "BICENTENARIO", "Banca Multiple", False, "Bicentenario — banco fallido, liquidado"),
    ("0000040161", "MERCANTIL DEL NORTE", "Banca Multiple", False, "Mercantil del Norte — entidad de Banorte"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync bank_dim_institucion")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = psycopg.connect(os.environ["DATABASE_URL"])

    try:
        with conn.cursor() as cur:
            # ─── Step 1: Normalize names ─────────────────────────────
            print("=== Step 1: Name normalizations ===")
            for old_name, new_name in NAME_FIXES.items():
                if args.dry_run:
                    cur.execute(
                        "SELECT clave_cnbv FROM bank_dim_institucion WHERE nombre_corto = %s",
                        (old_name,),
                    )
                    row = cur.fetchone()
                    if row:
                        print(f"  [DRY] {old_name} → {new_name} (code={row[0]})")
                    else:
                        print(f"  [SKIP] {old_name} not found in dim")
                else:
                    cur.execute(
                        "UPDATE bank_dim_institucion SET nombre_corto = %s, updated_at = NOW() "
                        "WHERE nombre_corto = %s",
                        (new_name, old_name),
                    )
                    print(f"  {old_name} → {new_name} ({cur.rowcount} rows)")

            # ─── Step 2: Mark inactive banks ─────────────────────────
            print("\n=== Step 2: Mark inactive banks ===")
            for code, (fecha_baja, comment) in INACTIVE_BANKS.items():
                if args.dry_run:
                    cur.execute(
                        "SELECT nombre_corto, activo FROM bank_dim_institucion WHERE clave_cnbv = %s",
                        (code,),
                    )
                    row = cur.fetchone()
                    if row:
                        status = "already inactive" if not row[1] else "→ INACTIVE"
                        print(f"  [DRY] {code} {row[0]}: {status}, baja={fecha_baja}")
                    else:
                        print(f"  [SKIP] {code} not in dim")
                else:
                    cur.execute(
                        "UPDATE bank_dim_institucion "
                        "SET activo = false, fecha_baja = %s, nombre_completo = %s, updated_at = NOW() "
                        "WHERE clave_cnbv = %s",
                        (fecha_baja, comment, code),
                    )
                    print(f"  {code}: set inactive, baja={fecha_baja} ({cur.rowcount} rows)")

            # ─── Step 3: Add comments ────────────────────────────────
            print("\n=== Step 3: Add comments (nombre_completo) ===")
            for code, comment in BANK_COMMENTS.items():
                if args.dry_run:
                    cur.execute(
                        "SELECT nombre_corto FROM bank_dim_institucion WHERE clave_cnbv = %s",
                        (code,),
                    )
                    row = cur.fetchone()
                    if row:
                        print(f"  [DRY] {code} {row[0]}: {comment[:60]}...")
                else:
                    cur.execute(
                        "UPDATE bank_dim_institucion "
                        "SET nombre_completo = %s, updated_at = NOW() "
                        "WHERE clave_cnbv = %s",
                        (comment, code),
                    )
                    if cur.rowcount:
                        print(f"  {code}: comment set ({cur.rowcount})")

            # ─── Step 4: Insert missing institutions ─────────────────
            print("\n=== Step 4: Insert missing institutions ===")
            # Fix sequence if out of sync with existing max id
            cur.execute(
                "SELECT setval('bank_dim_institucion_institucion_id_seq', "
                "(SELECT COALESCE(MAX(institucion_id), 0) + 1 FROM bank_dim_institucion), false)"
            )
            print(f"  Sequence reset to {cur.fetchone()[0]}")

            for clave, nombre, tipo, activo, comment in MISSING_INSTITUTIONS:
                cur.execute(
                    "SELECT 1 FROM bank_dim_institucion WHERE clave_cnbv = %s",
                    (clave,),
                )
                if cur.fetchone():
                    print(f"  [SKIP] {clave} {nombre} — already exists")
                    continue

                if args.dry_run:
                    status = "activo" if activo else "INACTIVO"
                    print(f"  [DRY] INSERT {clave} {nombre} ({status}): {comment[:50]}")
                else:
                    cur.execute(
                        "INSERT INTO bank_dim_institucion "
                        "(clave_cnbv, nombre_corto, nombre_completo, tipo_institucion, activo) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (clave, nombre, comment, tipo, activo),
                    )
                    print(f"  INSERT {clave} {nombre} ({cur.rowcount})")

            if not args.dry_run:
                conn.commit()
                print("\n  Committed.")

            # ─── Summary ─────────────────────────────────────────────
            print("\n=== Summary ===")
            cur.execute(
                "SELECT activo, COUNT(*) FROM bank_dim_institucion GROUP BY activo ORDER BY activo"
            )
            for r in cur.fetchall():
                label = "Activos" if r[0] else "Inactivos"
                print(f"  {label}: {r[1]}")
            cur.execute("SELECT COUNT(*) FROM bank_dim_institucion")
            print(f"  Total: {cur.fetchone()[0]}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
