# NUMA - AI-Powered Life Operating System

An intelligent platform that unifies your productivity, health, and integrations into one AI-powered system. Autonomous agents handle scheduling, fitness tracking, communication monitoring, and task management - so you don't have to.


## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Setup Guide](#setup-guide)
  - [Prerequisites](#prerequisites)
  - [1. Supabase Project](#1-supabase-project)
  - [2. Google Cloud OAuth & Fit API](#2-google-cloud-oauth--fit-api)
  - [3. GitHub OAuth](#3-github-oauth)
  - [4. Strava API](#4-strava-api)
  - [5. Google Fit Token](#5-google-fit-token)
  - [6. Environment Variables](#6-environment-variables)
  - [7. Running the Application](#7-running-the-application)
- [API Reference](#api-reference)
- [Integrations](#integrations)
- [AI & NLP Modules](#ai--nlp-modules)
- [Contributors](#contributors)


## Overview

**NUMA** is a multi-service AI platform built around the concept of a personal "Life OS". It aggregates data from health trackers, calendars, code repositories, and communication tools into a unified backend, then uses AI agents with LangChain/LangGraph to generate actionable daily plans - all while keeping user data private.

### Core Services

| Service | Description | Port |
|---|---|---|
| **client** | Next.js 16 web app - landing page, auth, task board, analytics | `3000` |
| **server** | FastAPI backend - auth, task CRUD, Supabase integration | `8000` |
| **google-calendar** | LangGraph agent - natural language calendar + Gmail control | `8001` |
| **slack-server** | Slack automation - intent parsing, channel monitoring, notifications | `9000` |
| **NLP-NUMA** | Custom NLP pipeline - sentiment, NER, performance classification | offline |


## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
│              Next.js 16 + React 19 + Tailwind CSS v4            │
│   Landing Page │ Auth (Email/OAuth) │ Kanban Board │ Analytics  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTPS / REST
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      NEXT.JS API PROXY                          │
│              /api/[...path] → FastAPI (port 8000)               │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │   Auth Service  │  │  Tasks Service  │  │  Health Check  │  │
│  │  /auth/*        │  │   /tasks/*      │  │  GET /health   │  │
│  │  JWT + Supabase │  │  CRUD + Stats   │  │                │  │
│  └────────┬────────┘  └────────┬────────┘  └────────────────┘  │
└───────────┼────────────────────┼───────────────────────────────┘
            │                    │
            ▼                    ▼
┌───────────────────┐  ┌────────────────────────────────────────┐
│  SUPABASE AUTH    │  │          SUPABASE POSTGRESQL           │
│  Email/Password   │  │  tasks table + RLS + indexes           │
│  Google OAuth     │  │  (hosted on AWS ap-northeast-2)        │
│  GitHub OAuth     │  └────────────────────────────────────────┘
└───────────────────┘

┌───────────────────────────────────────────────────────────────┐
│                     STANDALONE SERVICES                       │
│  ┌──────────────────────────────┐  ┌───────────────────────┐  │
│  │  Google Calendar Agent       │  │   Slack Server        │  │
│  │  LangGraph + Groq + Gmail    │  │   FastAPI + Groq      │  │
│  │  port 8001                   │  │   port 9000           │  │
│  └──────────────────────────────┘  └───────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  NLP-NUMA Pipeline                                      │  │
│  │  DistilBERT (Sentiment + Performance) │ spaCy NER       │  │
│  │  TF-IDF LogReg (Daily Productivity)  │ Burnout Risk     │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

### Authentication Flow

```
User fills form ──► POST /api/auth/signin ──► FastAPI ──► Supabase verify
                                                               │
                                                    ◄── Custom JWT (2-day)
                                                               │
                         localStorage["numa_token"] ◄──────────┘

OAuth Flow:
User clicks Google/GitHub ──► Supabase OAuth redirect
                                       │
                             Browser callback to /auth/callback
                                       │
                             POST /api/auth/exchange (Supabase token)
                                       │
                             ◄── Custom backend JWT
```


## Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS v4, shadcn/ui |
| **Animations** | Framer Motion, Three.js (LaserFlow background) |
| **Drag & Drop** | @dnd-kit/core, @dnd-kit/sortable |
| **Charts** | Recharts |
| **Backend** | Python 3.10+, FastAPI 0.128, Uvicorn |
| **Database** | Supabase (PostgreSQL), psycopg2 direct connection |
| **Auth** | Supabase Auth, PyJWT, python-jose, OAuth 2.0 |
| **AI / Agents** | LangChain, LangGraph, Groq API |
| **NLP** | Transformers (DistilBERT), spaCy, scikit-learn (TF-IDF + LogReg) |
| **Integrations** | Google Calendar API, Google Fit API, Strava API v3, Slack SDK |


## Project Structure

```
Numa/
├── client/                              # Next.js 16 frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx               # Root layout
│   │   │   ├── page.tsx                 # Landing page entry
│   │   │   ├── globals.css              # Global Tailwind v4 styles
│   │   │   ├── api/
│   │   │   │   └── [...path]/route.ts   # Catch-all proxy → FastAPI
│   │   │   ├── auth/
│   │   │   │   ├── page.tsx             # Sign in / Sign up page
│   │   │   │   └── callback/page.tsx    # OAuth callback handler
│   │   │   ├── home/
│   │   │   │   ├── layout.tsx           # AppShell wrapper
│   │   │   │   └── page.tsx             # Protected home page
│   │   │   ├── tasklist/
│   │   │   │   ├── layout.tsx           # AppShell wrapper
│   │   │   │   └── page.tsx             # Kanban + Analytics + History
│   │   │   └── under-construction/
│   │   │       └── page.tsx             # Placeholder for upcoming pages
│   │   ├── components/
│   │   │   ├── LandingPage.tsx          # Landing page layout
│   │   │   ├── Navbar.tsx               # Navigation bar
│   │   │   ├── LaserFlow.tsx            # Three.js animated background
│   │   │   ├── ContentBox.tsx           # Section container
│   │   │   ├── OrbitingIntegrations.tsx # Integration orbit visualization
│   │   │   ├── sections/                # 7 landing page sections
│   │   │   │   ├── HeroSection.tsx
│   │   │   │   ├── FeaturesSection.tsx
│   │   │   │   ├── HowItWorksSection.tsx
│   │   │   │   ├── IntegrationsSection.tsx
│   │   │   │   ├── ArchitectureSection.tsx
│   │   │   │   ├── CTASection.tsx
│   │   │   │   └── Footer.tsx
│   │   │   ├── tasklist/
│   │   │   │   ├── AppShell.tsx         # Sidebar + layout shell
│   │   │   │   ├── TasklistSidebar.tsx
│   │   │   │   ├── KanbanBoard.tsx      # DnD Kanban (4 columns)
│   │   │   │   ├── KanbanColumn.tsx
│   │   │   │   ├── TaskCard.tsx
│   │   │   │   ├── TaskDialog.tsx       # Create / edit task modal
│   │   │   │   ├── TaskDetailSheet.tsx  # Slide-out detail panel
│   │   │   │   ├── AnalyticsDashboard.tsx # Recharts analytics
│   │   │   │   ├── api.ts               # fetchTasks / fetchStats / fetchHistory
│   │   │   │   └── types.ts             # Task types + column/priority configs
│   │   │   └── ui/                      # shadcn/ui primitives
│   │   └── lib/
│   │       ├── supabase.ts              # Supabase JS client
│   │       └── utils.ts                 # cn() helper
│   ├── assets/
│   │   ├── Images/                      # Integration logos (WebP)
│   │   └── gc-epic-pro-demo/            # Custom font
│   ├── .env.local                       # Supabase URL + anon key
│   └── package.json
│
├── server/                              # FastAPI backend
│   ├── main.py                          # App entry point, CORS, router mount
│   ├── requirements.txt
│   ├── test_main.py
│   ├── .env                             # All server secrets
│   ├── sql/
│   │   └── schema_tasks.sql             # Tasks table DDL + RLS + indexes
│   └── src/
│       ├── db.py                        # psycopg2 connection + auto DDL
│       ├── auth/
│       │   ├── router.py                # /auth/* endpoints
│       │   ├── service.py               # Supabase + JWT logic
│       │   ├── schemas.py               # Pydantic auth models
│       │   └── dependencies.py          # get_current_user (Bearer JWT)
│       ├── tasks/
│       │   ├── router.py                # /tasks/* CRUD + stats + history
│       │   └── schemas.py               # Pydantic task models
│       ├── api/
│       │   ├── google_fit_api.py        # Google Fit integration
│       │   └── strava_api.py            # Strava integration
│       └── config/
│           ├── credentials.json         # Google OAuth credentials
│           ├── token.json               # Google OAuth token (auto-generated)
│           └── strava_credentials.json.template
│
├── server/google-calendar/              # Google Calendar LangGraph agent
│   ├── app.py                           # FastAPI wrapper (port 8001)
│   ├── requirements.txt
│   ├── agent/
│   │   ├── graph.py                     # LangGraph graph definition
│   │   ├── llm.py                       # LLM (Groq) setup
│   │   ├── state.py                     # Agent state schema
│   │   └── tools.py                     # Calendar + Gmail tools
│   └── services/
│       ├── calendar_service.py
│       ├── gmail_service.py
│       ├── datetime_parser.py
│       └── google_auth.py
│
├── slack-server/                        # Slack automation service
│   ├── requirements.txt
│   └── app/
│       ├── main.py                      # FastAPI app (port 9000)
│       ├── config.py                    # Settings from env vars
│       ├── intent_parser.py             # Groq-based intent parsing
│       ├── slack_router.py              # Slack action router
│       └── monitor/
│           ├── analyzer.py              # Channel message analysis
│           ├── scheduler.py             # APScheduler polling (15 min)
│           ├── slack_fetcher.py         # Slack API fetching
│           └── notifier/
│               ├── slack_notifier.py
│               ├── email_notifier.py
│               └── notification_service.py
│
├── NLP-NUMA/                            # Custom NLP pipeline (standalone)
│   ├── requirements.txt
│   ├── core/
│   │   ├── workout_analyzer.py          # Sentiment + NER + performance
│   │   ├── workout_nlg.py               # Numeric metrics → natural language
│   │   ├── hybrid_analyzer.py           # Cross-validates text vs numeric
│   │   └── unified_analyzer.py          # Daily orchestrator
│   ├── training/
│   │   ├── generate_training_data.py    # 4,000 workout samples
│   │   ├── train_sentiment.py           # Fine-tune DistilBERT (3-class)
│   │   ├── train_ner.py                 # spaCy NER (4 entity types)
│   │   ├── train_classifier.py          # DistilBERT performance classifier
│   │   └── train_daily_from_combined.py # TF-IDF + LogReg daily productivity
│   └── testing/
│
└── docs/
    ├── NumaDB_Plan.md                   # Multi-agent dual-DB architecture plan
    └── markdown.md                      # Technical specification
```


## Setup Guide

### Prerequisites

- Node.js v18+
- Python 3.10+
- pip + virtualenv
- A [Supabase](https://supabase.com) account


### 1. Supabase Project

Supabase provides the database (PostgreSQL) and authentication (email/password + OAuth).

#### 1.1 Create a Project

1. Go to [supabase.com](https://supabase.com) → **New Project**
2. Set a **project name**, **database password**, and choose a **region** (closest to your users)
3. Wait for the project to provision (~1 minute)

#### 1.2 Get API Credentials

1. In your project dashboard, go to **Settings** → **API**
2. Copy the following values:
   - **Project URL** → `SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL`
   - **anon public key** → `SUPABASE_ANON_KEY` / `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - **service_role secret key** → `SUPABASE_SERVICE_ROLE_KEY` (**keep this secret - never expose it client-side**)

#### 1.3 Get Database Connection String

1. Go to **Settings** → **Database**
2. Under **Connection string**, select **URI** mode
3. Copy the connection string (use the **pooler** URL for connection pooling):
   ```
   postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
4. This goes into `DATABASE_URL` in `server/.env`

#### 1.4 Enable Email Auth

1. Go to **Authentication** → **Providers**
2. Ensure **Email** is enabled
3. Optionally disable email confirmation for local development: **Authentication** → **Email Templates** → turn off "Enable email confirmations"

#### 1.5 Configure Redirect URLs

1. Go to **Authentication** → **URL Configuration**
2. Set **Site URL** to `http://localhost:3000`
3. Under **Redirect URLs**, add:
   ```
   http://localhost:3000/auth/callback
   ```

#### 1.6 Enable Google OAuth in Supabase

> You need Google OAuth credentials first - see [Section 2](#2-google-cloud-oauth--fit-api).

1. Go to **Authentication** → **Providers** → **Google**
2. Toggle **Enable Google provider**
3. Paste your **Google Client ID** and **Google Client Secret**
4. Copy the **Supabase Callback URL** shown on this page (format: `https://<ref>.supabase.co/auth/v1/callback`)
5. Add this callback URL to your Google Cloud OAuth app's authorized redirect URIs

#### 1.7 Enable GitHub OAuth in Supabase

> You need GitHub OAuth credentials first - see [Section 3](#3-github-oauth).

1. Go to **Authentication** → **Providers** → **GitHub**
2. Toggle **Enable GitHub provider**
3. Paste your **GitHub Client ID** and **GitHub Client Secret**
4. Copy the **Supabase Callback URL** shown on this page


### 2. Google Cloud OAuth & Fit API

Used for: Sign in with Google (via Supabase), Google Calendar agent, Google Fit data.

#### 2.1 Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown (top left) → **New Project**
3. Give it a name (e.g. `Numa`) → **Create**

#### 2.2 Enable Required APIs

1. Go to **APIs & Services** → **Library**
2. Search for and enable each of these:
   - **Google Fit API** (for fitness data)
   - **Google Calendar API** (for calendar agent)
   - **Gmail API** (for calendar agent email features)
   - **Google People API** (for OAuth user info)

#### 2.3 Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** → **Create**
3. Fill in:
   - **App name**: `Numa`
   - **User support email**: your email
   - **Developer contact email**: your email
4. Click **Save and Continue**
5. Under **Scopes**, add:
   - `email`, `profile`, `openid`
   - `https://www.googleapis.com/auth/fitness.activity.read`
   - `https://www.googleapis.com/auth/fitness.body.read`
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/gmail.send`
6. Under **Test users**, add your Google account email
7. Click **Save and Continue**

#### 2.4 Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**
2. Select **Web application**
3. Under **Authorized JavaScript origins**, add:
   ```
   http://localhost:3000
   ```
4. Under **Authorized redirect URIs**, add:
   ```
   http://localhost:3000/auth/callback
   https://<your-supabase-ref>.supabase.co/auth/v1/callback
   http://localhost:8501
   ```
5. Click **Create**
6. Copy the **Client ID** → `ClientID` (Google) in `server/.env`
7. Copy the **Client Secret** → `ClientSecretKey` (Google) in `server/.env`
8. Click **Download JSON** → save as `server/src/config/credentials.json`

#### 2.5 Note on IPv4

> **Important**: Supabase OAuth callbacks only work over IPv4. If you are on an IPv6-only network, the callback may fail. Use a VPN or ensure your ISP provides IPv4.


### 3. GitHub OAuth

Used for: Sign in with GitHub (via Supabase).

#### 3.1 Create a GitHub OAuth App

1. Go to [github.com](https://github.com) → **Settings** (your profile) → **Developer settings** → **OAuth Apps** → **New OAuth App**
2. Fill in:
   - **Application name**: `Numa`
   - **Homepage URL**: `http://localhost:3000`
   - **Authorization callback URL**: copy the Supabase Callback URL from **Supabase → Authentication → Providers → GitHub** (format: `https://<ref>.supabase.co/auth/v1/callback`)
3. Click **Register application**
4. Copy the **Client ID** → `ClientID` (GitHub) in `server/.env`
5. Click **Generate a new client secret** → copy it → `ClientSecretKey` (GitHub) in `server/.env`

#### 3.2 IPv4 Requirement

> GitHub OAuth redirects go through Supabase servers. Ensure your network supports IPv4 connections to Supabase. If you encounter connection errors, toggle your network or use a VPN with IPv4.


### 4. Strava API

Used for: Fetching workout activities, performance metrics, and activity logs.

#### 4.1 Create a Strava Application

1. Log in to [strava.com](https://www.strava.com)
2. Go to [www.strava.com/settings/api](https://www.strava.com/settings/api)
3. Fill in the application form:
   - **Application Name**: `Numa`
   - **Category**: `Athlete Data`
   - **Club**: leave blank
   - **Website**: `http://localhost:3000`
   - **Authorization Callback Domain**: `localhost`
4. Agree to the API Agreement → **Create**
5. Copy:
   - **Client ID** → `STRAVA_CLIENT_ID`
   - **Client Secret** → `STRAVA_CLIENT_SECRET`

#### 4.2 Get Access & Refresh Tokens

Strava uses OAuth 2.0. You need to do an initial authorization to get the tokens:

1. In a browser, open this URL (replace `YOUR_CLIENT_ID`):
   ```
   https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:8501&response_type=code&scope=read,activity:read_all
   ```
2. Authorize the app → you will be redirected to `http://localhost:8501?code=<AUTH_CODE>`
3. Copy the `code` value from the URL
4. Make this POST request to exchange the code for tokens:
   ```bash
   curl -X POST https://www.strava.com/oauth/token \
     -d client_id=YOUR_CLIENT_ID \
     -d client_secret=YOUR_CLIENT_SECRET \
     -d code=AUTH_CODE \
     -d grant_type=authorization_code
   ```
5. From the response, copy:
   - `access_token` → `STRAVA_ACCESS_TOKEN`
   - `refresh_token` → `STRAVA_REFRESH_TOKEN`
   - `expires_at` → `STRAVA_TOKEN_EXPIRES_AT`

> The backend automatically refreshes expired tokens using the refresh token.


### 5. Google Fit Token

Google Fit uses the same OAuth credentials from Section 2. The token is generated on first run via an interactive browser flow:

1. Ensure `server/src/config/credentials.json` is in place (downloaded in step 2.4)
2. Run the Google Fit script once to authorize:
   ```bash
   cd server
   python src/api/google_fit_api.py
   ```
3. A browser window will open asking you to log in with your Google account and grant fitness permissions
4. After approval, `server/src/config/token.json` is auto-generated and saved
5. Subsequent runs use the saved token (auto-refreshed by the library)


### 6. Environment Variables

#### `client/.env.local`

```env
NEXT_PUBLIC_SUPABASE_URL=https://<your-project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

#### `server/.env`

```env
# Supabase / PostgreSQL
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres

# JWT (choose a strong random secret)
JWT_SECRET=your-strong-random-secret-here

# App URLs
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000

# Google OAuth (from Google Cloud Console)
ClientID=<google-oauth-client-id>
ClientSecretKey=<google-oauth-client-secret>

# GitHub OAuth (from GitHub Developer Settings)
# ClientID=<github-oauth-client-id>
# ClientSecretKey=<github-oauth-client-secret>

# Google Fit
GOOGLE_FIT_CREDENTIALS_FILE=src/config/credentials.json

# Strava
STRAVA_CLIENT_ID=<strava-client-id>
STRAVA_CLIENT_SECRET=<strava-client-secret>
STRAVA_ACCESS_TOKEN=<strava-access-token>
STRAVA_REFRESH_TOKEN=<strava-refresh-token>
STRAVA_TOKEN_EXPIRES_AT=<unix-timestamp>
REDIRECT_URI=http://localhost:8501

# Timezone
TIMEZONE=Asia/Kolkata
```

#### `slack-server/.env` (for Slack service)

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
GROQ_API_KEY=gsk_...
MONITOR_CHANNELS=C01234567,C09876543
CHECK_INTERVAL_MINUTES=15
NOTIFICATION_USER_ID=U01234567
EMAIL_ENABLED=false
EMAIL_SENDER=your@email.com
EMAIL_PASSWORD=your-app-password
EMAIL_RECIPIENT=recipient@email.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

#### `server/google-calendar/.env` (for Calendar agent)

```env
GROQ_API_KEY=gsk_...
GOOGLE_CREDENTIALS_FILE=../src/config/credentials.json
GOOGLE_TOKEN_FILE=../src/config/token.json
```


### 7. Running the Application

#### Client (Next.js)

```bash
cd client
npm install
npm run dev
# → http://localhost:3000
```

#### Server (FastAPI)

```bash
cd server
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# → http://localhost:8000
```

#### Google Calendar Agent (optional)

```bash
cd server/google-calendar
pip install -r requirements.txt
uvicorn app:app --reload --port 8001
# → http://localhost:8001
```

#### Slack Server (optional)

```bash
cd slack-server
pip install -r requirements.txt
uvicorn app.main:app --reload --port 9000
# → http://localhost:9000
```

#### NLP-NUMA - Training (optional, standalone)

```bash
cd NLP-NUMA
pip install -r requirements.txt

# Generate training data
python training/generate_training_data.py

# Train models (run in order)
python training/train_sentiment.py
python training/train_ner.py
python training/train_classifier.py
python training/train_daily_from_combined.py

# Test
python testing/test_models_quick.py
```


## API Reference

Base URL: `http://localhost:8000`

### Auth Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/signup` | None | Register with email + password. Returns JWT. |
| `POST` | `/auth/signin` | None | Sign in with email + password. Returns JWT. |
| `POST` | `/auth/exchange` | None | Exchange Supabase OAuth token for backend JWT. |
| `GET` | `/auth/me` | Bearer JWT | Returns current user profile. |
| `POST` | `/auth/signout` | Bearer JWT | Stateless sign-out (client discards token). |

### Task Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/tasks` | Bearer JWT | List active tasks (excludes old completed). |
| `POST` | `/tasks` | Bearer JWT | Create a new task. |
| `PUT` | `/tasks/{task_id}` | Bearer JWT | Full update of a task. |
| `PATCH` | `/tasks/{task_id}/status` | Bearer JWT | Update task status only (used by Kanban DnD). |
| `DELETE` | `/tasks/{task_id}` | Bearer JWT | Delete a task. |
| `GET` | `/tasks/stats` | Bearer JWT | Analytics: by_status, completions (daily/weekly/monthly/yearly), streak. |
| `GET` | `/tasks/history` | Bearer JWT | Tasks completed on previous days. |

### System Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/` | None | Welcome message. |
| `GET` | `/health` | None | `{"status": "ok"}` |
| `GET` | `/home` | Bearer JWT | Protected home route - returns user info. |


## Integrations

| Integration | Status | Purpose |
|---|---|---|
| **Google Calendar** | Active (agent) | Natural language event creation, conflict detection, smart scheduling |
| **Google Fit** | Active | Activity metrics, step counts, workout data |
| **Strava** | Active | Workout analysis, performance metrics, activity logs |
| **Slack** | Active | Intent-based messaging, channel monitoring, notification delivery |
| **GitHub** | Planned | Commit tracking, contribution analytics |
| **LeetCode** | Planned | Problem-solving tracking, skill development |


## AI & NLP Modules

### Google Calendar Agent (`server/google-calendar/`)

A LangGraph-based stateful agent that accepts natural language commands to manage Google Calendar events and draft Gmail messages.

- **LLM**: Groq API (fast inference)
- **Tools**: Create event, list events, update event, delete event, send email
- **Flow**: User query → LangGraph state machine → tool calls → structured response

### Slack Automation (`slack-server/`)

A FastAPI service that monitors Slack channels and dispatches actions via LLM intent parsing.

- **Intent Parsing**: LangChain + Groq parses free-text commands into structured Slack actions
- **Monitoring**: APScheduler polls configured channels every 15 minutes
- **Notifications**: Slack DM + optional email (SMTP) alerts

### NLP-NUMA Pipeline (`NLP-NUMA/`)

A fully offline NLP pipeline with 4 trained models for workout and daily productivity analysis:

| Model | Architecture | Classes |
|---|---|---|
| **Sentiment** | Fine-tuned DistilBERT | Positive / Neutral / Negative |
| **NER** | Custom spaCy | BODY_PART, SYMPTOM, DISTANCE, LOCATION |
| **Performance Classifier** | Fine-tuned DistilBERT | Improvement / Neutral / Struggle |
| **Daily Productivity** | TF-IDF + Logistic Regression | High_Performance / Focused / Overloaded / Distracted / Recovery |

**Burnout Risk Score**:
```
risk = P(Overloaded) + 0.5 × P(Distracted)
HIGH   > 0.70
MODERATE  0.40 – 0.70
LOW    < 0.40
```


## Contributors

| Name | Role | Contact |
|---|---|---|
| Vinay R S | Full-Stack Developer | - |

**Institution**: BMS College of Engineering
**Course**: 6th Semester Mini Project
**Academic Year**: 2025-2026


## License

This project is licensed under the MIT License.
