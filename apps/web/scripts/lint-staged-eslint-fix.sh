#!/usr/bin/env bash
set -euo pipefail

# ESLint v9 defaults to "flat config" (eslint.config.js) and will ignore .eslintrc.*.
# Our Next.js app still uses `.eslintrc.json`, so we force legacy config mode for lint-staged.
export ESLINT_USE_FLAT_CONFIG=false

# Use pnpm exec so we always resolve the local eslint binary in CI/dev.
pnpm exec eslint --fix "$@"

