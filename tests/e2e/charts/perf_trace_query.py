#!/usr/bin/env python3
"""
Performance trace: measures SSE event timing for query latency analysis.

Sends a banking query and records the timestamp of each SSE event
to identify which pipeline phases dominate latency.

Usage:
    python tests/e2e/charts/perf_trace_query.py [prompt_index]

    prompt_index: 0=RANKING, 1=TREND, 2=ICAP (default: 0)
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.helpers import get_auth_token

BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("TIMEOUT", "120"))

PROMPTS = [
    # 0: RANKING snapshot — quebrantos
    (
        "Muéstrame un ranking de los quebrantos de cartera comercial "
        "para INVEX, BBVA, BANORTE, SANTANDER, SCOTIABANK y HSBC "
        "del mes más reciente."
    ),
    # 1: TREND — tasa MN
    (
        "Crea una gráfica donde se compare la tasa promedio en Moneda Nacional "
        "de INVEX contra el promedio de los bancos: MONEX, BANCREA, SABADELL, "
        "BANCA MIFEL, MULTIVA, AFIRME, BANSI, VE POR MAS Y BANCO BASE. "
        "De enero 2017 hasta el dato más reciente que tengas."
    ),
    # 2: ICAP snapshot
    (
        "Muéstrame el Índice de Capitalización (ICAP) más reciente para los "
        "10 bancos más grandes de México en una gráfica de barras. "
        "Marca a INVEX en rojo y muestra la línea del mínimo regulatorio."
    ),
]


@dataclass
class SSEEvent:
    timestamp_ms: float
    event_type: str
    data_len: int
    content_preview: str = ""


@dataclass
class TraceResult:
    prompt: str
    events: list[SSEEvent] = field(default_factory=list)
    t_start: float = 0.0
    t_end: float = 0.0
    error: str | None = None


def trace_query(token: str, prompt: str) -> TraceResult:
    """Send query and record timestamp of each SSE event."""
    result = TraceResult(prompt=prompt)

    hdrs = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream",
    }
    payload = {
        "message": prompt,
        "stream": True,
        "model": os.environ.get("TEST_MODEL", "Saptiva Turbo"),
    }

    result.t_start = time.perf_counter()

    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/chat",
            json=payload,
            headers=hdrs,
            stream=True,
            timeout=TIMEOUT,
        )
    except Exception as exc:
        result.error = str(exc)
        result.t_end = time.perf_counter()
        return result

    if resp.status_code != 200:
        result.error = f"HTTP {resp.status_code}"
        result.t_end = time.perf_counter()
        return result

    current_event = None

    for line in resp.iter_lines():
        if not line:
            continue

        ts = time.perf_counter()
        decoded = line.decode("utf-8")

        if decoded.startswith("event:"):
            current_event = decoded.split(":", 1)[1].strip()
            continue

        if decoded.startswith("data:") and current_event:
            data_str = decoded.split(":", 1)[1].strip()
            if data_str == "[DONE]":
                result.events.append(SSEEvent(
                    timestamp_ms=round((ts - result.t_start) * 1000, 1),
                    event_type="done",
                    data_len=0,
                ))
                continue

            result.events.append(SSEEvent(
                timestamp_ms=round((ts - result.t_start) * 1000, 1),
                event_type=current_event,
                data_len=len(data_str),
                content_preview=data_str[:60] if current_event == "chunk" else "",
            ))

    result.t_end = time.perf_counter()
    return result


def print_trace(trace: TraceResult, label: str = ""):
    """Pretty-print a trace result with phase breakdown."""
    total_ms = round((trace.t_end - trace.t_start) * 1000, 1)

    print(f"\n{'=' * 70}")
    print(f"  {label or 'TRACE'}")
    print(f"  Prompt: {trace.prompt[:80]}...")
    print(f"{'=' * 70}")

    if trace.error:
        print(f"  ERROR: {trace.error}")
        return

    # Print event timeline
    print(f"\n  {'Time':>10}  {'Delta':>8}  {'Event':<20} {'Size':>6}  Preview")
    print(f"  {'-' * 65}")

    prev_ts = 0.0
    meta_ts = None
    chart_ts = None
    first_chunk_ts = None
    last_chunk_ts = None
    chunk_count = 0

    for ev in trace.events:
        delta = ev.timestamp_ms - prev_ts
        delta_str = f"+{delta:.0f}ms" if prev_ts > 0 else ""

        if ev.event_type == "meta":
            meta_ts = ev.timestamp_ms
        elif ev.event_type in ("bank_chart", "chart"):
            chart_ts = ev.timestamp_ms
        elif ev.event_type == "chunk":
            chunk_count += 1
            if first_chunk_ts is None:
                first_chunk_ts = ev.timestamp_ms
            last_chunk_ts = ev.timestamp_ms

        # Print first 5 chunks, then summary
        if ev.event_type == "chunk" and chunk_count > 5 and ev != trace.events[-1]:
            if chunk_count == 6:
                print(f"  {'':>10}  {'':>8}  {'... (more chunks)':<20}")
            prev_ts = ev.timestamp_ms
            continue

        preview = ev.content_preview[:40] if ev.content_preview else ""
        print(
            f"  {ev.timestamp_ms:>8.1f}ms  {delta_str:>8}  "
            f"{ev.event_type:<20} {ev.data_len:>5}B  {preview}"
        )
        prev_ts = ev.timestamp_ms

    # Phase breakdown
    print(f"\n  {'─' * 50}")
    print(f"  PHASE BREAKDOWN:")
    print(f"  {'─' * 50}")

    if meta_ts is not None:
        print(f"  1. MCP blocking (0 → meta):      {meta_ts:>8.0f}ms")
    if meta_ts and chart_ts:
        print(f"  2. meta → chart:                  {chart_ts - meta_ts:>8.1f}ms")
    if chart_ts and first_chunk_ts:
        print(f"  3. chart → first LLM chunk:       {first_chunk_ts - chart_ts:>8.0f}ms")
    elif meta_ts and first_chunk_ts:
        print(f"  3. meta → first LLM chunk:        {first_chunk_ts - meta_ts:>8.0f}ms")
    if first_chunk_ts and last_chunk_ts:
        print(f"  4. LLM generation ({chunk_count} chunks):   {last_chunk_ts - first_chunk_ts:>8.0f}ms")

    print(f"  {'─' * 50}")
    print(f"  TOTAL:                            {total_ms:>8.0f}ms ({total_ms / 1000:.1f}s)")
    print()


def main():
    prompt_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if prompt_idx >= len(PROMPTS):
        print(f"Invalid prompt index. Use 0-{len(PROMPTS) - 1}")
        sys.exit(1)

    labels = ["RANKING (quebrantos)", "TREND (tasa_mn)", "ICAP (snapshot)"]

    print("Authenticating...")
    token = get_auth_token()
    if not token:
        print("ERROR: Could not get auth token")
        sys.exit(1)

    prompt = PROMPTS[prompt_idx]
    label = labels[prompt_idx]

    # Run 1: cold cache
    print(f"\nRun 1 (cold cache) — {label}")
    trace1 = trace_query(token, prompt)
    print_trace(trace1, f"Run 1 (cold) — {label}")

    # Run 2: warm cache
    print(f"\nRun 2 (warm cache) — {label}")
    trace2 = trace_query(token, prompt)
    print_trace(trace2, f"Run 2 (warm) — {label}")

    # Summary
    if not trace1.error and not trace2.error:
        t1 = round((trace1.t_end - trace1.t_start) * 1000)
        t2 = round((trace2.t_end - trace2.t_start) * 1000)
        savings = t1 - t2
        print(f"  CACHE EFFECT: {t1}ms → {t2}ms (saved {savings}ms, {savings/t1*100:.0f}%)")


if __name__ == "__main__":
    main()
