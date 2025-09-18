# Dual Environment CI/CD Setup

## Architecture
- **Staging (develop)**: Auto-deploy to Vercel
- **Production (main)**: Auto-deploy to Server (34.42.214.246)

## Required GitHub Secrets

### Vercel Configuration (for staging)
```
VERCEL_TOKEN=your_vercel_token_here
VERCEL_ORG_ID=team_Rmb86n9UYYRs2luERxSHie4i
VERCEL_PROJECT_ID=prj_lASK1K8FCumpXgUE59nXuT9K1kje
```

### Server Configuration (for production)
```
PRODUCTION_SSH_KEY=your_production_ssh_private_key
```

## Setup Instructions

### 1. Generate Vercel Token
1. Go to https://vercel.com/account/tokens
2. Create a new token named "GitHub Actions"
3. Copy the token and add it as `VERCEL_TOKEN` secret

### 2. Configure SSH Key for Production
1. Generate SSH key: `ssh-keygen -t rsa -b 4096 -C "github-actions"`
2. Add public key to server: `ssh-copy-id jf@34.42.214.246`
3. Add private key as `PRODUCTION_SSH_KEY` secret

### 3. Workflow Triggers
- `develop` branch push → Vercel staging deployment
- `main` branch push → Server production deployment

## URLs
- **Staging**: https://copilotos-bridge-jazielflores-projects.vercel.app
- **Production**: http://34.42.214.246

## Status
✅ Secrets configured
✅ SSH keys deployed
🚀 Ready for dual environment CI/CD

## Deployment Process
1. **CI Stage**: Tests, linting, build validation
2. **CD Stage**:
   - If develop → Deploy to Vercel
   - If main → Deploy to production server