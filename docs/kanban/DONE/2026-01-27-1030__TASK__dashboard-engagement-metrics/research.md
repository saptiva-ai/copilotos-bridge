# Research: Dashboard Engagement Metrics

## Current Implementation Analysis

### Architecture Overview

```
apps/dashboard/
├── app.py                    # Main Dash app, routing, auth
├── config.py                 # Environment config (MongoDB, auth)
├── db.py                     # MongoDB connection
├── auth.py                   # Login logic
├── layouts/
│   ├── main.py               # Tab container
│   ├── users.py              # Users & Activity tab
│   ├── conversations.py      # Conversations tab
│   ├── feedback.py           # Feedback tab
│   └── infrastructure.py     # Infrastructure tab
├── queries/
│   ├── users.py              # UserQueries class
│   ├── conversations.py      # ConversationQueries class
│   ├── feedback.py           # FeedbackQueries class
│   └── infrastructure.py     # InfraQueries class
├── callbacks/
│   ├── users.py              # Auto-refresh user KPIs
│   ├── conversations.py      # Auto-refresh conversation KPIs
│   ├── feedback.py           # Auto-refresh feedback KPIs
│   └── infrastructure.py     # Auto-refresh infra KPIs
└── components/
    ├── kpi_card.py           # Reusable KPI card
    └── chart_card.py         # Reusable chart container
```

### Tech Stack

- **Framework**: Plotly Dash 2.15.0
- **UI**: dash-bootstrap-components (Bootstrap 5.3)
- **Database**: MongoDB (direct pymongo queries)
- **Font**: Inter (Google Fonts)
- **Auth**: Simple session-based (username/password from env)

### MongoDB Collections Used

| Collection | Purpose | Key Fields |
|------------|---------|------------|
| `users` | User accounts | `email`, `created_at`, `last_login`, `role` |
| `messages` | Chat messages | `user_id`, `session_id`, `role`, `content`, `created_at`, `metadata` |
| `chat_sessions` | Conversations | `user_id`, `state`, `created_at` |
| `message_feedback` | Thumbs up/down | `message_id`, `rating`, `reason`, `created_at` |
| `documents` | Uploaded files | `filename`, `status`, `size`, `created_at` |
| `artifacts` | Generated charts | `message_id`, `type`, `data` |

---

## Latency Bug Investigation

### Current Query (Not Working)

```python
# apps/dashboard/queries/conversations.py:31-44
def get_average_latency(self) -> float:
    pipeline = [
        {
            "$match": {
                "latency_ms": {"$exists": True, "$ne": None},
                "role": "assistant",
            }
        },
        {"$group": {"_id": None, "avg_latency": {"$avg": "$latency_ms"}}},
    ]
    result = list(self.messages.aggregate(pipeline))
    return result[0]["avg_latency"] if result else 0.0
```

### Verification: Field Does Not Exist

```bash
# Run on production
docker exec octavios-chat-bajaware_invex-backend python3 -c "
from pymongo import MongoClient
import os
client = MongoClient(os.environ.get('MONGODB_URL'))
db = client['octavios']
# Check if ANY message has latency_ms
count = db.messages.count_documents({'latency_ms': {'$exists': True}})
print(f'Messages with latency_ms: {count}')
# Sample a message
sample = db.messages.find_one({'role': 'assistant'}, {'_id': 0, 'latency_ms': 1, 'content': 1})
print(f'Sample message fields: {list(sample.keys()) if sample else \"none\"}')
"
```

**Expected output**: `Messages with latency_ms: 0`

### Where Latency Should Be Tracked

Looking at the streaming pipeline:

```
apps/backend/src/services/streaming/
├── stream_processor.py       # Main streaming orchestration
├── message_service.py        # Saves messages to MongoDB
├── chunk_processor.py        # Processes SSE chunks
└── event_handlers/           # Various event handlers
```

The fix should be in `stream_processor.py` or `message_service.py`:

```python
# Pseudocode for fix
class StreamProcessor:
    async def process_stream(self, ...):
        start_time = time.perf_counter()

        # ... existing streaming logic ...

        # When saving assistant message
        latency_ms = (time.perf_counter() - start_time) * 1000
        await self.message_service.save_assistant_message(
            ...,
            latency_ms=latency_ms
        )
```

---

## Engagement Metrics Research

### Industry Benchmarks

| Metric | Good | Great | Exceptional |
|--------|------|-------|-------------|
| DAU/MAU | 10-20% | 20-30% | 30%+ |
| WAU/MAU | 40-50% | 50-60% | 60%+ |
| Session Duration (B2B) | 3-5 min | 5-10 min | 10+ min |
| Queries/Session | 2-3 | 4-6 | 6+ |

### Why WAU > DAU for Bank Advisor

From Ronald's feedback:
> "WAU es mejor que DAU, definitivamente" - Bank Advisor tiene ciclos de análisis semanales, no diarios.

Typical use patterns:
- Analysts run reports at end of week
- Monthly reports prepared in last week of month
- Ad-hoc queries during meetings

