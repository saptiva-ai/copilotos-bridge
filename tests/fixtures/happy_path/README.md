# Happy Path Test Suite - Expected Results

This directory contains reference data and expected results for the Happy Path test suite validation.

## Purpose

The Happy Path suite validates 40 core queries across different categories:
- **RAG**: Regulatory definitions and knowledge
- **NL2SQL**: Metric queries with SQL generation
- **Comparison**: INVEX vs Sistema comparisons
- **Temporal**: Time-based analysis
- **Multi-Bank**: Cross-bank rankings and comparisons
- **Segmentation**: Portfolio segment queries
- **Complex**: Multi-dimensional queries
- **Edge Cases**: Query variations and alternative phrasings

## Test Case Structure

Each test case includes:
- `id`: Unique identifier (1-40)
- `category`: Test category
- `query`: Natural language query
- `tier`: Performance tier (1=fast, 2=medium, 3=slow)
- `expected_type`: Response type (rag, chart, clarification)
- `expected_keywords`: Keywords that should appear in response
- `value_range`: Expected numeric range (for metrics)

## Expected Results Database

The `expected_results.json` file contains validated responses from successful test runs, including:
- SQL queries generated
- Chart configurations
- Response content samples
- Performance benchmarks

## Usage

### Running the full suite
```bash
python tests/test_happy_path_suite.py
```

### Running specific categories
```bash
python tests/test_happy_path_suite.py --category NL2SQL
```

### Running specific test IDs
```bash
python tests/test_happy_path_suite.py --ids 6,7,8
```

### Debug mode (save all outputs)
```bash
python tests/test_happy_path_suite.py --save-all --verbose
```

## Maintenance

When updating test cases:
1. Run the test suite with `--save-all` to capture outputs
2. Review generated files in `happy_path_debug/`
3. Extract validated patterns and update `expected_results.json`
4. Document any new expectations or changes

## Performance Tiers

- **Tier 1**: < 2s - Simple metric queries
- **Tier 2**: < 8s - Comparisons and temporal analysis
- **Tier 3**: < 5s - RAG/knowledge queries
