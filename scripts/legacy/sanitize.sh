#!/bin/bash
# Script to sanitize Capital414 and COPILOTO_414 references for open-source

set -e

echo "🧹 Sanitizing repository for open-source..."

# Find all relevant files (excluding node_modules, .git, dist, build)
FILES=$(find . -type f \( -name "*.md" -o -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.yaml" -o -name "*.yml" -o -name "*.sh" -o -name "*.json" -o -name "*.conf" \) \
  -not -path "./node_modules/*" \
  -not -path "./.git/*" \
  -not -path "./dist/*" \
  -not -path "./build/*" \
  -not -path "./.next/*" \
  -not -path "./venv/*" \
  -not -path "./.venv/*")

# Counter for changes
CHANGED=0

# Replace COPILOTO_414 with "Document Audit"
echo "📝 Replacing COPILOTO_414 with 'Document Audit'..."
for file in $FILES; do
  if grep -q "COPILOTO_414" "$file" 2>/dev/null; then
    sed -i 's/COPILOTO_414/Document Audit/g' "$file"
    echo "  ✓ $file"
    ((CHANGED++))
  fi
done

# Replace Capital414 / capital414 with generic references
echo "📝 Replacing Capital414 references..."
for file in $FILES; do
  if grep -qE "Capital414|capital414" "$file" 2>/dev/null; then
    # Replace in URLs and paths
    sed -i 's/capital414\/[^/]*/client-project/g' "$file"
    sed -i 's/Capital414/ClientProject/g' "$file"
    sed -i 's/capital414/client-project/g' "$file"
    echo "  ✓ $file"
    ((CHANGED++))
  fi
done

# Remove specific client data directories if they exist
echo "🗑️  Removing client-specific data..."
if [ -d "packages/tests-e2e/tests/data/capital414" ]; then
  rm -rf "packages/tests-e2e/tests/data/capital414"
  echo "  ✓ Removed packages/tests-e2e/tests/data/capital414/"
fi

if [ -d "docs/archive/legacy_2025/capital414" ]; then
  rm -rf "docs/archive/legacy_2025/capital414"
  echo "  ✓ Removed docs/archive/legacy_2025/capital414/"
fi

echo "✅ Sanitization complete! Changed $CHANGED files."
echo "📋 Next steps:"
echo "   1. Review changes: git diff"
echo "   2. Commit: git add . && git commit -m 'chore: sanitize client references for open-source'"
