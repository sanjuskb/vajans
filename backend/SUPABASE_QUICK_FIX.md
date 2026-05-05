# 🚀 Quick Fix: Supabase Connection

## In 3 Steps

### 1️⃣ Get Supabase Connection Details
```
https://app.supabase.com 
  → Your Project 
  → Settings 
  → Database 
  → Connection String (PostgreSQL)
```

Copy the connection string (looks like):
```
postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_ID.supabase.co:5432/postgres
```

### 2️⃣ Update .env
Edit `/home/sanju/vajans/backend/.env`:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_ID.supabase.co:5432/postgres?ssl=require
```

**Key changes from Supabase string:**
- `postgresql://` → `postgresql+asyncpg://` (async driver)
- Add `?ssl=require` at the end

### 3️⃣ Start Backend
```bash
cd /home/sanju/vajans/backend
uvicorn main:app --reload
```

✅ **Success** = See this in logs:
```
INFO: ✓ Database tables initialised (dev mode)
```

---

## Template (Copy & Paste)

Replace `PASSWORD` and `PROJECT_ID`:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@db.PROJECT_ID.supabase.co:5432/postgres?ssl=require
```

---

## Test Connection

```bash
curl http://localhost:8000/api/health
```

Should return: `{"status": "ok"}`

---

## ❌ If It Fails

Check logs for error message. Common issues:

| Error | Fix |
|-------|-----|
| `Connection refused` | Wrong password or project ID |
| `invalid authentication` | Wrong password |
| `FATAL: ...` | Check DATABASE_URL format |

See **SUPABASE_SETUP.md** for detailed troubleshooting.

---

## 📝 What Was Fixed

✅ SSL support for Supabase
✅ AsyncPG SSL configuration  
✅ Better error logging
✅ Connection string parsing

---

**That's it! Backend should now connect to Supabase successfully.** ✅
