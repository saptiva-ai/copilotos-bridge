# 🔐 Credentials Reference Card

Quick reference for all default credentials and configuration.

---

## 👤 Demo User (Default Development)

### Web Interface Login

```
URL:      http://localhost:3000/login
Username: demo
Password: Demo1234
Email:    demo@example.com
```

**Create with:**
```bash
make create-demo-user
```

**Test login:**
```bash
make test-login
```

**Get JWT token:**
```bash
make get-token
```

---

## 🗄️ Database Credentials (Development)

### MongoDB

```
Host:     localhost
Port:     27017
Username: copilotos_user
Password: secure_password_change_me
Database: copilotos
Auth DB:  admin

Connection String:
mongodb://copilotos_user:secure_password_change_me@localhost:27017/copilotos?authSource=admin
```

**Access shell:**
```bash
make shell-db
# or
docker exec -it copilotos-mongodb mongosh copilotos
```

**Manual connection:**
```bash
mongosh "mongodb://copilotos_user:secure_password_change_me@localhost:27017/copilotos?authSource=admin"
```

### Redis

```
Host:     localhost
Port:     6379
Password: redis_password_change_me

Connection String:
redis://:redis_password_change_me@localhost:6379/0
```

**Access CLI:**
```bash
make shell-redis
# or
docker exec -it copilotos-redis redis-cli
```

**Manual connection:**
```bash
redis-cli -h localhost -p 6379 -a redis_password_change_me
```

---

## 🔑 API Keys & Secrets (Environment Variables)

### Required for Production

```bash
# SAPTIVA API (Required - no demo mode)
SAPTIVA_API_KEY=your-saptiva-api-key-here
SAPTIVA_BASE_URL=https://api.saptiva.com

# JWT Authentication
JWT_SECRET_KEY=auto-generated-secure-key-change-in-prod
SECRET_KEY=auto-generated-secure-key-change-in-prod
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Database Passwords
MONGODB_PASSWORD=secure_password_change_me
REDIS_PASSWORD=redis_password_change_me
```

**Location:** `envs/.env` or `envs/.env.local`

**Generate secure secrets:**
```bash
bash scripts/generate-secrets.py
```

---

## 🌐 Application URLs (Development)

### Frontend (Next.js)
```
Main:         http://localhost:3000
Login:        http://localhost:3000/login
Register:     http://localhost:3000/register
Chat:         http://localhost:3000/chat
Health:       http://localhost:3000/healthz
```

### Backend (FastAPI)
```
Main:         http://localhost:8001
API:          http://localhost:8001/api
Docs:         http://localhost:8001/docs
ReDoc:        http://localhost:8001/redoc
Health:       http://localhost:8001/api/health
OpenAPI:      http://localhost:8001/openapi.json
```

---

## 🐳 Docker Container Names

```
Web:      copilotos-web
API:      copilotos-api
MongoDB:  copilotos-mongodb
Redis:    copilotos-redis
```

**Access containers:**
```bash
# Web container
docker exec -it copilotos-web sh

# API container
docker exec -it copilotos-api bash

# MongoDB
docker exec -it copilotos-mongodb mongosh

# Redis
docker exec -it copilotos-redis redis-cli
```

---

## 🧪 Testing Credentials

### API Testing with curl

```bash
# 1. Get authentication token
export TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"demo","password":"Demo1234"}' | \
  grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

# 2. Use token in requests
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello!","session_id":"test"}'
```

**Or use Make command:**
```bash
make get-token
# Follow the instructions to export TOKEN
```

---

## 🔄 Changing Credentials

### Change Demo User Password

**Option 1: Via API**
```bash
curl -X POST http://localhost:8001/api/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","new_password":"YourNewPassword123!"}'
```

**Option 2: Via Database**
```bash
make shell-db
# In MongoDB shell:
db.users.updateOne(
  {username: "demo"},
  {$set: {password_hash: "new-bcrypt-hash-here"}}
)
```

### Change Database Passwords

1. Edit `envs/.env`:
   ```bash
   MONGODB_PASSWORD=your-new-mongo-password
   REDIS_PASSWORD=your-new-redis-password
   ```

2. Restart services:
   ```bash
   make stop
   make clean-volumes  # ⚠️ Deletes data
   make dev
   ```

### Regenerate JWT Secret

```bash
# Generate new secret
openssl rand -base64 32

# Update envs/.env
JWT_SECRET_KEY=<new-secret-here>

# Restart API
make restart
```

---

## 🛡️ Security Best Practices

### Development
- ✅ Use default credentials (demo/Demo1234)
- ✅ Keep API keys in `envs/.env` (gitignored)
- ✅ Never commit credentials to git

### Production
- 🔒 Change ALL default passwords
- 🔒 Use strong, unique passwords (20+ characters)
- 🔒 Use environment variables or secrets manager
- 🔒 Enable TLS/SSL for all connections
- 🔒 Rotate secrets regularly
- 🔒 Use Docker secrets for sensitive data

**Production checklist:**
```bash
# Run security audit
bash scripts/security-audit.sh

# Validate configuration
bash scripts/validate-config.sh
```

---

## 📝 Quick Commands

```bash
# User Management
make create-demo-user  # Create demo user
make delete-demo-user  # Delete demo user
make list-users        # List all users
make test-login        # Test demo login
make get-token         # Get JWT token
make clear-cache       # Clear Redis cache

# Database Access
make shell-db          # MongoDB shell
make shell-redis       # Redis CLI

# Service Health
make health            # Check all services
make verify            # Full verification

# Logs & Debugging
make logs              # All service logs
make logs-api          # API logs only
make logs-web          # Web logs only
```

---

## 🆘 Troubleshooting

### Can't login with demo credentials

```bash
# Clear Redis cache first (important!)
make clear-cache

# Delete and recreate demo user
make delete-demo-user
make create-demo-user

# Test login
make test-login

# Check API health
make health
```

### Database connection failed

```bash
# Check database logs
docker logs copilotos-mongodb

# Test connection manually
mongosh "mongodb://copilotos_user:secure_password_change_me@localhost:27017/copilotos?authSource=admin"

# Restart database
docker restart copilotos-mongodb
```

### JWT token expired

```bash
# Get new token
make get-token

# Or login again via web interface
open http://localhost:3000/login
```

---

## 📖 See Also

- **Quick Start Guide**: [QUICK_START.md](QUICK_START.md)
- **Main README**: [README.md](README.md)
- **Security Guide**: [docs/SECURITY.md](docs/SECURITY.md)
- **Deployment Guide**: [docs/operations/deployment.md](docs/operations/deployment.md)

---

**🎯 Pro Tip:** Bookmark this page for quick reference during development!
