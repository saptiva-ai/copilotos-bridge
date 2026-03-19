# Plan: Dashboard Engagement Metrics

> Status: PENDING APPROVAL

---

## Phase 1: Latency Bug Fix (4h)

### 1.1 Backend Instrumentation

**Files to modify**:
- `apps/backend/src/services/streaming/stream_processor.py`
- `apps/backend/src/services/message_service.py` (if separate)

**Changes**:
```python
# stream_processor.py
import time

class StreamProcessor:
    async def process_stream(self, request, ...):
        start_time = time.perf_counter()

        # ... existing streaming logic ...

        # When creating assistant message
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Pass to message save
        await self._save_assistant_message(
            ...,
            extra_fields={"latency_ms": latency_ms}
        )
```

### 1.2 Verify Data Collection

```bash
# Test: Send a query, then check MongoDB
docker exec backend python3 -c "
from pymongo import MongoClient
import os
client = MongoClient(os.environ['MONGODB_URL'])
db = client['octavios']
recent = db.messages.find_one(
    {'role': 'assistant'},
    sort=[('created_at', -1)]
)
print(f'latency_ms: {recent.get(\"latency_ms\", \"NOT FOUND\")}')
"
```

### 1.3 Dashboard Already Works

The dashboard query is already correct - it just needs data:
```python
# queries/conversations.py - no changes needed
def get_average_latency(self) -> float:
    pipeline = [
        {"$match": {"latency_ms": {"$exists": True}, "role": "assistant"}},
        {"$group": {"_id": None, "avg_latency": {"$avg": "$latency_ms"}}}
    ]
    ...
```

**Deliverable**: New messages have `latency_ms`, dashboard shows real values.

---

## Phase 2: Engagement Metrics (8h)

### 2.1 Create queries/engagement.py

```python
"""Engagement metrics queries."""

from datetime import datetime, timedelta
from typing import Any
from pymongo.database import Database


class EngagementQueries:
    """Query class for engagement metrics (DAU, WAU, stickiness)."""

    def __init__(self, db: Database):
        self.db = db
        self.messages = db.messages
        self.users = db.users

    def get_dau(self, date: datetime = None) -> int:
        """Daily Active Users - users with at least 1 query today."""
        ...

    def get_wau(self) -> int:
        """Weekly Active Users - users with at least 1 query in 7 days."""
        ...

    def get_mau(self) -> int:
        """Monthly Active Users - users with at least 1 query in 30 days."""
        ...

    def get_stickiness(self) -> float:
        """DAU/MAU ratio as percentage."""
        ...

    def get_queries_per_user(self, period: str = "week") -> float:
        """Average queries per active user."""
        ...

    def get_wau_trend(self, weeks: int = 8) -> list[dict[str, Any]]:
        """WAU for each of last N weeks."""
        ...

    def get_query_distribution(self) -> list[dict[str, Any]]:
        """Distribution of query counts per user (1, 2-5, 5-10, 10+)."""
        ...

    def get_time_to_first_insight(self) -> dict[str, Any]:
        """TTFI - time from signup to first chart generation."""
        ...
```

### 2.2 Create layouts/engagement.py

