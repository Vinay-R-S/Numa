# AGENTS.md - NUMA: Unified Daily Application Platform
## Complete Build Guide: Orchestration, Agents & RAG

## 1. Project Overview

NUMA is a unified personal productivity platform that connects Google Calendar, Slack, GitHub, LeetCode, Strava, Google Fit, and a Journal into a single AI-driven interface. The core intelligence layer consists of a Master Orchestrator Agent and five domain Sub-Agents, all backed by a RAG pipeline using MiniLM embeddings and Qdrant as the vector store.

**Tech Stack Summary:**
- Frontend: Next.js + React + TypeScript + ShadCN + Tailwind CSS
- Backend: FastAPI (Python)
- LLM: Groq API (use `llama-3.3-70b-versatile` or `llama3-8b-8192` for speed)
- Primary DB: Supabase (PostgreSQL)
- Vector DB: Qdrant (self-hosted or Qdrant Cloud)
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`
- Data Window: 7 days rolling (Calendar = current month)

## 2. High-Level Architecture Decisions

### 2.1 Agent Design Philosophy

Use a **two-tier agent architecture**:

- **Tier 1 - Master Orchestrator Agent**: Receives all user natural language requests. Decides which sub-agent(s) to invoke, in what order, and how to synthesize the final response. Never directly calls external APIs.
- **Tier 2 - Sub-Agents**: Each sub-agent owns one integration domain. Responsible for fetching from external APIs, storing into Supabase, embedding and ingesting into Qdrant, and executing write-back actions (create, edit, delete).

### 2.2 Sync vs On-Demand

- **Scheduled Sync** (background): Sub-agents run on a cron schedule to pull fresh data into Supabase and Qdrant. This is the data ingestion pipeline.
- **On-Demand Invocation**: When the user makes a request, the Master Agent queries already-ingested Qdrant vectors + Supabase structured data. It does not re-fetch from external APIs unless a real-time write action is needed (e.g., creating a calendar event).

### 2.3 Memory and State

Each sub-agent is stateless between calls. All state lives in Supabase. The Master Agent constructs context for each LLM call by pulling from Qdrant (semantic) and Supabase (structured/recent) fresh each time.

## 3. Supabase Schema Design

### 3.1 Core Tables

**users**
Stores authenticated user profile and OAuth tokens per integration.
Fields: id, email, google_access_token, google_refresh_token, slack_access_token, slack_team_id, github_username, strava_access_token, google_fit_token, created_at

**calendar_events**
Stores Google Calendar events for the current month.
Fields: id, user_id, event_id (Google's ID), title, description, start_time, end_time, attendees (jsonb array), meet_link, location, status, synced_at

**slack_messages**
Stores last 7 days of Slack messages.
Fields: id, user_id, channel_id, channel_name, sender_name, sender_id, message_text, is_mention, has_action_item, timestamp, synced_at

**tasks**
Kanban tasks auto-created by agents or manually by user.
Fields: id, user_id, title, description, source (slack/github/manual/agent), status (todo/inprogress/done), priority, due_date, created_at

**github_activity**
Stores commits, PRs, and issues for last 7 days.
Fields: id, user_id, repo_name, activity_type (commit/pr/issue), title, description, url, committed_at, synced_at

**leetcode_activity**
Stores solved problems for last 7 days.
Fields: id, user_id, problem_title, difficulty, slug, solved_at, synced_at

**health_data**
Stores daily aggregated health metrics for last 7 days.
Fields: id, user_id, date, steps, calories_burned, active_minutes, distance_km, sleep_hours, heart_rate_avg, source (strava/google_fit), synced_at

**strava_activities**
Stores individual Strava workout sessions.
Fields: id, user_id, activity_name, activity_type (run/ride/walk), duration_seconds, distance_km, avg_heart_rate, start_time, synced_at

**journal_entries**
Stores AI-generated daily journal entries.
Fields: id, user_id, date, content, health_summary (jsonb), productivity_summary (jsonb), mood_inference, created_at

**vector_sync_log**
Tracks what has been embedded and ingested into Qdrant to avoid re-embedding.
Fields: id, user_id, source_table, source_id, qdrant_point_id, embedded_at

### 3.2 Data Retention Policy

On every sync, run a cleanup step that deletes records older than 7 days for all tables except `calendar_events` (keep current month) and `journal_entries` (keep indefinitely).

## 4. Qdrant Vector DB Design

### 4.1 Collections

Use a single global Qdrant collection `numa_events` with a `user_id` payload field for filtering. This is simpler to manage than per-user collections.

**Collection name:** `numa_events`
**Vector size:** 384 (MiniLM-L6-v2 output dimension)
**Distance metric:** Cosine

### 4.2 Payload Schema per Point

Every vector point stored in Qdrant must carry this payload structure:

```
{
  user_id: string,
  source: "calendar" | "slack" | "github" | "leetcode" | "health" | "strava" | "journal",
  record_id: string,           // FK back to Supabase row ID
  text_chunk: string,          // the raw text that was embedded
  date: string,                // ISO date for recency filtering
  metadata: {}                 // source-specific extra fields
}
```

### 4.3 Text to Embed per Source

The quality of RAG depends entirely on what text you embed. Use these text templates for each source:

**Calendar Events:**
`"{title} with {attendees} on {start_time} at {location}. Description: {description}"`

**Slack Messages:**
`"[{channel_name}] {sender_name}: {message_text}"`
For mentions, prepend "MENTION: " to boost retrieval signal.

**GitHub Activity:**
`"{activity_type} in {repo_name}: {title}. {description}"`

**LeetCode:**
`"Solved {difficulty} problem: {problem_title}"`

**Health/Strava:**
`"On {date}: {steps} steps, {active_minutes} active minutes, {distance_km}km, {sleep_hours} hours sleep. Workout: {activity_name} for {duration} minutes."`

**Journal:**
Embed the full journal content text (chunk if over 500 tokens).

### 4.4 Ingestion Pipeline (runs inside each Sub-Agent after every sync)

1. Fetch new records from Supabase that are NOT in `vector_sync_log`
2. Build the text string per the templates above
3. Run text through MiniLM model → get 384-dim vector
4. Upsert into Qdrant with payload (use deterministic point ID derived from `source_table + source_id + user_id`)
5. Insert into `vector_sync_log` to mark as ingested

Use batched upserts (batch size 50-100) for efficiency.

### 4.5 Retrieval Strategy

When the Master Agent needs context for a user query:

1. Embed the user's query using MiniLM
2. Query Qdrant with mandatory `user_id` filter + optional `source` filter + optional date range filter on the `date` payload field
3. Retrieve top-K results (K=10 to 15 depending on query type)
4. Apply a recency boost: slightly prefer results from the last 2 days when re-ranking
5. Pass the `text_chunk` values of top results to the LLM as context

## 5. Master Orchestrator Agent

### 5.1 Role and Responsibilities

The Master Agent is the single entry point for all user interactions. It:

- Parses the user's intent from natural language
- Decides which sub-agents to invoke and with what parameters
- Queries Qdrant + Supabase for relevant context
- Calls Groq LLM with assembled context + user query
- Synthesizes a final response
- Optionally triggers write-back actions via sub-agents

### 5.2 Intent Classification

Before routing, the Master Agent classifies the user's message into one of these intent categories:

**Planning intent:** "Plan my day", "What should I focus on today", "Give me a schedule"
→ Invoke all sub-agents for context retrieval, then do day planning

**Query intent:** "What meetings do I have?", "Show my GitHub commits", "How many steps yesterday?"
→ Invoke the single relevant sub-agent for retrieval only

**Action intent:** "Schedule a meeting with John at 3pm", "Add a task for code review"
→ Invoke the relevant sub-agent to perform a write operation

**Summary intent:** "Summarize my Slack", "What happened in GitHub this week?"
→ Targeted retrieval from Qdrant + Supabase, then summarize

**Journal intent:** "Write my journal for today", "What did I do this week?"
→ Invoke Journal Agent

### 5.3 Orchestration Logic (Step by Step)

**Step 1:** Receive user message from FastAPI endpoint

**Step 2: Classify intent**
Send the user message to Groq with a short system prompt asking it to return JSON with `intent_type` and `target_agents` array. Use a fast/small model here (`llama3-8b-8192`) for speed.

**Step 3: Retrieve context**
Based on the classified intent:
- Embed user query with MiniLM
- Query Qdrant filtered by `user_id` and relevant `source` values
- Pull structured data from Supabase for any time-specific queries (e.g., today's calendar events)
- Combine: vector results + structured query results into a unified context block

**Step 4: Build the Master Agent prompt**
Construct a prompt with:
- System role: "You are NUMA, an AI daily assistant..."
- Today's date and day of week
- Retrieved context (from Qdrant + Supabase)
- User's message
- Available actions the agent can take (as a tool/function list)

**Step 5: Call Groq LLM**
Send to Groq. Expect either:
- A plain text response (for queries/summaries)
- A structured JSON response with an `action` field (for planning/write intents)

**Step 6: Handle action outputs**
If the LLM response contains an action (e.g., `{"action": "create_calendar_event", "params": {...}}`), pass it to the appropriate sub-agent's action handler.

**Step 7:** Return final response to frontend

### 5.4 Day Planning Flow (Special Case)

When the user asks to plan the day, the Master Agent runs a multi-step orchestration:

1. Pull today's calendar events from Supabase (structured query)
2. Pull pending tasks from `tasks` table where status != done
3. Query Qdrant for recent health data → assess energy level
4. Query Qdrant for recent Slack mentions → identify urgent items
5. Query Qdrant for GitHub open PRs or issues → identify pending dev work
6. Assemble all context
7. Call Groq with a planning-specific system prompt instructing it to produce a time-blocked schedule
8. Parse the schedule and optionally create new tasks in Supabase
9. Optionally create time blocks in Google Calendar via Calendar Agent

### 5.5 Tool/Function Definitions for Master Agent

Define these as Groq tool-call functions:

- `get_calendar_events(date_range)` → calls Calendar Agent retrieval
- `create_calendar_event(title, start, end, attendees, description)` → calls Calendar Agent action
- `get_slack_summary(hours_back)` → calls Slack Agent retrieval
- `get_health_summary(days_back)` → calls Health Agent retrieval
- `get_github_summary(days_back)` → calls GitHub Agent retrieval
- `create_task(title, description, priority, due_date, source)` → writes to Supabase tasks table
- `update_task_status(task_id, new_status)` → updates task in Supabase
- `generate_journal(date)` → calls Journal Agent

## 6. Sub-Agent Specifications

### 6.1 Google Calendar Agent

**Sync Schedule:** Every 30 minutes

**Data Scope:** All events in the current calendar month

**Ingestion Flow:**
- Hit Google Calendar API `events.list` with `timeMin` = start of month, `timeMax` = end of month
- Upsert into `calendar_events` table using `event_id` as the unique key to handle updates
- Embed and ingest into Qdrant any new or updated events not already in `vector_sync_log`

**Action Capabilities:**
- Create event: POST to Google Calendar API → upsert into Supabase → embed into Qdrant
- Update event: PATCH to Google Calendar API → update Supabase → update Qdrant point payload
- Delete event: DELETE from Google Calendar API → remove from Supabase → delete Qdrant point
- Invite attendees: handled as part of create/update via the attendees array in the API request
- Auto-create meeting links: use `conferenceData` in Google Calendar API request

**Retrieval Interface:**
Accept a natural language query → embed it → query Qdrant with `source=calendar` filter → return top results + today's events from Supabase as structured data.

**Edge Cases:**
- Recurring events: store each occurrence separately with its specific start/end time
- Cancelled events: mark status as cancelled in Supabase, keep Qdrant point with updated payload
- All-day events: treat as full-day blocks in the day planner

### 6.2 Slack Agent

**Sync Schedule:** Every 15 minutes

**Data Scope:** Last 7 days of messages across all channels the user is a member of

**Ingestion Flow:**
- Use Slack API `conversations.list` to get all channels the user belongs to
- For each channel, use `conversations.history` with `oldest` = 7 days ago timestamp
- For each message, check if the user is mentioned by scanning for `<@user_id>` or user's display name → set `is_mention = true`
- Use a keyword heuristic to detect action items (contains: "please", "can you", "by when", "deadline", "ASAP", "need you to") → set `has_action_item = true`
- Upsert into `slack_messages` table
- Embed and ingest into Qdrant

**Action Capabilities:**
- Auto-create tasks: if `has_action_item = true` and `is_mention = true`, create a record in the `tasks` table with `source = slack`
- Auto-create calendar event: if message contains scheduling language ("let's meet", "call at", "schedule a sync"), pass to Calendar Agent
- No sending of Slack messages for now - read-only

**Retrieval Interface:**
Embed query → query Qdrant with `source=slack` filter. Also support structured Supabase queries like "all mentions from today".

**Special UI Behavior:**
The frontend Slack Page has two tabs: "Mentions" (filtered by `is_mention=true`) and "General". Both are served from Supabase, not Qdrant. Qdrant is only used when the Master Agent performs semantic search over Slack data.

### 6.3 Health Agent

**Sync Schedule:** Every 6 hours

**Data Sources:** Strava API + Google Fit REST API (Google Fit reads from Samsung Health via sync)

**Data Scope:** Last 7 days

**Ingestion Flow (Strava):**
- Hit Strava API `athlete/activities` endpoint with `after` = 7 days ago as Unix timestamp
- Store each activity in `strava_activities` table
- Aggregate daily totals (distance, duration, avg HR) into `health_data` table with `source = strava`

**Ingestion Flow (Google Fit):**
- Hit Google Fit `users.dataset.aggregate` API for steps, calories, active minutes, sleep
- Aggregate by day and upsert into `health_data` table with `source = google_fit`
- Merge with Strava data per day: prefer Strava for workout-specific data, Fit for passive data like steps

**Embed and Ingest:** Create one Qdrant vector point per day that summarizes all health metrics for that day using the text template in section 4.3.

**Action Capabilities:** None - Health Agent is read-only.

**Retrieval Interface:**
Semantic search via Qdrant + structured time-range queries from Supabase. Used by Master Agent during day planning to infer energy levels and recommend activity.

**Inference Rules (encode in Master Agent planning prompt):**
- Sleep < 6 hours → suggest lighter schedule, no intense meetings in first 2 hours
- Steps < 3000 yesterday → suggest a walk break in the plan
- Workout logged today → factor recovery time into afternoon slots

### 6.4 GitHub & LeetCode Agent

**Sync Schedule:** Every 1 hour

**Data Scope:** Last 7 days

**Ingestion Flow (GitHub):**
- Use GitHub REST API to fetch commits per repo: `repos/{owner}/{repo}/commits` with `since` = 7 days ago
- Fetch PRs: `repos/{owner}/{repo}/pulls` with `state=all`, filter by `updated_at` in last 7 days
- Fetch issues assigned to user across all repos
- Upsert into `github_activity` table

**Ingestion Flow (LeetCode):**
- LeetCode has no official public API. Use the unofficial GraphQL endpoint at `https://leetcode.com/graphql` with the user's session cookie, or use an open-source wrapper like `alfa-leetcode-api`
- Query `recentAcSubmissionList` for the user
- Upsert into `leetcode_activity` table

