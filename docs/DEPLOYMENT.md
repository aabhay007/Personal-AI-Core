# Personal AI Core — Production Deployment Guide

This guide details the complete production deployment procedures for **Personal AI Core**, covering self-hosted Docker deployments, cloud database connections (Neon PostgreSQL with pgvector), Vercel frontend hosting, automatic HTTPS via Caddy, rate limiting, and backup/disaster recovery workflows.

---

## 1. Architecture Overview

```
                      +-----------------------------+
                      |         Internet            |
                      +--------------+--------------+
                                     |
                                     v
                 +---------------------------------------+
                 |    Caddy Reverse Proxy (HTTPS/TLS)    |
                 +-------------------+-------------------+
                                     |
              +----------------------+----------------------+
              |                                             |
              v                                             v
+---------------------------+                 +---------------------------+
|    Next.js App Router     |                 |      FastAPI Backend      |
|    Frontend (Port 3000)   |                 |    AI Core (Port 8000)    |
+---------------------------+                 +-------------+-------------+
                                                            |
                                             +--------------+--------------+
                                             |                             |
                                             v                             v
                              +---------------------------+  +---------------------------+
                              |      Neon PostgreSQL      |  |   Local Storage Volume    |
                              |       with pgvector       |  |  (PDFs, Chunks, Embeds)   |
                              +---------------------------+  +---------------------------+
```

---

## 2. Environment Variables & Secrets Checklist

Create a secure `.env` file for the backend:

```ini
# Core Configuration
ENVIRONMENT=production
DEBUG=false
PROJECT_NAME="Personal AI Core"
VERSION=1.0.0
API_V1_PREFIX=/api/v1

# Security & Cryptography (Generate with: openssl rand -hex 32)
SECRET_KEY=generate_a_secure_random_64_character_hex_string_here
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database Connection (Neon PostgreSQL or local pgvector container)
DATABASE_URL=postgresql+asyncpg://<username>:<password>@<neon-endpoint>.neon.tech/<dbname>?ssl=require
DATABASE_CONNECT_TIMEOUT_SECONDS=10

# AI Provider Configuration (Zero Paid APIs by default)
GROQ_API_KEY=your_free_groq_api_key_here
DEFAULT_LLM_PROVIDER=groq
DEFAULT_MODEL_NAME=llama-3.3-70b-versatile
MAX_CONTEXT_MESSAGES=20
MAX_TOKENS_PER_REQUEST=4096

# CORS Origin Allowlist
BACKEND_CORS_ORIGINS=["https://yourdomain.com", "http://localhost:3000"]
```

---

## 3. Database Migrations (Neon PostgreSQL)

Before launching the backend container, execute Alembic migrations to apply all schema revisions:

```bash
cd backend
# Using local virtual environment:
.\.venv\Scripts\alembic.exe upgrade head

# Or inside Docker:
docker exec -it personal_ai_backend alembic upgrade head
```

All 6 migration revisions will be executed in sequence:
- `001_phase1_auth_conversations` (Users, Workspaces, Conversations, Messages)
- `002_phase3_tools` (Tools & Tool Execution Audit Logs)
- `003_phase4_documents` (Documents & RAG Chunks with Vector Embeddings)
- `004_phase5_integrations` (PostgreSQL & SQLite Integrations with Encrypted Credentials)
- `005_phase6_developer_assistant` (Code Repositories & Syntax Indexing)
- `006_phase7_advanced_agent` (Autonomous Tasks & Human-in-the-Loop Approvals)

---

## 4. Self-Hosted Full-Stack Deployment (Docker Compose)

The production Docker Compose configuration sets up:
- **Caddy** (Reverse proxy with automatic Let's Encrypt SSL/TLS certificates and gzip/zstd compression)
- **FastAPI Backend** (Python 3.12 with sliding window rate limiting and Uvicorn workers)
- **Next.js Frontend** (Node.js 20 lightweight standalone production build)
- **PostgreSQL + pgvector** (Self-hosted fallback if not using Neon)

### Steps to Deploy:

1. Configure domain in `infrastructure/Caddyfile`:
   ```caddy
   yourdomain.com {
       encode zstd gzip
       handle /* {
           reverse_proxy frontend:3000
       }
       handle /api/* {
           reverse_proxy backend:8000
       }
       handle /health {
           reverse_proxy backend:8000
       }
   }
   ```

2. Start the stack:
   ```bash
   cd infrastructure
   docker compose up -d --build
   ```

3. Verify running containers:
   ```bash
   docker compose ps
   ```

4. Test health check:
   ```bash
   curl -i https://yourdomain.com/health
   # Expected: HTTP/2 200 {"status": "healthy", "service": "personal_ai_core", ...}
   ```

---

## 5. Frontend Vercel Deployment (Alternative)

If you prefer hosting the Next.js frontend on Vercel:

1. Connect the GitHub repository to Vercel.
2. Set Root Directory to `frontend`.
3. Add Environment Variable:
   - `NEXT_PUBLIC_API_BASE_URL`: `https://api.yourdomain.com` (pointing to your FastAPI backend).
4. Click **Deploy**. Vercel will automatically run `npm run build` and serve the App Router frontend globally.

---

## 6. Rate Limiting & Protection

Personal AI Core enforces in-memory sliding-window rate limits:
- **Authentication Endpoints** (`/api/v1/auth/login`, `/api/v1/auth/register`): 15 requests per minute per IP.
- **General API Endpoints**: 120 requests per minute per client.
- When exceeded, returns `HTTP 429 Too Many Requests` with a `Retry-After` header.

---

## 7. Backup and Disaster Recovery

### Creating a Backup:
Run the backup script to capture both the database state and document storage files:

- **Linux / VPS**:
  ```bash
  cd infrastructure/scripts
  chmod +x backup.sh
  ./backup.sh
  ```
- **Windows PowerShell**:
  ```powershell
  cd infrastructure/scripts
  .\backup.ps1
  ```

Backups are saved to `./backups/db_<name>_<timestamp>.sql.gz` and `storage_<timestamp>.tar.gz`.

### Restoring from Backup:
- **Linux / VPS**:
  ```bash
  ./restore.sh ./backups/db_personal_ai_core_20261113_234400.sql.gz ./backups/storage_20261113_234400.tar.gz
  ```
- **Windows PowerShell**:
  ```powershell
  .\restore.ps1 -DbBackupFile .\backups\db_personal_ai_core_20261113_234400.sql -StorageBackupFile .\backups\storage_20261113_234400.zip
  ```

---

## 8. Monitoring & Observability

- **Uptime Monitoring**: Point your uptime monitor (Better Uptime, Pingdom, UptimeKuma) to `GET https://yourdomain.com/health`.
- **API Health**: `GET https://yourdomain.com/api/v1/health` verifies database connectivity and schema readiness.
- **Container Logs**:
  ```bash
  docker logs -f personal_ai_backend
  docker logs -f personal_ai_caddy
  ```
