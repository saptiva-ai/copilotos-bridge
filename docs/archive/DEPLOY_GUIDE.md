# 🚀 Deployment Guide - CopilotOS

Complete guide for deploying CopilotOS with the new interactive one-click setup system.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Development Setup](#development-setup)
4. [Production Setup](#production-setup)
5. [Security Best Practices](#security-best-practices)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Configuration](#advanced-configuration)

---

## Quick Start

### For Development (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/your-org/copilotos-bridge.git
cd copilotos-bridge

# 2. Interactive setup (auto-generates secrets, prompts for API keys)
make setup

# 3. Start services
make dev

# 4. Create demo user
make create-demo-user

# 5. Access application
open http://localhost:3000
```

That's it! The interactive setup handles everything automatically.

### For Production

```bash
# 1. Clone on production server
git clone https://github.com/your-org/copilotos-bridge.git
cd copilotos-bridge

# 2. Interactive production setup
make setup-interactive-prod

# 3. Deploy
make deploy-clean

# 4. Verify deployment
make deploy-status
```

---

## Prerequisites

### System Requirements

- **Docker** 20.10+ and Docker Compose
- **Git** 2.30+
- **Bash** 4.0+
- **openssl** (for secret generation)

### Required Credentials

Before running setup, have these ready:

1. **SAPTIVA API Key** (REQUIRED)
   - Get from: https://saptiva.com/dashboard/api-keys
   - Format: `va-ai-...`

2. **Aletheia API Key** (optional)
   - Required only if using deep research features
   - Get from: https://aletheia.saptiva.ai/keys

3. **Domain/Server IP** (production only)
   - Your server's public IP or domain name

---

## Development Setup

### Option 1: Interactive Setup (Recommended)

The interactive setup will:
- ✅ Auto-generate strong passwords and secrets
- ✅ Prompt for required API keys
- ✅ Create properly configured `.env.local` file
- ✅ Set secure file permissions (600)
- ✅ Never hardcode credentials

```bash
make setup
```

**What it asks:**

1. **Project name** (default: `copilotos`)
2. **SAPTIVA API key** (REQUIRED - you provide)
3. **Aletheia configuration** (optional)

**What it generates automatically:**

- MongoDB password (24 characters)
- Redis password (24 characters)
- JWT secret key (64 hex characters)
- Application secret key (64 hex characters)

### Option 2: Quick Setup (Manual Configuration)

If you prefer to configure manually:

```bash
# Uses example file, requires manual editing
make setup-quick

# Edit configuration
nano envs/.env.local

# Add your SAPTIVA API key
# SAPTIVA_API_KEY=va-ai-your-key-here
```

### Verifying Setup

```bash
# Check services are running
make health

# View logs
make logs

# Check configuration
cat envs/.env.local
```

### Common Development Tasks

```bash
# Start/stop services
make dev          # Start all services
make stop         # Stop services
make restart      # Restart services

# Create users
make create-demo-user     # Demo user (demo/Demo1234)

# View logs
make logs                 # All services
make logs-api            # API only
make logs-web            # Web only

# Rebuild (if code changes don't reflect)
make rebuild-api         # API container
make rebuild-web         # Web container
make rebuild-all         # All containers
```

---

## Production Setup

### Step 1: Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

### Step 2: Clone Repository

```bash
# Create deployment directory
sudo mkdir -p /opt/copilotos-bridge
sudo chown $(whoami):$(whoami) /opt/copilotos-bridge

# Clone
git clone https://github.com/your-org/copilotos-bridge.git /opt/copilotos-bridge
cd /opt/copilotos-bridge
```

### Step 3: Interactive Production Setup

```bash
make setup-interactive-prod
```

**You'll be prompted for:**

1. **Domain/IP**: Your server's public address
2. **SAPTIVA API key**: Production API key
3. **Aletheia configuration**: Optional deep research

**Auto-generated (production-grade):**

- Strong database passwords
- Cryptographically secure JWT secrets
- Production-optimized configuration

**Generated file:** `envs/.env.prod`

### Step 4: Deploy

```bash
# Option 1: Clean build (first deployment)
make deploy-clean

# Option 2: Quick deploy (subsequent updates)
make deploy-quick

# Option 3: Tar-based deploy (no registry needed)
make deploy-tar
```

### Step 5: Configure Nginx (Optional)

For production with custom domain:

```bash
# Create Nginx config
sudo nano /etc/nginx/sites-available/copilotos

# Add configuration (see DEPLOYMENT.md for full config)

# Enable site
sudo ln -s /etc/nginx/sites-available/copilotos /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com
```

### Step 6: Verify Deployment

```bash
# Check status
make deploy-status

# Health check
curl http://localhost:8001/api/health

# View logs
make logs

# Monitor resources
make resources
```

---

## Security Best Practices

### ⚠️ CRITICAL: Before First Deployment

Run security check:

```bash
./scripts/security-check.sh
```

This will scan for:
- Tracked .env files in Git
- Hardcoded API keys
- Weak passwords
- Insecure file permissions

### Secure Secrets Management

#### DO:

✅ Use interactive setup (`make setup`)
✅ Let the script generate secrets automatically
✅ Store production secrets in environment variables or vault
✅ Use different secrets for dev/staging/prod
✅ Rotate secrets regularly (every 90 days)
✅ Set file permissions to 600 or 400

#### DON'T:

❌ Commit .env files to Git
❌ Share secrets via email/Slack
❌ Use weak or default passwords
❌ Reuse the same secrets across environments
❌ Store production secrets in code

### Credential Rotation

If credentials are compromised:

1. **Immediate actions:**
   ```bash
   # Remove from Git
   git rm --cached envs/.env envs/.env.prod
   git commit -m "security: remove env files"
   ```

2. **Rotate credentials:**
   ```bash
   # Regenerate with interactive setup
   make setup-interactive-prod

   # Update production
   make deploy-clean
   ```

3. **Update services:**
   - Revoke old SAPTIVA API key
   - Change database passwords
   - Restart all services

### File Permissions

```bash
# Secure env files
chmod 600 envs/.env*

# Verify
ls -la envs/
# Should show: -rw------- (600)
```

---

## Troubleshooting

### Issue: "SAPTIVA API key is invalid"

**Symptoms:**
- API returns 401 Unauthorized
- Chat requests fail

**Solution:**
```bash
# 1. Verify key in env file
cat envs/.env.local | grep SAPTIVA_API_KEY

# 2. Test key directly
curl -H "Authorization: Bearer YOUR_KEY" https://api.saptiva.com/v1/models

# 3. Regenerate if needed
make setup-interactive
```

### Issue: "Cannot connect to database"

**Symptoms:**
- MongoDB connection errors
- App crashes on startup

**Solution:**
```bash
# 1. Check MongoDB is running
docker ps | grep mongodb

# 2. Check credentials
cat envs/.env.local | grep MONGODB_

# 3. Restart services
make restart

# 4. Check MongoDB logs
make logs | grep mongodb
```

### Issue: "Authentication fails with Test4@saptiva.com"

**Status:** ✅ FIXED in this version

**What was the bug:**
- Register: `Test4@saptiva.com` → stored as `test4@saptiva.com`
- Login: `Test4@saptiva.com` → lookup failed (case-sensitive)

**Solution (automatic):**
- Email normalization now consistent across register/login
- All emails converted to lowercase before storage/lookup
- Tests added to prevent regression

**Verify fix:**
```bash
# Run email normalization tests
cd apps/api
source .venv/bin/activate
pytest tests/test_email_utils.py -v
pytest tests/test_auth_email_normalization.py -v
```

### Issue: "Code changes not reflected"

**Symptoms:**
- Modified code doesn't run
- Old behavior persists

**Solution:**
```bash
# Rebuild with --no-cache
make rebuild-api      # For API changes
make rebuild-web      # For frontend changes
make rebuild-all      # For env var changes
```

**Why?**
- Docker caches image layers
- `docker restart` keeps old container
- Need `down` + `up` to recreate

### Issue: ".env file already exists"

**Symptoms:**
- Interactive setup shows "file already exists"

**Solution:**
```bash
# Option 1: Update existing file (preserves values)
make setup
# Answer "yes" to update

# Option 2: Backup and recreate
mv envs/.env.local envs/.env.local.backup
make setup

# Option 3: Edit manually
nano envs/.env.local
```

### Issue: "Permission denied" on scripts

**Solution:**
```bash
# Make scripts executable
chmod +x scripts/*.sh

# Verify
ls -la scripts/
```

---

## Advanced Configuration

### Custom Environment Variables

Add custom variables to `.env.local`:

```bash
# Custom API timeouts
SAPTIVA_TIMEOUT=60
ALETHEIA_TIMEOUT=180

# Custom rate limits
RATE_LIMIT_REQUESTS_PER_MINUTE=50

# Feature flags
NEXT_PUBLIC_FEATURE_WEB_SEARCH=false
DEEP_RESEARCH_KILL_SWITCH=true
```

### Multiple Environments

```bash
# Development
make setup-interactive          # Creates .env.local

# Staging
./scripts/interactive-env-setup.sh staging
# Edit staging-specific values

# Production
make setup-interactive-prod     # Creates .env.prod
```

### Environment-Specific Secrets

```bash
envs/
├── .env.local          # Development (auto-generated)
├── .env.staging        # Staging (manual)
├── .env.prod           # Production (auto-generated)
├── .env.local.example  # Template (committed)
└── .env.secrets.example # Secrets template (committed)
```

### Docker Compose Profiles

```bash
# Development (default)
docker compose up -d

# Production
docker compose --profile production up -d

# With resource limits
COMPOSE_RESOURCES=1 make dev
```

### Resource Monitoring

```bash
# Quick check
make resources

# Continuous monitoring
make resources-monitor

# Cleanup
make docker-cleanup              # Safe (old cache only)
make docker-cleanup-aggressive   # Deep (all unused)
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Run `./scripts/security-check.sh`
- [ ] Verify no .env files in Git
- [ ] Test authentication flow (email normalization)
- [ ] Run complete test suite (`make test-all`)
- [ ] Review `SECURITY_ALERT.md` if it exists
- [ ] Backup current database (`make db-backup`)

### Deployment

- [ ] Run interactive setup
- [ ] Verify SAPTIVA API key
- [ ] Configure domain/SSL
- [ ] Deploy with `make deploy-clean`
- [ ] Verify health endpoints
- [ ] Create admin user
- [ ] Test login with various email formats

### Post-Deployment

- [ ] Monitor logs for errors
- [ ] Verify authentication works
- [ ] Test email case-insensitivity
- [ ] Check resource usage (`make resources`)
- [ ] Update documentation
- [ ] Notify team

---

## Support

### Documentation

- **Main README:** `README.md`
- **Deployment:** `docs/DEPLOYMENT.md`
- **Security:** `SECURITY_ALERT.md`
- **Resource Optimization:** `docs/RESOURCE_OPTIMIZATION.md`
- **Token Handling:** `docs/TOKEN_EXPIRATION_HANDLING.md`

### Commands Reference

```bash
make help                    # Show all commands
make setup                   # Interactive setup
make dev                     # Start development
make deploy-clean            # Production deploy
make test-all               # Run all tests
make security               # Security audit
./scripts/security-check.sh  # Security scan
```

### Getting Help

1. Check `make help` for available commands
2. Review `docs/` directory for guides
3. Run `./scripts/security-check.sh` for security issues
4. Check logs with `make logs`
5. Verify configuration with `cat envs/.env.local`

---

## Summary

### What We Fixed

✅ **Email Normalization Bug**
- Emails now case-insensitive
- `Test4@saptiva.com` = `test4@saptiva.com`
- Comprehensive test suite added

✅ **One-Click Deployment**
- Interactive setup script
- Auto-generated secure secrets
- No hardcoded credentials
- Idempotent (safe to re-run)

✅ **Security Hardening**
- Secret detection script
- Security alert documentation
- Proper .gitignore validation
- File permission checks

### Key Improvements

1. **Developer Experience:**
   - One command setup: `make setup`
   - No manual .env editing required
   - Clear error messages

2. **Security:**
   - No secrets in code
   - Auto-generated strong passwords
   - Regular security audits

3. **Reliability:**
   - Email authentication works consistently
   - Production-grade configuration
   - Comprehensive testing

### Next Steps

1. **First time?**
   ```bash
   make setup
   make dev
   ```

2. **Existing project?**
   ```bash
   ./scripts/security-check.sh
   make setup  # Regenerate with secure defaults
   ```

3. **Production?**
   ```bash
   make setup-interactive-prod
   make deploy-clean
   ```

---

**Remember:** Always run `./scripts/security-check.sh` before deployment!