**Action Capabilities:** None - read-only.

**Retrieval Interface:**
Semantic search for questions like "what did I work on in repo X this week?" or "did I solve any hard problems?". Also serves structured summary queries for the frontend dashboard card (commit count, PR status, problems solved) via Supabase.

**LeetCode Fragility Note:**
Wrap all LeetCode API calls in broad exception handling. If it fails, log and skip - do not fail the entire sync. Show LeetCode data as "unavailable" on the frontend if sync has been failing for over 24 hours.

### 6.5 Journal Agent (NLP Pipeline)

**Trigger:** On-demand when user requests journal generation, OR scheduled nightly at 11 PM

**Role:** This is more of an NLP pipeline function than a traditional orchestrating agent. It does not classify intent or invoke other agents - it gathers structured signals then calls Groq once to generate the journal.

**Inputs (all pulled from Supabase for the target date):**

- `health_data`: steps, active_minutes, sleep_hours, workout logged (from strava_activities)
- `github_activity`: commit count, PR updates, repos touched
- `slack_messages`: message count received, mention count, action items created from Slack
- `calendar_events`: number of meetings, total meeting hours
- `tasks`: tasks completed today (status changed to done), tasks created today
- `leetcode_activity`: problems solved

**Generation Flow:**

1. Pull all structured signals from Supabase for the target date
2. Query Qdrant for notable events from that date across all sources using a broad date-filtered search (this catches specific context like a particular meeting or workout the structured aggregates miss)
3. Construct a generation prompt: provide all signals as a structured data block, instruct Groq to write a first-person reflective journal entry in a natural tone
4. Include mood inference: based on sleep quality, meeting load, and activity level, instruct the LLM to infer a mood tag (energized / productive / drained / balanced / stressed)
5. Store the generated journal in `journal_entries` table
6. Embed the journal content and ingest into Qdrant with `source=journal`

