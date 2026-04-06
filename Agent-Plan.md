NUMA — Multi-Agent AI System: README Content

Overview
NUMA's multi-agent system is an AI-powered personal intelligence layer that sits on top of all connected data sources. It allows users to ask any natural language question about their week — "plan my day", "why was I unproductive on Tuesday", "how has my sleep been" — and receive a cross-domain intelligent answer powered by their own real data from the past 7 days.
The system is built using LangGraph for agent orchestration, Groq for fast LLM inference, Qdrant as the vector database, and Supabase as the raw data store.

Architecture Overview
The system has 5 layers that work together:
Layer 1 — Data Sources
Google Calendar, Google Fit, Strava, Slack, GitHub, Gmail, Tasks, Journal
Layer 2 — Supabase (Raw Storage)
All source data stored in structured tables with a strict 1-week rolling window. Auto-delete cron job runs every midnight.
Layer 3 — Ingestion Pipeline
Converts Supabase rows into natural language sentences, embeds them using sentence-transformers, and upserts into Qdrant with source and user metadata.
Layer 4 — Qdrant (Vector Store)
Stores embedded sentences per user. Agents query this using semantic search filtered by source and user ID.
Layer 5 — Multi-Agent System (LangGraph)
Orchestrator + 5 specialist agents + 1 insight synthesizer. Specialists run in parallel, results converge to the Insight Agent.

Data Storage — Supabase
1-Week Rolling Window
Every data source has its own table in Supabase. Every table contains a user_id and created_at column. A daily cron job running at midnight uses these to enforce the rolling window.
SourceWindowGoogle CalendarPast 7 days + Future 7 daysGoogle FitPast 7 days onlyStravaPast 7 days onlySlackPast 7 days onlyGitHubPast 7 days onlyGmailPast 7 days onlyTasksPast 7 days onlyJournalPast 7 days only
Google Calendar is the only exception — it stores future events up to 7 days ahead because the system needs upcoming schedule data to plan the user's day. All other sources store only historical data.
Auto-Delete Logic
A scheduled job using APScheduler runs at midnight UTC every day. It calculates a cutoff timestamp of 7 days ago and deletes all rows older than that cutoff for every table except Calendar. For Calendar it deletes only past events older than 7 days while preserving all future events regardless of when they were created.

Ingestion Pipeline
The ingestion pipeline is the most critical piece of the system. It is responsible for converting raw structured database rows into searchable vector embeddings stored in Qdrant.
When It Runs

Immediately when new data arrives from any external API
After the nightly cron cleanup to remove stale embeddings

How It Works
Each Supabase row is converted into a plain English sentence that captures the meaning and context of that record. That sentence is then embedded using the all-MiniLM-L6-v2 model from sentence-transformers, producing a 384-dimensional vector. That vector is upserted into Qdrant along with metadata including user_id, source, date, and type.
Why Sentences and Not Raw Data
Qdrant performs semantic search — it finds records by meaning, not by exact keyword match. A plain English sentence like "On Monday, user slept 4.5 hours and resting heart rate was 78 bpm" will semantically match a query like "how tired was I this week" far more accurately than a raw JSON object ever could. The quality of these sentences directly determines the quality of every agent's responses.
Sentence Format Per Source
Strava
"On {date}, user completed a {type} of {distance}km at {pace} pace, average heart rate {avg_hr} bpm, duration {duration} minutes."
Google Fit
"On {date}, user slept {sleep_hours} hours, took {steps} steps, burned {calories} calories, resting heart rate {resting_hr} bpm."
Slack
"On {date}, user sent {message_count} Slack messages across {channel_count} channels, average response time {avg_response_time} minutes."
GitHub
"On {date}, user made {commit_count} commits across {repos} repositories, added {additions} lines, removed {deletions} lines. Commit messages: {commit_messages}."
Google Calendar
"On {date}, user has meeting '{title}' from {start_time} to {end_time}, duration {duration} minutes, with {attendee_count} attendees."
Tasks
"Task '{title}' with priority {priority} was {status} on {date}. Deadline: {deadline}."
Journal
"Journal entry on {date}: {text}. Sentiment: {sentiment} with confidence {confidence}."
Gmail
"On {date}, user received {received_count} emails and sent {sent_count} emails. Average response time: {avg_response_time} hours."

