# Code Review Patterns

## Code Smells to Flag

### Complexity Smells

| Smell | Detection | Recommendation |
|-------|-----------|----------------|
| Long method | >20 lines | Extract smaller methods |
| Long class | >200 lines | Split by responsibility |
| Deep nesting | >3 levels | Early returns, extract |
| Long parameter list | >4 params | Use object/dataclass |
| Feature envy | Method uses other class more | Move method |
| God class | Does everything | Apply SRP |

### Duplication Smells

```python
# ❌ Code duplication
def get_user_by_id(user_id):
    user = db.query(f"SELECT * FROM users WHERE id = {user_id}")
    if not user:
        raise NotFoundError("User not found")
    return user

def get_user_by_email(email):
    user = db.query(f"SELECT * FROM users WHERE email = {email}")
    if not user:
        raise NotFoundError("User not found")  # Duplicated!
    return user

# ✅ Extract common logic
def _get_user(query, params):
    user = db.query(query, params)
    if not user:
        raise NotFoundError("User not found")
    return user
```

### Naming Smells

| Smell | Example | Better |
|-------|---------|--------|
| Single letter | `x`, `d` | `user`, `document` |
| Abbreviation | `usr`, `doc` | `user`, `document` |
| Generic | `data`, `info` | `user_profile`, `order_details` |
| Misleading | `userList` (is dict) | `users_by_id` |
| Boolean without is/has | `valid` | `is_valid` |

### Error Handling Smells

```python
# ❌ Swallowing exceptions
try:
    process_data()
except Exception:
    pass  # Silent failure!

# ❌ Catching too broad
try:
    user = get_user(id)
except Exception as e:
    return None  # Hides real errors

# ✅ Specific exceptions
try:
    user = get_user(id)
except UserNotFoundError:
    return None
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    raise
```

## Anti-Patterns

### Backend (Python/FastAPI)

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Fat router | Business logic in router | Move to service layer |
| Anemic service | Service just calls DB | Add business logic |
| Missing DI | `service = ChatService()` | Use `Depends()` |
| Sync in async | `requests.get()` in async | Use `httpx.AsyncClient` |
| N+1 queries | Loop with DB calls | Batch query |

```python
# ❌ Fat router
@router.post("/orders")
async def create_order(request: OrderRequest):
    # Validation
    if not request.items:
        raise HTTPException(400, "No items")
    # Business logic (should be in service!)
    total = sum(item.price * item.qty for item in request.items)
    if total > user.credit_limit:
        raise HTTPException(400, "Credit exceeded")
    # Database
    order = Order(user_id=user.id, total=total)
    await order.insert()
    # Notification (should be in service!)
    await send_email(user.email, "Order created")
    return order

# ✅ Thin router
@router.post("/orders")
async def create_order(
    request: OrderRequest,
    service: OrderService = Depends(get_order_service),
    user: User = Depends(get_current_user),
):
    return await service.create_order(user, request)
```

### Frontend (React/TypeScript)

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Prop drilling | Props passed 5+ levels | Context or state management |
| God component | 500+ lines | Split into smaller components |
| useEffect abuse | Effects for derived state | useMemo, computed values |
| Inline handlers | `onClick={() => ...}` | useCallback for stable refs |
| any type | `data: any` | Define proper interface |

```typescript
// ❌ Prop drilling
<App>
  <Layout user={user}>
    <Sidebar user={user}>
      <UserProfile user={user}>  {/* 4 levels deep! */}
        <UserAvatar user={user} />

// ✅ Context
const UserContext = createContext<User | null>(null);

function App() {
  return (
    <UserContext.Provider value={user}>
      <Layout>
        <Sidebar>
          <UserProfile />  {/* Uses useContext(UserContext) */}
```

## Review Questions

### For New Endpoints
1. Is authentication required?
2. Is authorization checked?
3. Are inputs validated?
4. Are errors handled?
5. Is it tested?

### For Database Changes
1. Is migration reversible?
2. Are indexes needed?
3. Is data integrity maintained?
4. Are existing records migrated?

### For Frontend Changes
1. Does it handle loading state?
2. Does it handle error state?
3. Is it accessible (a11y)?
4. Is it responsive?
5. Are there tests?

## Evidence Template

```markdown
## Code Review: [PR Title]

### Summary
[1-2 sentences on what the PR does]

### Findings

#### Critical
| File:Line | Issue | Fix |
|-----------|-------|-----|
| src/auth.py:42 | SQL injection | Use ORM |

#### High
| File:Line | Issue | Fix |
|-----------|-------|-----|
| src/api.py:88 | Missing null check | Add guard |

#### Medium
| File:Line | Issue | Fix |
|-----------|-------|-----|
| src/service.py:120 | Long method (45 lines) | Extract |

### Test Coverage
- [ ] `POST /orders` needs integration test
- [x] `OrderService.create()` has unit test

### Verdict
**REQUEST_CHANGES** - Critical security issue must be fixed
```
