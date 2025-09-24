# 🚀 Production Deployment Guide

## 📋 Overview
This system now operates in **production mode only** - all demo/mock functionality has been removed. SAPTIVA_API_KEY configuration is **required** for operation.

## 🔑 SAPTIVA API Key Configuration

### Environment Variable Setup
```bash
# Required in production environment
SAPTIVA_API_KEY=your-saptiva-api-key-here
SAPTIVA_BASE_URL=https://api.saptiva.com
SAPTIVA_TIMEOUT=120
SAPTIVA_MAX_RETRIES=3
```

### Configuration Priority
1. **Database** - Configured via admin UI (highest priority)
2. **Environment Variable** - SAPTIVA_API_KEY in .env
3. **No Fallback** - System will fail if no key is configured

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