# NUMA — Complete Setup Guide

Follow every step in order. Nothing will work until all credentials are in place.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Get a Groq API Key](#2-get-a-groq-api-key)
3. [Create a Supabase Project](#3-create-a-supabase-project)
4. [Run the Database Schema](#4-run-the-database-schema)
5. [Create & Configure a Slack App](#5-create--configure-a-slack-app)
6. [Configure the Backend (.env)](#6-configure-the-backend-env)
7. [Configure the Frontend (.env)](#7-configure-the-frontend-env)
8. [Run the Project (Local Dev)](#8-run-the-project-local-dev)
9. [Run with Docker](#9-run-with-docker)
10. [Verify Everything Works](#10-verify-everything-works)
11. [Optional — Email Notifications](#11-optional--email-notifications)

---

## 1. Prerequisites

Install these tools before anything else.

| Tool | Min Version | Download |
|------|-------------|----------|
| Python | 3.12 | https://www.python.org/downloads/ |
| Node.js | 20 LTS | https://nodejs.org/ |
| Git | any | https://git-scm.com/ |
| Docker Desktop *(optional, for containerised run)* | 4.x | https://www.docker.com/products/docker-desktop/ |

Verify installs:

```bash
python --version    # Python 3.12.x
node --version      # v20.x.x
npm --version       # 10.x.x
```

---

## 2. Get a Groq API Key

NUMA uses Groq to run the LLaMA 3 model that powers the AI chat interface.

1. Go to **https://console.groq.com**
2. Sign in / create a free account.
3. Click **API Keys** in the left sidebar → **Create API Key**.
4. Name it `NUMA` and copy the key — it starts with `gsk_`.

> **Keep this key secret.** It only goes into `backend/.env`, never the frontend.

---

## 3. Create a Supabase Project

Supabase is the database + real-time backend.

1. Go to **https://supabase.com** → **Start your project** → Sign in with GitHub.
2. Click **New project**.
   - **Name**: `numa` (or anything you like)
   - **Database Password**: generate a strong one and save it somewhere safe
   - **Region**: pick the one closest to you
3. Wait ~2 minutes for provisioning.
4. Once the project is ready, open **Settings → API**.

Copy these three values — you'll need them in step 6:

| What | Where to find it | Env var name |
|------|-----------------|--------------|
| **Project URL** | Settings → API → Project URL | `SUPABASE_URL` |
| **anon / public key** | Settings → API → Project API keys → `anon` `public` | `SUPABASE_ANON_KEY` |
| **service_role key** | Settings → API → Project API keys → `service_role` `secret` *(click Reveal)* | `SUPABASE_SERVICE_KEY` |

> `SUPABASE_SERVICE_KEY` bypasses Row Level Security — **never** put it in frontend code or commit it to Git.

---

## 4. Run the Database Schema

This creates all the tables NUMA needs (users, user_tokens, channels, messages, tasks, extracted_intelligence, analytics, etc).

1. In your Supabase dashboard, click **SQL Editor** in the left sidebar.
2. Click **+ New query**.
3. Open the file `supabase/schema.sql` from this project in a text editor, select all, and paste it into the Supabase SQL Editor.
4. Click **Run** (▶).

You should see `Success. No rows returned` — that means all tables were created cleanly.

> If you see an error like `relation already exists`, the table already exists from a previous run — that is fine, the schema uses `CREATE TABLE IF NOT EXISTS` so it is safe to re-run.

---

## 5. Create & Configure a Slack App

This is the longest step. Take it one section at a time.

### 5a. Create the app

1. Go to **https://api.slack.com/apps** and sign in.
2. Click **Create New App** → **From scratch**.
3. **App Name**: `NUMA`
4. **Workspace**: pick the Slack workspace you want to connect.
5. Click **Create App**.

You are now on the app management page. Keep this tab open.

---

### 5b. Enable Socket Mode (for the App Token)

1. In the left sidebar, click **Socket Mode**.
2. Toggle **Enable Socket Mode** to ON.
3. You will be prompted to create an **App-Level Token**.
   - **Token Name**: `numa-socket`
   - **Scopes**: add `connections:write`
4. Click **Generate** and copy the token — it starts with `xapp-`.

> This is your `SLACK_APP_TOKEN`.

---

### 5c. Add Bot Token Scopes

1. Left sidebar → **OAuth & Permissions**.
2. Scroll down to **Scopes → Bot Token Scopes**.
3. Click **Add an OAuth Scope** and add each of these one by one:

| Scope | Why |
|-------|-----|
| `channels:history` | Read channel messages (monitor) |
| `channels:read` | List channels |
| `chat:write` | Send messages / DMs |
| `commands` | Handle `/numa` slash command |
| `im:write` | Open DM conversations |
| `reactions:read` | Track emoji reactions |
| `users:read` | Resolve user names |
| `users:read.email` | Read user emails (optional) |

---

### 5d. Install the App to Your Workspace

1. Still in **OAuth & Permissions**, scroll to the top.
2. Click **Install to Workspace** → **Allow**.
3. Copy the **Bot User OAuth Token** — it starts with `xoxb-`.

> This is your `SLACK_BOT_TOKEN`.

---

### 5e. Copy Signing Secret and OAuth credentials

From the left sidebar → **Basic Information**:

| Value | Env var |
|-------|---------|
| **Signing Secret** (App Credentials section) | `SLACK_SIGNING_SECRET` |
| **Client ID** | `SLACK_CLIENT_ID` |
| **Client Secret** | `SLACK_CLIENT_SECRET` |

---

### 5f. Add the OAuth Redirect URL

1. Left sidebar → **OAuth & Permissions**.
2. Under **Redirect URLs**, click **Add New Redirect URL**.
3. Enter: `https://<your-ngrok-domain>.ngrok-free.dev/auth/slack/callback`
4. Click **Save URLs**.

---

### 5g. Enable Event Subscriptions

1. Left sidebar → **Event Subscriptions** → toggle **Enable Events** to ON.
2. For **Request URL**, enter: `https://<your-ngrok-domain>.ngrok-free.dev/slack/events`
   *(Slack requires HTTPS for local dev; use ngrok)*
3. Under **Subscribe to bot events**, add:
   - `message.channels`
   - `app_mention`
   - `reaction_added`
4. Click **Save Changes**.

---

### 5h. Add the /numa Slash Command

1. Left sidebar → **Slash Commands** → **Create New Command**.

| Field | Value |
|-------|-------|
| Command | `/numa` |
| Request URL | `https://<your-ngrok-domain>.ngrok-free.dev/slack/commands` |
| Short Description | `Your personal NUMA assistant` |
| Usage Hint | `[add task Buy milk] [plan today] [how am I doing?]` |

2. Click **Save**.
3. Reinstall the app when prompted (**OAuth & Permissions → Reinstall to Workspace**).

---

### 5i. Find Your Slack User ID and Channel IDs

**Your User ID** (for `NOTIFICATION_USER_ID`):
1. Open Slack.
2. Click your name in the sidebar → **View profile**.
3. Click the three-dot menu (⋯) → **Copy member ID**.
   It looks like `U04XXXXXXX`.

**Channel IDs** (for `MONITOR_CHANNELS`):
1. In Slack, right-click a channel → **View channel details**.
2. Scroll to the bottom — the Channel ID is shown (e.g. `C04XXXXXXX`).
3. Repeat for every channel you want NUMA to monitor.
4. Comma-separate them: `C04XXXXX,C04YYYYY`

> Make sure the NUMA bot has been **invited to each channel** (`/invite @NUMA` in the channel).

---

## 6. Start ngrok (Required for Slack)

Slack requires HTTPS URLs for OAuth redirects, events, and slash commands.

1. Create a free ngrok account.
2. Go to **Domains** in the ngrok dashboard and reserve a dev domain (free).
3. Start the tunnel (leave this running):

```bash
ngrok http --url=https://<your-ngrok-domain>.ngrok-free.dev 8000
```

You will use this HTTPS domain in the Slack app settings above.

---

## 7. Configure the Backend (.env)

```bash
cd backend
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux
```

Open `backend/.env` in a text editor and fill in every value:

```env
# ── App ───────────────────────────────────────────────────────
APP_ENV=development
SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_hex(32))">
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080          # 7 days

# ── Slack ─────────────────────────────────────────────────────
SLACK_BOT_TOKEN=xoxb-...          # from step 5d
SLACK_APP_TOKEN=xapp-...          # from step 5b
SLACK_SIGNING_SECRET=...          # from step 5e
SLACK_CLIENT_ID=...               # from step 5e
SLACK_CLIENT_SECRET=...           # from step 5e
SLACK_REDIRECT_URI=https://<your-ngrok-domain>.ngrok-free.dev/auth/slack/callback

# ── Supabase ──────────────────────────────────────────────────
SUPABASE_URL=https://xxxx.supabase.co   # from step 3
SUPABASE_SERVICE_KEY=eyJ...             # from step 3 (service_role)
SUPABASE_ANON_KEY=eyJ...                # from step 3 (anon)

# ── Groq ──────────────────────────────────────────────────────
GROQ_API_KEY=gsk_...              # from step 2

# ── Monitor ───────────────────────────────────────────────────
MONITOR_CHANNELS=C04XXXXX,C04YYYYY   # from step 5i
CHECK_INTERVAL_MINUTES=15
NOTIFICATION_USER_ID=U04XXXXX        # from step 5i

# ── Email (leave as-is for now, see step 12) ──────────────────
EMAIL_ENABLED=false
```

**Generate the SECRET_KEY** by running this once in a terminal:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the output as the value of `SECRET_KEY`.

---

## 8. Configure the Frontend (.env)

```bash
cd frontend
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux
```

Open `frontend/.env` and fill in:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=https://xxxx.supabase.co     # same as backend
VITE_SUPABASE_ANON_KEY=eyJ...                   # same anon key as backend
```

> `VITE_API_BASE_URL` is only needed if you are not using the Vite dev proxy. In development the proxy transparently routes `/api` to `http://localhost:8000` already.

---

## 9. Run the Project (Local Dev)

Open **three separate terminals**.

### Terminal 1 — Backend

```bash
cd backend

# Create virtual environment (first time only)
python -m venv .venv

# Activate
.venv\Scripts\activate          # Windows PowerShell
# source .venv/bin/activate     # macOS / Linux

# Install dependencies (first time only)
pip install -r requirements.txt

# Start
uvicorn app.main:app --reload --port 8000
```

You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     NUMA API starting up...
INFO:     Slack monitor started — polling every 15 minute(s).
```

### Terminal 2 — Frontend

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Start
npm run dev
```

You should see:

```
  VITE v5.x.x  ready in xxx ms
  ➜  Local:   http://localhost:5173/
```

Open **http://localhost:5173** in your browser.

### Terminal 3 — ngrok

```bash
ngrok http --url=https://<your-ngrok-domain>.ngrok-free.dev 8000
```

---

## 10. Run with Docker

Requires Docker Desktop to be running.

```bash
# From the numa/ root folder:
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

To stop:

```bash
docker compose down
```

---

## 11. Verify Everything Works

Work through this checklist in order:

- [ ] **API health** — open http://localhost:8000/docs — you should see the Swagger UI with all routes listed.
- [ ] **Supabase tables** — in the Supabase dashboard, open **Table Editor** and confirm tables like `users`, `tasks`, `messages` exist.
- [ ] **Login** — open http://localhost:5173, click **Sign in with Slack**, complete the OAuth flow. You should land on the Dashboard.
- [ ] **AI chat** — in Slack, type `/numa add task Buy groceries`. Check the NUMA dashboard — the task should appear in real-time.
- [ ] **Monitor** — wait up to 15 minutes after startup (or post a message in a monitored channel). The backend logs should show `Monitor cycle starting…`.
- [ ] **Real-time sync** — open the Tasks page in two browser tabs. Add a task in one — it should appear in the other instantly.

---

## 12. Optional — Email Notifications

NUMA can also send you an email digest when your monitored channels have urgent activity.

1. If using Gmail, create an **App Password**:
   - Go to https://myaccount.google.com/security
   - Under **How you sign in to Google** → **2-Step Verification** (must be enabled)
   - Scroll to the bottom → **App passwords** → **Create**
   - Name it `NUMA`, copy the 16-character password.

2. In `backend/.env`, update:

```env
EMAIL_ENABLED=true
EMAIL_SENDER=you@gmail.com
EMAIL_PASSWORD=xxxx xxxx xxxx xxxx    # the app password (spaces are fine)
EMAIL_RECIPIENT=you@gmail.com         # where to receive digests
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

3. Restart the backend. Email digests will be sent alongside Slack DMs during each monitor cycle.

---

## Common Problems

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError` on startup | Run `pip install -r requirements.txt` inside the activated `.venv` |
| `Invalid token` on login | Regenerate `SECRET_KEY` and restart the backend |
| Slack OAuth redirects to an error | Double-check `SLACK_REDIRECT_URI` exactly matches the HTTPS ngrok URL in Slack |
| `/numa` command times out | Make sure Socket Mode is enabled and `SLACK_APP_TOKEN` is set correctly |
| Supabase `row-level security` error | The backend must use `SUPABASE_SERVICE_KEY`, not the anon key |
| Real-time updates not working | Check that `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` in `frontend/.env` are correct |
| `MONITOR_CHANNELS` channel not fetched | Invite the bot to the channel with `/invite @NUMA` in Slack |
