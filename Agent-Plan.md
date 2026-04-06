# NUMA — Multi-Agent AI System

## Overview
NUMA is a multi-agent AI system that acts as a personal intelligence layer over connected data sources. It allows users to ask natural language questions about their week (e.g., planning, productivity, sleep) and generates cross-domain insights using real user data from the past 7 days.

**Core Stack**
- LangGraph — Agent orchestration  
- Groq — LLM inference  
- Qdrant — Vector database  
- Supabase — Raw data storage  

---

## Architecture

The system is divided into 5 layers:

### 1. Data Sources
- Google Calendar  
- Google Fit  
- Strava  
- Slack  
- GitHub  
- Gmail  
- Tasks  
- Journal  

### 2. Supabase (Raw Storage)
- Structured tables per source  
- Fields: `user_id`, `created_at`  
- Maintains a strict 1-week rolling window  
- Daily auto-cleanup via cron  

### 3. Ingestion Pipeline
- Converts database rows → natural language sentences  
- Generates embeddings using `all-MiniLM-L6-v2`  
- Stores vectors in Qdrant with metadata  

### 4. Qdrant (Vector Store)
- Stores embeddings per user  
- Enables semantic search with filtering  

### 5. Multi-Agent System (LangGraph)
- Orchestrator  
- 5 specialist agents  
- 1 Insight synthesizer  

---

## Data Storage (Supabase)

### Rolling Window Policy

| Source            | Data Range                  |
|------------------|----------------------------|
| Google Calendar  | Past 7 days + Future 7 days |
| All Others       | Past 7 days only           |

### Auto-Delete Logic
- Runs daily at midnight UTC  
- Deletes records older than 7 days  
- Calendar preserves future events  

---

## Ingestion Pipeline

### When It Runs
- On new incoming data  
- After nightly cleanup  

### Processing Steps
1. Convert row → plain English sentence  
2. Generate embedding (384-dimension)  
3. Store in Qdrant with metadata  

### Metadata Stored
- `user_id`  
- `source`  
- `date`  
- `type`  

### Example Sentence Formats

**Strava**
On {date}, user completed a {type} of {distance}km at {pace} pace...
**Google Fit**
On {date}, user slept {sleep_hours} hours, took {steps} steps...

**Slack**
On {date}, user sent {message_count} messages across {channel_count} channels...

**GitHub**
On {date}, user made {commit_count} commits across {repos} repositories...

---

## Vector Database (Qdrant)

### Why Qdrant
- Payload filtering before search  
- Better performance and precision  
- Tunable HNSW parameters  

### Collection Structure
- Collection: `numa_user_data`  
- Each record:
  - ID: `{source}_{record_id}`  
  - Vector (384-dim)  
  - Metadata payload  

### Query Pattern
- Semantic search + filter  

user_id = "user_123"
AND source IN ["google_fit", "strava"]

---

## Multi-Agent System

### Agents Overview

| Agent            | Role                    | Sources                  |
|-----------------|------------------------|--------------------------|
| Orchestrator    | Intent parsing         | None                     |
| Calendar        | Schedule analysis      | Google Calendar          |
| Health          | Physical state         | Google Fit, Strava       |
| Productivity    | Work output            | Tasks, GitHub, Slack     |
| Journal         | Emotional state        | Journal                  |
| Gmail           | Communication load     | Gmail                    |
| Insight         | Final synthesis        | All outputs              |

---

## Agent Details

### Orchestrator
- Parses user intent  
- Selects required agents  
- Defines time scope  

---

### Calendar Agent
- Extracts meetings  
- Identifies free time blocks  
- Detects back-to-back meetings  

---

### Health Agent
- Computes:
  - Average sleep  
  - Sleep debt  
  - Energy level  
- Detects overtraining  

---

### Productivity Agent
- Parallel queries:
  - Tasks  
  - GitHub  
  - Slack  
- Detects:
  - Distraction patterns  
  - Burnout signals  

---

### Journal Agent
- Analyzes sentiment  
- Detects:
  - Mood trends  
  - Stress triggers  
  - Positive signals  

---

### Gmail Agent
- Tracks:
  - Email volume  
  - Response time  
- Classifies communication load  

---

### Insight Agent
- Combines all agent outputs  
- Detects cross-domain patterns  

**Examples**
- Poor sleep + heavy meetings → burnout  
- High Slack + low tasks → distraction  
- Good sleep + high commits → flow state  

---

## Parallel Execution

### Problem
Sequential execution > 3.5 seconds  

### Solution — Fan-Out / Fan-In

#### Phase 1 — Orchestrator (~350ms)
- Runs first  

#### Phase 2 — Specialists (~500–600ms)
- Run in parallel  

#### Phase 3 — Insight (~450ms)
- Runs after all complete  

### Total Latency
~1.4 seconds  

---

### Parallelism Levels
- Level 1: Agent-level parallelism (LangGraph)  
- Level 2: Internal async queries (e.g., asyncio)  

---

### Failure Handling
- 2-second timeout per agent  
- Fallback response:
  
- available: false

- - Insight agent ignores missing data  

---

## Technology Stack

| Component          | Technology                          |
|-------------------|------------------------------------|
| Orchestration     | LangGraph                          |
| LLM               | Groq (llama3-8b-8192)              |
| Vector DB         | Qdrant                             |
| Embeddings        | sentence-transformers MiniLM       |
| Storage           | Supabase (PostgreSQL)              |
| Scheduler         | APScheduler                        |
| NLP               | DistilBERT + spaCy + TF-IDF LogReg |
| API               | FastAPI                            |

---

## Build Order

1. Supabase schema  
2. Cron cleanup  
3. Qdrant setup  
4. Sentence conversion functions  
5. Ingestion pipeline  
6. Groq helper  
7. Orchestrator  
8. Specialist agents  
9. Insight agent  
10. LangGraph graph  
11. API endpoint  
12. Frontend integration  

---

## API

### Endpoint

POST /agent/chat

### Request
json
{
  "user_id": "string",
  "message": "string"
}
Response
{
  "response": "string"
}
Behavior
Executes full agent pipeline
Returns Insight Agent output
Target latency: < 1.5 seconds
