# Deployment Lessons & Post-Mortems

This directory contains historical records of **deployment incidents**, post-mortems, and the lessons learned from them.

> **Note:** For architecture guides (UV, CI/CD, etc.), see [architectures/](../../../00_architecture/deployment/).

## Incident Reports (2026)

- [Web Build Environment Variables (Feb 5)](2026-02-05_web_build_env_incident.md) - **CRITICAL**: `NEXT_PUBLIC_API_URL` hardcoded at build time causing CORS errors. Always verify web builds.

## Deployment Reports (2026)

- [v1.3.2 Deployment](2026-01-07_deployment_v1.3.2.md) - Critical fixes and Weaviate Cloud migration.
- [v1.3.0 Deployment](2026-01-06_deploy_v1.3.0.md) - Transition to Weaviate Cloud and Next.js Docker fixes.

## Incident Reports (2025)

- [Data Loss Incident (Oct 9)](2025-10-09_data_loss_incident.md) - Database backup lessons.
- [Deployment Failures (Oct 9)](2025-10-09_deployment_failures.md) - Named volume issues.
- [Prod Deploy Report (Oct 11)](2025-10-11_prod_deploy_report.md) - Production debugging.
- [Deploy Errors Summary (Oct 16)](2025-10-16_deploy_errors_summary.md) - Common error patterns.

## Key Takeaways for Operators

1. **Volume Persistence**: Always understand where your data lives. Named volumes can persist code you thought you updated.
2. **Environment Drift**: Production is not Local. Always test with `docker-compose.production.yml` logic when possible.
3. **Database Backups**: Never deploy without a snapshot.
4. **Next.js Build-Time Variables**: `NEXT_PUBLIC_*` variables are inlined at build time, not runtime. Always verify web bundles before pushing. See [Web Build Verification Runbook](../runbooks/web_build_verification.md).
