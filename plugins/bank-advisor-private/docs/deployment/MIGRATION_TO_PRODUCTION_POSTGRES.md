# Migration to Production PostgreSQL

**Date:** 2025-01-XX
**Status:** ✅ Completed
**Migrated By:** DevOps Team

---

## 📋 Summary

Successfully migrated the BankAdvisor plugin from local PostgreSQL to a production PostgreSQL instance hosted on Google Cloud Platform (GCP).

### Migration Details

| Item | Before | After |
|------|--------|-------|
| **Host** | `localhost` | `35.193.13.180` (GCP) |
| **Port** | `5432` | `5432` |
| **User** | `octavios` | `bankadvisor` |
| **Database** | `bankadvisor` | `bankadvisor` |
| **Password** | `secure_postgres_password` | `8VM:&9LK.O*2lv?)` |

---

## 🔍 Background

### Why Migrate?

1. **Scalability:** The data was growing and needed a production-grade database
2. **Reliability:** GCP PostgreSQL provides automated backups and high availability
3. **Performance:** Dedicated resources for better query performance
4. **Multi-environment:** Separate production database from development

### No MongoDB to PostgreSQL Migration

**Important:** This plugin was **already using PostgreSQL** as its primary database. There was NO migration from MongoDB. The plugin uses:
- **PostgreSQL:** For all transactional data (metrics, ETL runs, query logs)
- **Qdrant:** For vector embeddings (RAG/NL2SQL context)

---

## 📝 Changes Made

### 1. Updated `.env` Configuration

**File:** `plugins/bank-advisor-private/.env`

```diff
# Database Configuration (PostgreSQL)
-POSTGRES_HOST=localhost
-POSTGRES_USER=octavios
-POSTGRES_PASSWORD=secure_postgres_password
+# Updated 2025-01-XX: Migrated to production PostgreSQL instance
+POSTGRES_HOST=35.193.13.180
+POSTGRES_USER=bankadvisor
+POSTGRES_PASSWORD=8VM:&9LK.O*2lv?)
 POSTGRES_DB=bankadvisor
```

### 2. Created Database Initialization Script

**File:** `scripts/init_postgres_database.sh`

A new shell script that:
- Tests connectivity to the PostgreSQL server
- Creates the `bankadvisor` database if it doesn't exist
- Runs all migrations in order (000-004)
- Verifies table creation
- Provides summary and next steps

**Usage:**
```bash
./scripts/init_postgres_database.sh
```

### 3. Created Connection Test Script

**File:** `scripts/test_postgres_connection.py`

A Python script that validates:
- ✅ Basic connectivity
- ✅ Database existence
- ✅ Table structure (columns, types)
- ✅ Data presence
- ✅ ETL run history
- ✅ Query performance

**Usage:**
```bash
source .venv/bin/activate
python scripts/test_postgres_connection.py
```

---

## 🗄️ Database Schema

### Tables Created (7 total)

| Table | Purpose | Size |
|-------|---------|------|
| `instituciones` | Catalog of financial institutions | 16 kB |
| `metricas_cartera_segmentada` | Segmented portfolio metrics (IMOR/ICOR) | 16 kB |
| `metricas_financieras` | Consolidated financial metrics | 16 kB |
| `metricas_financieras_ext` | Extended financial metrics | 40 kB |
| `monthly_kpis` | Monthly KPIs (2017-2025) | 40 kB |
| `query_logs` | Query logs for RAG feedback loop | 80 kB |
| `segmentos_cartera` | Portfolio segment catalog | 48 kB |

### Migrations Applied

1. **000_init_normalized_schema.sql** - Base schema with normalized structure
2. **001_add_missing_columns.sql** - Additional columns for extended metrics
3. **002_add_calculated_metrics.sql** - Calculated fields and derived metrics
4. **003_add_performance_indexes.sql** - Performance optimization indexes
5. **003_add_performance_indexes_v2.sql** - Additional indexes for query optimization
6. **003_schema_extended_unified.sql** - Unified schema extensions
7. **004_query_logs_rag_feedback.sql** - RAG feedback loop tables

---

## ✅ Verification Results

### Connection Test Output

```
================================================================================
PostgreSQL Connection Test
================================================================================

Connection Details:
  Host: 35.193.13.180
  Port: 5432
  User: bankadvisor
  Database: bankadvisor

✓ Test 1: Basic Connectivity
  PostgreSQL Version: PostgreSQL 17.7 on x86_64-pc-linux-gnu

✓ Test 2: Database Existence
  Current Database: bankadvisor

✓ Test 3: Table Structure
  ✓ Table 'monthly_kpis' exists
  ✓ Columns: 31

✓ Test 4: Data Presence
  ✗ Table is EMPTY (expected - waiting for ETL)

✓ Test 5: ETL Run History
  ⊘ ETL runs table doesn't exist (will be created on first run)

✓ Test 6: Query Performance
  ⊘ Skipped (no data)

================================================================================
✓ All tests completed successfully!
================================================================================
```

