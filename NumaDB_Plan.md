# Multi-Source AI Agent System — Implementation Plan

This is a plain-text implementation plan. No code. Just logic, structure, and steps.
Read this fully before building anything. Build in the exact order listed.

---

## What We Are Building

A system where multiple AI sub-agents control, interact with their respective apps and collect data from different sources (Strava, GitHub, Slack, LeetCode, Google Calendar, Google Fit, Journal, Tasks), store that data in two databases simultaneously, and a master agent reads all of it to produce a personalized daily plan for each user.

The system supports multiple users. Each user's data is completely isolated. All data expires after 7 days automatically.

---

## The Core Idea (Read This First)

There are two databases running side by side:

**Database 1 — Structured DB (Postgres)**
This is your source of truth. Every piece of data from every source is stored here with full precision. Numbers stay numbers. Timestamps stay timestamps. Nothing is rounded or summarized. This database answers the question: "Give me the exact facts."

**Database 2 — Vector DB (Qdrant or Pinecone)**
This is your search index. It stores embeddings (vector representations) of plain-English summaries of each event. This database answers the question: "What is relevant to right now?" It does NOT store raw numbers. It only stores text embeddings and a small amount of metadata needed to link back to Database 1.

These two databases are always written together. When data comes in, it goes to both at the same time. When data is updated, both are updated. When data expires, both are cleaned. They are never out of sync.

---

## The Three Layers

**Layer 1 — Data Collection**
Sub-agents fetch raw data from APIs and internal tools. Each agent is responsible for one source. Agents run on a schedule (e.g., every 15 minutes or hourly depending on source).

**Layer 2 — Storage**
All data is normalized into a standard format and written to both databases simultaneously. This is called a dual write. It always happens together — never one without the other.

**Layer 3 — Planning**
The master agent reads from both databases, assembles context for the user, resolves any conflicts, and produces a structured daily plan. This runs once per day per user, but can also run on demand.

---

## Data Flow (Step by Step)

1. A sub-agent fetches raw data from its source (e.g., Strava returns a run activity).
2. The agent converts the raw data into a standard canonical format (described below).
3. The canonical data is written to Postgres with full precision (exact numbers, exact timestamps).
4. A plain-English summary of the event is generated from the canonical data.
5. That summary is embedded into a vector using an embedding model.
6. The vector is stored in the Vector DB along with metadata (user_id, source, timestamp, a reference ID that links back to Postgres).
7. Later, when the master agent needs context, it searches the Vector DB semantically to find relevant events.
8. For each relevant event found, it fetches the full exact data from Postgres using the reference ID.
9. The master agent combines all of this into a context object and sends it to an LLM.
10. The LLM produces the daily plan as structured output.
11. The daily plan is saved and delivered to the user.

---

## The Canonical Format (Standard Structure for All Events)

Every event from every source must be converted into the same structure before being stored. This structure has these fields:

- row_id: a unique identifier. Format is: sourcename_eventtype_date_userid. Example: strava_run_20260314_usr123
- user_id: which user this belongs to
- source: which system it came from (strava, github, slack, gcalendar, gfit, leetcode, journal, tasks)
- event_type: what kind of event it is (run, commit, message, meeting, task, solve, etc.)
- status: current state of the event (active, completed, rescheduled, cancelled)
- priority: a number from 1 to 5 indicating importance (defined by the priority table below)
- start_time: when the event starts, in UTC
- end_time: when the event ends, in UTC (if applicable)
- ttl_expires: exactly 7 days after the event was created. This is when it gets deleted.
- exact_data: a nested object containing all numeric and boolean values. Every number, count, distance, score, or flag goes here. These values are never put in the text summary.
- text_summary: a plain English sentence or two describing the event. This is what gets embedded. It should mention the key facts but not repeat the numbers from exact_data.

---

## Priority Score Table

Each source has a base priority. Sub-agents use this when setting the priority field.

- Slack message with urgent, investor, deadline, or critical keywords: priority 5
- GitHub pull request with a deadline or milestone: priority 4
- Google Calendar meeting: priority 3
- Journal entry or user-created task: priority 3
- LeetCode problem: priority 2
- Strava or Google Fit activity: priority 2
- Normal Slack message (no urgency keywords): priority 2
- Regular GitHub commit: priority 1

If an event contains urgency signals in its title or description, increase its base priority by 1 or 2. For example, a Google Calendar meeting titled "Investor Call" gets a priority of 4 or 5, not 3.

---

## Sub-Agents (One Per Source)

Each sub-agent does exactly four things:
1. Fetch raw data from its source API or internal store.
2. Convert the raw data into the canonical format described above.
3. Write the canonical data to both databases (dual write).
4. Return the list of events it processed.

Sub-agents do not make decisions. They do not resolve conflicts. They only collect, normalize, and store.

The eight sub-agents to build are:

