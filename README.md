<p align="center">
  <h1 align="center">NUMA</h1>
  <p align="center"><strong>Unified Daily Application Hub</strong></p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Next.js-000000?style=flat-square&logo=nextdotjs&logoColor=white" alt="Next.js" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white" alt="Tailwind CSS" />
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Qdrant-DC382D?style=flat-square&logo=qdrant&logoColor=white" alt="Qdrant" />
  <img src="https://img.shields.io/badge/LangChain-1C3C3C?style=flat-square&logo=langchain&logoColor=white" alt="LangChain" />
</p>

<p align="center">
  NUMA unifies your daily apps - Calendar, Tasks, Slack, Health, GitHub, LeetCode, Journal, and Mental Peace - into a single AI-powered dashboard with multi-agent orchestration.
</p>

## Features

- **Master Agent Dashboard** - unified stats across all connected services
- **Google Calendar Sync** - AI-powered scheduling with natural language commands
- **Slack Integration** - message search, channel monitoring, and intent-based actions
- **Health Tracking** - Google Fit + Strava data aggregation and insights
- **GitHub Contribution Tracking** - commit history and contribution analytics
- **LeetCode Progress Monitoring** - problem-solving stats and skill tracking
- **Daily Journal** - AI-summarized entries with semantic memory
- **Mental Peace** - guided meditation, yoga sessions, and breathing exercises
- **Task Management** - Kanban board with drag-and-drop and analytics
- **Multi-Provider AI** - Groq, OpenAI, Anthropic, Gemini, and Ollama support

## Tech Stack

