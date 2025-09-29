# 📦 Archive

This directory contains historical documentation that captures important context about past fixes, improvements, and decisions.

## Purpose

Archive documents are kept for:
- **Historical Reference** - Understanding why certain decisions were made
- **Troubleshooting** - Similar issues may arise in the future
- **Onboarding** - New team members can understand project evolution
- **Knowledge Preservation** - Preventing loss of institutional knowledge

## Contents

### Recent (2025-09-29)

**[DEPLOYMENT_FIXES_SUMMARY.md](DEPLOYMENT_FIXES_SUMMARY.md)**
- **Date:** 2025-09-29
- **Purpose:** Documents fixes for 404 errors on Next.js assets and cache issues
- **Key Changes:**
  - Fixed `distDir` configuration
  - Enhanced middleware matcher
  - Implemented Deep Research kill switch
  - Created health check endpoint
- **Status:** ✅ Completed and deployed

**[DEVELOPMENT_IMPROVEMENTS.md](DEVELOPMENT_IMPROVEMENTS.md)**
- **Date:** 2025-09-29  
- **Purpose:** Documents workflow improvements and Makefile enhancements
- **Key Changes:**
  - New comprehensive Makefile with colored output
  - Automatic `.venv` management
  - Fixed authentication API URL issues
  - Created QUICK_START.md and CREDENTIALS.md
- **Status:** ✅ Completed and integrated

### Older Archives

**[SAPTIVA_INTEGRATION_SUMMARY.md](SAPTIVA_INTEGRATION_SUMMARY.md)**
- Summary of SAPTIVA API integration

**[NEXT_STEPS.md](NEXT_STEPS.md)**
- Historical next steps from earlier development phases

**[test_saptiva_integration.py](test_saptiva_integration.py)**
- Original integration test script

## Usage

### When to Reference
- Encountering similar issues (404s, auth errors, Docker permissions)
- Understanding architectural decisions
- Planning future improvements
- Debugging mysterious behavior

### When NOT to Use
- Daily development (use main docs)
- Production deployment (use docs/DEPLOYMENT.md)
- Quick reference (use QUICK_START.md or CREDENTIALS.md)

## Document Lifecycle

Documents move to archive when:
1. ✅ The work is completed and deployed
2. 📅 The information is historical but valuable
3. 🔄 The content has been superseded by newer docs
4. 💡 The context is important for future reference

## Maintenance

Archive documents are **read-only** and should not be updated except to:
- Add clarifying notes at the top
- Fix broken links
- Add cross-references to related archives

---

**Need current documentation?** See [README.md](../../README.md) for the main documentation index.
