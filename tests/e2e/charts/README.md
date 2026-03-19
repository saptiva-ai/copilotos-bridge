# E2E Chart Validators

Component-based validation framework for bank advisor chart responses.
Each test sends a prompt to the backend, parses the SSE response, and runs
a battery of `ComponentCheck` validators against the result.

## Test Files

| File | Chart Type | Prompts | Validators | Focus |
|------|-----------|---------|------------|-------|
| `test_peer_average_chart.py` | Line (scatter) | 2 | 14 (V1-V14) | Peer average INVEX vs PROMEDIO — regression guard for colon/parens parser bug |
| `test_peer_avg_cartera_comercial_chart.py` | Line (scatter) | 3 | 14 (V1-V14) | Cartera comercial peer average — includes text grounding validators |
| `test_variacion_cartera_bar_chart.py` | Horizontal bar | 1 | 14 (V1-V14) | Cartera total delta bar chart — period comparison + markdown table |
| `test_variacion_cartera_comercial_bar_chart.py` | Horizontal bar | 1 | 15 (V1-V15) | Cartera comercial delta bar chart — metric detection + markdown table |
| `test_variacion_cc_sin_gob_bar_chart.py` | Horizontal bar | 1 | 15 (V1-V15) | Cartera comercial sin gobierno — KPI table pipeline |
| `test_chart_persistence.py` | Any | 1 | Custom | Artifact persistence — save/restore cycle across page reloads |

## Running

```bash
# Single test
python tests/e2e/charts/test_peer_avg_cartera_comercial_chart.py

# All chart tests
for f in tests/e2e/charts/test_*.py; do python "$f"; done

# Custom backend URL
TEST_BACKEND_URL=http://localhost:8000 python tests/e2e/charts/test_peer_average_chart.py

# Custom timeout (seconds)
TIMEOUT=180 python tests/e2e/charts/test_variacion_cartera_bar_chart.py
```

Results are saved as JSON in the same directory (e.g. `peer_avg_cartera_comercial_results.json`).

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All checks passed |
| `1` | One or more checks failed |
| `2` | Infrastructure failure (auth, timeout, connection) |

## Validator Catalog

### Chart Structure Validators

These validate that the plotly chart was generated correctly.

| ID | Name | Used In | Description |
|----|------|---------|-------------|
| V1 | `CHART_EXISTS` | All | Chart must exist in response with at least one data trace. Bar chart tests also verify `type=bar` and `orientation=h`. |
| V2 | `PEER_AVG_SERIES` | Peer avg tests | Chart must have exactly 2 series: `INVEX` and `PROMEDIO`. Detects wrong handler routing (>5 series = EvolucionBancoHandler fallback). |
| V2 | `PERIOD_PARSING` | Delta bar tests | Chart title or metadata must reference both comparison dates (e.g. 2024 and 2025). |
| V3 | `NO_SYSTEM_LEAK` | Peer avg tests | Response must NOT contain major system banks (BBVA, Santander, etc.) that weren't requested. Guards against `peer_average_mode=False` regression where all 46 banks are returned. |
| V3 | `METRIC_DETECTION` | CC delta tests | Chart title must contain the specific metric (`CARTERA_COMERCIAL_TOTAL` or `CARTERA_COMERCIAL_SIN_GOB`). |

### Data Integrity Validators

These validate the actual data values in the chart.

| ID | Name | Used In | Description |
|----|------|---------|-------------|
| V4 | `PERIOD_COVERAGE` | Peer avg tests | Data should span the requested range (e.g. 2021-01 to recent). |
| V4 | `BANK_COVERAGE` | Delta bar tests | At least 7/10 requested banks must appear in chart. |
| V5 | `DATA_POINTS` | Peer avg tests | Each series should have >= 48 data points (~4 years monthly). |
| V5 | `INVEX_HIGHLIGHT` | Delta bar tests | INVEX bar must be colored red (`#E45756`). |
| V6 | `VALUES_PLAUSIBLE` | Peer avg tests | Y-values must be positive and non-zero. |
| V6 | `NEUTRAL_COLORS` | Delta bar tests | Non-INVEX bars must be grey (`#999999`). |
| V7 | `PROMEDIO_MAGNITUDE` | Peer avg tests | PROMEDIO must be a peer average (not a sum). Rejects values > 1e13. |
| V7 | `ZEROLINE` | Delta bar tests | `xaxis.zeroline=true` for variation charts. |
| V8 | `TABLE_DATA` | Delta bar tests | Response must include `table_data` with expected columns (4 for cartera total, 4+ for others). |
| V9 | `VARIATION_VALUES` | Delta bar tests | Variation percentages must be in plausible range (`-100%` to `+200%`). |
| V10 | `TEXT_LABELS` | Delta bar tests | Bar text labels must show formatted percentages with `%` sign. |
| V12 | `TABLE_BANK_COVERAGE` | All delta bar tests | `table_data.rows` must cover at least 7/10 requested banks. |
| V14/V15 | `MARKDOWN_TABLE` | All delta bar tests | LLM text must contain a markdown table with pipe-separated columns matching chart banks. |

