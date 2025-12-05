# Password Reset 500 Error - Troubleshooting Guide

## Problem

Users see "Error al procesar la solicitud de recuperación de contraseña" when trying to reset password, with a 500 Internal Server Error in browser console:

```
POST /api/auth/forgot-password - Status: 500 Internal Server Error
```

## Root Causes

The 500 error occurs when the `/api/auth/forgot-password` endpoint fails. Common causes:

### 1. **Missing SMTP Configuration (Most Common)**

**Symptoms:**
- 503 Service Unavailable response
- Error message: "El servicio de recuperación de contraseña no está configurado"

**Solution:**
```bash
# Check environment variables
./scripts/check-password-reset-config.sh

# Required variables in envs/.env:
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=YOUR_EMAIL_HERE
SMTP_PASSWORD=YOUR_GMAIL_APP_PASSWORD_HERE  # NOT regular password!
SMTP_FROM_EMAIL=YOUR_FROM_EMAIL_HERE
PASSWORD_RESET_URL_BASE=https://your-domain.com
```

**Generate Gmail App Password:**
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Other (Custom name)"
3. Copy the 16-character password
4. Use that in `SMTP_PASSWORD` (no spaces)

---

### 2. **Invalid JWT Secret Key**

**Symptoms:**
- 500 error when creating reset token
- Logs show JWT encoding errors

**Solution:**
```bash
# Generate strong secret key
openssl rand -hex 32

# Add to envs/.env:
JWT_SECRET_KEY=<generated-key>
JWT_ALGORITHM=HS256
```

---

### 3. **Database Connection Issues**

**Symptoms:**
- 500 error when querying user
- Logs show MongoDB connection errors

**Solution:**
```bash
# Check MongoDB is running
docker ps | grep mongodb

# Check MongoDB connection
docker exec octavios-backend-1 python -c "
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
async def test():
    # Use environment variable MONGODB_URL
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    await client.admin.command('ping')
    print('MongoDB OK')
asyncio.run(test())
"
```

---

### 4. **Missing Environment Variables in Container**

**Symptoms:**
- Config check passes locally but fails in container
- Variables not visible in docker exec

**Solution:**
```bash
# Verify env vars are loaded in container
docker exec octavios-backend-1 env | grep SMTP

# If missing, restart with explicit env file
cd infra
docker compose down
docker compose --env-file ../envs/.env up -d --force-recreate
```

---

## Step-by-Step Debugging

### Step 1: Check Backend Logs

```bash
# Watch backend logs in real-time
docker logs octavios-backend-1 -f --tail=50

# Look for these patterns:
# - "SMTP configuration missing"
# - "Password reset email task scheduled"
# - "Failed to send email"
# - Any exception tracebacks
```

### Step 2: Verify Configuration

```bash
# Run automated config checker
./scripts/check-password-reset-config.sh

# Check if all required variables are set
# Pay attention to warnings and errors
```

### Step 3: Test Email Service Directly

```bash
# Test SMTP connection from backend container
docker exec -it octavios-backend-1 python -c "
import asyncio
from apps.backend.src.services.email_service import get_email_service

async def test():
    service = get_email_service()
    result = await service.send_email(
        to_email='test@example.com',
        subject='Test Email',
        html_body='<h1>Test</h1>'
    )
    print(f'Email sent: {result}')

asyncio.run(test())
"
```

### Step 4: Check Frontend Error Handling

```javascript
// In browser console, check the actual error response:
fetch('http://your-api-url/api/auth/forgot-password', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'test@example.com' })
})
.then(r => r.json())
.then(console.log)
.catch(console.error)
```

---

## Quick Fixes

### Fix 1: Add Missing SMTP Configuration

```bash
# Edit production env file
nano envs/.env

# Add SMTP variables
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=YOUR_EMAIL_HERE
SMTP_PASSWORD=YOUR_APP_PASSWORD_HERE  # Gmail App Password (16 chars)
SMTP_FROM_EMAIL=YOUR_FROM_EMAIL_HERE
PASSWORD_RESET_URL_BASE=https://your-domain.com

# Restart backend
cd infra
docker compose restart backend
```

### Fix 2: Regenerate JWT Secret

```bash
# Generate new secret
openssl rand -hex 32 > /tmp/jwt_secret.txt

# Add to envs/.env
echo "JWT_SECRET_KEY=$(cat /tmp/jwt_secret.txt)" >> envs/.env

# Restart backend
cd infra
docker compose restart backend

# Clean up
rm /tmp/jwt_secret.txt
```

### Fix 3: Force Container Recreation

```bash
# Complete restart with env reload
cd infra
docker compose down
docker compose --env-file ../envs/.env up -d --force-recreate backend

# Verify
docker logs octavios-backend-1 -f
```

---

## Verification After Fix

### 1. Check Backend Health
```bash
curl http://localhost:8001/health
# Should return: {"status":"healthy"}
```

### 2. Test Password Reset Flow
```bash
# Send password reset request
curl -X POST http://localhost:8001/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com"}'

# Expected response:
# {
#   "message": "Si el correo existe en nuestro sistema, recibirás un enlace de recuperación",
#   "email": "demo@example.com"
# }
```

### 3. Check Logs for Success
```bash
docker logs octavios-backend-1 --tail=20 | grep "Password reset email task scheduled"
# Should show log entry with email and user_id
```

---

## Prevention

### 1. Add to Deployment Checklist
```markdown
- [ ] SMTP credentials configured in envs/.env
- [ ] JWT_SECRET_KEY generated and set (32+ chars)
- [ ] PASSWORD_RESET_URL_BASE matches production domain
- [ ] Test password reset after deployment
- [ ] Monitor backend logs for SMTP errors
```

### 2. Add Monitoring Alert
```yaml
# Example alert rule (adjust for your monitoring system)
- alert: PasswordResetFailures
  expr: rate(http_requests_total{endpoint="/api/auth/forgot-password",status=~"5.."}[5m]) > 0
  for: 1m
  annotations:
    summary: "Password reset endpoint returning 500 errors"
    description: "Check SMTP configuration and backend logs"
```

### 3. Add Smoke Test to CI/CD
```bash
# Add to deployment pipeline
./scripts/check-password-reset-config.sh --production
```

---

## Additional Resources

- **Gmail App Password Setup**: https://myaccount.google.com/apppasswords
- **SMTP Configuration Guide**: `docs/guides/PASSWORD_RESET_SETUP.md`
- **Environment Template**: `envs/.env.production.example`
- **Config Checker Script**: `scripts/check-password-reset-config.sh`
- **Test Script**: `scripts/testing/test_password_reset.sh`

---

## Still Not Working?

If none of the above fixes work:

1. **Enable debug logging:**
   ```bash
   # In envs/.env
   LOG_LEVEL=debug

   # Restart backend
   docker compose restart backend
   ```

2. **Check full exception trace:**
   ```bash
   docker logs octavios-backend-1 --tail=100 | grep -A 20 "Traceback"
   ```

3. **Verify network connectivity:**
   ```bash
   # Test SMTP from backend container
   docker exec octavios-backend-1 telnet smtp.gmail.com 587
   ```

4. **Contact support:**
   - Include backend logs
   - Include output from `./scripts/check-password-reset-config.sh`
   - Describe exact steps to reproduce

---

**Last Updated:** 2025-12-05
**Related Issues:** Production deployment, SMTP configuration, environment variables
