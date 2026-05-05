# VAJANS Backend Quick Start — Phase 0

## ⚡ 5-Minute Setup

### 1. Install Dependencies
```bash
cd /home/sanju/vajans/backend
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example and fill in your database details:
```bash
cp .env.example .env
```

**For Local PostgreSQL (Development):**
```bash
# .env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=vajans
DB_USER=vajans
DB_PASSWORD=your_password
DB_SSL_MODE=disable
ENVIRONMENT=development
DEBUG=true
```

**For Supabase (Production):**
```bash
# .env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.supabase.co:5432/postgres?ssl=require
ENVIRONMENT=production
DEBUG=false
```

### 3. Start Backend

```bash
cd /home/sanju/vajans/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 4. Test Health Endpoint

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{"status": "ok"}
```

---

## 📋 Troubleshooting

### Issue: Backend won't start
```
ERROR: No module named 'shared'
```
**Fix:** Make sure you're in the `backend/` directory and you have the latest `main.py`.

### Issue: Database connection fails
```
ConnectionRefusedError: [Errno 111] Connection refused
```
**Status:** ⚠️ **This is expected** if PostgreSQL isn't running
- Backend still starts successfully
- You can test non-DB endpoints
- Once DB is ready, restart backend

### Issue: Supabase connection fails
```
asyncpg.exceptions.UnknownServerError: FATAL: invalid authentication
```
**Fix:** Check your DATABASE_URL password is correct

---

## 🎯 Endpoint Testing

Once backend is running:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Health check (no DB needed) |
| `/api/v1/jobs` | GET | List jobs (needs DB) |
| `/api/v1/files` | POST | Upload file (needs DB) |
| `/api/docs` | GET | Interactive API docs (if DEBUG=true) |

---

## 🔄 Database Operations

### Create Tables (Dev Mode)
Tables are auto-created on startup in development mode.
Check logs for: `"Database tables initialised (dev mode)"`

### Run Migrations (Production)
```bash
# Apply all pending migrations
alembic upgrade head

# Check current migration status
alembic current

# Create new migration
alembic revision --autogenerate -m "add user table"
```

---

## 🚀 Next Steps

- [ ] Backend running without errors
- [ ] Health endpoint responding
- [ ] Database connected (optional for now)
- [ ] Ready for Phase 1 development

See [PHASE_0_STABILIZATION_FIX.md](PHASE_0_STABILIZATION_FIX.md) for complete documentation.

