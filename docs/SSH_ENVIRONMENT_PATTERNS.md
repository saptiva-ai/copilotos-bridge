# SSH Environment Variable Patterns

This document explains how to properly handle environment variables when executing commands via SSH on remote servers.

## The Problem

During our deployment on 2025-10-11, we encountered multiple issues with environment variables not being available when running scripts remotely via SSH. This is a common problem that occurs because:

1. **SSH uses a non-interactive shell** - Environment variables from files like `.bashrc`, `.profile`, or `.env` files are NOT automatically loaded
2. **No environment inheritance** - Variables set in your local shell don't transfer to the remote shell
3. **Script sourcing doesn't work** - Commands like `source .env.prod` fail in SSH one-liners

## Incident Examples

### ❌ Problem 1: Environment Variables Not Found
```bash
# This FAILS because .env.prod isn't sourced in SSH context
ssh user@server "cd /path && source envs/.env.prod && ./script.sh"

# Error: bash: line 1: envs/.env.prod: No such file or directory
```

### ❌ Problem 2: Variables Not Propagated
```bash
# This FAILS - PASSWORD environment variable is not available
ssh user@server 'MONGODB_PASSWORD=$PASSWORD ./backup-mongodb.sh'

# Error: MONGODB_PASSWORD environment variable is required!
```

## Solutions and Patterns

### ✅ Solution 1: Pass Variables Inline (Best for Single Variables)

**When to use:** You need to pass 1-3 environment variables

```bash
# Pass variables directly in the SSH command
ssh user@server "cd /path && MONGODB_PASSWORD='secret123' MONGODB_USER='user' ./backup-mongodb.sh"
```

**Pros:**
- Simple and explicit
- Works reliably
- No file dependencies

**Cons:**
- Exposes credentials in process list (temporarily)
- Cumbersome for many variables

### ✅ Solution 2: Use Script with Here-Doc (Best for Multiple Variables)

**When to use:** You need to pass many variables or execute complex commands

```bash
# Create a script on-the-fly and execute it
ssh user@server 'bash -s' << 'EOF'
export MONGODB_PASSWORD='secret123'
export MONGODB_USER='copilotos_user'
export MONGODB_DATABASE='copilotos'

cd /opt/copilotos-bridge
./scripts/backup-mongodb.sh
EOF
```

**Pros:**
- Clean and readable
- Supports complex logic
- Variables not in process list

**Cons:**
- Slightly more verbose
- Requires heredoc syntax knowledge

### ✅ Solution 3: Use --env-file Flag (Best Practice)

**When to use:** Script supports loading from file (like our updated backup-mongodb.sh)

```bash
# Script loads environment from file on remote server
ssh user@server "cd /path && ./backup-mongodb.sh --env-file envs/.env.prod"
```

**Pros:**
- Clean and secure
- No credential exposure
- Consistent with Docker patterns

**Cons:**
- Requires script modification to support flag
- File must exist on remote server

### ✅ Solution 4: Remote Bash with Source (Best for Interactive-like Execution)

**When to use:** You need the full environment as if logged in interactively

```bash
# Execute command in a login shell that sources environment
ssh user@server "bash -l -c 'cd /path && source envs/.env.prod && ./script.sh'"
```

**Pros:**
- Mimics interactive login
- Sources standard profile files

**Cons:**
- Still requires explicit source for custom .env files
- More complex command structure

## Real-World Examples from Our Deployment

### Example 1: MongoDB Backup (Solution 2 - Here-Doc)

```bash
# What we did during emergency deployment
cat > /tmp/verify_prod_data.sh << 'EOF'
#!/bin/bash
docker exec copilotos-prod-mongodb mongosh -u copilotos_prod_user -p 'ProdMongo2024!SecurePass' --authenticationDatabase admin copilotos --quiet --eval 'print("Users: " + db.users.countDocuments())'
EOF

scp /tmp/verify_prod_data.sh user@server:/tmp/
ssh user@server 'bash /tmp/verify_prod_data.sh'
```

### Example 2: Deployment Script Execution (Solution 3 - Env File)

