# Validation

## Commands

### Pre-implementation Checks
```bash
# Verify MongoDB is accessible
docker compose -f infra/docker-compose.yml exec mongodb mongosh --eval "db.stats()"

# Verify collections exist
docker compose -f infra/docker-compose.yml exec mongodb mongosh octavios --eval "db.getCollectionNames()"
```

### Build & Deploy
```bash
# Build dashboard image
docker compose -f infra/docker-compose.yml --profile monitoring build dashboard

# Start dashboard service
docker compose -f infra/docker-compose.yml --profile monitoring up dashboard -d

# Check logs
docker compose -f infra/docker-compose.yml logs dashboard -f
```

### Functional Tests
```bash
# Health check (should return 401 without auth)
curl -I http://localhost:8050/

# Health check with auth (should return 200)
curl -u admin:${DASHBOARD_PASSWORD} http://localhost:8050/

# Run unit tests
cd apps/dashboard && pytest tests/ -v --tb=short
```

### Performance Checks
```bash
# Measure response time
time curl -s -u admin:${DASHBOARD_PASSWORD} http://localhost:8050/ > /dev/null

# Check memory usage
docker stats dashboard --no-stream
```

## Results
- Implementation: COMPLETE (27 files created)

## Files Created

### Core Files (6)
- [x] `apps/dashboard/app.py` - Main Dash application
- [x] `apps/dashboard/requirements.txt` - Python dependencies
- [x] `apps/dashboard/config.py` - Environment configuration
- [x] `apps/dashboard/db.py` - MongoDB connection handler
- [x] `apps/dashboard/auth.py` - dash-auth setup
- [x] `apps/dashboard/Dockerfile` - Docker container

### Components (3)
- [x] `apps/dashboard/components/__init__.py`
- [x] `apps/dashboard/components/kpi_card.py`
- [x] `apps/dashboard/components/chart_card.py`

### Layouts (6)
- [x] `apps/dashboard/layouts/__init__.py`
- [x] `apps/dashboard/layouts/main.py`
- [x] `apps/dashboard/layouts/users.py`
- [x] `apps/dashboard/layouts/conversations.py`
- [x] `apps/dashboard/layouts/feedback.py`
- [x] `apps/dashboard/layouts/infrastructure.py`

### Queries (5)
- [x] `apps/dashboard/queries/__init__.py`
- [x] `apps/dashboard/queries/users.py`
- [x] `apps/dashboard/queries/conversations.py`
- [x] `apps/dashboard/queries/feedback.py`
- [x] `apps/dashboard/queries/infrastructure.py`

### Callbacks (5)
- [x] `apps/dashboard/callbacks/__init__.py`
- [x] `apps/dashboard/callbacks/users.py`
- [x] `apps/dashboard/callbacks/conversations.py`
- [x] `apps/dashboard/callbacks/feedback.py`
- [x] `apps/dashboard/callbacks/infrastructure.py`

### Tests (3)
- [x] `apps/dashboard/tests/__init__.py`
- [x] `apps/dashboard/tests/test_queries.py`
- [x] `apps/dashboard/tests/test_layouts.py`

### Docker Integration (1 modified)
- [x] `infra/docker-compose.yml` - Added dashboard service with monitoring profile

## Checklist

### Phase 1 - Core Setup
- [x] Directory structure created
- [x] Dependencies defined (requirements.txt)
- [x] MongoDB connection handler (db.py)
- [x] Auth configuration (auth.py)
- [x] Main app entry point (app.py)
- [x] Config from environment (config.py)

### Phase 2 - Components
- [x] KPI card component
- [x] Chart card component
- [x] Table card component

### Phase 3 - Queries
- [x] User queries (total, active, new, trend)
- [x] Conversation queries (total, latency, messages)
- [x] Feedback queries (satisfaction, thumbs, comments)
- [x] Infrastructure queries (documents, storage, status)

### Phase 4 - Layouts
- [x] Main layout with tabs
- [x] Users & Activity tab
- [x] Conversations tab
- [x] Feedback tab
- [x] Infrastructure tab

### Phase 5 - Callbacks
- [x] Users tab callbacks
- [x] Conversations callbacks
- [x] Feedback callbacks
- [x] Infrastructure callbacks
- [x] Last updated timestamp callback

### Phase 6 - Docker
- [x] Dockerfile created
- [x] docker-compose.yml updated
- [x] monitoring profile configured

### Phase 7 - Testing
- [x] Query unit tests (test_queries.py)
- [x] Layout smoke tests (test_layouts.py)

## Deployment Instructions

1. Set the dashboard password in `envs/.env`:
   ```
   DASHBOARD_PASSWORD=your_secure_password
   ```

2. Build and start with monitoring profile:
   ```bash
   docker compose -f infra/docker-compose.yml --profile monitoring up dashboard -d
   ```

3. Access at http://localhost:8050 (username: admin)

## Notes
- Dashboard runs independently on port 8050
- Uses monitoring profile to avoid starting by default
- Requires DASHBOARD_PASSWORD environment variable for authentication
- Auto-refreshes every 60 seconds (configurable via REFRESH_INTERVAL)
- All charts handle empty data gracefully with placeholder messages