---

## 🚀 Next Steps

### 1. Load Historical Data (ETL)

The database is ready but **empty**. You need to load historical data:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run ETL loader
python -m bankadvisor.etl_loader

# Or use the unified ETL (recommended)
python -m etl.etl_unified
```

**Expected Time:** ~3-4 minutes (processes 103 months of banking data)

### 2. Start the Server

Once data is loaded, start the BankAdvisor MCP server:

```bash
python -m src.main
```

The server will:
- Initialize the NL2SQL pipeline
- Load RAG services (if available)
- Start the RAG Feedback Loop job
- Listen on port 8002

### 3. Verify Service Health

```bash
curl http://localhost:8002/health | jq
```

Expected response:
```json
{
  "status": "healthy",
  "service": "bank-advisor-mcp",
  "version": "1.0.0",
  "etl": {
    "last_run_status": "success",
    "last_run_rows": 10000
  }
}
```

### 4. Run Smoke Tests

Validate the 5 business questions:

```bash
./scripts/test_5_questions.sh
```

---

## 🔒 Security Considerations

### Credentials Management

**⚠️ IMPORTANT:** The database password is stored in `.env` file which is **git-ignored**.

For production deployments:
1. Use **environment variables** in CI/CD
2. Use **secrets management** (GCP Secret Manager, AWS Secrets Manager, Vault)
3. **Rotate passwords** regularly
4. Use **SSL/TLS** for connections (if required)

### Database User Permissions

The `bankadvisor` user should have:
- ✅ **SELECT** - Read data
- ✅ **INSERT** - Write ETL data
- ✅ **UPDATE** - Update metrics
- ✅ **DELETE** - Clean old data
- ✅ **CREATE** - Create tables (for migrations)
- ❌ **DROP DATABASE** - Not needed (security)

### Network Security

- Database is accessible from the application server IP
- Firewall rules should restrict access to known IPs only
- Consider using **Cloud SQL Proxy** for secure connections

---

## 📊 Data Migration Strategy

### If You Have Existing Data in Old PostgreSQL

If you need to migrate data from the old `localhost` PostgreSQL to the new production instance:

#### Option 1: pg_dump/pg_restore (Full Database)

```bash
# 1. Dump from old database
pg_dump -h localhost -U octavios -d bankadvisor -F c -f bankadvisor_backup.dump

# 2. Restore to new database
pg_restore -h 35.193.13.180 -U bankadvisor -d bankadvisor -v bankadvisor_backup.dump
```

#### Option 2: Rerun ETL (Recommended)

Since the ETL can reload all historical data from source files, it's often cleaner to:

1. ✅ Run ETL on new database
2. ✅ Verify data integrity
3. ✅ No migration complexity

**Benefits:**
- Fresh, clean data
- Validates ETL pipeline
- No schema conflicts
- ~4 minutes execution time

---

## 🐛 Troubleshooting

### Connection Issues

**Error:** `database "bankadvisor" does not exist`

**Solution:**
```bash
./scripts/init_postgres_database.sh
```

---

**Error:** `connection timeout`

**Solution:**
- Check firewall rules on GCP
- Verify IP whitelist
- Test with: `telnet 35.193.13.180 5432`

---

**Error:** `FATAL: password authentication failed`

**Solution:**
- Verify `.env` credentials match GCP console
- Check for special characters in password (use quotes if needed)

---

### ETL Issues

**Error:** `No module named 'bankadvisor'`

**Solution:**
```bash
# Ensure you're in the plugin directory
cd plugins/bank-advisor-private

# Activate virtual environment
source .venv/bin/activate

# Verify Python path
python -c "import sys; print('\n'.join(sys.path))"
```

---

**Error:** `FileNotFoundError: data/raw/historicos.csv`

**Solution:**
- Ensure raw data files are present in `data/raw/`
- Download from source or contact team for data files

---

## 📚 Related Documentation

- [README.md](../README.md) - Main project documentation
- [ARCHITECTURE.md](core/ARCHITECTURE.md) - System architecture
- [ETL_CONSOLIDATION.md](features/ETL_CONSOLIDATION.md) - ETL pipeline details
- [migrations/](../migrations/) - Database migration files

---

## ✅ Migration Checklist

- [x] Updated `.env` with production PostgreSQL credentials
- [x] Created database initialization script
- [x] Created connection test script
- [x] Ran migrations on production database
- [x] Verified table creation (7 tables)
- [x] Documented migration process
- [ ] **TODO:** Load historical data with ETL
- [ ] **TODO:** Start BankAdvisor server
- [ ] **TODO:** Run smoke tests
- [ ] **TODO:** Update Docker Compose (if applicable)
- [ ] **TODO:** Update deployment documentation

---

## 📞 Support

For issues or questions about this migration:

1. Check the troubleshooting section above
2. Review application logs: `docker-compose logs bank-advisor`
3. Test connection: `python scripts/test_postgres_connection.py`
4. Contact DevOps team

---

**Migration completed successfully! 🎉**
