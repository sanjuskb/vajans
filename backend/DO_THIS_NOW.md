# 🎯 IMMEDIATE ACTION REQUIRED

## 1️⃣ Get Your Supabase Connection Details

Visit: https://app.supabase.com
1. Open your VAJANS project
2. Settings → Database → Connection String
3. Copy the **PostgreSQL** string

Example:
```
postgresql://postgres:ABC123xyz@db.your-project-id.supabase.co:5432/postgres
```

---

## 2️⃣ Update Your .env File

File: `/home/sanju/vajans/backend/.env`

Replace this:
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=vajans
DB_USER=vajans
DB_PASSWORD=vajans_dev_password
```

With this (from Step 1):
```bash
DATABASE_URL=postgresql+asyncpg://postgres:ABC123xyz@db.your-project-id.supabase.co:5432/postgres?ssl=require
```

**Key points:**
- Replace `ABC123xyz` with your actual password
- Replace `your-project-id` with your actual project ID
- Keep `?ssl=require` at the end (IMPORTANT!)
- Change `postgresql://` to `postgresql+asyncpg://` (IMPORTANT!)

---

## 3️⃣ Start Your Backend

```bash
cd /home/sanju/vajans/backend
uvicorn main:app --reload
```

---

## 4️⃣ Check the Logs

You should see:
```
INFO: ✓ Database tables initialised (dev mode)
```

If you see this, **you're connected!** ✅

---

## ❌ If It Fails

Check these first:
- [ ] Is the password correct? (Copy from Supabase again)
- [ ] Is the project ID correct? (Check the db. part)
- [ ] Does URL have `?ssl=require`? (Must be there)
- [ ] Does URL start with `postgresql+asyncpg://`? (Not just `postgresql://`)

---

## 🧪 Test Your Connection

```bash
curl http://localhost:8000/api/health
```

Should return:
```json
{"status":"ok"}
```

---

## 📝 .env Template (Copy & Paste)

Update the password and project ID, then paste this into `.env`:

```bash
# ── App ────────────────────────────────────────────────
APP_NAME=VAJANS
ENVIRONMENT=development
DEBUG=true

# ── Database (Supabase) ────────────────────────────────
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_ID.supabase.co:5432/postgres?ssl=require

# ── Redis ──────────────────────────────────────────────
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## ✅ That's It!

Once you update .env and restart backend, you're done!

---

## 📚 Need More Help?

- **Step-by-step guide:** See `SUPABASE_CHECKLIST.md`
- **Troubleshooting:** See `SUPABASE_SETUP.md`
- **What changed:** See `SUPABASE_CHANGELOG.md`

---

## 🎉 SUCCESS STATE

These logs mean you're connected:
```
INFO: Attempting database connection url=postgresql+asyncpg://postgres:***:***@db.*****.supabase.co:5432/postgres?ssl=require
INFO: ✓ Database tables initialised (dev mode)
INFO:     Application startup complete
```

**Backend is now connected to Supabase!** 🚀
