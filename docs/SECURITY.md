# 🔒 Security Guide - Copilotos Bridge

## Critical Security Issues Fixed

### ❌ **PREVIOUS SECURITY VULNERABILITIES** ❌

The following **critical security issues** were identified and **IMMEDIATELY FIXED**:

1. **Hardcoded Production API Keys** 🚨
   - **Risk**: CRITICAL - Production SAPTIVA API key exposed in source code
   - **Impact**: Unauthorized API usage, credential theft, financial losses
   - **Status**: ✅ FIXED - API keys removed from all files

2. **Hardcoded Database Passwords** 🚨
   - **Risk**: HIGH - Default passwords in configuration examples
   - **Impact**: Database compromise, data theft
   - **Status**: ✅ FIXED - Replaced with secure secrets management

3. **Exposed JWT Secrets** 🚨
   - **Risk**: HIGH - JWT signing keys in plain text
   - **Impact**: Session hijacking, privilege escalation
   - **Status**: ✅ FIXED - Secure key generation and storage

## 🛡️ New Security Architecture

### Secrets Management System

We've implemented a **multi-layer secrets management system**:

```
Priority Order:
1. Docker Secrets (/run/secrets/) - HIGHEST SECURITY
2. Environment Variables - MEDIUM SECURITY
3. Secure Files (/etc/copilotos/secrets/) - HIGH SECURITY
4. Fallback to env (development only) - LOW SECURITY
```

### Key Security Features

- ✅ **Zero Hardcoded Credentials**: All secrets loaded dynamically
- ✅ **Secret Validation**: Length, format, and strength validation
- ✅ **Secure Logging**: Credentials automatically masked in logs
- ✅ **Cache TTL**: Secrets cached for max 5 minutes
- ✅ **Fail-Fast**: Production fails immediately if secrets missing
- ✅ **Audit Trail**: All secret access logged (without values)

## 🔐 Production Deployment (SECURE)

### Step 1: Generate Secure Secrets

```bash
# Generate cryptographically secure secrets
./scripts/generate-secrets.py

# OR use OpenSSL directly:
openssl rand -hex 32  # For keys
openssl rand -base64 32 | tr -d "=+/" | cut -c1-25  # For passwords
```

### Step 2: Docker Secrets (Recommended)

```bash
# Setup Docker Swarm secrets
./scripts/setup-docker-secrets.sh

# Deploy with secure configuration
docker stack deploy -c docker-compose.secure.yml copilotos
```

### Step 3: Kubernetes Secrets

```bash
# Create Kubernetes secrets
kubectl create secret generic copilotos-secrets \
  --from-literal=mongodb-password='your-secure-password' \
  --from-literal=redis-password='your-secure-password' \
  --from-literal=jwt-secret-key='your-secure-key' \
  --from-literal=saptiva-api-key='your-api-key'

# Apply secure configuration
kubectl apply -f k8s-secure.yml
```

### Step 4: AWS Secrets Manager

```bash
# Store secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name "copilotos/mongodb-password" \
  --secret-string "your-secure-password"

aws secretsmanager create-secret \
  --name "copilotos/saptiva-api-key" \
  --secret-string "your-api-key"
```

## 🔧 Development Setup (SECURE)

### 1. Local Development

```bash
# Copy and configure environment
cp envs/.env.secrets.template envs/.env.local

# Generate secure secrets
python3 scripts/generate-secrets.py

# Edit envs/.env.local with your values (NEVER commit this file)
```

### 2. Secret File Method

```bash
# Create secure secrets directory
sudo mkdir -p /etc/copilotos/secrets
sudo chmod 700 /etc/copilotos/secrets

# Store secrets in individual files
echo "your-secure-password" | sudo tee /etc/copilotos/secrets/mongodb_password
sudo chmod 600 /etc/copilotos/secrets/*

# The application will automatically detect and use these files
```

## 🚨 Security Checklist

### Pre-Deployment Security Audit