**Strava Agent**
Fetches recent activities (runs, rides, swims). The exact_data should include distance, pace, heart rate average, calories, elevation, and activity type. The text_summary should describe the activity in plain English.

**Google Fit Agent**
Fetches daily health metrics. The exact_data should include step count, active minutes, sleep hours, resting heart rate, and weight if available. The text_summary summarizes the day's health snapshot.

**GitHub Agent**
Fetches recent commits and pull requests. The exact_data should include repo name, PR number, files changed, lines added, lines deleted, and whether there is a deadline. The text_summary describes what was worked on.

**Slack Agent**
Fetches recent messages and mentions. The exact_data should include channel, message ID, whether urgency keywords were detected, and whether the message directly mentions the user. The text_summary describes the message context. Priority must be set based on urgency keyword detection.

**LeetCode Agent**
Fetches recently solved or attempted problems. The exact_data should include problem ID, difficulty, topic tags, whether it was solved, number of attempts, and time taken. The text_summary describes the problem and outcome.

**Google Calendar Agent**
Fetches upcoming events for today and tomorrow. The exact_data should include event ID, number of attendees, whether it is recurring, location, conference link, and organizer. The text_summary describes the meeting in plain English.

**Journal Agent**
Reads from the internal journal store. The exact_data should include entry ID, word count, mood tag, and topic list. The text_summary is a brief description of the journal entry's theme.

**Tasks Agent**
Reads from the internal task list. The exact_data should include task ID, due date, whether it is recurring, parent task ID if it is a subtask, and completion percentage. The text_summary describes the task and its urgency.

---

## Dual Write — The Most Important Rule

Every time a sub-agent has a canonical event ready, it must write to both databases before moving on. This is a single operation from the perspective of the rest of the system.

The write process is:
1. Write the full canonical event to Postgres.
2. Generate the embedding of the text_summary field.
3. Write the embedding to the Vector DB with the metadata fields: user_id, source, event_type, priority, start_time, ttl_expires, and row_id.
4. If either write fails, rollback and do not proceed. Log the error.

The Vector DB stores only metadata and the embedding. It never stores exact_data. The exact_data always lives only in Postgres.

---

## Conflict Detection and Resolution

A conflict exists when two events for the same user overlap in time and both require the user's active attention.

The resolution process happens inside the master agent before the daily plan is built:

Step 1 — Find overlaps. Query Postgres for all active events for the user for today. Find any pairs where the time ranges intersect.

Step 2 — Score each event. Use the priority field. If priorities are equal, prefer the source with higher base priority from the priority table.

Step 3 — Declare winner and loser. The higher-scoring event is the winner. The lower-scoring event is the loser.

Step 4 — Log the conflict. Write a record to the conflict log table with the winner's row_id, the loser's row_id, the reason, and the action taken. This record is permanent and never deleted.

Step 5 — Update the loser's status. In Postgres, change the loser's status field from active to rescheduled. Do NOT delete the loser event. It must remain in the database as a historical fact.

Step 6 — Re-embed the loser. Generate a new text_summary for the loser that includes a note saying it was rescheduled and which source overrode it. Delete the old vector from the Vector DB. Insert a new vector with the updated summary and updated metadata (status: rescheduled).

Step 7 — Include both in the plan. The daily plan shows the winner at its original time. The loser appears in the plan under a "needs rescheduling" section, not deleted, not hidden.

The reason we re-embed the loser is that its meaning has changed. If someone later searches "what meetings got moved today," the re-embedded vector will surface it. The old embedding would not.

---

## Master Agent

The master agent runs once per day per user. It can also be triggered on demand.

Its job is to read everything, resolve conflicts, and produce a daily plan.

Here is its full process:

Step 1 — Trigger all sub-agents for the user. Each sub-agent fetches fresh data and dual-writes to both databases.

Step 2 — Semantic search in the Vector DB. Search for the top 20 to 30 most relevant events for today, filtered strictly by user_id and ttl_expires greater than now. The query can be something like "today's schedule, tasks, health, and work."

Step 3 — Fetch exact data. For every row_id returned from the Vector DB, fetch the corresponding full row from Postgres to get all the exact_data fields.

Step 4 — Merge context. Combine the semantic search results with the exact Postgres data into a single structured context object. Group it by category: meetings, tasks, health, coding, and journal.

Step 5 — Run conflict resolution. Check all active events for time overlaps. Resolve using the process described above. Update both databases.

Step 6 — Build the prompt. Inject the full merged context into the master agent prompt. The prompt should instruct the LLM to produce a structured daily plan with these sections: time-blocked schedule for the day, task list with priorities, health reminders every 90 minutes during work hours, coding suggestions for free slots, and a conflict resolution summary.

Step 7 — Call the LLM. Send the prompt and receive structured output.

Step 8 — Save the daily plan. Store the plan in the daily_plans table in Postgres keyed by user_id and today's date.

Step 9 — Deliver the plan. Push to the frontend or send notifications as needed.

---

## Multi-User Isolation Rules

