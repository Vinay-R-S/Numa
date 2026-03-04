# NUMA — Project Memory

> This file is a living document capturing the full understanding of the NUMA project. Update as the project evolves.

---

## What is NUMA?

NUMA is a **unified life-management web application** built by Antigravity AI. The core idea is simple: instead of juggling 10+ apps for health, productivity, and communication, the user connects everything to NUMA and manages their life from one place.

It combines:
- **External platform integrations** (via their APIs)
- **Built-in mini-apps** (tools native to NUMA)
- **AI agents** (LangGraph + LangChain) per domain + a master orchestrator agent
- **An NLP module** (course project showcase, toggle-able vs AI mode)

---

## Integrated Platforms

### Health & Fitness
| Platform | Purpose |
|---|---|
| **Strava** | Collects smartwatch/workout activity data |
| **Google Fit** | Aggregates health metrics from wearables/apps |

### Professional & Productivity
| Platform | Purpose |
|---|---|
| **GitHub** | Tracks commits, PRs, work done, pending tasks |
| **LeetCode** | Student progress tracking (problems solved, streaks, etc.) |
| **Slack** | Professional communication, channel management |
| **Google Calendar & Meet** | Meetings, scheduling, virtual interactions |

---

## Built-in NUMA Tools (Native Mini-Apps)

| Tool | Notes |
|---|---|
| **Pomodoro Timer** | Focus/work session timer |
| **Meditation & Yoga App** | Wellness tool (Yoga side still being planned) |
| **Journal** | Note-taking / personal diary |
| **Todo List** | Advanced — Kanban board style, not a basic checklist |
| **Diet Planner & Health Recommender** | With appropriate disclaimers |

---

## AI Agent Architecture

Built using **LangGraph + LangChain**.

### Domain Agents (one per integration/tool area)
Each agent is responsible for interacting with, controlling, and fetching data from its respective platform:
- Health Agent (Strava + Google Fit)
- Productivity Agent (GitHub + LeetCode)
- Communication Agent (Slack)
- Calendar Agent (Google Calendar + Meet)
- Internal Tools Agent (Pomodoro, Journal, Todo, Diet Planner)

### Master Agent
- Orchestrates all domain agents
- Context-aware (uses Vector DB for semantic memory + Supabase/PostgreSQL for structured data)
- Provides unified recommendations, planning, and summaries
- Reduces app-hopping by being the single point of interaction

---

## Data Storage

| Store | Use Case |
|---|---|
| **Supabase (PostgreSQL)** | Structured data — user profiles, activity records, todos, etc. |
| **Vector DB** | Semantic/context memory for the master agent (conversation history, embeddings) |

---

## NLP Module

- Built as a **course project showcase** (NLP academic project)
- Handles workout/health text analysis (classifier, NER, sentiment, NLG)
- Trained on custom data (`combined_train/val/test_data.json`)
- Plan: add a **toggle** on relevant components to switch between:
  - `NLP mode` — local NLP models generate the summary/insight
  - `AI mode` — LangChain/LLM agent generates the summary/insight

---

## Tech Stack

### Frontend
- **Next.js 15** (App Router)
- **Tailwind CSS**
- **Framer Motion** (animations)
- **shadcn/ui** (component library)
- TypeScript

### Backend
- **FastAPI** (Python) — main server
- **FastAPI** — Slack server (separate service)
- **LangChain + LangGraph** — agent workflows
- **Groq API** (Llama 3) / **Google Gemini API** — LLM providers
- **Google APIs** — Calendar, Fit, Gmail
- **Strava API** — fitness data

### Infrastructure
- **Supabase** — PostgreSQL + Auth
- **Vector DB** — TBD (likely Pinecone or pgvector via Supabase)
- **MCP (Model Context Protocol)** — agent-to-tool communication standard

---

## Current State of the Codebase

| Area | Status |
|---|---|
| Client (Next.js landing page) | Working — landing/marketing UI built |
| FastAPI server (main) | Skeleton — health check + CORS only, API integrations stubbed |
| Google Calendar Agent | Fully built — LangGraph agent, event CRUD, Gmail, free slot finder |
| Slack Agent | Fully built — deterministic router, full Slack SDK control |
| NLP Module | Built for course — classifiers, NER, NLG, sentiment analysis |
| Auth | Stubbed (`client/src/app/auth/page.tsx`) |
| Supabase / DB | Not yet integrated |
| Master Agent | Not yet built |

---

## Key Design Principles
- **Privacy-first** — AI agents never read raw user inputs, only aggregated data
- **Explainable AI** — every recommendation traces back to a metric
- **User control** — users set their own autonomy levels
- **Immutable raw data** — inputs are never modified once stored
- **Auditable decisions** — all agent actions are logged and traceable