```python
"""Engagement tab layout."""

from dash import html
import dash_bootstrap_components as dbc
from components.kpi_card import kpi_card
from components.chart_card import chart_card


def engagement_layout() -> dbc.Container:
    return dbc.Container([
        # KPI Row
        dbc.Row([
            dbc.Col(kpi_card(
                card_id="kpi-wau",
                title="WAU",
                icon="people",
                color="primary",
                subtitle="Weekly Active Users"
            ), md=3),
            dbc.Col(kpi_card(
                card_id="kpi-dau",
                title="DAU",
                icon="person-check",
                color="success",
            ), md=3),
            dbc.Col(kpi_card(
                card_id="kpi-stickiness",
                title="Stickiness",
                icon="graph-up",
                color="info",
                subtitle="DAU/MAU"
            ), md=3),
            dbc.Col(kpi_card(
                card_id="kpi-queries-per-user",
                title="Queries/User",
                icon="chat-dots",
                color="warning",
                subtitle="Weekly avg"
            ), md=3),
        ]),
        # Charts Row 1
        dbc.Row([
            dbc.Col(chart_card(
                card_id="chart-wau-trend",
                title="Weekly Active Users Trend",
                subtitle="Last 8 weeks",
                height=300,
            ), md=8),
            dbc.Col(chart_card(
                card_id="chart-query-distribution",
                title="Queries per User",
                subtitle="Distribution",
                height=300,
            ), md=4),
        ]),
        # TTFI Row
        dbc.Row([
            dbc.Col(kpi_card(
                card_id="kpi-ttfi",
                title="Time to First Insight",
                icon="stopwatch",
                color="primary",
                subtitle="Avg minutes"
            ), md=4),
            dbc.Col(chart_card(
                card_id="chart-ttfi-distribution",
                title="TTFI Distribution",
                height=250,
            ), md=8),
        ]),
    ], fluid=True, className="py-3")
```

### 2.3 Create callbacks/engagement.py

```python
"""Engagement tab callbacks."""

from dash import callback, Output, Input
import plotly.express as px
import plotly.graph_objects as go
from db import get_db
from queries.engagement import EngagementQueries


def register_engagement_callbacks(app):
    @app.callback(
        [
            Output("kpi-wau", "children"),
            Output("kpi-dau", "children"),
            Output("kpi-stickiness", "children"),
            Output("kpi-queries-per-user", "children"),
            Output("kpi-ttfi", "children"),
        ],
        Input("refresh-interval", "n_intervals"),
    )
    def update_engagement_kpis(n):
        db = get_db()
        queries = EngagementQueries(db)

        wau = queries.get_wau()
        dau = queries.get_dau()
        stickiness = queries.get_stickiness()
        qpu = queries.get_queries_per_user()
        ttfi = queries.get_time_to_first_insight()

        return (
            str(wau),
            str(dau),
            f"{stickiness:.1f}%",
            f"{qpu:.1f}",
            f"{ttfi['avg_minutes']:.0f} min",
        )

    @app.callback(
        Output("chart-wau-trend", "figure"),
        Input("refresh-interval", "n_intervals"),
    )
    def update_wau_trend(n):
        db = get_db()
        queries = EngagementQueries(db)
        data = queries.get_wau_trend()

        fig = px.line(
            data,
            x="week",
            y="wau",
            markers=True,
            title=None,
        )
        fig.update_layout(
            font_family="IBM Plex Sans",
            margin=dict(l=40, r=20, t=20, b=40),
        )
        return fig

    # ... more callbacks for other charts
```

### 2.4 Update layouts/main.py

```python
# Add import
from layouts.engagement import engagement_layout

# Add new tab (as first tab)
dbc.Tabs([
    dbc.Tab(
        engagement_layout(),
        label="Engagement",
        tab_id="tab-engagement",
        className="pt-4",
    ),
    # ... existing tabs
])
```

### 2.5 Update callbacks/__init__.py

```python
from callbacks.engagement import register_engagement_callbacks

def register_all_callbacks(app):
    register_engagement_callbacks(app)
    # ... existing
```

**Deliverable**: New "Engagement" tab with WAU, DAU, Stickiness, Queries/User, TTFI.

---

## Phase 3: Design Improvements (6h)

### 3.1 Typography Migration

**File**: `apps/dashboard/app.py`

```css
/* Replace Inter with IBM Plex */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    --font-sans: 'IBM Plex Sans', -apple-system, sans-serif;
    --font-mono: 'IBM Plex Mono', 'SF Mono', monospace;
}

body {
    font-family: var(--font-sans);
}

/* KPI values use monospace for alignment */
.kpi-value, h3 {
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
}
```

### 3.2 Update Plotly Chart Defaults

**File**: Create `apps/dashboard/chart_config.py`

