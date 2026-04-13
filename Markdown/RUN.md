# NUMA - Project Setup & Run Guide

> Complete instructions for setting up and running the NUMA productivity platform locally.
> Stack: **Next.js 16** (frontend) · **FastAPI** (backend) · **Supabase** (Postgres) · **Qdrant local** (vector DB) · **Groq** (LLM) · **Google Calendar OAuth** · **Slack Events API**

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Project Structure](#2-project-structure)
3. [Environment Variables](#3-environment-variables)
4. [Database Setup (Supabase)](#4-database-setup-supabase)
5. [Vector DB Setup (Qdrant - no Docker)](#5-vector-db-setup-qdrant--no-docker)
6. [Google Calendar OAuth Setup](#6-google-calendar-oauth-setup)
7. [Slack Integration Setup](#7-slack-integration-setup)
8. [Running the Backend](#8-running-the-backend)
9. [Running the Frontend](#9-running-the-frontend)
10. [First-Time Usage Flow](#10-first-time-usage-flow)
11. [Troubleshooting](#11-troubleshooting)

## 1. Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | ≥ 3.11 | https://python.org |
| Node.js | ≥ 18 | https://nodejs.org |
| uv | latest | `pip install uv` or https://docs.astral.sh/uv |
| Git | any | https://git-scm.com |

> **Windows note:** Enable Developer Mode (Settings → For Developers) to allow symlinks - this helps HuggingFace model caching run faster.

## 2. Project Structure

```
Numa/
├── client/                  ← Next.js frontend (React 19, Tailwind v4)
│   ├── .env.local           ← Frontend environment variables
│   └── src/
├── server/                  ← FastAPI backend
│   ├── .env                 ← Backend environment variables  ← EDIT THIS
│   ├── google_tokens/       ← OAuth token files (auto-created, gitignored)
│   ├── qdrant_storage/      ← Vector DB data files (auto-created, gitignored)
│   ├── google_web_oauth_client.json  ← Google OAuth credentials (you provide)
│   ├── pyproject.toml       ← Python dependencies (managed by uv)
│   └── src/
│       ├── auth/            ← JWT auth, Supabase integration
│       ├── calendar/        ← Google Calendar sync, cache, normalized DB
│       ├── calendar_agent/  ← LangGraph calendar AI agent  
│       ├── master_agent/    ← Master orchestrator agent (routes to sub-agents)
│       ├── slack_agent/     ← Slack sub-agent (LangGraph ReAct + Qdrant RAG)
│       ├── memory/          ← Qdrant semantic memory service
│       ├── tasks/           ← Task management
│       └── db.py            ← DB schema init (auto-runs on startup)
├── Markdown/
│   └── RUN.md               ← This file
└── .gitignore
```

## 3. Environment Variables

### 3a. Backend - `server/.env`

Create `server/.env` (copy the block below and fill in your values):

```env
# ── APP URLS ──────────────────────────────────────────────────────────────────
REDIRECT_URI=http://localhost:8501
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
TIMEZONE=Asia/Kolkata                  # change to your local timezone

# ── SUPABASE ──────────────────────────────────────────────────────────────────
# Get these from: https://supabase.com → Your Project → Settings → API
DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
PASSWORD=<your-supabase-db-password>

# ── JWT ───────────────────────────────────────────────────────────────────────
JWT_SECRET=numa-jwt-secret-key-change-in-production

# ── LLM - Groq ────────────────────────────────────────────────────────────────
# Free keys at: https://console.groq.com
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TEMPERATURE=0.2
GROQ_MASTER_MODEL=llama-3.3-70b-versatile
GROQ_MASTER_TEMPERATURE=0.1

# ── GOOGLE OAUTH (for login) ──────────────────────────────────────────────────
# Create credentials at: https://console.cloud.google.com → APIs & Services → Credentials
# App type: Web Application
ClientID=<your-google-client-id>.apps.googleusercontent.com
ClientSecretKey=<your-google-client-secret>

# ── GOOGLE CALENDAR OAUTH ─────────────────────────────────────────────────────
# Separate web OAuth client for Calendar API access (can be the same project)
# Download as JSON and place at the path below
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/calendar/oauth/callback
GOOGLE_OAUTH_SUCCESS_REDIRECT=http://localhost:3000/calendar
GOOGLE_CALENDAR_CREDENTIALS_FILE=E:/Numa/server/google_web_oauth_client.json
GOOGLE_CALENDAR_TOKEN_DIR=E:/Numa/server/google_tokens

# ── VECTOR DB - Qdrant (local file mode, no Docker) ──────────────────────────
OPENAI_API_KEY=""                      # leave empty - we use local embeddings
QDRANT_URL=""                          # leave empty → local file mode activates
QDRANT_LOCAL_PATH=E:/Numa/server/qdrant_storage   # vectors stored here on disk
QDRANT_API_KEY=""
EMBEDDING_PROVIDER=local               # uses sentence-transformers, no internet needed after first run
LOCAL_EMBEDDING_MODEL=all-MiniLM-L6-v2            # ~90MB, downloaded once, cached
EMBEDDING_MODEL=text-embedding-3-large             # only used if provider=openai
EMBEDDING_DIMENSIONS=384
QDRANT_COLLECTION=numa_agent_memory_local
MEMORY_RECREATE_COLLECTION_ON_DIM_MISMATCH=true
MEMORY_CONTEXT_LIMIT=4
HF_HUB_DISABLE_SYMLINKS_WARNING=1

# ── HEALTH DATA (optional) ────────────────────────────────────────────────────
STRAVA_CLIENT_ID=
STRAVA_CLIENT_SECRET=
STRAVA_ACCESS_TOKEN=
STRAVA_REFRESH_TOKEN=
```

### 3b. Frontend - `client/.env.local`

```env
# Get from: https://supabase.com → Your Project → Settings → API
NEXT_PUBLIC_SUPABASE_URL=https://<ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>

# Backend URL (default for local dev)
BACKEND_URL=http://127.0.0.1:8000
```

> ⚠️ **Never commit either `.env` file to git.** They contain secrets.

## 4. Database Setup (Supabase)

NUMA uses **Supabase** (managed Postgres) for all relational data.

### 4a. Create a Supabase project
1. Go to https://supabase.com and create a free project
2. Note your **Project URL**, **anon key**, **service role key**, and **database password**
3. Fill them into `server/.env` (section above)

### 4b. Apply the schema - automatic on server startup

The schema is applied automatically when the FastAPI server starts via `init_db()`.  
Tables created on first run:

| Table | Purpose |
|---|---|
| `public.profiles` | User profile (linked to Supabase auth.users) |
| `public.tasks` | Task management with calendar sync + Slack-sourced tasks |
| `public.cal_calendars` | One row per Google calendar per user |
| `public.cal_events` | Normalized calendar events (no raw JSON blobs) |
| `public.cal_attendees` | One row per attendee per event |
| `public.cal_watch_channels` | Google Calendar push notification channels |
| `public.google_calendars` | Legacy calendar list (kept for compat) |
| `public.google_calendar_events` | Legacy events (raw_event blob removed) |
| `public.google_calendar_sync_state` | Sync state tracking |
| `public.slack_channels` | Tracked Slack channels |
| `public.slack_messages` | Slack messages — 7-day rolling window |
| `public.slack_auth` | Per-user Slack OAuth tokens |

> **No manual SQL needed.** Just start the server and tables are created automatically.

## 5. Vector DB Setup (Qdrant - no Docker)

NUMA uses **Qdrant in local file mode** - data is stored on disk, no server or Docker needed.

### How it works
- `qdrant-client` v1.12+ supports `QdrantClient(path="./qdrant_storage")`
- Vectors are persisted to `server/qdrant_storage/` automatically
- The `all-MiniLM-L6-v2` embedding model (~90MB) is downloaded from HuggingFace on first use and cached in `C:\Users\<you>\.cache\huggingface\`

### Setup steps

```bash
# Install dependencies (from server/ directory)
uv sync

# That's it - Qdrant starts automatically when the server starts
# You can verify at: GET http://localhost:8000/health
```

Expected `/health` response when working:
```json
{
  "status": "ok",
  "vector_memory": {
    "enabled": true,
    "mode": "local_file",
    "embedding_provider": "local",
    "collection": "numa_agent_memory_local",
    "local_path": "E:/Numa/server/qdrant_storage"
  }
}
```

### Embedding model: `all-MiniLM-L6-v2` vs alternatives

| Model | Dims | Size | Best for |
|---|---|---|---|
| **`all-MiniLM-L6-v2`** ✅ (current) | 384 | ~90MB | Short sentences, tasks, calendar text. Fast, low RAM |
| `BAAI/bge-base-en-v1.5` | 768 | ~90MB | Higher accuracy, more RAM, slower |
| `all-mpnet-base-v2` | 768 | ~420MB | Best quality, high RAM |

`all-MiniLM-L6-v2` is the best choice here because:
- Calendar events and tasks are short text snippets (< 100 tokens)
- 384 dims = half the Qdrant storage, faster search
- The text payload sent to **Groq** is the stored text, not the vector - smaller embedding = same Groq context quality, less disk/RAM

## 6. Google Calendar OAuth Setup

### 6a. Create OAuth credentials in Google Cloud Console

1. Go to https://console.cloud.google.com
2. Create a project (or use existing)
3. Enable **Google Calendar API**: APIs & Services → Library → search "Calendar"
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Add Authorized redirect URI: `http://localhost:8000/calendar/oauth/callback`
7. Download the JSON file → save as `server/google_web_oauth_client.json`

### 6b. Set OAuth consent screen

1. APIs & Services → OAuth consent screen
2. Set to **External** (for testing) or **Internal** (for your org)
3. Add your Google account as a **test user** (if External + Testing mode)

> ⚠️ **Important:** If your app is in "Testing" mode, Google tokens expire after **7 days**. Publish the app or switch to Internal to get long-lived tokens.

### 6c. Connect Calendar from the UI

1. Start the backend and frontend
2. Log in to NUMA
3. Navigate to the Calendar page
4. Click "Connect Google Calendar" → complete the OAuth flow
5. Your token is saved to `server/google_tokens/<your-user-id>.json`

### 6d. Fix `invalid_grant` errors

If you see `invalid_grant: Bad Request`:
- The token has expired/been revoked
- The code **automatically** deletes the stale token and returns a 401
- Just re-connect from the UI (step 3 above)

## 7. Slack Integration Setup

Slack is integrated as a full sub-agent. The master agent routes Slack queries to the
`slack_agent` which uses LangGraph + Groq and stores message vectors in Qdrant (7-day window).

### 7a. Create a Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps) → **Create New App → From scratch**
2. Name: `NUMA` | Workspace: your workspace

### 7b. Configure OAuth & Permissions

In your Slack App → **OAuth & Permissions**:

**Bot Token Scopes** (add all):

| Scope | Reason |
|---|---|
| `channels:history` | Read public channel messages |
| `channels:read` | List channels |
| `chat:write` | Post messages |
| `users:read` | Resolve user names |
| `team:read` | Get workspace info |

**User Token Scopes**: `channels:history`, `chat:write`

Add **Redirect URL**:
```
http://localhost:8000/slack/callback
```

### 7c. Enable Event Subscriptions (HTTP Events — industry standard)

1. Install **ngrok**: `ngrok http 8000`
2. Slack App → **Event Subscriptions** → Enable Events → ON
3. Request URL: `https://<your-ngrok-id>.ngrok.io/slack/events`
4. Wait for green ✓ **Verified** (NUMA auto-responds to URL verification challenge)
5. Under **Subscribe to Bot Events**, add: `message.channels`, `message.groups`
6. Save Changes

> NUMA uses **HMAC-SHA256 signature verification** on every incoming event — the industry-standard security pattern for Slack apps.

### 7d. Get your credentials

| Variable | Where to find it |
|---|---|
| `SLACK_BOT_TOKEN` | OAuth & Permissions → Bot User OAuth Token (`xoxb-...`) |
| `SLACK_SIGNING_SECRET` | Basic Information → App Credentials → Signing Secret |
| `SLACK_CLIENT_ID` | Basic Information → App Credentials → Client ID |
| `SLACK_CLIENT_SECRET` | Basic Information → App Credentials → Client Secret |

### 7e. Add to `server/.env`

```env
# ====== SLACK ======
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
SLACK_CLIENT_ID=your-client-id-here
SLACK_CLIENT_SECRET=your-client-secret-here
SLACK_REDIRECT_URI=http://localhost:8000/slack/callback

# Qdrant collection for Slack message vectors (7-day rolling window)
QDRANT_SLACK_COLLECTION=numa_slack_messages
SLACK_MESSAGE_RETENTION_DAYS=7
```

### 7f. Install Slack dependencies

```bash
cd server
uv pip install slack_sdk httpx
```

### 7g. Connect from the NUMA UI

1. Open NUMA → **Slack** (sidebar)
2. Click **Connect Slack** → authorize in the OAuth popup
3. You'll be redirected to the Slack page with `?connected=1`
4. Messages from your workspace will now sync automatically

### 7h. Slack API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/slack/events` | HMAC | Slack Events API webhook |
| `POST` | `/slack/chat` | JWT | Chat with Slack sub-agent |
| `GET` | `/slack/messages` | JWT | List recent messages (7-day) |
| `GET` | `/slack/channels` | JWT | List tracked channels |
| `GET` | `/slack/status` | JWT | Check connection status |
| `GET` | `/slack/connect` | JWT | Initiate OAuth flow |
| `GET` | `/slack/callback` | — | OAuth callback |

### 7i. 7-Day Data Retention

| Store | Retention mechanism |
|---|---|
| **PostgreSQL** `slack_messages` | `WHERE created_at > NOW() - INTERVAL '7 days'` on reads; nightly DELETE |
| **Qdrant** `numa_slack_messages` | Nightly purge via `created_at < cutoff` filter |

The nightly purge runs at **03:00 IST** via APScheduler.

## 8. Running the Backend

```bash
# From the server/ directory

# Install dependencies (first time only)
uv sync

# Start the dev server with hot-reload
uv run uvicorn main:app --reload --port 8000

# OR if your venv is activated:
uvicorn main:app --reload --port 8000
```

The server will:
1. Load `server/.env`
2. Auto-create/migrate all DB tables including Slack tables (`init_db()`)
3. Start Qdrant in local file mode (creates `qdrant_storage/` if not exists)
4. Download the embedding model on **first request** (~90MB, cached after)
5. Schedule the nightly Slack purge job at 03:00 IST

**API docs:** http://localhost:8000/docs  
**Health check:** http://localhost:8000/health

## 9. Running the Frontend

```bash
# From the client/ directory

# Install dependencies (first time only)
npm install

# Start the dev server
npm run dev
```

Open http://localhost:3000

## 10. First-Time Usage Flow

Follow these steps the very first time you set up the project:

```
1. Start Backend        →  cd server && uv run uvicorn main:app --reload --port 8000
2. Start Frontend       →  cd client && npm run dev
3. Open Browser         →  http://localhost:3000
4. Sign Up / Log In     →  via Supabase Auth (Google or email)
5. Connect Calendar     →  Calendar page → "Connect Google Calendar" → OAuth flow
6. Connect Slack        →  Slack page → "Connect Slack" → OAuth flow
7. Start ngrok          →  ngrok http 8000  (then update Slack Event Subscriptions URL)
8. Done                 →  Chat with the AI agent about your schedule and Slack messages
```

> On subsequent runs, steps 1–2 are enough. Calendar data is cached (30-min TTL) and
> Qdrant memory is persistent on disk.

## 11. Troubleshooting

### `invalid_grant: Bad Request` (Calendar)
- Token expired or revoked
- Fix: Re-connect Google Calendar from the UI → Calendar page → Connect

### Slack signature verification fails (`403`)
- Check `SLACK_SIGNING_SECRET` in `server/.env` matches your Slack App's signing secret
- Check the timestamp isn't more than 5 minutes old (clock skew)

### Slack bot can't find channel
- Invite the bot: in Slack type `/invite @NUMA` in the target channel

### ngrok URL expired
- Restart ngrok and update the Request URL in Slack App → Event Subscriptions

### Qdrant not working
```bash
# Verify Qdrant health
curl http://localhost:8000/health
# Should show: "enabled": true, "mode": "local_file"
```
- Check `QDRANT_LOCAL_PATH` is set in `.env` and `QDRANT_URL` is empty
- Check `EMBEDDING_PROVIDER=local` is set

### Embedding model download fails
- Ensure internet connection on first run
- Model is cached at `C:\Users\<you>\.cache\huggingface\hub\`
- Re-run server after connectivity is restored - download resumes

### DB connection errors
- Check `DATABASE_URL` in `server/.env`
- Format: `postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres`
- Make sure the Supabase project is not paused (free tier pauses after inactivity)

### Frontend can't reach backend (CORS)
- Check `FRONTEND_URL=http://localhost:3000` in `server/.env`
- Check `BACKEND_URL=http://127.0.0.1:8000` in `client/.env.local`

### Port already in use
```bash
# Kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```

### `uv sync` fails
```bash
# Ensure Python 3.11+ is installed and on PATH
python --version

# Reinstall uv
pip install --upgrade uv

# Force recreate venv
uv venv --python 3.11
uv sync
```

## Quick Reference

| Component | Command | URL |
|---|---|---|
| Backend | `uv run uvicorn main:app --reload --port 8000` | http://localhost:8000 |
| Frontend | `npm run dev` | http://localhost:3000 |
| API Docs | — | http://localhost:8000/docs |
| Health | — | http://localhost:8000/health |
| Vector DB | auto-started by backend | `qdrant_storage/` on disk |
| DB Schema | auto-applied on startup | Supabase dashboard |
| Slack Events | ngrok → `/slack/events` | HMAC-verified webhook |
| Slack OAuth | `/slack/connect` → Slack | Per-user token in `slack_auth` |

