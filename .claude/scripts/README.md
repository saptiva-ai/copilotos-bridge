# Claude Validation Scripts

Scripts to prevent process gaps and ensure quality before marking work as DONE.

## Scripts Overview

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `validate_epic.sh` | Validate EPIC before marking DONE | Before closing any EPIC |
| `phase_gate.sh` | Enforce phase transitions | Between workflow phases |

---

## validate_epic.sh

**Purpose**: Prevents EPICs from being marked DONE without proper validation.

**What it checks**:
1. ✅ All Target Files exist
2. ✅ Demo Evidence is present
3. ✅ Validation Commands are documented
4. ✅ Definition of Done has criteria

**Usage**:
```bash
./.claude/scripts/validate_epic.sh docs/context/EPICS/EPIC-HU4.md
```

**Exit codes**:
- `0` - Validation passed, EPIC can be marked DONE
- `1` - Validation failed, fix issues first

**Example output**:
```
==========================================
EPIC Validation Script
==========================================
File: docs/context/EPICS/EPIC-HU4.md

[CHECK 1] Verifying Target Files...
  ✓ plugins/bank-advisor-private/src/bankadvisor/handlers/knowledge_handler.py
  ✓ plugins/bank-advisor-private/src/bankadvisor/handlers/__init__.py
  ✓ plugins/bank-advisor-private/src/main.py
  PASSED: All target files exist

[CHECK 2] Verifying Demo Evidence...
  ✓ docs/demos/EPIC-HU4_screenshot.png
  ✓ docs/demos/EPIC-HU4_demo.mp4

[CHECK 3] Checking Validation Commands Section...
  ✓ Found 5 validation commands documented

[CHECK 4] Checking Definition of Done...
  ✓ Found 8 passing criteria

==========================================
VALIDATION PASSED
EPIC is ready to be marked DONE
```

---

## phase_gate.sh

**Purpose**: Enforces proper workflow phase transitions.

**Phases**:
- `explore` - Check prerequisites before exploration
- `plan` - Check prerequisites before planning
- `code` - Check prerequisites before implementation
- `test` - Check prerequisites before testing
- `review` - Check prerequisites before review
- `done` - Check all phases complete before marking DONE

**Usage**:
```bash
# Check if ready for testing phase
./.claude/scripts/phase_gate.sh test T-20260102-feature

# Check if ready to mark as DONE
./.claude/scripts/phase_gate.sh done T-20260102-feature
```

**What it checks per phase**:

| Phase | Checks |
|-------|--------|
| `explore` | Epic linked in ticket |
| `plan` | Exploration context exists |
| `code` | Plan approved, status updated |
| `test` | Code complete, pr_files listed |
| `review` | Tests passed, status is TESTING |
| `done` | All phases complete, EPIC validated |

**Exit codes**:
- `0` - Gate passed, proceed to next phase
- `1` - Gate failed, fix prerequisites first

---

## CI/CD Integration

### GitHub Actions Workflow

The `.github/workflows/epic-validation.yml` workflow runs automatically when:
- EPICs are modified in a PR
- Manually triggered via workflow_dispatch

**What it does**:
1. Detects modified EPIC files
2. Runs `validate_epic.sh` on each
3. Comments on PR with results
4. Blocks merge if validation fails

**Manual trigger**:
```bash
# Via GitHub UI: Actions → EPIC Validation → Run workflow
# Specify: docs/context/EPICS/EPIC-HUx.md
```

---

## Process Changes Summary

### Before (What led to HU4 gap)

```
Documentation → Assumed Execution → Self-Attestation
     ↓                 ↓                  ↓
  Write EPIC      Hope it works     Mark ✅ DONE
     ↓                 ↓                  ↓
 NO VERIFICATION AT ANY STEP
```

### After (With validation scripts)

```
Documentation → Automated Checks → Evidence Required → Gated Completion
     ↓                 ↓                  ↓                  ↓
  Write EPIC      CI validates      Demo required      Can't bypass
     ↓                 ↓                  ↓                  ↓
    ✅ Files exist    ✅ Commands     ✅ Screenshot    ✅ phase_gate
    ✅ Tests work     ✅ DoD          ✅ Sign-off      ✅ CI passes
```

---

## EPIC Template Updates

The PRD builder template (`.claude/skills/prd-builder/template.md`) now includes:

### New Section: Demo Evidence (REQUIRED)

```markdown
## Demo Evidence (REQUIRED)

| Evidence Type | Location | Date | Verified By |
|---------------|----------|------|-------------|
| Screenshot | `docs/demos/EPIC-HUx_screenshot.png` | | |
| Demo Video | `docs/demos/EPIC-HUx_demo.mp4` | | |
| Stakeholder Sign-off | Email/Slack link | | @[name] |
```

### Updated Definition of Done

Now includes:
```markdown
| All target files exist | `.claude/scripts/validate_epic.sh` | Exit 0 |
| Demo evidence | Check Demo Evidence table above | All files exist |
```

---

## How to Use in Workflow

### When Creating a New EPIC

1. Use PRD builder to generate EPIC from template
2. Template now includes Demo Evidence section automatically
3. Fill in Target Files as you implement

### When Implementing an EPIC

1. Follow normal workflow (explore → plan → code → test → review)
2. Use `phase_gate.sh` to verify readiness for each phase:
   ```bash
   ./.claude/scripts/phase_gate.sh code T-xxx
   ./.claude/scripts/phase_gate.sh test T-xxx
   ```

### Before Marking EPIC as DONE

1. Create demo evidence:
   ```bash
   # Record screen or take screenshot
   # Save to docs/demos/EPIC-HUx_screenshot.png
   ```

2. Run validation script:
   ```bash
   ./.claude/scripts/validate_epic.sh docs/context/EPICS/EPIC-HUx.md
   ```

3. Fix any issues reported

4. Only mark DONE when validation passes

5. PR will be automatically validated by CI

---

## Troubleshooting

### "File not found" errors

**Problem**: `validate_epic.sh` reports files don't exist

**Solution**:
1. Check the Target Files table in your EPIC
2. Verify paths are correct (relative to project root)
3. Create missing files or remove from table if not needed

### "No demo evidence" warnings

**Problem**: `validate_epic.sh` warns about missing demo files

**Solution**:
1. Record a screen capture showing the feature working
2. Save to `docs/demos/EPIC-HUx_demo.mp4`
3. Take a screenshot: `docs/demos/EPIC-HUx_screenshot.png`
4. Update Demo Evidence table in EPIC

### Phase gate blocks transition

**Problem**: `phase_gate.sh` blocks moving to next phase

**Solution**:
1. Read the error message carefully
2. Fix the prerequisite (e.g., update ticket status, add pr_files)
3. Run phase gate again

---

## Related Documentation

- [Post-Mortem: HU4 Integration Gap](../../docs/context/project/POSTMORTEMS/2026-01-02_HU4_integration_gap.md)
- [Audit: Claude Workflow Gaps](../../docs/context/project/AUDITS/2026-01-02_claude_workflow_gaps.md)
- [PRD Builder Template](../.claude/skills/prd-builder/template.md)
- [Orchestration Workflow](../.claude/skills/orchestration-playbooks/workflow.md)
