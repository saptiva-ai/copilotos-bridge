# 🚀 Secure Production Deployment Guide

## 🔒 Security Notice
⚠️ **SECURITY UPDATE**: This system has been hardened with comprehensive secrets management. All hardcoded credentials have been **REMOVED** and replaced with secure configuration.

## 📋 Overview
This system operates in **production mode only** with mandatory security requirements:
- **Zero hardcoded credentials** ✅
- **Secure secrets management** ✅
- **Encrypted credential storage** ✅
- **Fail-fast security validation** ✅

## 🔑 SAPTIVA API Key Configuration

### 🔐 Secure Configuration Methods

**⚠️ SECURITY WARNING: Never use hardcoded credentials!**

#### Method 1: Docker Secrets (Production Recommended)
```bash
# 1. Generate secure secrets
python3 scripts/generate-secrets.py

# 2. Setup Docker secrets
./scripts/setup-docker-secrets.sh

# 3. Deploy securely
docker stack deploy -c docker-compose.secure.yml copilotos
```

#### Method 2: Environment Variables (Development Only)
```bash
# Generate secure values first!
export SAPTIVA_API_KEY=your-saptiva-api-key-here
export MONGODB_PASSWORD=$(openssl rand -base64 32)
export JWT_SECRET_KEY=$(openssl rand -hex 32)
export SECRET_KEY=$(openssl rand -hex 32)
```

### Security Priority Order
1. **Docker Secrets** (/run/secrets/) - HIGHEST SECURITY
2. **Environment Variables** - MEDIUM SECURITY
3. **Secure Files** (/etc/copilotos/secrets/) - HIGH SECURITY
4. **Admin UI** - For API key management only

## ⚙️ Deployment Steps

### 1. Environment Variables
Ensure `SAPTIVA_API_KEY` is set in your deployment environment:
```bash
# For Docker
export SAPTIVA_API_KEY=your-key
docker-compose up

# For Kubernetes
kubectl create secret generic saptiva-secret \
  --from-literal=SAPTIVA_API_KEY=your-key

# For other platforms
# Add SAPTIVA_API_KEY to your environment variables
```

### 2. Verify Configuration
After deployment, check the API key status:
```bash
# Health check
curl http://your-domain/api/health

# Key status (requires authentication)
curl -H "Authorization: Bearer YOUR_JWT" \
     http://your-domain/api/settings/saptiva-key
```

Expected response:
```json
{
  "configured": true,
  "mode": "live",
  "source": "environment" | "database",
  "hint": "••••hc_A",
  "status_message": "API key configured"
}
```

## 🔄 Automatic Loading
- API key is loaded automatically on startup
- Database configuration overrides environment variables
- System validates connectivity with SAPTIVA servers
- No manual intervention required after deployment

## ❌ Breaking Changes
- **Removed**: All mock/demo response functionality
- **Removed**: Fallback responses when API fails
- **Changed**: System fails fast if API key is missing
- **Changed**: All responses now come directly from SAPTIVA

## 🛡️ Security Notes
- API keys are encrypted when stored in database
- Environment variables should use secure secret management
- Key hints are shown as `••••last4` for privacy
- Keys are never logged in plaintext

## 🚨 Troubleshooting

### No API Key Error
```
Error: SAPTIVA API key is required but not configured
```
**Solution**: Set SAPTIVA_API_KEY environment variable or configure via admin UI

### API Connection Failed
```
Error: Error calling SAPTIVA API
```
**Solution**: Check network connectivity and API key validity

### Service Status Check
```bash
# Check service logs
docker logs infra-api

# Verify environment
docker exec infra-api env | grep SAPTIVA
```

## ✅ Validation Checklist

Before deployment:
- [ ] SAPTIVA_API_KEY is set in environment
- [ ] API key is valid and active
- [ ] Network access to api.saptiva.com is available
- [ ] Health endpoint returns 200
- [ ] Chat functionality produces real responses (not demo text)
- [ ] No "demo mode" indicators in UI
- [ ] Error handling works correctly without fallbacks

## 📞 Support
If you encounter issues:
1. Check environment variable configuration
2. Verify API key validity with SAPTIVA support
3. Review application logs for specific error messages
4. Test API connectivity manually with curl

---
Generated: $(date)
System: Production Ready ✅