### Query Designs

#### DAU (Daily Active Users)

```python
def get_dau(self, date: datetime = None) -> int:
    """Users who sent at least 1 query on given date."""
    date = date or datetime.utcnow()
    start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    pipeline = [
        {"$match": {
            "created_at": {"$gte": start, "$lt": end},
            "role": "user"  # Only count user messages, not assistant
        }},
        {"$group": {"_id": "$user_id"}},  # Distinct users
        {"$count": "dau"}
    ]
    result = list(self.messages.aggregate(pipeline))
    return result[0]["dau"] if result else 0
```

#### WAU (Weekly Active Users)

```python
def get_wau(self) -> int:
    """Users who sent at least 1 query in last 7 days."""
    cutoff = datetime.utcnow() - timedelta(days=7)

    pipeline = [
        {"$match": {
            "created_at": {"$gte": cutoff},
            "role": "user"
        }},
        {"$group": {"_id": "$user_id"}},
        {"$count": "wau"}
    ]
    result = list(self.messages.aggregate(pipeline))
    return result[0]["wau"] if result else 0
```

#### MAU (Monthly Active Users)

```python
def get_mau(self) -> int:
    """Users who sent at least 1 query in last 30 days."""
    cutoff = datetime.utcnow() - timedelta(days=30)

    pipeline = [
        {"$match": {
            "created_at": {"$gte": cutoff},
            "role": "user"
        }},
        {"$group": {"_id": "$user_id"}},
        {"$count": "mau"}
    ]
    result = list(self.messages.aggregate(pipeline))
    return result[0]["mau"] if result else 0
```

#### Stickiness (DAU/MAU)

```python
def get_stickiness(self) -> float:
    """DAU/MAU ratio as percentage."""
    dau = self.get_dau()
    mau = self.get_mau()
    return (dau / mau * 100) if mau > 0 else 0.0
```

#### Queries per Active User

```python
def get_queries_per_user(self, period: str = "week") -> float:
    """Average queries per active user in period."""
    if period == "day":
        cutoff = datetime.utcnow() - timedelta(days=1)
        users = self.get_dau()
    else:  # week
        cutoff = datetime.utcnow() - timedelta(days=7)
        users = self.get_wau()

    query_count = self.messages.count_documents({
        "created_at": {"$gte": cutoff},
        "role": "user"
    })

    return query_count / users if users > 0 else 0.0
```

#### WAU Trend (8 weeks)

```python
def get_wau_trend(self, weeks: int = 8) -> list[dict]:
    """WAU for each of the last N weeks."""
    results = []
    now = datetime.utcnow()

    for i in range(weeks):
        week_end = now - timedelta(weeks=i)
        week_start = week_end - timedelta(days=7)

        pipeline = [
            {"$match": {
                "created_at": {"$gte": week_start, "$lt": week_end},
                "role": "user"
            }},
            {"$group": {"_id": "$user_id"}},
            {"$count": "wau"}
        ]
        result = list(self.messages.aggregate(pipeline))
        wau = result[0]["wau"] if result else 0

        results.append({
            "week": f"W-{i}",
            "week_start": week_start.isoformat(),
            "wau": wau
        })

    return list(reversed(results))  # Oldest first
```

---

## Time to First Insight (TTFI)

### Definition

Time from user account creation (`users.created_at`) to their first message that generated a chart (`messages.metadata.bank_chart_data` exists).

### Query Design

```python
def get_time_to_first_insight(self) -> dict:
    """
    Calculate average and median TTFI in minutes.
    Only includes users who have achieved first insight.
    """
    pipeline = [
        # Start with users collection
        {"$lookup": {
            "from": "messages",
            "let": {"user_id": {"$toString": "$_id"}},
            "pipeline": [
                {"$match": {
                    "$expr": {"$eq": ["$user_id", "$$user_id"]},
                    "metadata.bank_chart_data": {"$exists": True},
                    "role": "assistant"
                }},
                {"$sort": {"created_at": 1}},
                {"$limit": 1}
            ],
            "as": "first_insight"
        }},
        # Only users who have achieved first insight
        {"$match": {"first_insight": {"$ne": []}}},
        {"$unwind": "$first_insight"},
        # Calculate TTFI in minutes
        {"$project": {
            "ttfi_minutes": {
                "$divide": [
                    {"$subtract": ["$first_insight.created_at", "$created_at"]},
                    60000  # milliseconds to minutes
                ]
            }
        }},
        # Aggregate stats
        {"$group": {
            "_id": None,
            "avg_ttfi": {"$avg": "$ttfi_minutes"},
            "min_ttfi": {"$min": "$ttfi_minutes"},
            "max_ttfi": {"$max": "$ttfi_minutes"},
            "count": {"$sum": 1}
        }}
    ]

    result = list(self.db.users.aggregate(pipeline))
    if result:
        return {
            "avg_minutes": round(result[0]["avg_ttfi"], 1),
            "min_minutes": round(result[0]["min_ttfi"], 1),
            "max_minutes": round(result[0]["max_ttfi"], 1),
            "users_with_insight": result[0]["count"]
        }
    return {"avg_minutes": 0, "min_minutes": 0, "max_minutes": 0, "users_with_insight": 0}
```