```python
"""Shared chart configuration."""

CHART_LAYOUT = dict(
    font=dict(
        family="IBM Plex Sans, -apple-system, sans-serif",
        size=12,
        color="#1e293b",
    ),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=40, r=20, t=40, b=40),
    xaxis=dict(
        tickfont=dict(size=11),
        gridcolor="#e2e8f0",
    ),
    yaxis=dict(
        tickfont=dict(size=11),
        gridcolor="#e2e8f0",
    ),
)

def apply_layout(fig):
    """Apply consistent layout to a figure."""
    fig.update_layout(**CHART_LAYOUT)
    return fig
```

### 3.3 Add Sparklines to KPI Cards

**File**: Update `apps/dashboard/components/kpi_card.py`

```python
def kpi_card(
    card_id: str,
    title: str,
    value: str = "0",
    icon: str = "bar-chart",
    color: str = "primary",
    subtitle: str | None = None,
    sparkline_data: list[int] | None = None,  # NEW
) -> dbc.Card:
    """Create a KPI card with optional sparkline."""

    # ... existing code ...

    # Add sparkline if data provided
    if sparkline_data:
        sparkline = create_sparkline(sparkline_data, color)
        # Insert sparkline div
```

### 3.4 Tab Icons

```python
dbc.Tab(
    engagement_layout(),
    label=[html.I(className="bi bi-graph-up me-2"), "Engagement"],
    ...
)
```

**Deliverable**: IBM Plex fonts, consistent chart styling, sparklines on KPIs.

---

## Phase 4: Export & Extras (4h)

### 4.1 Add Export Button

**File**: Update `apps/dashboard/layouts/conversations.py`

```python
# Add to layout
dbc.Row([
    dbc.Col([
        dbc.Button(
            [html.I(className="bi bi-download me-2"), "Export CSV"],
            id="btn-export-conversations",
            color="outline-primary",
            size="sm",
        ),
        dcc.Download(id="download-conversations"),
    ], className="text-end mb-3"),
])
```

### 4.2 Export Callback

**File**: `apps/dashboard/callbacks/conversations.py`

```python
@app.callback(
    Output("download-conversations", "data"),
    Input("btn-export-conversations", "n_clicks"),
    prevent_initial_call=True,
)
def export_conversations(n_clicks):
    db = get_db()

    # Query conversations with user info
    pipeline = [
        {"$match": {"role": "user"}},
        {"$sort": {"created_at": -1}},
        {"$limit": 10000},
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "user"
        }},
        {"$unwind": "$user"},
        {"$project": {
            "timestamp": "$created_at",
            "user_email": "$user.email",
            "session_id": 1,
            "query": "$content",
        }}
    ]

    data = list(db.messages.aggregate(pipeline))
    df = pd.DataFrame(data)

    return dcc.send_data_frame(df.to_csv, "conversations.csv", index=False)
```

**Deliverable**: Export button downloads conversation history as CSV.

---

## Testing Plan

### Unit Tests

```python
# apps/dashboard/tests/test_engagement_queries.py
def test_get_wau():
    db = get_test_db()
    queries = EngagementQueries(db)
    wau = queries.get_wau()
    assert isinstance(wau, int)
    assert wau >= 0

def test_get_stickiness():
    db = get_test_db()
    queries = EngagementQueries(db)
    stickiness = queries.get_stickiness()
    assert 0 <= stickiness <= 100
```

### Manual Testing

1. Send 3 queries from test user
2. Verify DAU = 1
3. Verify WAU includes test user
4. Verify Queries/User = 3
5. Export CSV, verify data

---

## Rollout Plan

1. **Dev**: Implement all phases, test locally
2. **Staging**: Deploy to staging, verify with real-ish data
3. **Production**: Deploy during low-traffic window
4. **Monitor**: Watch for MongoDB query performance issues

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Latency shows real values | > 0 ms for new messages |
| WAU displays correctly | Matches manual count |
| Export works | CSV downloads successfully |
| Font renders correctly | IBM Plex visible in DevTools |
| Page load time | < 3 seconds |
