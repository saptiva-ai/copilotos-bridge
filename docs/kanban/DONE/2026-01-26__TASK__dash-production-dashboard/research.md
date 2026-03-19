# Research

## Questions
- What MongoDB collections contain the metrics data?
- What aggregation queries are needed for each dashboard tab?
- How should authentication be implemented for the dashboard?
- What Docker configuration is required for deployment?

## Findings

### MongoDB Collections Structure

Based on codebase analysis, the following collections are available:

#### 1. `users` Collection
```json
{
  "_id": "ObjectId",
  "email": "string",
  "name": "string",
  "created_at": "datetime",
  "last_login": "datetime",
  "is_active": "boolean",
  "role": "string"
}
```

#### 2. `conversations` Collection
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "title": "string",
  "created_at": "datetime",
  "updated_at": "datetime",
  "status": "string (active|archived)",
  "message_count": "integer"
}
```

#### 3. `messages` Collection
```json
{
  "_id": "ObjectId",
  "conversation_id": "ObjectId",
  "role": "string (user|assistant|system)",
  "content": "string",
  "created_at": "datetime",
  "latency_ms": "integer (optional)",
  "tokens_used": "integer (optional)"
}
```

#### 4. `feedback` Collection
```json
{
  "_id": "ObjectId",
  "message_id": "ObjectId",
  "user_id": "ObjectId",
  "rating": "string (thumbs_up|thumbs_down)",
  "comment": "string (optional)",
  "created_at": "datetime"
}
```

#### 5. `documents` Collection
```json
{
  "_id": "ObjectId",
  "filename": "string",
  "file_type": "string",
  "size_bytes": "integer",
  "status": "string (pending|processing|completed|failed)",
  "uploaded_at": "datetime",
  "processed_at": "datetime (optional)",
  "user_id": "ObjectId"
}
```

### MongoDB Aggregation Queries

#### Users Metrics
```python
# Total users
db.users.count_documents({})

# Active users (last 24h)
db.users.count_documents({
    "last_login": {"$gte": datetime.now() - timedelta(hours=24)}
})

# New users today
db.users.count_documents({
    "created_at": {"$gte": datetime.now().replace(hour=0, minute=0)}
})

# User registrations trend (last 30 days)
db.users.aggregate([
    {"$match": {"created_at": {"$gte": thirty_days_ago}}},
    {"$group": {
        "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
        "count": {"$sum": 1}
    }},
    {"$sort": {"_id": 1}}
])
```

#### Conversations Metrics
```python
# Total conversations
db.conversations.count_documents({})

# Active conversations
db.conversations.count_documents({"status": "active"})

# Messages today
db.messages.count_documents({
    "created_at": {"$gte": today_start}
})

# Average latency
db.messages.aggregate([
    {"$match": {"latency_ms": {"$exists": True}, "role": "assistant"}},
    {"$group": {"_id": None, "avg_latency": {"$avg": "$latency_ms"}}}
])

# Messages trend (last 7 days)
db.messages.aggregate([
    {"$match": {"created_at": {"$gte": seven_days_ago}}},
    {"$group": {
        "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
        "count": {"$sum": 1}
    }},
    {"$sort": {"_id": 1}}
])

# Latency percentiles
db.messages.aggregate([
    {"$match": {"latency_ms": {"$exists": True}}},
    {"$group": {
        "_id": None,
        "latencies": {"$push": "$latency_ms"}
    }},
    {"$project": {
        "p50": {"$arrayElemAt": [
            {"$sortArray": {"input": "$latencies", "sortBy": 1}},
            {"$floor": {"$multiply": [{"$size": "$latencies"}, 0.5]}}
        ]},
        "p95": {"$arrayElemAt": [
            {"$sortArray": {"input": "$latencies", "sortBy": 1}},
            {"$floor": {"$multiply": [{"$size": "$latencies"}, 0.95]}}
        ]},
        "p99": {"$arrayElemAt": [
            {"$sortArray": {"input": "$latencies", "sortBy": 1}},
            {"$floor": {"$multiply": [{"$size": "$latencies"}, 0.99]}}
        ]}
    }}
])

# Role distribution
db.messages.aggregate([
    {"$group": {"_id": "$role", "count": {"$sum": 1}}}
])
```

#### Feedback Metrics
```python
# Total feedback
db.feedback.count_documents({})

# Thumbs up count
db.feedback.count_documents({"rating": "thumbs_up"})

# Thumbs down count
db.feedback.count_documents({"rating": "thumbs_down"})

# Satisfaction rate
thumbs_up / total_feedback * 100

# Feedback trend
db.feedback.aggregate([
    {"$match": {"created_at": {"$gte": thirty_days_ago}}},
    {"$group": {
        "_id": {
            "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "rating": "$rating"
        },
        "count": {"$sum": 1}
    }},
    {"$sort": {"_id.date": 1}}
])

# Recent comments
db.feedback.find(
    {"comment": {"$exists": True, "$ne": ""}},
    {"comment": 1, "rating": 1, "created_at": 1}
).sort("created_at", -1).limit(10)
```

#### Infrastructure Metrics
```python
# Total documents
db.documents.count_documents({})

# Storage used
db.documents.aggregate([
    {"$group": {"_id": None, "total_bytes": {"$sum": "$size_bytes"}}}
])

# Documents by status
db.documents.aggregate([
    {"$group": {"_id": "$status", "count": {"$sum": 1}}}
])

# Documents trend
db.documents.aggregate([
    {"$match": {"uploaded_at": {"$gte": seven_days_ago}}},
    {"$group": {
        "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$uploaded_at"}},
        "count": {"$sum": 1}
    }},
    {"$sort": {"_id": 1}}
])
```

### Authentication Research

**dash-auth** is the recommended solution for Dash authentication:

```python
import dash_auth
from werkzeug.security import generate_password_hash, check_password_hash

# Password hashing
VALID_USERS = {
    "admin": generate_password_hash("secure_password"),
    "viewer": generate_password_hash("viewer_password")
}

# Auth setup
auth = dash_auth.BasicAuth(app, VALID_USERS)
```

Alternative options considered:
1. **Flask-Login**: More complex, overkill for this use case
2. **OAuth2**: Would require external identity provider
3. **Custom JWT**: Too much overhead for internal dashboard

**Decision**: Use `dash-auth` with bcrypt for simplicity and security.

### Docker Research

Dash applications run well in Docker with gunicorn:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8050
CMD ["gunicorn", "-b", "0.0.0.0:8050", "app:server"]
```

The dashboard should be added to docker-compose with a `monitoring` profile to allow optional deployment.

### Technology Stack Decision

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Framework | Plotly Dash 2.x | Best for Python dashboards, interactive charts |
| Async Driver | motor | Native async MongoDB support |
| Charts | Plotly Express | Declarative, consistent styling |
| Auth | dash-auth | Simple, built for Dash |
| Server | gunicorn | Production-grade WSGI |
| Container | python:3.11-slim | Small footprint, fast builds |

## References

- [Plotly Dash Documentation](https://dash.plotly.com/)
- [Motor MongoDB Driver](https://motor.readthedocs.io/)
- [dash-auth Package](https://dash.plotly.com/authentication)
- Backend models: `apps/backend/src/models/`
- Database config: `apps/backend/src/core/database.py`