**Prompt Design Note:** The journal prompt must instruct the LLM NOT to recite raw numbers mechanically. It should weave them into natural narrative - "had a packed meeting day" not "you had 6 meetings today", "got a solid run in" not "you ran 5.2km". The output should read like something a person wrote, not a stats report.

## 7. RAG Pipeline - Detailed Design

### 7.1 Embedding Setup

Use `sentence-transformers/all-MiniLM-L6-v2` via the `sentence-transformers` Python library.

- Output dimension: 384
- Fast enough to run on CPU for our text sizes
- Works well for short to medium text chunks
- Load the model once at FastAPI startup and keep in memory - do not reload per request

### 7.2 Chunking Strategy

For most NUMA data, each record is one chunk. The data is already naturally short - one Slack message, one calendar event, one health day summary. No recursive chunking needed.

Exception: Journal entries may grow long. If a journal entry exceeds 500 tokens, split into 300-token chunks with 50-token overlap before embedding. Store each chunk as a separate Qdrant point with the same `record_id` but a chunk index suffix in the payload.

### 7.3 Qdrant Operations Reference

**Collection setup (run once):**
Create collection `numa_events` with vector size 384, cosine distance metric, and enable payload indexing on `user_id`, `source`, and `date` fields for efficient filtered search.

**Upsert:**
Generate deterministic point IDs from `md5(user_id + source_table + source_id)` to make upserts idempotent. This means re-running ingestion after an update correctly overwrites the old vector rather than creating duplicates.

