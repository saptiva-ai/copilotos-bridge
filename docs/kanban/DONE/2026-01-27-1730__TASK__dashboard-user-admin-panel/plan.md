# Implementation Plan: Dashboard User Administration Panel

## Overview
Extend the dashboard's Users tab with a comprehensive admin panel featuring user monitoring table and secure user creation.

---

## Phase 1: User Queries Extension
**Files:** `apps/dashboard/queries/users.py`

Add methods to:
1. `get_all_users_with_stats()` - Return all users with message/conversation/rating counts via MongoDB aggregation
2. `create_user()` - Create new user with hashed password using Argon2

---

## Phase 2: User Table Layout
**Files:** `apps/dashboard/layouts/users.py`

Add below existing KPI/chart rows:
1. `dash_table.DataTable` with columns: email, username, created_at, last_login, status, messages, conversations, ratings
2. Pagination support
3. Sorting by column

---

## Phase 3: User Creation Panel
**Files:** `apps/dashboard/layouts/users.py`, `apps/dashboard/callbacks/users.py`

Add:
1. Email input field
2. Generate password button (calls `openssl rand -base64 16`)
3. Password display field with:
   - Visibility toggle (show/hide)
   - Copy to clipboard button
4. Create User button

---

## Phase 4: Callbacks & Integration
**Files:** `apps/dashboard/callbacks/users.py`

Implement callbacks for:
1. Generate password → run `openssl rand` via subprocess
2. Toggle password visibility
3. Copy to clipboard (clientside callback)
4. Create user → call `create_user()` query
5. Refresh table after user creation

---

## Phase 5: Branding & Styling
**Files:** `apps/dashboard/app.py`, `apps/dashboard/assets/` (if needed)

1. Add mint green color variables:
   - `--mint-primary: #2DD4BF`
   - `--mint-bright: #49F7D9`
2. Apply to buttons, accents, active states
3. Add OctaviOS/Saptiva logo to login page and header

---

## Acceptance Checklist
- [ ] User table displays all required columns
- [ ] Password generated securely with `openssl rand`
- [ ] Password visibility toggle works
- [ ] Copy to clipboard shows feedback
- [ ] New user appears in table after creation
- [ ] Mint green styling applied
- [ ] Company logo visible on login/header
