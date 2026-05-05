# Supabase PostgreSQL Connection Guide

## Step 1: Get Supabase Connection String

1. Go to your Supabase project dashboard: https://app.supabase.com
2. Click **Settings** → **Database**
3. Look for **Connection String** section
4. Copy the **PostgreSQL** connection string (NOT the URI)
5. Example format:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres
   ```

## Step 2: Update .env

Replace the DATABASE_URL line in `/home/sanju/vajans/backend/.env`:

```bash
# ── Database ───────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres?ssl=require
```

**Important:**
- Replace `[YOUR-PASSWORD]` with your actual Supabase password
- Replace `[PROJECT-ID]` with your Supabase project ID (from URL: db.YOUR-PROJECT-ID.supabase.co)
- Keep `?ssl=require` at the end (required for Supabase)
- Change `postgresql://` to `postgresql+asyncpg://` (async driver)

## Step 3: Verify Connection

Run the backend:
```bash
cd /home/sanju/vajans/backend
uvicorn main:app --reload
```

**Success indicators:**
```
INFO:     Application startup complete
INFO: Attempting database connection url=postgresql+asyncpg://postgres:***:***@db.*****.supabase.co:5432/postgres?ssl=require
INFO: ✓ Database tables initialised (dev mode)
```

**If connection fails:**
```
ERROR: ✗ Database connection refused
  host=Supabase
  error=[Errno 111] Connection refused or similar
```

## Troubleshooting

### Error: "Connection refused"
- ❌ Check: Is the password correct?
- ❌ Check: Is the project ID correct?
- ❌ Check: Does URL have `?ssl=require`?
- ❌ Check: Are you using `postgresql+asyncpg://` (not just `postgresql://`)?

### Error: "FATAL: invalid authentication"
- Password is incorrect
- Solution: Get password from Supabase dashboard → Settings → Database

### Error: "SSL certificate verification failed"
- Supabase requires SSL - already handled in code
- Should not occur if using `?ssl=require`

### Error: "server closed the connection unexpectedly"
- Usually means authentication failed or firewall issue
- Double-check password and URL format

## Common Mistakes

❌ Wrong:
```
DATABASE_URL=postgresql://postgres:password@db.project.supabase.co:5432/postgres
```

✅ Correct:
```
DATABASE_URL=postgresql+asyncpg://postgres:password@db.project.supabase.co:5432/postgres?ssl=require
```

Key differences:
1. `postgresql+asyncpg://` (not just `postgresql://`)
2. Password must be URL-encoded if it contains special characters
3. **Must** include `?ssl=require` for Supabase

## Password URL Encoding

If your password contains special characters, URL-encode them:
- `@` → `%40`
- `#` → `%23`
- `:` → `%3A`
- `&` → `%26`

Example: If password is `my@password`, use `my%40password`

## Example .env Configuration

```bash
# ── App ────────────────────────────────────────────────
ENVIRONMENT=development
DEBUG=true

# ── Database (Supabase) ────────────────────────────────
DATABASE_URL=postgresql+asyncpg://postgres:your_password@db.your_project_id.supabase.co:5432/postgres?ssl=require

# ── Redis ──────────────────────────────────────────────
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Getting Database Tables

Once connected, tables are auto-created on startup in development mode.

Or run migrations:
```bash
alembic upgrade head
```

## Verify Tables Created

Connect to your Supabase dashboard → SQL Editor and run:
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';
```

You should see: `job`, `file`, `chunk`, `extracted_data`, `result`, `audit`

---

✅ After these steps, backend should connect successfully to Supabase!
