#!/usr/bin/env bash
# =========================================================
# SAFE DEPLOYMENT SCRIPT
# =========================================================
# Usage: ./scripts/DEPLOY-NOW.sh [deploy|deploy-fast|deploy-clean]

set -euo pipefail

SCRIPT_DIR="$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd)"
REPO_ROOT="$(git -C \"${SCRIPT_DIR}\" rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${REPO_ROOT}"

DEPLOY_METHOD="${1:-deploy}"
ALLOWED_METHODS=(
  "deploy"
  "deploy-clean"
  "deploy-quick"
  "deploy-tar"
  "deploy-fast"
  "deploy-tar-fast"
  "deploy-registry"
  "deploy-prod"
)

log_header() {
  printf '\n%s\n' "============================================================"
  printf '%s\n' "$1"
  printf '%s\n\n' "============================================================"
}

log_section() {
  printf '\n--- %s ---\n\n' "$1"
}

log_ok() {
  printf '[ OK ] %s\n' "$1"
}

log_warn() {
  printf '[WARN] %s\n' "$1"
}

log_error() {
  printf '[FAIL] %s\n' "$1"
}

abort() {
  log_error "$1"
  printf 'Deployment aborted.\n'
  exit 1
}

ensure_allowed_method() {
  for method in "${ALLOWED_METHODS[@]}"; do
    if [[ "${method}" == "${DEPLOY_METHOD}" ]]; then
      return
    fi
  done
  abort "Unsupported deployment method: ${DEPLOY_METHOD}"
}

ensure_allowed_method

log_header "SAFE DEPLOYMENT WORKFLOW"
printf 'Method: make %s\n' "${DEPLOY_METHOD}"
printf 'Time:   %s\n\n' "$(date '+%Y-%m-%d %H:%M:%S')"

# Phase 1: Pre-flight checks
log_section "Phase 1/5: Pre-flight checks"

if ! git status --short; then
  abort "Unable to read git status"
fi

if [[ -n "$(git status --porcelain)" ]]; then
  log_warn "Uncommitted changes detected."
  read -r -p "Continue anyway? (y/N) " reply
  if [[ ! "${reply}" =~ ^[Yy]$ ]]; then
    abort "Clean the working tree and rerun the script."
  fi
else
  log_ok "Working tree is clean."
fi

if [[ ! -x scripts/backup-mongodb.sh || ! -x scripts/restore-mongodb.sh ]]; then
  abort "Backup scripts not found or not executable."
fi
log_ok "Backup scripts present."

if ! make help >/dev/null 2>&1; then
  abort "Makefile is not accessible."
fi

if ! make help | grep -q "backup-mongodb-prod"; then
  log_warn "Target backup-mongodb-prod not found in Makefile (check Makefile)."
else
  log_ok "Makefile deployment targets available."
fi

# Phase 2: Pre-deployment backup reminder
log_section "Phase 2/5: Pre-deployment backup"
printf 'Creating a fresh backup is mandatory before deploying.\n'
read -r -p "Have you already created the latest production backup? (y/N) " backup_confirm
if [[ ! "${backup_confirm}" =~ ^[Yy]$ ]]; then
  printf '\nRun on production:\n'
  printf '  cd ~/octavios-bridge\n'
  printf '  source envs/.env.prod\n'
  printf '  make backup-mongodb-prod\n\n'
  read -r -p "Press Enter to continue once the backup is done..." _
fi

# Phase 3: Deployment
log_section "Phase 3/5: Deployment"
printf 'About to run: make %s\n' "${DEPLOY_METHOD}"
printf 'Estimated duration: 8-12 minutes (depends on method).\n'
read -r -p "Proceed with deployment? (Y/n) " proceed
if [[ "${proceed}" =~ ^[Nn]$ ]]; then
  printf 'Deployment cancelled by user.\n'
  exit 0
fi

START_TIME="$(date +%s)"
if ! make "${DEPLOY_METHOD}"; then
  abort "Deployment command failed."
fi
END_TIME="$(date +%s)"
DURATION=$((END_TIME - START_TIME))
log_ok "Deployment completed in ${DURATION}s."

# Phase 4: Verification
log_section "Phase 4/5: Post-deployment verification"
printf 'Waiting 30 seconds for services to stabilise...\n'
sleep 30

if make deploy-status >/dev/null 2>&1; then
  log_ok "deploy-status completed (see output above for details)."
else
  log_warn "deploy-status failed locally. Run checks manually on the server."
fi

# Phase 5: Post-deploy actions
log_section "Phase 5/5: Post-deployment tasks"
cat <<'EOF'
Follow-up checklist:
  1. Clear cache on the server: make clear-cache
  2. Validate backups: make monitor-backups (server)
  3. Perform functional smoke tests in production
  4. Tail API/web logs for at least 5 minutes
EOF

# Summary
log_header "DEPLOYMENT WORKFLOW COMPLETED"
printf 'Deployment summary:\n'
printf '  Method:   %s\n' "${DEPLOY_METHOD}"
printf '  Duration: %ss\n' "${DURATION}"
printf '  Finished: %s\n\n' "$(date '+%Y-%m-%d %H:%M:%S')"

cat <<'EOF'
Next steps:
  - Review the playbook: docs/operations/deployment.md
  - Update the deployment log / incident tracker if needed
  - Share status with the team
EOF

printf '\nDone.\n'