```bash
# Updated backup script now supports --env-file
ssh user@server "cd /opt/copilotos-bridge && ./scripts/backup-mongodb.sh --env-file envs/.env.prod"

# This is cleaner than:
ssh user@server "cd /opt/copilotos-bridge && MONGODB_PASSWORD='...' MONGODB_USER='...' ./scripts/backup-mongodb.sh"
```

### Example 3: Health Check with Variables (Solution 1 - Inline)

```bash
# Simple inline for read-only operations
ssh user@server "cd /opt/copilotos-bridge && curl -s http://localhost:8001/api/health | jq ."

# No environment variables needed - API is already configured via Docker
```

## Best Practices

### 1. Design Scripts to Accept --env-file Flag

```bash
#!/bin/bash
# Support both environment variables AND --env-file flag

ENV_FILE=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
  esac
done

# Load from file if specified
if [ -n "$ENV_FILE" ] && [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
fi

# Use environment variables with defaults
MONGODB_USER="${MONGODB_USER:-copilotos_user}"
MONGODB_PASSWORD="${MONGODB_PASSWORD:-}"
```

### 2. Create Wrapper Scripts on Remote Server

```bash
# /opt/copilotos-bridge/scripts/backup-with-prod-env.sh
#!/bin/bash
cd "$(dirname "$0")/.."
source envs/.env.prod
./scripts/backup-mongodb.sh "$@"
```

Then from local machine:
```bash
ssh user@server '/opt/copilotos-bridge/scripts/backup-with-prod-env.sh'
```

### 3. Use SSH Configuration for Environment Setup

Add to `~/.ssh/config`:
```
Host prod-server
    HostName 34.42.214.246
    User jf
    SendEnv MONGODB_PASSWORD
    RemoteCommand cd /opt/copilotos-bridge && bash
```

Then:
```bash
MONGODB_PASSWORD='secret' ssh prod-server './scripts/backup-mongodb.sh'
```

### 4. Document Required Variables

Always document in script headers:
```bash
# Environment Variables Required:
#   MONGODB_PASSWORD   MongoDB password (required)
#   MONGODB_USER       MongoDB username (default: copilotos_user)
#
# Usage:
#   # Option 1: With env file
#   ./script.sh --env-file envs/.env.prod
#
#   # Option 2: With inline variables
#   MONGODB_PASSWORD='secret' ./script.sh
#
#   # Option 3: Via SSH
#   ssh user@server "cd /path && ./script.sh --env-file envs/.env.prod"
```

## Testing Patterns

### Test 1: Verify Variables Are Set
```bash
ssh user@server "bash -s" << 'EOF'
export MONGODB_PASSWORD='test'
if [ -z "$MONGODB_PASSWORD" ]; then
    echo "FAIL: Variable not set"
else
    echo "PASS: Variable is set"
fi
EOF
```

### Test 2: Test Script with Different Methods
```bash
# Test 1: Inline
ssh user@server "VAR='value' ./script.sh"

# Test 2: Here-doc
ssh user@server 'bash -s' << 'EOF'
export VAR='value'
./script.sh
EOF

# Test 3: Env file
ssh user@server "./script.sh --env-file .env"
```

## Security Considerations

1. **Don't log credentials**: Ensure scripts don't echo passwords
2. **Use process substitution**: `<(echo "$PASSWORD")` instead of passing directly
3. **Temporary file cleanup**: Always clean up any temp files containing credentials
4. **Audit script execution**: Monitor who executes sensitive scripts

## Conclusion

The key lesson from our deployment incident:

> **Never assume environment variables are available in SSH contexts.**
>
> Always use explicit patterns:
> 1. Pass inline for simple cases
> 2. Use here-docs for complex cases
> 3. Support --env-file in scripts (best practice)
> 4. Test SSH commands locally first

## References

- Post-mortem: `docs/POST-MORTEM-DEPLOYMENT-2025-10-11.md`
- Backup script: `scripts/backup-mongodb.sh`
- Deployment script: `scripts/deploy-on-server.sh`
