# Security Review Checklist

## OWASP Top 10 (2021)

### A01: Broken Access Control

```python
# ❌ Missing authorization check
@router.get("/users/{user_id}/data")
async def get_user_data(user_id: str):
    return await db.get_user_data(user_id)  # Anyone can access!

# ✅ With authorization
@router.get("/users/{user_id}/data")
async def get_user_data(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(403, "Not authorized")
    return await db.get_user_data(user_id)
```

**Check for:**
- Every endpoint has auth check (`Depends(get_current_user)`)
- Resource ownership verified
- Admin-only endpoints protected

### A02: Cryptographic Failures

```python
# ❌ Weak hashing
password_hash = hashlib.md5(password.encode()).hexdigest()

# ✅ Strong hashing
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password_hash = pwd_context.hash(password)
```

**Check for:**
- Passwords use bcrypt/argon2
- Secrets not in code
- HTTPS enforced

### A03: Injection

```python
# ❌ SQL injection
query = f"SELECT * FROM users WHERE id = '{user_id}'"
cursor.execute(query)

# ✅ Parameterized query
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# ✅ ORM (Beanie)
user = await User.find_one(User.id == user_id)
```

```python
# ❌ Command injection
os.system(f"convert {user_filename} output.png")

# ✅ Safe subprocess
import shlex
subprocess.run(["convert", shlex.quote(user_filename), "output.png"])
```

**Check for:**
- No string interpolation in queries
- ORM used for database access
- User input sanitized before shell commands

### A04: Insecure Design

**Check for:**
- Rate limiting on auth endpoints
- Account lockout after failed attempts
- Sensitive actions require re-authentication

### A05: Security Misconfiguration

```python
# ❌ Debug mode in production
app = FastAPI(debug=True)

# ✅ Environment-based
app = FastAPI(debug=settings.debug)
```

**Check for:**
- Debug disabled in production
- Default credentials changed
- Error messages don't expose internals

### A06: Vulnerable Components

```bash
# Check for known vulnerabilities
pip audit
pnpm audit
```

**Check for:**
- Dependencies up to date
- No known CVEs in dependencies

### A07: Authentication Failures

```python
# ❌ Weak JWT
token = jwt.encode(payload, "secret", algorithm="HS256")

# ✅ Strong JWT
token = jwt.encode(
    payload,
    settings.jwt_secret,  # From environment
    algorithm="HS256"
)

# Verify token expiration
if payload["exp"] < datetime.utcnow().timestamp():
    raise HTTPException(401, "Token expired")
```

**Check for:**
- JWT secret from environment
- Token expiration checked
- Refresh token rotation

### A08: Software and Data Integrity

**Check for:**
- Dependencies from trusted sources
- Integrity checks on downloads
- CI/CD pipeline protected

### A09: Logging Failures

```python
# ❌ Logging sensitive data
logger.info(f"User login: {email}, password: {password}")

# ✅ Safe logging
logger.info(f"User login: {email}")
```

**Check for:**
- No passwords/tokens in logs
- Failed auth attempts logged
- Audit trail for sensitive operations

### A10: SSRF

```python
# ❌ User-controlled URL
response = requests.get(user_provided_url)

# ✅ Allowlist
ALLOWED_HOSTS = ["api.example.com", "cdn.example.com"]
parsed = urlparse(user_provided_url)
if parsed.netloc not in ALLOWED_HOSTS:
    raise ValueError("URL not allowed")
```

**Check for:**
- External URLs validated
- Internal networks not accessible
- Redirects limited

## Quick Security Scan

| Pattern | Risk | Search |
|---------|------|--------|
| `eval(` | Code injection | `grep -r "eval(" src/` |
| `exec(` | Code injection | `grep -r "exec(" src/` |
| `pickle.loads` | Deserialization | `grep -r "pickle" src/` |
| `shell=True` | Command injection | `grep -r "shell=True" src/` |
| `password` in code | Hardcoded secret | `grep -ri "password.*=" src/` |
| `secret` in code | Hardcoded secret | `grep -ri "secret.*=" src/` |
| `f"SELECT` | SQL injection | `grep -r 'f"SELECT' src/` |
