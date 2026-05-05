# ✅ Supabase Connection Setup Checklist

## 🎯 Goal
Connect VAJANS backend to Supabase PostgreSQL database

## 📋 Checklist

### Phase 1: Gather Information (5 minutes)
- [ ] Open https://app.supabase.com in browser
- [ ] Click on your VAJANS project
- [ ] Go to: **Settings** → **Database**
- [ ] Find: **Connection String** section
- [ ] Copy: **PostgreSQL** connection string (click copy button)
- [ ] Example: `postgresql://postgres:ABC123@db.xyz.supabase.co:5432/postgres`

### Phase 2: Update Configuration (2 minutes)
- [ ] Open: `/home/sanju/vajans/backend/.env` in editor
- [ ] Find line: `DB_HOST=localhost`
- [ ] REPLACE the entire DATABASE section with:
  ```
  DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_ID.supabase.co:5432/postgres?ssl=require
  ```
- [ ] Replace `YOUR_PASSWORD` from copied connection string
- [ ] Replace `YOUR_PROJECT_ID` from copied connection string
- [ ] **Save file**

### Phase 3: Start Backend (2 minutes)
- [ ] Open terminal in VS Code
- [ ] Navigate: `cd /home/sanju/vajans/backend`
- [ ] Run: `uvicorn main:app --reload`
- [ ] **Wait for startup** (takes ~5 seconds)

### Phase 4: Verify Connection (1 minute)
- [ ] Check logs for: `INFO: ✓ Database tables initialised (dev mode)`
- [ ] OR check for: `INFO: Attempting database connection url=postgresql+asyncpg://...`
- [ ] ❌ If you see `ERROR: ✗ Database connection refused`, go to **Troubleshooting**

### Phase 5: Test Endpoint (1 minute)
- [ ] Open new terminal
- [ ] Run: `curl http://localhost:8000/api/health`
- [ ] Expected response: `{"status":"ok"}`
- [ ] ✅ If you get the response, **SUCCESS!**

---

## ⏱️ Total Time: ~15 minutes

---

## 🆘 Troubleshooting

### Issue 1: "Connection refused"
**Problem:** Backend fails to connect to Supabase

**Checklist:**
- [ ] Is DATABASE_URL set correctly? (Check .env)
- [ ] Is password correct? (Compare with Supabase)
- [ ] Is project ID correct? (Check URL format)
- [ ] Does URL have `?ssl=require`? (Required for Supabase)
- [ ] Does URL use `postgresql+asyncpg://`? (Not just `postgresql://`)

**Solution:**
1. Go to Supabase dashboard again
2. Settings → Database
3. Copy EXACT connection string
4. Replace in .env
5. Restart backend

### Issue 2: "FATAL: invalid authentication"
**Problem:** Password is wrong

**Solution:**
1. Go to Supabase → Settings → Database
2. Click **Reset database password**
3. Copy new password
4. Update DATABASE_URL in .env
5. Restart backend

### Issue 3: Backend starts but DB tables not created
**Problem:** Connection works but tables missing

**Expected:** `✓ Database tables initialised (dev mode)` in logs

**Solution:**
1. Tables are auto-created on first startup
2. Check logs for any errors
3. If tables still not created, run:
   ```bash
   alembic upgrade head
   ```

### Issue 4: "ssl=" in URL but still fails
**Problem:** SSL configuration issue

**Solution:**
1. Ensure URL is exactly:
   ```
   postgresql+asyncpg://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres?ssl=require
   ```
2. Check for typos in password
3. Ensure no extra spaces

---

## 📝 Example .env (Complete)

```bash
# ── App ────────────────────────────────────────────────
APP_NAME=VAJANS
APP_VERSION=0.1.0
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=change-me-later

# ── Database (Supabase) ────────────────────────────────
DATABASE_URL=postgresql+asyncpg://postgres:your_supabase_password@db.your_project_id.supabase.co:5432/postgres?ssl=require

# ── Redis ──────────────────────────────────────────────
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

---

## ✅ Success Indicators

### Logs show:
```
INFO:     Application startup complete
INFO: Attempting database connection url=postgresql+asyncpg://postgres:***:***@db.*****.supabase.co:5432/postgres?ssl=require
INFO: ✓ Database tables initialised (dev mode)
```

### Health endpoint works:
```bash
$ curl http://localhost:8000/api/health
{"status":"ok"}
```

### Swagger UI works:
Visit: http://localhost:8000/api/docs (if DEBUG=true)

---

## 🎉 You're Done!

If all checkboxes are checked and you see the success indicators, **backend is connected to Supabase!**

### Next Steps:
1. Stop backend: `Ctrl+C`
2. Proceed to Phase 1 development
3. Keep `.env` file safe (don't commit to git)

---

## 📚 More Information

- **Detailed guide:** See `SUPABASE_SETUP.md`
- **Common mistakes:** See `SUPABASE_FIX_SUMMARY.md`
- **Technical details:** See `SUPABASE_CHANGELOG.md`
- **Quick reference:** See `SUPABASE_QUICK_FIX.md`

---

## 💾 File Locations

| File | Purpose |
|------|---------|
| `/home/sanju/vajans/backend/.env` | Configuration (your password here) |
| `/home/sanju/vajans/backend/main.py` | ASGI entry point |
| `/home/sanju/vajans/backend/app/core/settings.py` | Settings loader |
| `/home/sanju/vajans/backend/app/db/session.py` | Database engine |
| `/home/sanju/vajans/backend/app/main.py` | FastAPI app |

---

## ⏰ Remember

- ✅ Never commit `.env` to git (it has your password!)
- ✅ `.env.example` shows example without secrets
- ✅ Each developer needs their own `.env` file
- ✅ Keep Supabase password safe

---

**Questions?** Check the documentation files in `/home/sanju/vajans/backend/`

**Status:** 🟢 Phase 0 Complete — Ready for Phase 1
