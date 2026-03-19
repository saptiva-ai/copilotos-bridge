# Plan

## Objective
- Create a standalone Plotly Dash dashboard for real-time production metrics monitoring
- Enable operations team to visualize user activity, conversations, feedback, and infrastructure health
- Provide auto-refreshing KPIs and charts with basic authentication

## Scope
### In
- Standalone Dash app in `apps/dashboard/`
- Direct MongoDB connection (no backend API dependency)
- 4 tabs: Users & Activity, Conversations, Feedback, Infrastructure
- Basic auth with dash-auth + bcrypt
- Docker deployment with monitoring profile
- Auto-refresh every 60 seconds
- KPI cards + interactive charts

### Out
- Integration with existing backend API
- Real-time websocket push
- User management interface
- Data export functionality
- Custom date range pickers (future enhancement)
- Alert/notification system

## File Structure

```
apps/dashboard/
├── app.py                 # Main Dash application
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container build
├── config.py             # Environment configuration
├── auth.py               # Authentication setup
├── db.py                 # MongoDB connection handler
├── layouts/
│   ├── __init__.py
│   ├── main.py           # Main layout with tabs
│   ├── users.py          # Users & Activity tab
│   ├── conversations.py  # Conversations tab
│   ├── feedback.py       # Feedback tab
│   └── infrastructure.py # Infrastructure tab
├── callbacks/
│   ├── __init__.py
│   ├── users.py          # Users tab callbacks
│   ├── conversations.py  # Conversations callbacks
│   ├── feedback.py       # Feedback callbacks
│   └── infrastructure.py # Infrastructure callbacks
├── components/
│   ├── __init__.py
│   ├── kpi_card.py       # Reusable KPI card component
│   └── chart_card.py     # Reusable chart container
├── queries/
│   ├── __init__.py
│   ├── users.py          # User aggregation queries
│   ├── conversations.py  # Conversation queries
│   ├── feedback.py       # Feedback queries
│   └── infrastructure.py # Document queries
└── tests/
    ├── __init__.py
    ├── test_queries.py   # Query unit tests
    └── test_layouts.py   # Layout tests
```

## Phases

### Phase 1 - Core Setup
- [x] Create `apps/dashboard/` directory structure
- [ ] Create `requirements.txt` with dependencies
- [ ] Create `config.py` for environment variables
- [ ] Create `db.py` MongoDB connection handler
- [ ] Create `auth.py` authentication setup
- [ ] Create `app.py` main application entry point

#### Phase 1 Files
- `apps/dashboard/requirements.txt`
- `apps/dashboard/config.py`
- `apps/dashboard/db.py`
- `apps/dashboard/auth.py`
- `apps/dashboard/app.py`

#### Phase 1 Dependencies
```txt
dash==2.14.2
dash-bootstrap-components==1.5.0
dash-auth==2.0.0
plotly==5.18.0
motor==3.3.2
pymongo==4.6.1
gunicorn==21.2.0
python-dotenv==1.0.0
bcrypt==4.1.2
```

### Phase 2 - Reusable Components
- [ ] Create `components/kpi_card.py` - KPI display component
- [ ] Create `components/chart_card.py` - Chart container component
- [ ] Create component styling with Bootstrap classes

#### Phase 2 Files
- `apps/dashboard/components/__init__.py`
- `apps/dashboard/components/kpi_card.py`
- `apps/dashboard/components/chart_card.py`

#### Phase 2 KPI Card Component
```python
def kpi_card(title: str, value: str, icon: str, color: str = "primary") -> dbc.Card:
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className=f"bi bi-{icon} fs-1 text-{color}"),
                html.Div([
                    html.H6(title, className="text-muted mb-0"),
                    html.H3(value, className="mb-0 fw-bold")
                ], className="ms-3")
            ], className="d-flex align-items-center")
        ])
    ], className="shadow-sm h-100")
```

### Phase 3 - Database Queries
- [ ] Create `queries/users.py` - User metrics queries
- [ ] Create `queries/conversations.py` - Conversation queries
- [ ] Create `queries/feedback.py` - Feedback queries
- [ ] Create `queries/infrastructure.py` - Document queries

#### Phase 3 Files
- `apps/dashboard/queries/__init__.py`
- `apps/dashboard/queries/users.py`
- `apps/dashboard/queries/conversations.py`
- `apps/dashboard/queries/feedback.py`
- `apps/dashboard/queries/infrastructure.py`

### Phase 4 - Tab Layouts
- [ ] Create `layouts/main.py` - Main layout with tab navigation
- [ ] Create `layouts/users.py` - Users & Activity tab
- [ ] Create `layouts/conversations.py` - Conversations tab
- [ ] Create `layouts/feedback.py` - Feedback tab
- [ ] Create `layouts/infrastructure.py` - Infrastructure tab

#### Phase 4 Files
- `apps/dashboard/layouts/__init__.py`
- `apps/dashboard/layouts/main.py`
- `apps/dashboard/layouts/users.py`
- `apps/dashboard/layouts/conversations.py`
- `apps/dashboard/layouts/feedback.py`
- `apps/dashboard/layouts/infrastructure.py`