### Anti-Fabrication Validators

These detect when the LLM invents data or contradicts real data.

| ID | Name | Used In | Description |
|----|------|---------|-------------|
| V8 | `NO_FABRICATION` | All | Response text must NOT contain fabrication markers: "estimado", "proyectado", "aproximado basado en". Bar chart tests also detect suspiciously round values (`$XX,500,000,000`). |
| V9 | `NO_TEXT_CONTRADICTION` | Peer avg tests | LLM text must NOT deny having data when the chart contains valid data. Detects phrases like "no tengo datos", "no está disponible", etc. |
| V11 | `NO_TEXT_CONTRADICTION` | All delta bar tests | Same as above but checks against trace `x` values instead of trace count. |

### Text Grounding Validators

These verify that the LLM's narrative is consistent with chart data.

| ID | Name | Used In | Description |
|----|------|---------|-------------|
| V10 | `LAYOUT_TITLE` | Peer avg CC test | Chart title must contain "comercial". Reports `PARTIAL_TITLE` if "cartera" present but "comercial" missing. |
| V11 | `INVEX_IN_TEXT` | Peer avg tests | LLM response text must mention INVEX by name. |
| V12 | `PROMEDIO_IN_TEXT` | Peer avg tests | LLM text must reference "promedio", "pares", "average", or "peer". |
| V12 | `TEXT_CHART_COHERENCE` | All delta bar tests | Extracts percentages from LLM bullet points (`- BANK: NN.N%`) and compares against chart variation values. Tolerance: 2 percentage points. |
| V13 | `TEXT_VALUES_COHERENCE` | All peer avg tests | Extracts monetary values from LLM text (`$14,230 millones`, `NN MDP`, raw numbers >= 1e9) and compares against the last Y-values of each trace. Tolerance: 20% relative difference. |
| V14 | `TEXT_DIRECTION_COHERENCE` | All peer avg tests | Verifies directional claims match reality. If INVEX < PROMEDIO in chart, LLM must NOT say "por encima", "supera", "ventaja relativa", etc. Checks 12 above-phrases and 8 below-phrases in Spanish and English. |
| V14 | `TEXT_CHART_COHERENCE` | CC delta tests | Same as V12 in `test_variacion` — line-level percentage cross-check. |

### Cross-Prompt Validators

These run across multiple prompt variants (peer average tests only).

| Check | Description |
|-------|-------------|
| `CROSS_PROMPT_CONSISTENCY` | All prompt variants must produce the same trace names (series). Detects cases where prompt A routes to peer_average handler but prompt B falls through to evolution handler. |

## Architecture

```
ComponentCheck (name, description, validate_fn)
     │
     ▼
run_checks(response) ──▶ [CheckResult(check, passed, detail), ...]
     │
     ▼
run_single_prompt(token, prompt, label) ──▶ (results, raw_response)
     │
     ▼
main() ──▶ runs N prompts, cross-checks, saves JSON, returns exit code
```

### Data Flow

```
User prompt
  │
  ▼
send_chat_message() ──▶ SSE stream ──▶ parse_sse_response()
  │                                        │
  ▼                                        ▼
Backend:                              Parsed response dict:
  QueryRouter                           ├─ content: str (LLM text)
  → QuerySpecParser                     ├─ bank_chart:
  → Handler                             │   ├─ plotly_config: {data, layout}
  → EvolutionUseCase                    │   ├─ table_data: {columns, rows}
  → chart_formatter                     │   └─ bank_names: [str]
  → SystemPromptBuilder                 └─ events: [str]
  → LLM streaming
```

### Adding a New Validator

1. Write a function `_check_your_name(resp: dict) -> tuple[bool, str]`
2. Return `(True, "detail msg")` for pass, `(False, "REASON: detail")` for fail
3. Add a `ComponentCheck(name="VN_YOUR_NAME", ...)` to `ALL_CHECKS`
4. Update this README

### Naming Conventions

- Validator IDs are sequential per test file: `V1`, `V2`, ... `V15`
- Validator names use UPPER_SNAKE: `NO_FABRICATION`, `TEXT_CHART_COHERENCE`
- Failure details start with a tag: `CHART_MISSING:`, `REGRESSION:`, `INCOHERENT:`
- Soft passes (inconclusive): `SOFT_PASS:` or `SKIP:` prefix