---

## Design Research: Typography

### Current: Inter

```css
/* Current in app.py */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
```

**Issues**:
- Good for body text, but numbers can be hard to scan
- No tabular figures variant loaded
- Plotly charts use default sans-serif

### Proposed: IBM Plex

```css
/* Proposed */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    --font-sans: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'IBM Plex Mono', 'SF Mono', Consolas, monospace;
}
```

**Benefits**:
- IBM Plex Mono has tabular figures by default
- Better legibility at small sizes (11-12px for chart labels)
- Open source, well-maintained
- Used by IBM Carbon Design System (enterprise-grade)

### Plotly Chart Font Override

```python
# In chart generation
layout = go.Layout(
    font=dict(
        family="IBM Plex Sans, -apple-system, sans-serif",
        size=12,
        color="#1e293b"
    ),
    title_font=dict(size=14, weight=600),
    # Axis tick fonts
    xaxis=dict(tickfont=dict(size=11)),
    yaxis=dict(tickfont=dict(size=11)),
)
```

---

## Sparklines Research

### Option 1: Plotly Mini Charts

```python
import plotly.graph_objects as go

def create_sparkline(data: list[int], color: str = "#0d6efd") -> go.Figure:
    """Create a minimal sparkline figure."""
    fig = go.Figure(go.Scatter(
        y=data,
        mode='lines',
        line=dict(color=color, width=1.5),
        fill='tozeroy',
        fillcolor=f'rgba(13, 110, 253, 0.1)',
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=30,
        width=80,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig
```

### Option 2: CSS-only Sparklines (lighter weight)

```html
<div class="sparkline" data-values="10,15,12,18,22,20,25">
    <!-- Generated via JS or server-side -->
    <svg viewBox="0 0 80 30">
        <polyline fill="none" stroke="#0d6efd" stroke-width="1.5"
                  points="0,20 11,15 22,18 33,12 44,8 55,10 66,5 77,0"/>
    </svg>
</div>
```

**Recommendation**: Use Plotly mini charts for consistency with existing charts.

---

## Export Feature Research

### Requirements from Carlos

> "Me puedes dar los historiales de conversación para estudiar qué preguntan?"

### Proposed Export Format (CSV)

| Column | Description |
|--------|-------------|
| timestamp | Message created_at |
| user_email | User who sent the query |
| session_id | Conversation ID |
| query | User's question |
| response_preview | First 200 chars of assistant response |
| had_chart | Boolean - did response include chart? |
| feedback | up/down/none |
| latency_ms | Response time |

### Implementation Options

1. **Dashboard Button**: Export via Dash callback (simpler)
2. **API Endpoint**: `/api/admin/export/conversations` (more flexible)

**Recommendation**: Start with Dashboard button, add API later if needed.

```python
# Dashboard callback
@app.callback(
    Output("download-conversations", "data"),
    Input("btn-export", "n_clicks"),
    State("date-range", "start_date"),
    State("date-range", "end_date"),
    prevent_initial_call=True,
)
def export_conversations(n_clicks, start, end):
    df = query_conversations_for_export(start, end)
    return dcc.send_data_frame(df.to_csv, "conversations.csv", index=False)
```

---

## Performance Considerations

### Current Refresh Interval

```python
# config.py
REFRESH_INTERVAL_MS: int = int(os.getenv("REFRESH_INTERVAL", "60000"))  # 60 seconds
```

### New Queries Impact

| Query | Estimated Cost | Frequency |
|-------|---------------|-----------|
| DAU | O(n) scan of today's messages | Every 60s |
| WAU | O(n) scan of 7 days messages | Every 60s |
| MAU | O(n) scan of 30 days messages | Every 60s |
| Stickiness | 2 queries above | Every 60s |
| Queries/User | 1 count + 1 distinct | Every 60s |
| WAU Trend | 8 queries (1 per week) | Every 60s |
| TTFI | Complex join, heavy | Every 300s (5 min) |

### Optimization Ideas

1. **Index on messages**: `{created_at: 1, role: 1, user_id: 1}`
2. **Cache TTFI**: Only recalculate every 5 minutes
3. **Pre-aggregate WAU trend**: Store in separate collection, update daily

```python
# Suggested index
db.messages.create_index([
    ("created_at", -1),
    ("role", 1),
    ("user_id", 1)
])
```

---

## Summary: Key Findings

1. **Latency Bug**: Field `latency_ms` not saved in messages - requires backend instrumentation
2. **WAU > DAU**: Business prefers weekly metrics for analyst workflow
3. **Typography**: IBM Plex recommended for better number legibility
4. **Sparklines**: Plotly mini charts for visual consistency
5. **Export**: CSV download via Dash callback, filtered by date range
6. **Performance**: Add index on messages, cache heavy queries like TTFI
