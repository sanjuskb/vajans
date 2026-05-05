# VAJANS — Automated Government Tender Evaluation System

> **Phase 0 — Foundation** | Production-grade base for an AI-assisted, rule-based tender evaluation pipeline.

---

## Architecture Overview

```
Upload → Ingestion → Criteria Extraction → RAG → Extraction
       → Normalization → Rule Engine → TrustScore
       → Routing → Explainability → Dashboard
```

### Core Principle
**LLM is ONLY used for reading and extracting data. Zero AI in decision-making.**  
All verdicts come from a deterministic rule engine. Every output traces to a document → page → snippet.

---

## Monorepo Structure

```
vajans/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/      # FastAPI route handlers
│   │   │   ├── health.py          # /health + /health/ready
│   │   │   ├── jobs.py            # CRUD for evaluation jobs
│   │   │   └── files.py           # File upload endpoint
│   │   ├── core/
│   │   │   ├── settings.py        # Pydantic-Settings config
│   │   │   └── logging.py         # Structured JSON logging
│   │   ├── db/
│   │   │   └── session.py         # Async SQLAlchemy engine + session
│   │   ├── models/                # SQLAlchemy ORM models
│   │   │   ├── job.py             # Job
│   │   │   ├── file.py            # File
│   │   │   ├── chunk.py           # Chunk (RAG unit)
│   │   │   ├── extracted_data.py  # LLM extraction result
│   │   │   ├── result.py          # Evaluation result + trust score
│   │   │   └── audit.py          # Append-only audit log
│   │   ├── services/
│   │   │   └── storage.py         # Storage abstraction (Local / S3)
│   │   └── main.py               # App factory, middleware, router setup
│   ├── worker/
│   │   ├── celery_app.py          # Celery configuration
│   │   └── tasks/
│   │       ├── ingestion.py       # ingest_file, ingest_job tasks
│   │       ├── extraction.py      # extract_bidder, extract_criteria tasks
│   │       └── evaluation.py      # evaluate_bidder, evaluate_job tasks
│   ├── alembic/                   # DB migration scripts
│   ├── main.py                    # Uvicorn entry point
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   └── src/
│       ├── services/
│       │   ├── apiClient.ts       # Axios instance with interceptors
│       │   ├── api.ts             # Domain-specific API functions
│       │   └── types.ts           # TypeScript types (mirrors backend schemas)
│       ├── components/layout/     # Layout shell (sidebar + outlet)
│       └── pages/
│           ├── DashboardPage.tsx  # System health + job stats
│           ├── JobsPage.tsx       # Job list + create
│           └── JobDetailPage.tsx  # File uploads + pipeline status
│
├── shared/
│   └── contracts/
│       └── schemas.py             # ★ Single source of truth: all Pydantic schemas
│
├── data/
│   └── sample/
│       ├── tender_KSRDC_NH275_2024.json   # Realistic tender document
│       └── bidders_all_5.json              # 5 bidder profiles (all edge cases)
│
└── docker-compose.yml             # PostgreSQL 16 + Redis 7
```

---

## Data Contracts (shared/contracts/schemas.py)

| Schema | Purpose |
|---|---|
| `Job` | Top-level evaluation job |
| `File` | Uploaded tender / bidder document |
| `Chunk` | RAG text unit (page + index + embedding) |
| `ExtractedDocument` | Full parsed document with page-level text |
| `Criterion` | A single rule from the tender (field + operator + threshold) |
| `CriteriaSet` | All criteria for one tender |
| `ExtractedField` | One value pulled from a bidder document |
| `BidderExtraction` | All extracted fields for one bidder |
| `CriterionResult` | Verdict for one rule (with source trace) |
| `EvaluationResult` | Full bidder evaluation (deterministic) |
| `TrustScore` | Reliability score for a bidder's extraction |
| `AuditLog` | Append-only action trail |

---

## Prerequisites (WSL / Ubuntu)

```bash
# System packages
sudo apt update && sudo apt install -y \
  python3.11 python3.11-venv python3-pip \
  tesseract-ocr tesseract-ocr-eng \
  libgl1-mesa-glx libglib2.0-0 \
  postgresql-client \
  nodejs npm

# Docker (for Postgres + Redis)
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER   # re-login after this
```

---

## Setup Instructions

### 1. Clone & enter the project

```bash
git clone <repo-url>
cd vajans
```

