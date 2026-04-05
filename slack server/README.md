# NUMA — Personal Slack Productivity Dashboard

> A full-stack personal productivity app that turns your Slack workspace into a smart daily planner — with an AI chat interface, real-time updates, mood & reflection logs, and automated channel monitoring.

---

## Architecture

```
numa/
├── backend/          FastAPI + Slack Bolt + LangChain/Groq + APScheduler
├── frontend/         React 18 + Vite + Tailwind CSS + Zustand + Supabase Realtime
├── supabase/         PostgreSQL schema (run once in Supabase SQL Editor)
└── docker-compose.yml
```

```
Slack Workspace
      │  events / slash commands
      ▼
  Slack Bolt  ───► Supabase (messages, nudges, analytics)
      │                     │
  FastAPI  ◄────────────────┘  ◄── JWT-authenticated REST API
      │
  Groq LLM (llama‑3.1‑8b)  ← intent classification
      │
  React SPA  ◄── Supabase Realtime (tasks, nudges, messages)
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.12+ |
| Node.js | 20+ |
| Supabase project | Free tier is fine |
| Slack app | with Bot + Socket Mode tokens |
| Groq API key | [console.groq.com](https://console.groq.com) |

---

## Quick Start

### 1. Supabase Schema

1. Open your Supabase project → **SQL Editor → New query**.
2. Paste and run the entire contents of [`supabase/schema.sql`](supabase/schema.sql).

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # fill in all values
uvicorn app.main:app --reload --port 8000
```

#### Required environment variables (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Random 32-byte hex string for JWT signing |
| `SLACK_BOT_TOKEN` | `xoxb-…` bot OAuth token |
| `SLACK_APP_TOKEN` | `xapp-…` Socket Mode app token |
| `SLACK_SIGNING_SECRET` | Request signing secret from Slack app settings |
| `SLACK_CLIENT_ID` | OAuth app client ID |
| `SLACK_CLIENT_SECRET` | OAuth app client secret |
| `SLACK_REDIRECT_URI` | `https://<your-ngrok-domain>/auth/slack/callback` (dev) |
| `SUPABASE_URL` | Your project URL, e.g. `https://xxxx.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Service role key (bypasses RLS — keep secret) |
| `SUPABASE_ANON_KEY` | Anon/public key (used by frontend for Realtime) |
| `GROQ_API_KEY` | Groq API key |
| `MONITOR_CHANNELS` | Comma-separated Slack channel IDs, e.g. `C0123,C0456` |
| `NOTIFICATION_USER_ID` | Your Slack user ID for DM notifications |
| `EMAIL_ENABLED` | `true` / `false` |
| `EMAIL_SENDER` | Sender address for email notifications |
| `EMAIL_PASSWORD` | SMTP password / app password |
| `EMAIL_RECIPIENT` | Recipient address |
| `SMTP_SERVER` | e.g. `smtp.gmail.com` |
| `SMTP_PORT` | e.g. `587` |

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env   # fill in VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
npm run dev            # starts on http://localhost:5173
```

#### Required environment variables (`frontend/.env`)

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | `/api` (dev proxy) or `https://your-api.com` |
| `VITE_SUPABASE_URL` | Same as backend `SUPABASE_URL` |
| `VITE_SUPABASE_ANON_KEY` | Same as backend `SUPABASE_ANON_KEY` |

### 4. Slack App Configuration

Slack requires HTTPS URLs for OAuth redirects, events, and slash commands. For local dev, use ngrok.

#### 4a. Start ngrok (local HTTPS)

1. Create a free ngrok account and reserve a dev domain in **Domains**.
2. Start the tunnel (leave this running):

```bash
ngrok http --url=https://your-ngrok-domain.ngrok-free.dev 8000
```

Your backend stays on `http://localhost:8000`, but Slack will call the ngrok HTTPS URL.

#### 4b. Configure the Slack App

In your [Slack App](https://api.slack.com/apps) settings:

- **OAuth & Permissions** → Bot Token Scopes:
  `channels:history`, `channels:read`, `chat:write`, `commands`, `im:write`, `reactions:read`, `users:read`
- **Event Subscriptions** → Subscribe to bot events:
  `message.channels`, `app_mention`, `reaction_added`
- **Request URL**: `https://your-ngrok-domain.ngrok-free.dev/slack/events`
- **Slash Commands**: Create `/numa` pointing to `https://your-ngrok-domain.ngrok-free.dev/slack/commands`
- **OAuth Redirect URL**: `https://your-ngrok-domain.ngrok-free.dev/auth/slack/callback`

After saving Slack settings, reinstall the app when prompted.

---



## Features

| Feature | Path |
|---------|------|
| **Dashboard** | `/dashboard` — today's score, tasks, plan, mood, Slack messages |
| **AI Chat** | `/api/chat` — natural language → Slack actions via Groq + LangChain |
| **Tasks** | `/tasks` — full CRUD with priority/status, real-time sync |
| **Schedule** | `/schedule` — daily time block editor |
| **Analytics** | `/analytics` — weekly/monthly Recharts graphs |
| **Mood Log** | `/mood` — 5-point mood pick + energy slider + note |
| **Reflection** | `/reflect` — guided end-of-day journal |
| **Monitor** | Background job (every 15 min) — fetches Slack channels, analyses for mentions/urgency, sends DM/email digest |

---

## API Reference

Full interactive docs at **`http://localhost:8000/docs`** (Swagger UI).

Key endpoints:

```
GET  /auth/slack                 → redirect to Slack OAuth
GET  /auth/slack/callback        → exchange code → JWT
GET  /dashboard/today
GET  /messages
GET  /tasks          POST /tasks
PUT  /tasks/{id}     DELETE /tasks/{id}
GET  /schedule/today POST /schedule/plan
POST /mood           GET  /mood
POST /reflect        GET  /reflect
GET  /analytics/week
GET  /analytics/month
GET  /analytics/score/today
POST /chat
POST /slack/events   (Slack Bolt)
POST /slack/commands (Slack Bolt)
```

---

## Development Notes

- **Hot reload**: both `uvicorn --reload` and `vite` support it out of the box.
- **Supabase Realtime**: the frontend subscribes to changes on `tasks`, `messages`, and `nudges` tables via the anon key. Backend uses the service role key for writes.
- **Monitor interval**: default 15 minutes — change by passing `interval_minutes` to `start_scheduler()` in `main.py`.
- **JWT expiry**: default 7 days (`JWT_EXPIRE_DAYS` env var).