#### Phase 4 Main Layout Structure
```python
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col(html.H2("OctaviOS Production Metrics", className="mb-0")),
        dbc.Col(html.Div(id="last-updated", className="text-muted text-end"))
    ], className="py-3 border-bottom mb-4"),

    # Tabs
    dbc.Tabs([
        dbc.Tab(users_layout(), label="Users & Activity", tab_id="users"),
        dbc.Tab(conversations_layout(), label="Conversations", tab_id="conversations"),
        dbc.Tab(feedback_layout(), label="Feedback", tab_id="feedback"),
        dbc.Tab(infrastructure_layout(), label="Infrastructure", tab_id="infra"),
    ], id="tabs", active_tab="users"),

    # Auto-refresh interval
    dcc.Interval(id="refresh-interval", interval=60*1000, n_intervals=0)
], fluid=True, className="py-4")
```

### Phase 5 - Callbacks
- [ ] Create `callbacks/users.py` - User metrics callbacks
- [ ] Create `callbacks/conversations.py` - Conversation callbacks
- [ ] Create `callbacks/feedback.py` - Feedback callbacks
- [ ] Create `callbacks/infrastructure.py` - Infrastructure callbacks
- [ ] Register all callbacks in `app.py`

#### Phase 5 Files
- `apps/dashboard/callbacks/__init__.py`
- `apps/dashboard/callbacks/users.py`
- `apps/dashboard/callbacks/conversations.py`
- `apps/dashboard/callbacks/feedback.py`
- `apps/dashboard/callbacks/infrastructure.py`

#### Phase 5 Sample Callback
```python
@app.callback(
    [Output("total-users", "children"),
     Output("active-users", "children"),
     Output("users-chart", "figure")],
    [Input("refresh-interval", "n_intervals")]
)
async def update_users_metrics(n):
    db = get_database()

    total = await db.users.count_documents({})
    active = await db.users.count_documents({
        "last_login": {"$gte": datetime.now() - timedelta(hours=24)}
    })

    trend_data = await db.users.aggregate([...]).to_list(None)
    fig = px.line(trend_data, x="date", y="count", title="User Registrations")

    return f"{total:,}", f"{active:,}", fig
```

### Phase 6 - Docker Integration
- [ ] Create `apps/dashboard/Dockerfile`
- [ ] Update `infra/docker-compose.yml` with dashboard service
- [ ] Add environment variables documentation

#### Phase 6 Files
- `apps/dashboard/Dockerfile`
- `infra/docker-compose.yml` (modify)

#### Phase 6 Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8050

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8050/ || exit 1

# Run with gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8050", "-w", "2", "--timeout", "120", "app:server"]
```

#### Phase 6 Docker Compose Addition
```yaml
services:
  dashboard:
    build:
      context: ../apps/dashboard
      dockerfile: Dockerfile
    ports:
      - "8050:8050"
    environment:
      - MONGO_URI=${MONGO_URI}
      - DASHBOARD_USER=${DASHBOARD_USER:-admin}
      - DASHBOARD_PASSWORD=${DASHBOARD_PASSWORD}
    depends_on:
      - mongodb
    profiles:
      - monitoring
    networks:
      - octavios-network
```

### Phase 7 - Testing & Documentation
- [ ] Create `tests/test_queries.py` - Query unit tests
- [ ] Create `tests/test_layouts.py` - Layout smoke tests
- [ ] Add startup documentation to card.md

#### Phase 7 Files
- `apps/dashboard/tests/__init__.py`
- `apps/dashboard/tests/test_queries.py`
- `apps/dashboard/tests/test_layouts.py`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017/octavios` |
| `DASHBOARD_USER` | Dashboard admin username | `admin` |
| `DASHBOARD_PASSWORD` | Dashboard admin password | (required) |
| `REFRESH_INTERVAL` | Auto-refresh interval (ms) | `60000` |
| `DEBUG` | Enable debug mode | `false` |

## Validation Commands
```bash
# Start dashboard in Docker
docker compose -f infra/docker-compose.yml --profile monitoring up dashboard -d

# Check health
curl -u admin:password http://localhost:8050/

# Run tests
cd apps/dashboard && pytest tests/ -v

# Local development
cd apps/dashboard && python app.py
```

## Success Criteria
- [ ] Dashboard accessible at http://localhost:8050
- [ ] Authentication required for all pages
- [ ] All 4 tabs display KPIs and charts
- [ ] Auto-refresh updates data every 60 seconds
- [ ] Docker container starts successfully with monitoring profile
- [ ] No errors in console during normal operation
- [ ] Query response time < 2 seconds for all metrics

## Security Considerations
1. **Authentication**: All routes protected by dash-auth
2. **Passwords**: Stored with bcrypt hashing
3. **MongoDB**: Read-only queries, no write operations
4. **Network**: Dashboard on internal network only (not exposed externally)
5. **CORS**: Not applicable (no external API calls)

## Rollback Plan
If issues arise:
1. Stop dashboard container: `docker compose --profile monitoring stop dashboard`
2. No impact on main application (standalone service)
3. Remove from compose if needed (comment out service)