### 2. Start infrastructure (Postgres + Redis)

```bash
docker-compose up -d
# Verify:
docker-compose ps
```

### 3. Backend — Python environment

```bash
cd backend

python3.11 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

# Add shared/ to PYTHONPATH so imports resolve
export PYTHONPATH=$(pwd)/..:$PYTHONPATH
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env — set OPENROUTER_API_KEY and any other values
nano .env
```

### 5. Run database migrations

```bash
# Using Alembic (production-safe):
alembic upgrade head

# OR for development (auto-create tables):
# Tables are auto-created on startup in ENVIRONMENT=development (default)
```

### 6. Start the backend

```bash
# From backend/ with venv active and PYTHONPATH set:
python main.py
# OR:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs: http://localhost:8000/api/docs  
Health: http://localhost:8000/api/health/ready

### 7. Start Celery worker

```bash
# In a new terminal, from backend/ with venv + PYTHONPATH:
source .venv/bin/activate
export PYTHONPATH=$(pwd)/..:$PYTHONPATH

celery -A worker.celery_app worker \
  --loglevel=info \
  --queues=ingestion,extraction,evaluation,default \
  --concurrency=4
```

### 8. Frontend

```bash
cd ../frontend

npm install

# Create local env
cp .env.example .env

npm run dev
# → http://localhost:3000
```

---

## API Endpoints (Phase 0)

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness probe |
| GET | `/api/health/ready` | Readiness (DB + Redis) |
| POST | `/api/v1/jobs/` | Create job |
| GET | `/api/v1/jobs/` | List jobs |
| GET | `/api/v1/jobs/{id}` | Get job |
| DELETE | `/api/v1/jobs/{id}` | Delete job |
| POST | `/api/v1/files/upload` | Upload file (multipart) |
| GET | `/api/v1/files/job/{id}` | List files for job |
| GET | `/api/v1/files/{id}` | Get file record |

---

## Pipeline Phases

| Phase | Status | Scope |
|---|---|---|
| 0 — Foundation | ✅ **Current** | Schema, DB models, API skeleton, Celery scaffold, frontend shell |
| 1 — Backend Skeleton | ⬜ Next | Service layer, repository pattern |
| 2 — Ingestion | ⬜ | PyMuPDF, pdfplumber, Tesseract OCR, chunking |
| 3 — RAG + Extraction | ⬜ | FAISS, embeddings, LLM field extraction |
| 4 — Rule Engine | ⬜ | Deterministic criterion evaluation |
| 5 — TrustScore | ⬜ | Confidence scoring, OCR noise detection |
| 6 — Explainability | ⬜ | Reason generation, source tracing |
| 7 — Frontend | ⬜ | Results dashboard, evaluation reports |
| 8 — Integration | ⬜ | S3 storage, auth, production hardening |

---

## Branch Strategy

```
main          ← stable, tested code only
develop       ← integration branch
phase/0-foundation  ← Phase 0 work (this branch)
phase/1-skeleton
phase/2-ingestion
...
feature/<name>  ← individual feature branches off phase branches
fix/<name>      ← hotfixes
```

PRs go to the phase branch → reviewed → merged to develop → QA → main.

---

## Design Decisions

**Why async SQLAlchemy?**  
FastAPI is async-native; async DB prevents thread-pool exhaustion under concurrent requests.

**Why Celery + Redis over async background tasks?**  
PDF ingestion + LLM calls can take 60–120s. Celery gives durability, retries, monitoring, and horizontal scaling that `BackgroundTasks` cannot.

**Why JSONB for extracted fields?**  
Schema evolution. As new criteria are added, the JSONB columns adapt without migrations. The rule engine reads from the Pydantic layer, not raw JSONB.

**Why shared/contracts/schemas.py?**  
One source of truth prevents drift between DB models, API schemas, and Celery task payloads — a common failure mode in distributed systems.

---

## Troubleshooting

**ImportError on shared.contracts.schemas**  
```bash
# Ensure PYTHONPATH includes the monorepo root:
export PYTHONPATH=/path/to/vajans/backend:/path/to/vajans:$PYTHONPATH
```

**Celery worker can't connect to broker**  
```bash
docker-compose ps   # verify Redis is running
redis-cli ping      # should return PONG
```

**DB connection refused**  
```bash
docker-compose ps   # verify Postgres is healthy
psql -h localhost -U vajans -d vajans -c "SELECT 1;"
```