Vector Database — Qdrant
Qdrant is used as the vector store for the multi-agent system. It was chosen over ChromaDB for its superior HNSW implementation, payload filtering capability, and higher recall accuracy at scale.
Why Qdrant Over ChromaDB
Qdrant performs payload filtering — filtering by user_id and source — before the vector search happens rather than after. This means the search space is narrowed before similarity is calculated, which gives both better speed and better precision. ChromaDB applies filters after the search, which is less efficient and less accurate. Qdrant also exposes HNSW construction parameters (ef_construction, m) which can be tuned to increase recall at the cost of indexing speed — useful as the dataset grows.
Collection Structure
One collection per deployment named numa_user_data. Every point in the collection has:

A unique ID in the format {source_type}_{record_id}
A 384-dimensional vector embedding
A payload containing user_id, source, date, type

How Agents Query Qdrant
Every specialist agent queries Qdrant using two things simultaneously — a semantic search vector generated from a domain-specific query string, and a payload filter that restricts results to the correct user_id and source. This ensures the Calendar agent never accidentally retrieves a Slack message, and that one user's data never surfaces in another user's results.
Example filter structure for the Health Agent:
user_id = "user_123" AND source IN ["google_fit", "strava"]
The agent requests the top 8 most semantically similar results matching that filter. Those results are passed to Groq as context.

The Multi-Agent System
Agent Overview
AgentRoleData SourcesOrchestratorParse intent, route to specialistsNone — no Qdrant queriesCalendar AgentSchedule, meetings, free blocksGoogle CalendarHealth AgentSleep, steps, workouts, energyGoogle Fit, StravaProductivity AgentTasks, commits, communication loadTasks, GitHub, SlackJournal AgentMood, sentiment, stress signalsJournalGmail AgentEmail volume, response time, cognitive loadGmailInsight AgentCross-domain synthesis, final responseNone — reads specialist outputs only

Agent 1 — Orchestrator
Role: Entry point for every user message. Parses intent and decides which specialist agents to activate.
What it does:
Receives the raw user query and sends it to Groq with a routing prompt. Groq returns a structured JSON containing the list of agents needed, the detected intent, the time focus of the query (today, this week, specific date), and whether the user is asking for a full day plan. The Orchestrator writes this to the shared LangGraph state and stops. It does not query Qdrant.
Key design decision: The Orchestrator uses a small fast Groq model for routing since it is a classification task, not a reasoning task. Speed here directly impacts total response time since every request passes through it.

Agent 2 — Calendar Agent
Role: Understands the user's schedule for the past and upcoming 7 days.
What it does:

Retrieves calendar events from Qdrant filtered by source = "calendar"
Identifies meetings for the day, their times and durations
Calculates total meeting load — heavy, moderate, or light
Finds free time blocks suitable for deep work or exercise
Detects back-to-back meeting patterns that cause cognitive fatigue
For real-time future data, can also call the Google Calendar API directly

Output to Insight Agent:
Structured JSON containing meetings today, meeting load classification, list of free blocks, back-to-back flag, busiest day of the week, and a plain English summary.

Agent 3 — Health Agent
Role: Understands the user's physical state — sleep quality, activity levels, heart rate, and recovery.
What it does:

Queries Qdrant for both Google Fit and Strava data simultaneously
Calculates average sleep hours for the week
Detects sleep debt — consistently under 7 hours
Identifies sleep trend — improving, declining, or stable
Detects overtraining risk — high workout intensity on consecutive days with no rest
Estimates today's energy level based on last night's sleep and recent workout load
Correlates workout performance with preceding night's sleep

