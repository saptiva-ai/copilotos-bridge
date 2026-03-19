---
name: quick-checks
description: Run minimal checks and capture output; collect logs on failure.
argument-hint: "[RUN_E2E=1 START=1]"
allowed-tools: [Bash, Read]
disable-model-invocation: true
---

!bash
set -euo pipefail

root_dir="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$root_dir"

out_file=".claude/docs/quick_checks.md"
log_file=".claude/docs/quick_checks_logs.md"

mkdir -p .claude/docs

echo "+ preflight (.claude/hooks/preflight.sh)" | tee "$out_file"
if ! ./.claude/hooks/preflight.sh 2>&1 | tee -a "$out_file"; then
  echo "preflight failed (exit $?)" | tee -a "$out_file"
fi

echo "" | tee -a "$out_file"
echo "+ quick checks" | tee -a "$out_file"

set +e
./.claude/skills/project-navigation/scripts/quick_checks.sh 2>&1 | tee -a "$out_file"
rc=${PIPESTATUS[0]}
set -e

if [[ $rc -ne 0 ]]; then
  echo "" | tee -a "$out_file"
  echo "quick checks failed (exit $rc). collecting logs..." | tee -a "$out_file"

  services=$(docker compose -f infra/docker-compose.yml config --services 2>/dev/null || true)
  log_services=()
  for svc in backend redis mongodb minio; do
    if printf '%s\n' "$services" | grep -qx "$svc"; then
      log_services+=("$svc")
    fi
  done

  if [[ ${#log_services[@]} -gt 0 ]]; then
    docker compose -f infra/docker-compose.yml logs --tail=200 "${log_services[@]}" > "$log_file" || true
    echo "logs saved to $log_file" | tee -a "$out_file"
  else
    echo "no known services found for logs" | tee -a "$out_file"
  fi

  exit "$rc"
fi

echo ""
echo "If failed, review .claude/docs/quick_checks.md and .claude/docs/quick_checks_logs.md"
