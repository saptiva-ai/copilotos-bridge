# Happy Path Test Suite - Integration Guide

## Overview

This document explains how the Happy Path test suite is structured and how to integrate it into your development workflow.

## Structure

```
tests/
├── test_happy_path_suite.py       # Main test runner (40 test cases)
└── fixtures/
    └── happy_path/
        ├── README.md              # Usage documentation
        ├── test_cases.yaml        # Reference database of all 40 cases
        ├── expected_results.json  # Extracted results from test runs
        ├── extract_expected_results.py  # Extraction script
        └── INTEGRATION.md         # This file
```

## What Changed

### Before
- Test outputs were stored locally in `happy_path_debug/` (now gitignored)
- No structured reference for expected results
- Difficult to share test cases with team

### After
- **`test_cases.yaml`**: Complete reference of all 40 test cases with expected behavior
- **`expected_results.json`**: Database of actual test run results for analysis
- **`extract_expected_results.py`**: Tool to extract and analyze test outputs
- **Documentation**: Clear usage guides and maintenance procedures

## Files Explained

### 1. `test_cases.yaml`
**Purpose**: Source of truth for test case definitions and expected behavior

**Contains**:
- All 40 test case definitions
- Expected response types (chart, rag, clarification)
- Expected keywords and SQL patterns
- Known issues and affected test IDs

**Use for**:
- Reference when writing new tests
- Understanding test expectations
- Bug triage (known_issues section)

### 2. `expected_results.json`
**Purpose**: Database of actual test execution results

**Contains**:
- Parsed SSE responses
- Extracted SQL queries
- Chart configurations
- Performance metrics
- Failure reasons

**Use for**:
- Regression detection
- Performance benchmarking
- Debugging test failures

### 3. `extract_expected_results.py`
**Purpose**: Extract structured data from test run outputs

**Usage**:
```bash
# After running tests with --save-all
python tests/test_happy_path_suite.py --save-all

# Extract results
python tests/fixtures/happy_path/extract_expected_results.py
```

**Workflow**:
1. Run tests and save outputs to `happy_path_debug/`
2. Run extraction script
3. Review `expected_results.json`
4. Update `test_cases.yaml` if expectations changed

## Integration with CI/CD

### Recommended Setup

```yaml
# Example .github/workflows/test.yml
- name: Run Happy Path Suite
  run: |
    python tests/test_happy_path_suite.py --max 10 --stop-on-fail

- name: Upload debug artifacts on failure
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: happy-path-debug
    path: happy_path_debug/
```

### Performance Gating

Use tier thresholds to gate deployments:
- **Tier 1** (simple queries): Must be < 2s
- **Tier 2** (complex queries): Must be < 8s
- **Tier 3** (RAG queries): Must be < 5s

## Development Workflow

### Adding a New Test Case

1. **Add to `test_cases.yaml`**:
```yaml
- id: 41
  query: "Nueva consulta aquí"
  category: "NL2SQL"
  expected_type: "chart"
  expected_keywords: ["keyword1", "keyword2"]
```

2. **Add to `test_happy_path_suite.py`**:
```python
TestCase(41, "NL2SQL", "Nueva consulta aquí", 1, "chart", ["keyword1", "keyword2"])
```

3. **Run and validate**:
```bash
python tests/test_happy_path_suite.py --ids 41 --verbose --save-all
```

4. **Extract and document**:
```bash
python tests/fixtures/happy_path/extract_expected_results.py
# Review output and update test_cases.yaml if needed
```

### Debugging Failed Tests

1. **Run with verbose output**:
```bash
python tests/test_happy_path_suite.py --ids 7 --verbose --save-all
```

2. **Check debug output**:
```bash
cat happy_path_debug/07__*.json | jq '.sse.parsed.bank_chart.metadata'
```

3. **Compare with expected**:
```bash
cat tests/fixtures/happy_path/expected_results.json | jq '.results[] | select(.test_id==7)'
```

4. **Update expectations if behavior changed intentionally**

### Updating Expected Results

After fixing bugs or changing behavior:

1. Run full suite with save-all:
```bash
python tests/test_happy_path_suite.py --save-all
```

2. Extract new expected results:
```bash
python tests/fixtures/happy_path/extract_expected_results.py
```

3. Review changes:
```bash
git diff tests/fixtures/happy_path/expected_results.json
```

4. Update `test_cases.yaml` known_issues section if applicable

5. Commit both files together:
```bash
git add tests/fixtures/happy_path/
git commit -m "test: update happy path expected results after [fix description]"
```

## Known Issues Tracking

The `test_cases.yaml` file includes a `known_issues` section:

```yaml
known_issues:
  - issue: "Chart has no data points"
    affected_cases: [7, 14, 21, 22, 23, 28, 29, 30]
    priority: "high"
```

**Workflow**:
1. When tests fail consistently, document in `known_issues`
2. Link to GitHub issue or Jira ticket
3. Mark priority (high/medium/low)
4. Remove from `known_issues` when fixed

## Benefits

### For Developers
- Clear test expectations documented in YAML
- Easy debugging with structured outputs
- Fast iteration with selective test running

### For QA
- Reference database for manual validation
- Performance benchmarks for regression detection
- Structured failure analysis

### For Team
- Shared understanding of expected behavior
- Git-tracked test cases (versioned)
- Historical record of test results

## Future Enhancements

### Planned
- [ ] Automated comparison of expected_results.json across commits
- [ ] Performance regression detection in CI
- [ ] Visual diff tool for chart configurations
- [ ] Integration with test reporting dashboard

### Ideas
- [ ] Auto-generate test cases from user query logs
- [ ] Fuzzy matching for title validation
- [ ] Parallel test execution
- [ ] Test case prioritization based on feature usage

## Questions?

See the main [README.md](./README.md) for usage examples, or check the [test_happy_path_suite.py](../../test_happy_path_suite.py) source code for implementation details.