**Search with filters:**
Always apply `user_id` as a mandatory must-match filter. Add `source` filter for domain-specific queries. Add date range filter using must conditions on the `date` payload field (ISO string comparison works with Qdrant's match conditions).

**Delete:**
When a Supabase record is deleted (e.g., calendar event cancelled), look up the corresponding `qdrant_point_id` from `vector_sync_log` and delete it from Qdrant. Then remove the `vector_sync_log` entry.

### 7.4 Context Assembly for LLM

When the Master Agent assembles context for a Groq call:

1. Run Qdrant semantic search → get top 10-15 text chunks with their source and date
2. Run Supabase structured queries → get today's events, pending tasks, etc.
3. Format as a context block:

```
=== Relevant Context from Your Data ===
[source: calendar, 2025-01-15] Team standup with Alice, Bob on Jan 15 at 10am...
[source: slack, 2025-01-15] MENTION: Alice: can you review the PR before EOD?
[source: health, 2025-01-14] On Jan 14: 8200 steps, 45 active minutes, 7.5 hours sleep...

=== Today's Structured Data ===
Calendar Events Today: 10:00 AM - Standup | 2:00 PM - 1:1 with manager
Pending Tasks: [Code review for auth PR] [Fix login bug] [Write tests]
```

4. Keep total context under 3000 tokens to leave headroom for LLM response within Groq's limits.

### 7.5 Retrieval Quality Guidelines

- For day planning queries: include all sources in the Qdrant filter, no source restriction
- For domain-specific queries: filter to the relevant source to reduce noise
- Implement a minimum score threshold (cosine score > 0.4) - if results are below this, fall back to a Supabase structured query for that source
- Always inject today's date and current time into the LLM system prompt so temporal reasoning works correctly
- Include a recency signal: if two results have similar scores, prefer the more recent one

## 8. FastAPI Backend Structure

### 8.1 Router Organization

```
/api/auth/{provider}        - OAuth flows for Google, Slack, GitHub, Strava
/api/agent/chat             - Master Agent general chat (POST)
/api/agent/plan-day         - Master Agent day planning (POST)
/api/sync/{source}          - Manual sync trigger per source (also called by cron jobs)
/api/calendar/events        - Calendar CRUD (proxies to Calendar Agent)
/api/tasks                  - Task CRUD (direct Supabase read/write)
/api/slack/messages         - Slack messages read
/api/slack/mentions         - Slack mentions filtered view
/api/health/summary         - Health data read
/api/github/activity        - GitHub + LeetCode activity read
/api/journal/entries        - Journal read
/api/journal/generate       - Trigger journal generation (POST)
```

### 8.2 Background Job Scheduler

Use APScheduler (`AsyncIOScheduler`) integrated into FastAPI's startup event to run sync jobs:

- Calendar Agent sync: every 30 minutes
- Slack Agent sync: every 15 minutes
- Health Agent sync: every 6 hours
- GitHub + LeetCode Agent sync: every 1 hour
- Journal generation: nightly at 11 PM (optional - user can also trigger manually via the journal page)

Each sync job must be wrapped in a try/except so a failure in one agent does not crash the others or the scheduler.

### 8.3 Agent Class Structure

**MasterAgent** class:
- `async chat(user_id, message)` - general query handler
- `async plan_day(user_id, date)` - day planning handler
- `_classify_intent(message)` - returns intent type and target agents
- `_retrieve_context(user_id, query, sources, date_range)` - queries Qdrant + Supabase
- `_call_llm(system_prompt, context, user_message, tools)` - hits Groq API

**Each Sub-Agent** class (CalendarAgent, SlackAgent, HealthAgent, GitHubAgent, JournalAgent):
- `async sync(user_id)` - full data ingestion pipeline for that domain
- `async retrieve(user_id, query, date_range)` - RAG retrieval for that domain
- (Where applicable) action methods: `create_event`, `update_event`, `delete_event`, etc.

**EmbeddingService** (singleton):
- Loads MiniLM at startup
- `embed(text)` → returns 384-dim vector
- `embed_batch(texts)` → batched embedding for ingestion

**QdrantService** (singleton):
- Wraps Qdrant client
- `upsert(points)`, `search(user_id, vector, filters, top_k)`, `delete(point_id)`

## 9. Frontend Integration Points

### 9.1 Chat Interface

Every page has a persistent chat drawer or sidebar that POSTs to `/api/agent/chat`. The Master Agent determines context automatically - the frontend passes only the user message and user ID. No need to specify domain.

### 9.2 Page-Specific Data Fetching

Each page fetches its display data directly from Supabase via the corresponding FastAPI router. The agent is only invoked for natural language queries or action requests, not for rendering the page's data tables/cards.

- Task Page → `/api/tasks`
- Slack Page → `/api/slack/messages` and `/api/slack/mentions`
- Calendar Page → `/api/calendar/events`
- Health Page → `/api/health/summary`
- GitHub & LeetCode Page → `/api/github/activity`
- Journal Page → `/api/journal/entries`

### 9.3 Sync Status Indicator

Show a "last synced" timestamp on each page, pulled from the most recent `synced_at` value in Supabase for that domain's table. Include a manual refresh button that calls `/api/sync/{source}` to trigger an immediate sync.

### 9.4 Mental Health Page

This page has no backend agent or API calls. It is entirely static:
- Guided meditation content (embedded YouTube videos or local audio player)
- Yoga routine cards (static text/image content)
- No data collection, no personalization, no Supabase reads

## 10. OAuth and Token Management

### 10.1 Required OAuth Scopes per Provider

**Google (covers Calendar + Google Fit):**
`https://www.googleapis.com/auth/calendar.events` (read/write calendar)
`https://www.googleapis.com/auth/fitness.activity.read`
`https://www.googleapis.com/auth/fitness.sleep.read`

**Slack:**
`channels:history`, `channels:read`, `users:read`

**GitHub:**
`repo`, `read:user` (OAuth App, not GitHub App)

**Strava:**
`activity:read_all`

### 10.2 Token Storage and Refresh

Store all tokens encrypted in the `users` table in Supabase. Google and Strava use refresh tokens - implement refresh logic at the start of each sub-agent sync: check token expiry, refresh if needed, update Supabase before proceeding. GitHub tokens do not expire. Slack tokens do not expire unless manually revoked.

## 11. Error Handling and Degradation

### 11.1 Sub-Agent Sync Failures

If a sync fails (API rate limit, expired token, network error):
- Log to a `sync_errors` table with timestamp, source, and error message
- Do not surface the error to the user unless they are actively requesting data from that source
- Continue serving stale data from Qdrant and Supabase
- Show a small "sync issue" indicator on the relevant page's status area

### 11.2 Qdrant Unavailability

If Qdrant is unreachable when the Master Agent needs context:
- Fall back to Supabase-only structured queries
- Notify the LLM in the system prompt: "semantic context unavailable, rely on structured data only"
- Do not return an error to the user - degrade gracefully with slightly less relevant answers

### 11.3 Groq Rate Limits

Groq enforces per-minute token limits. Mitigate by:
- Using the smaller model (`llama3-8b-8192`) for intent classification
- Using the larger model (`llama-3.3-70b-versatile`) only for final response generation
- Implementing exponential backoff on 429 responses
- Queuing concurrent chat requests rather than allowing parallel LLM calls

## 12. Build Order Recommendation

Build in this sequence to have a working end-to-end loop as early as possible:

**Phase 1 - Foundation**
FastAPI setup → Supabase schema → Qdrant collection → MiniLM embedding loader → Google OAuth → Calendar Agent sync + ingestion. Verify you can query Qdrant and retrieve calendar events semantically.

**Phase 2 - Master Agent (Basic)**
Intent classification → context retrieval → Groq call → basic Q&A over calendar data. Wire up the frontend chat interface. Get a working conversation loop before adding more data sources.

**Phase 3 - Remaining Sub-Agents**
Add Slack Agent → GitHub Agent → Health Agent, one at a time. Each follows the same pattern: sync → Supabase → embed → Qdrant → expose retrieval to Master Agent.

**Phase 4 - Actions and Write-Back**
Calendar Agent write operations (create/edit/delete). Auto-task creation from Slack Agent. Wire up the Tasks page with full CRUD.

**Phase 5 - Day Planning**
Full day planning orchestration in Master Agent. Health data integration for planning recommendations. Optional calendar block creation from the plan.

**Phase 6 - Journal Agent**
NLP pipeline setup. Connect all signals. Implement nightly generation trigger.

**Phase 7 - Frontend Polish**
All page-specific views. Sync status indicators. Mental Health static page. Overall UX pass.

## 13. Key Prompt Engineering Notes

### Master Agent System Prompt Structure

The system prompt for the Master Agent should always include:
- NUMA's role: concise, action-oriented personal AI assistant
- Today's date and current time
- User's first name (from profile)
- A structured list of available tools/actions the agent can invoke
- Instruction: return a JSON object when an action is required; return plain text for queries and summaries
- Instruction: be brief, specific, and personal - not verbose or generic
- Instruction: when context is insufficient, say so honestly rather than hallucinating

### Planning Prompt Specifics

The day planning prompt should explicitly instruct the model to:
- Produce a time-blocked schedule starting from the current time
- Treat existing calendar events as immovable anchors
- Suggest realistic time allocations (do not over-schedule)
- Prioritize Slack mentions and flagged action items
- Include at least one break if the day has 4 or more hours of meetings
- Account for health data (low sleep = lighter morning load)
- Output a structured JSON format with a `time_blocks` array that the frontend can parse and render

### Journal Generation Prompt Specifics

- Provide all signals as a structured data block before asking for generation
- Instruct the model to write first-person, past-tense, reflective prose
- Instruct it NOT to recite numbers directly - weave them into narrative
- Ask for a one-word mood tag at the end as a separate JSON field
- Specify length: 150-250 words for the journal body, concise and readable