These rules must be enforced everywhere without exception:

Rule 1 — Every Postgres query must filter by user_id. No query should ever return data without a user_id condition.

Rule 2 — Every Vector DB query must include a metadata filter on user_id. Never run an unfiltered semantic search.

Rule 3 — The row_id always includes the user_id as a suffix. This prevents any accidental ID collision between users.

Rule 4 — The master agent is instantiated separately per user. It never has access to another user's context object.

Rule 5 — Daily plans are stored per user_id and date. The combination must be unique. No shared plan records.

Rule 6 — The conflict log is per user. A conflict resolution for user A never touches user B's data.

---

## TTL and Data Expiry (7-Day Rolling Window)

Every event written to either database has a ttl_expires timestamp set to exactly 7 days after its created_at time.

For Postgres: run a cleanup job every night at 2am that deletes all rows from the events table where ttl_expires is less than the current time. Do the same for the conflict_log and daily_plans tables if you want to keep those lean too (optional — conflict_log can be kept longer for audit purposes).

For the Vector DB: run the same nightly job and delete all vectors where the ttl_expires metadata field is less than the current Unix timestamp.

The conflict_log table is the only table you may choose not to auto-expire, since it serves as a permanent audit trail of what decisions were made.

---

## Database Tables to Create

**events table**
Stores all raw canonical events from all sources. Fields: row_id (primary key), user_id, source, event_type, status, priority, start_time, end_time, exact_data (as JSON), text_summary, created_at, ttl_expires.
Add indexes on: user_id + start_time (for day queries), and ttl_expires (for cleanup queries).

**conflict_log table**
Stores one record per resolved conflict. Fields: id (auto increment), user_id, winner_row_id, loser_row_id, reason, action, resolved_at.
Never delete from this table automatically.

**daily_plans table**
Stores one plan per user per day. Fields: id (auto increment), user_id, plan_date, plan_json (full plan as JSON), created_at.
Unique constraint on user_id + plan_date.

---

## Vector DB Collection

One collection called user_contexts.

Each record in the collection has:
- The vector embedding of the text_summary
- Metadata fields: user_id, source, event_type, priority, start_time (as Unix timestamp), ttl_expires (as Unix timestamp), row_id

Create payload indexes on user_id (keyword type) and ttl_expires (float/numeric type) for fast filtered searches.

Do not create separate collections per user. One shared collection with user_id filtering is the correct approach.

---

## Build Order

Build in this exact sequence. Each step depends on the previous one.

1. Create the three Postgres tables with correct indexes.
2. Set up the Vector DB collection with payload indexes.
3. Build the embedder utility — a single function that takes a string and returns a vector. Test it works.
4. Build the normalizer — a function per source that converts raw API data into the canonical format. Test each one with sample data.
5. Build the dual write function — takes a canonical event, writes to Postgres, generates embedding, writes to Vector DB. Test that both writes happen and both can be queried.
6. Build the Strava sub-agent using the template. Test end to end.
7. Build the Google Calendar sub-agent. Test end to end.
8. Build the Slack sub-agent with urgency keyword detection. Test priority scoring.
9. Build the GitHub sub-agent. Test end to end.
10. Build the remaining sub-agents: LeetCode, Google Fit, Journal, Tasks. Test each.
11. Build the conflict resolver. Test it with two overlapping Calendar and Slack events. Verify the loser is rescheduled in both databases and the conflict_log has a record.
12. Build the master agent. Test it for a single user and verify the daily plan output contains all sections.
13. Add user_id filtering everywhere. Test with two users who have overlapping data. Verify complete isolation.
14. Build the nightly TTL cleanup job. Test by setting a short TTL and verifying records are deleted from both databases.
15. Wire up the daily trigger scheduler to run the master agent at 6am per user.

---

## What the Daily Plan Looks Like

The output of the master agent for each user should be a structured object with these sections:

- Time blocks: a list of events placed on the calendar for the day, each with a time, title, type, source, priority, and any notes. Conflicts are already resolved here.
- Task list: all tasks due today or overdue, sorted by priority.
- Health reminders: timed reminders throughout the day (drink water, stretch, eat) based on health data and gaps in the schedule.
- Coding suggestions: recommended GitHub commits or LeetCode problems to tackle during free time slots, based on recent activity and streak data.
- Conflict summary: a plain-English explanation of any conflicts that were resolved, who won and why, and what happened to the displaced event.
- Suggestions: anything else the agent recommends based on patterns in the data.

---

## Key Rules to Never Break

- Never delete a raw event record. Only change its status field.
- Never store exact numbers in the Vector DB. They go in Postgres only.
- Never query the Vector DB without a user_id filter.
- Always write to both databases together. Never one without the other.
- Always re-embed when meaning changes. If status or summary changes, delete the old vector and insert a new one.
- The conflict_log is append-only. Never update or delete its records.
- row_id is the link between the two databases. Always include it in Vector DB metadata.