NLP Integration:
The existing NLP-NUMA pipeline (DistilBERT sentiment + performance classifier + spaCy NER) can be plugged into this agent to analyze workout description text. When Strava data includes a description, the Health Agent passes it through the NLP pipeline before sending to Groq, adding sentiment, performance classification, and extracted entities (BODY_PART, SYMPTOM, DISTANCE, LOCATION) to the context.
Output to Insight Agent:
Structured JSON with average sleep, sleep debt flag, sleep trend, average steps, workout frequency, overtraining risk flag, energy level estimate, and one specific health recommendation.

Agent 4 — Productivity Agent
Role: Understands how much actual work the user is getting done across tasks, code, and communication.
What it does:

Runs three Qdrant queries in parallel using asyncio.gather — one for tasks, one for GitHub, one for Slack
Calculates task completion rate for the week
Identifies pending high-priority tasks with their deadlines
Measures GitHub coding activity — active days vs quiet days, total commits
Uses Slack message volume as a proxy for communication load
Detects the distracted day pattern — high Slack activity combined with low task completion and zero commits
Detects burnout signal — high output every single day with no low-activity recovery days

Sources: Tasks, GitHub commits, Slack — all queried from Qdrant in parallel within the agent itself, giving a second level of parallelism below the LangGraph fan-out.
Output to Insight Agent:
Structured JSON with tasks completed, pending high-priority task titles, task completion rate, coding active days, total commits, Slack activity level, distracted day flag, most productive day of the week, and burnout signal flag.

Agent 5 — Journal Agent
Role: Understands the user's emotional and mental state through their written journal entries.
What it does:

Queries Qdrant for journal entries using emotion-focused search terms
Uses sentiment scores already stored in the sentence during ingestion
Identifies overall mood for the week — positive, neutral, or negative
Detects mood trend direction — improving, declining, or stable
Extracts dominant emotions from the language used
Identifies stress triggers — topics that appear repeatedly in negative entries
Identifies positive triggers — topics associated with good mood entries
Handles gracefully when no journal entries exist for the week

Output to Insight Agent:
Structured JSON with overall mood, mood trend, dominant emotions list, stress level, stress triggers, positive triggers, number of days with entries, and a 2-sentence plain English summary of emotional state.

Agent 6 — Gmail Agent
Role: Uses email behaviour as a signal for cognitive load, communication pressure, and engagement level.
What it does:

Queries Qdrant for Gmail activity records
Tracks average emails received per day vs sent per day
Measures average response time in hours — slow response indicates overload or disengagement
Identifies specific days where inbox volume exceeded normal thresholds
Classifies overall communication load — high, medium, or low
Distinguishes between received-heavy days (information overload) and sent-heavy days (active outreach)

Output to Insight Agent:
Structured JSON with average received per day, average sent per day, average response time, email overload days list, communication load classification, and engagement level.

Agent 7 — Insight Agent (Synthesizer)
Role: The final agent. Receives all specialist outputs and produces one coherent cross-domain response to the user's original question.
What it does:

Does not query Qdrant — works only with structured JSON from specialists
Reads all available results and finds connections that span multiple domains
Detects cross-domain patterns automatically

Example patterns it detects:

Poor sleep + heavy meetings + zero commits = burnout signal
High Slack + low tasks + negative journal = distracted and overwhelmed
Good sleep + light calendar + high commits = flow state day
Low steps + negative journal + email overload = recovery day needed

For "plan my day" queries it builds a concrete optimized schedule using calendar free blocks, current energy level from health data, pending high-priority tasks, current mood from journal, and email load context.
NLP Integration:
The Insight Agent is the ideal place to integrate the NLP-NUMA daily productivity classifier (TF-IDF + Logistic Regression). The combined data from all agents maps directly to the classifier's input — meetings, messages, commits, sleep, workout, journal. The classifier returns a daily state label (High Performance, Focused, Overloaded, Distracted, Recovery) and a burnout risk score that the Insight Agent can include in its response.
Output: Plain English conversational response, 100-200 words, second person, specific numbers and days referenced, sent directly to the chat UI.

