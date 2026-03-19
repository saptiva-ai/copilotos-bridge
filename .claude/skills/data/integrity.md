# Data Integrity Playbook

## Core Verification Scripts

| Script | Description | Usage |
|--------|-------------|-------|
| `verify_weaviate_content.py` | Validates consistency between Source and Vector DB | `python scripts/verify_weaviate_content.py` |
| `fix-orphaned-drafts.py` | Identifies and links/removes orphaned message drafts | `python scripts/database/fix-orphaned-drafts.py` |

## Routine Checks

### 1. Vector Store Consistency
Check if the number of objects in Weaviate matches the source of truth (PostgreSQL/Docs).

```bash
cd apps/backend
python scripts/verify_weaviate_content.py --collection BankAdvisor
```

### 2. MongoDB Cleanup
Remove conversation artifacts that have no owners or are stale.

```bash
# Dry run first
python scripts/database/fix-orphaned-drafts.py --dry-run

# Apply fixes
python scripts/database/fix-orphaned-drafts.py --apply
```

### 3. Unique Index Validation
Ensure business rules (like unique emails) are enforced at DB level.

```bash
python scripts/database/apply-email-unique-index.py
```
