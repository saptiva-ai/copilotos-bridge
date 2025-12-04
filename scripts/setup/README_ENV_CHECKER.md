# Environment Checker Script

## Overview

The `env-checker.sh` script validates critical environment variables required for the OctaviOS Chat application. It ensures all necessary configuration is set before starting services, preventing runtime errors due to missing or invalid environment variables.

## Features

- ✅ **Three validation modes**: `strict`, `warn` (default), `info`
- ✅ **Categorized variables**: Critical, Important, Development
- ✅ **Security validation**: Checks minimum length for secrets (32+ chars)
- ✅ **Sensitive data masking**: Hides passwords/keys in info mode
- ✅ **Color-coded output**: Easy to spot issues
- ✅ **Descriptive messages**: Each variable includes purpose description

## Usage

### Via Makefile (Recommended)

```bash
# Quick validation (warns about missing optional vars)
make env-check

# Detailed info (shows all values with masking)
make env-info

# Strict mode (fails on missing important vars)
make env-strict
```

### Direct Script Usage

```bash
# Default mode (warn)
./scripts/env-checker.sh

# Strict mode
./scripts/env-checker.sh strict

# Info mode
./scripts/env-checker.sh info

# Custom env file
./scripts/env-checker.sh warn envs/.env.prod
```

## Validation Modes

### 1. Warn Mode (Default)

**Command**: `make env-check`

- ✅ Validates all **critical** variables
- ⚠️ Shows warnings for missing **important** variables
- ✅ Performs **security validation** (secret lengths)
- **Exit code**: 0 (passes even with warnings)

**Use case**: Daily development, pre-commit checks

### 2. Info Mode

**Command**: `make env-info`

- ✅ Validates all variables
- 🔒 **Masks sensitive values** (shows last 4 chars)
- ✅ Performs **security validation**
- **Exit code**: 0 if critical vars are set

**Use case**: Debugging, environment documentation

### 3. Strict Mode

**Command**: `make env-strict`

- ✅ Validates **critical** variables only
- ❌ Fails on any missing critical variable
- **Exit code**: 1 if any critical var is missing

**Use case**: CI/CD pipelines, production deployments

## Variable Categories

### Critical Variables (Required)

| Variable | Description |
|----------|-------------|
| `SAPTIVA_API_KEY` | SAPTIVA API authentication key |
| `JWT_SECRET_KEY` | JWT token signing key (32+ chars) |
| `MONGODB_URL` | MongoDB connection string |
| `REDIS_URL` | Redis connection string |
| `MINIO_ENDPOINT` | MinIO S3 endpoint |

### Important Variables (Recommended)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Frontend API base URL |
| `CORS_ORIGINS` | Allowed CORS origins |
| `ALETHEIA_API_URL` | Aletheia research API endpoint |

## Integration with `make dev`

The `make dev` command **automatically runs** `env-check` before starting services:

```bash
make dev
# Output:
🔍 Validating environment variables...
✓ All critical variables are set
✓ Environment check passed

🟡 Starting development environment...
```

If validation fails:
```bash
✗ Missing critical variable(s)
❌ Environment validation failed. Run 'make setup' to fix.
```

## Best Practices

1. **Always run** `make env-check` after updating `.env` manually
2. **Use** `make env-info` when debugging configuration issues
3. **Run** `make env-strict` in CI/CD pipelines
4. **Never commit** `.env` files to version control
5. **Regenerate secrets** using `openssl rand -hex 32` for production