Parallel Execution — Fan-Out and Fan-In
The Problem With Sequential Execution
If agents run one after another the total time is the sum of all agent times. With 5 specialist agents at 500ms each plus Orchestrator and Insight Agent, total response time exceeds 3.5 seconds. That is unacceptable for a chat interface.
The Solution — LangGraph Fan-Out with Fan-In Join
Phase 1 — Orchestrator (always sequential, ~350ms)
Runs alone. Cannot be parallelized because all agents depend on its output.
Phase 2 — Specialist Agents (fully parallel, ~500-600ms)
All agents selected by the Orchestrator fire simultaneously as independent async tasks. Each queries Qdrant and calls Groq independently. They do not communicate with each other. The slowest agent determines phase duration — not the sum of all agents.
Phase 3 — Insight Agent (always sequential, ~450ms)
Runs only after all active specialist branches have completed and merged their results back into shared state.
Total: ~1.4 seconds regardless of how many specialists run
How Fan-Out Works
The Orchestrator returns a list of agent names. LangGraph's add_conditional_edges function receives this list and activates all destinations simultaneously — not one chosen from many, but all activated at once. Each branch gets its own copy of the state to read from. Each branch writes only to its dedicated key — Calendar writes to calendar_result, Health writes to health_result, and so on. No shared mutable state between branches means no race conditions and no coordination logic needed.
How Fan-In Works
Every specialist agent has an edge pointing to the Insight Agent. When LangGraph sees multiple incoming edges on a single node it automatically treats that node as a join point — it waits for all active incoming branches to complete before executing that node. This waiting is not implemented in code. It is expressed by the graph structure itself. The moment the last active specialist finishes, LangGraph merges all branch writes into a unified state and passes it to the Insight Agent.
Two Levels of Parallelism
Level 1 — LangGraph fan-out: All specialist agents run in parallel across the agent graph.
Level 2 — asyncio.gather within agents: The Productivity Agent runs its three Qdrant queries (tasks, GitHub, Slack) in parallel inside its own execution using Python's asyncio.gather. This prevents the Productivity Agent from being the bottleneck despite needing three separate queries.
Partial Failure Handling
Each specialist agent has a 2-second timeout. If an agent times out or its Qdrant query fails, it writes a fallback value to its state key containing available: false. The join still completes because the branch technically finished. The Insight Agent detects the unavailable flag and omits that domain from synthesis without surfacing an error to the user. This means one slow query or one rate-limited Groq call never crashes the entire response.

Technology Stack
ComponentTechnologyAgent OrchestrationLangGraphLLM InferenceGroq API (llama3-8b-8192)Vector DatabaseQdrant (self-hosted)Embedding Modelsentence-transformers all-MiniLM-L6-v2Raw Data StoreSupabase (PostgreSQL)Scheduler (cron)APScheduler inside FastAPINLP PipelineNLP-NUMA (DistilBERT + spaCy + TF-IDF LogReg)API LayerFastAPI — endpoint /agent/chat

Build Order

Supabase tables for all 8 sources with user_id and created_at
Auto-delete cron job via APScheduler
Qdrant collection setup and connection
Sentence conversion functions for each source
Ingestion pipeline — Supabase → sentence → embed → Qdrant upsert
Shared Groq helper function
Orchestrator Agent
Calendar, Health, Productivity, Journal, Gmail agents
Insight Agent with NLP-NUMA integration
LangGraph graph — nodes, fan-out edges, fan-in join, compile
FastAPI /agent/chat endpoint
Frontend chat UI — new section in Numa


API Endpoint
POST /agent/chat
Request body:
{
  "user_id": "string",
  "message": "string"
}
Response:
{
  "response": "string"
}
The endpoint invokes the compiled LangGraph graph asynchronously and returns the Insight Agent's final response. Target response time under 1.5 seconds for all query types.