| Layer | Technology |
|---|---|
| ![](https://img.shields.io/badge/Frontend-000?style=flat-square) | ![Next.js](https://img.shields.io/badge/Next.js_16-000000?style=flat-square&logo=nextdotjs&logoColor=white) ![React](https://img.shields.io/badge/React_19-61DAFB?style=flat-square&logo=react&logoColor=black) ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white) ![Tailwind](https://img.shields.io/badge/Tailwind_CSS_v4-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white) ![shadcn/ui](https://img.shields.io/badge/shadcn/ui-000000?style=flat-square&logo=shadcnui&logoColor=white) |
| ![](https://img.shields.io/badge/Backend-000?style=flat-square) | ![Python](https://img.shields.io/badge/Python_3.11+-3776AB?style=flat-square&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) ![Uvicorn](https://img.shields.io/badge/Uvicorn-2F4F4F?style=flat-square) ![uv](https://img.shields.io/badge/uv-DE5FE9?style=flat-square&logo=uv&logoColor=white) |
| ![](https://img.shields.io/badge/Database-000?style=flat-square) | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white) ![Supabase](https://img.shields.io/badge/Supabase-3FCF8E?style=flat-square&logo=supabase&logoColor=white) ![Qdrant](https://img.shields.io/badge/Qdrant-DC382D?style=flat-square&logo=qdrant&logoColor=white) |
| ![](https://img.shields.io/badge/AI_/_Agents-000?style=flat-square) | ![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=flat-square&logo=langchain&logoColor=white) ![Groq](https://img.shields.io/badge/Groq-F55036?style=flat-square&logo=groq&logoColor=white) ![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat-square&logo=openai&logoColor=white) ![Anthropic](https://img.shields.io/badge/Anthropic-191919?style=flat-square) ![Gemini](https://img.shields.io/badge/Gemini-8E75B2?style=flat-square&logo=googlegemini&logoColor=white) ![Ollama](https://img.shields.io/badge/Ollama-000000?style=flat-square&logo=ollama&logoColor=white) |
| ![](https://img.shields.io/badge/Auth-000?style=flat-square) | ![Supabase Auth](https://img.shields.io/badge/Supabase_Auth-3FCF8E?style=flat-square&logo=supabase&logoColor=white) ![JWT](https://img.shields.io/badge/JWT-000000?style=flat-square&logo=jsonwebtokens&logoColor=white) ![OAuth 2.0](https://img.shields.io/badge/OAuth_2.0-4285F4?style=flat-square) |
| ![](https://img.shields.io/badge/Integrations-000?style=flat-square) | ![Google Calendar](https://img.shields.io/badge/Google_Calendar-4285F4?style=flat-square&logo=googlecalendar&logoColor=white) ![Slack](https://img.shields.io/badge/Slack-4A154B?style=flat-square&logo=slack&logoColor=white) ![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white) ![Strava](https://img.shields.io/badge/Strava-FC4C02?style=flat-square&logo=strava&logoColor=white) ![Google Fit](https://img.shields.io/badge/Google_Fit-4285F4?style=flat-square&logo=googlefit&logoColor=white) ![LeetCode](https://img.shields.io/badge/LeetCode-FFA116?style=flat-square&logo=leetcode&logoColor=black) |

## Prerequisites

| Requirement | Version |
|---|---|
| Node.js | 18+ |
| Python | 3.11+ |
| uv | latest ([install](https://docs.astral.sh/uv/getting-started/installation/)) |
| PostgreSQL | Supabase (hosted) |
| Qdrant | Cloud or local |

## Getting Started

```bash
# Clone the repository
git clone https://github.com/your-username/Numa.git
cd Numa

# Install frontend dependencies
cd client
npm install

# Install backend dependencies
cd ../server
uv venv
uv pip install -r requirements.txt
```

Copy the example environment file and fill in your keys:

```bash
cp server/.env.example server/.env
```

## API Keys Setup

### Google Calendar API

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Navigate to **APIs & Services → Library** and enable **Google Calendar API**
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Set application type to **Web application**
6. Add authorized redirect URIs:
   ```
   http://localhost:8000/calendar/oauth/callback
   ```
7. Click **Create**, then copy the credentials:
   - Client ID → `GOOGLE_CALENDAR_CLIENT_ID`
   - Client Secret → `GOOGLE_CALENDAR_CLIENT_SECRET`
8. Download the JSON file and save it to `server/apiConfig/google/google_web_oauth_client.json`
9. Under **OAuth consent screen**, add scopes:
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/calendar.events`
10. Add your email as a test user if the app is in **Testing** mode

### Supabase (PostgreSQL + Auth)

1. Go to [supabase.com](https://supabase.com/) and create a new project
2. Once provisioned, go to **Settings → API** and copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon public key** → `SUPABASE_ANON_KEY`
   - **service_role key** → `SUPABASE_SERVICE_ROLE_KEY`
3. Go to **Settings → Database → Connection string (URI)** and copy:
   ```
   postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
   → Set as `DATABASE_URL`
4. For GitHub OAuth via Supabase Auth:
   - Go to **Authentication → Providers → GitHub**
   - Add your GitHub OAuth app's Client ID and Client Secret

### Slack Integration

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
2. Choose **From scratch**, name it, and select your workspace
3. Under **OAuth & Permissions**, add Bot Token Scopes:
   - `channels:history`, `channels:read`, `chat:write`, `users:read`
   - `groups:history`, `groups:read`, `im:history`, `mpim:history`
4. Under **Event Subscriptions**, enable events and set the Request URL:
   ```
   https://your-domain/api/slack/events
   ```
5. Subscribe to bot events:
   - `message.channels`, `message.groups`, `message.im`, `message.mpim`
6. **Install the app** to your workspace
7. Copy **Bot User OAuth Token** → `SLACK_BOT_TOKEN`
8. Go to **Basic Information** and copy **Signing Secret** → `SLACK_SIGNING_SECRET`
9. Copy **Client ID** → `SLACK_CLIENT_ID` and **Client Secret** → `SLACK_CLIENT_SECRET`

### Google Fit API

1. Go to [console.cloud.google.com](https://console.cloud.google.com/) (same project as Calendar)
2. Enable **Fitness API** from the API Library
3. The same OAuth 2.0 credentials can be reused - add these scopes:
   - `https://www.googleapis.com/auth/fitness.activity.read`
   - `https://www.googleapis.com/auth/fitness.sleep.read`
   - `https://www.googleapis.com/auth/fitness.body.read`
4. Add redirect URI if using a separate flow:
   ```
   http://localhost:8000/api/health-agent/callback
   ```
5. Set `GOOGLE_FIT_CLIENT_ID` and `GOOGLE_FIT_CLIENT_SECRET` in `.env` (can reuse Calendar credentials)

### Strava API

1. Go to [strava.com/settings/api](https://www.strava.com/settings/api)
2. Create an application
3. Set **Authorization Callback Domain** to `localhost`
4. Copy your credentials:
   - Client ID → `STRAVA_CLIENT_ID`
   - Client Secret → `STRAVA_CLIENT_SECRET`
5. Users authorize via OAuth at runtime; tokens are auto-refreshed by the backend

### GitHub OAuth

1. Go to [github.com/settings/developers](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Fill in:
   - **Homepage URL**: `http://localhost:3000`
   - **Authorization callback URL**: `http://localhost:8000/api/github/callback`
4. Copy your credentials:
   - Client ID → `GITHUB_CLIENT_ID`
   - Client Secret → `GITHUB_CLIENT_SECRET`

### LLM Providers

| Provider | Console | Env Variable |
|---|---|---|
| **Groq** | [console.groq.com](https://console.groq.com/) → API Keys | `GROQ_API_KEY` |
| **OpenAI** | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | `OPENAI_API_KEY` |
| **Anthropic** | [console.anthropic.com](https://console.anthropic.com/) → API Keys | `ANTHROPIC_API_KEY` |
| **Gemini** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | `GOOGLE_API_KEY` |
| **Ollama** | [ollama.com](https://ollama.com/) - install locally, no API key needed | - |

## Environment Variables

Create a `server/.env` file with the following variables:

```env
# ====== Supabase / PostgreSQL ======
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

# ====== JWT ======
JWT_SECRET=your-strong-random-secret

# ====== App URLs ======
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000

# ====== Google Calendar ======
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/calendar/oauth/callback
GOOGLE_OAUTH_SUCCESS_REDIRECT=http://localhost:3000/calendar
GOOGLE_CALENDAR_CREDENTIALS_FILE=/path/to/google_web_oauth_client.json
GOOGLE_CALENDAR_TOKEN_DIR=/path/to/token/directory

# ====== Slack ======
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_CLIENT_ID=your-slack-client-id
SLACK_CLIENT_SECRET=your-slack-client-secret
SLACK_REDIRECT_URI=https://your-domain/slack/callback
SLACK_MESSAGE_RETENTION_DAYS=7

# ====== GitHub OAuth ======
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_OAUTH_REDIRECT_URI=http://localhost:8000/api/github/callback

# ====== Strava ======
STRAVA_CLIENT_ID=your-strava-client-id
STRAVA_CLIENT_SECRET=your-strava-client-secret
REDIRECT_URI=http://localhost:8501

# ====== LLM Providers ======
GROQ_API_KEY=gsk_your-groq-api-key
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TEMPERATURE=0.2
GROQ_MASTER_MODEL=llama-3.3-70b-versatile
GROQ_MASTER_TEMPERATURE=0.1
OPENAI_API_KEY=sk-your-openai-api-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key
GOOGLE_API_KEY=your-gemini-api-key

# ====== Qdrant Vector Database ======
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_URL_ENDPOINT=https://your-cluster.cloud.qdrant.io

# ====== Embeddings ======
EMBEDDING_PROVIDER=local
HUGGINGFACE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS=384

# ====== Encryption ======
NUMA_ENCRYPTION_KEY=your-fernet-encryption-key

# ====== Misc ======
TIMEZONE=Asia/Kolkata
SYNC_SCHEDULER_INTERVAL_MINUTES=30
```

Create a `client/.env.local` file:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

## Running the App

```bash
# Backend
cd server
uv pip install -r requirements.txt
uv run uvicorn main:app --reload --port 8000
```

```bash
# Frontend
cd client
npm install
npm run dev
```

The frontend runs at `http://localhost:3000` and the backend at `http://localhost:8000`.

## Project Structure

```
Numa/
├── client/                          # Next.js frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── (protected)/
│   │   │   │   ├── home/            # Master agent dashboard
│   │   │   │   ├── calendar/        # Google Calendar view
│   │   │   │   ├── tasklist/        # Kanban board
│   │   │   │   ├── slack/           # Slack integration
│   │   │   │   ├── health/          # Health tracking (Google Fit + Strava)
│   │   │   │   ├── journal/         # Daily journal
│   │   │   │   ├── mental-peace/    # Meditation & yoga
│   │   │   │   ├── productivity/    # GitHub & LeetCode analytics
│   │   │   │   ├── settings/        # App & API settings
│   │   │   │   └── under-construction/
│   │   │   ├── auth/                # Sign in / Sign up
│   │   │   └── api/                 # Next.js API proxy → FastAPI
│   │   ├── components/              # Shared UI components
│   │   └── lib/                     # Utilities & config
│   ├── public/                      # Static assets
│   └── package.json
│
├── server/                          # FastAPI backend
│   ├── main.py                      # App entry point & router registration
│   ├── src/
│   │   ├── ai_settings/             # LLM provider config
│   │   ├── api/                     # Internal API utilities
│   │   ├── auth/                    # Authentication & JWT
│   │   ├── calendar/                # Google Calendar service
│   │   ├── calendar_agent/          # AI calendar sub-agent
│   │   ├── dashboard/               # Dashboard aggregation
│   │   ├── github_agent/            # GitHub sub-agent
│   │   ├── health_agent/            # Health data sub-agent (Google Fit + Strava)
│   │   ├── journal/                 # Journal service
│   │   ├── leetcode/                # LeetCode tracker
│   │   ├── master_agent/            # Orchestrator / routing agent
│   │   ├── memory/                  # Qdrant vector memory
│   │   ├── slack_agent/             # Slack sub-agent
│   │   ├── tasks/                   # Task CRUD & analytics
│   │   ├── context_assembler.py     # Token-budget context builder
│   │   ├── data_planner.py          # Zero-cost intent classifier
│   │   ├── data_sync.py             # Background data sync scheduler
│   │   ├── db.py                    # Pooled DB connection (asyncpg)
│   │   ├── embedder.py              # HuggingFace embedding service
│   │   ├── llm_factory.py           # Multi-provider LLM factory
│   │   └── rate_limiter.py          # Token-bucket rate limiter w/ fallback
│   ├── migrations/                  # Alembic DB migrations
│   │   └── versions/
│   ├── apiConfig/
│   │   └── google/                  # Google OAuth JSON credentials
│   ├── sql/                         # Raw SQL schema files
│   ├── alembic.ini                  # Alembic configuration
│   ├── pyproject.toml               # Project metadata & dependencies
│   ├── requirements.txt             # pip-compatible dependency list
│   └── uv.lock                      # uv lockfile
│
├── models/                          # Cached HuggingFace embedding models
├── scripts/                         # Dev utility scripts (cache cleanup, etc.)
├── docs/                            # Architecture diagrams & project docs
└── .gitignore
```

## License

MIT