- [ ] **No hardcoded credentials** in source code
- [ ] **Strong passwords** generated (min 24 characters)
- [ ] **Unique secrets** per environment (dev/staging/prod)
- [ ] **Encrypted storage** (Docker secrets, K8s secrets, or vault)
- [ ] **TLS/SSL certificates** configured
- [ ] **Firewall rules** restrict database access
- [ ] **Regular secret rotation** scheduled
- [ ] **Monitoring** for unauthorized access attempts

### Runtime Security

- [ ] **HTTPS enforced** for all connections
- [ ] **Secure cookies** enabled in production
- [ ] **CORS properly configured** with specific origins
- [ ] **Rate limiting** active
- [ ] **Request logging** enabled (without secrets)
- [ ] **Error messages** don't expose sensitive info
- [ ] **Health checks** don't reveal credentials

## 🔄 Secret Rotation

### Automated Rotation (Recommended)

```bash
# Weekly rotation script
#!/bin/bash
NEW_PASSWORD=$(openssl rand -base64 32)
docker secret rm copilotos_mongodb_password
echo "$NEW_PASSWORD" | docker secret create copilotos_mongodb_password -
docker service update --secret-rm old_secret --secret-add new_secret copilotos_api
```

### Manual Rotation

1. Generate new secret
2. Create new Docker secret
3. Update service with new secret
4. Remove old secret
5. Verify application functionality

## 🚫 What NOT to Do

### ❌ **NEVER DO THESE:**

1. **Commit secrets to git** (even private repos)
2. **Share secrets via chat/email/slack**
3. **Use default/demo credentials** in production
4. **Store secrets in config files** without encryption
5. **Log secret values** even for debugging
6. **Reuse secrets** across environments
7. **Skip secret validation** to "make it work"

### ❌ **Bad Examples:**

```bash
# DON'T DO THIS:
export MONGODB_PASSWORD="password123"
export JWT_SECRET="secret"

# DON'T PUT THESE IN CODE:
api_key = "va-ai-123456789..."
password = "admin"
secret = "changeme"
```

### ✅ **Good Examples:**

```bash
# DO THIS:
export MONGODB_PASSWORD="$(openssl rand -base64 32)"
docker secret create mongodb_password /path/to/secure/file

# IN CODE, DO THIS:
api_key = get_secret("SAPTIVA_API_KEY", required=True)
password = get_secret("MONGODB_PASSWORD", min_length=24)
```

## 📊 Security Monitoring

### Log Analysis

```bash
# Monitor secret access (no values logged)
grep "secret loaded" /var/log/copilotos/*.log

# Check for failed authentication
grep "authentication failed" /var/log/copilotos/*.log

# Monitor unusual API usage
grep "rate limit exceeded" /var/log/copilotos/*.log
```

### Metrics to Monitor

- Failed authentication attempts per minute
- Unusual API key usage patterns
- Database connection failures
- Memory/CPU spikes (potential attacks)
- Network connections from unknown IPs

## 🆘 Incident Response

### If Credentials Are Compromised:

1. **Immediate Actions**:
   - Rotate ALL secrets immediately
   - Review access logs for unauthorized usage
   - Check for data exfiltration
   - Document the incident

2. **Assessment**:
   - Determine scope of compromise
   - Identify affected systems
   - Estimate potential damage

3. **Recovery**:
   - Deploy with new secrets
   - Monitor for continued attacks
   - Update security procedures
   - Notify stakeholders if required

### Emergency Contacts

- **Security Team**: security@yourcompany.com
- **DevOps Team**: devops@yourcompany.com
- **On-Call Engineer**: +1-XXX-XXX-XXXX

## 📚 Additional Resources

- [OWASP Security Guidelines](https://owasp.org/www-project-top-ten/)
- [Docker Secrets Documentation](https://docs.docker.com/engine/swarm/secrets/)
- [Kubernetes Secrets Best Practices](https://kubernetes.io/docs/concepts/security/secrets-good-practices/)
- [AWS Secrets Manager Guide](https://docs.aws.amazon.com/secretsmanager/)

---

**⚠️ REMEMBER: Security is not a one-time setup. Regular audits, updates, and monitoring are essential.**