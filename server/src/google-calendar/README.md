# Agentic AI — Google Calendar Assistant

An intelligent calendar assistant powered by **Groq LLM**, **LangChain**, and **LangGraph**. It manages Google Calendar events and Gmail through natural language — scheduling, rescheduling, deletion, availability checks, and email — all via a single FastAPI endpoint.

---

## Features

- **Event Scheduling** — create events with natural language, with configurable duration and attendees
- **Automatic Google Meet Links** — every event gets a Meet link generated via `conferenceData`
- **Attendees Support** — pass email addresses to send calendar invitations
- **Reminders** — popup and email notifications 30 minutes before each event
- **Natural Language Deletion** — delete events by description with fuzzy, case-insensitive matching
- **Event Rescheduling** — modify event times in place without creating duplicates
- **Free Slot Finder** — deterministic availability reasoning across a configurable working window
- **Gmail Integration** — send emails through the Gmail API
- **Duplicate Prevention** — blocks same-title events within a 2-hour window
- **IST Timezone Enforcement** — all datetimes are force-localized to `Asia/Kolkata`

---

## Tech Stack

| Component           | Technology                        |
|---------------------|-----------------------------------|
| **LLM Provider**    | Groq (via `langchain-groq`)       |
| **Agent Framework** | LangChain + LangGraph             |
| **API Server**      | FastAPI + Uvicorn                  |
| **Calendar API**    | Google Calendar API v3             |
| **Email API**       | Gmail API                          |
| **Authentication**  | Google Service Account (JSON key)  |
| **Language**        | Python 3.8+                        |
| **Timezone**        | Asia/Kolkata (IST)                 |

---

## Project Structure

```
AgenticAi-GoogleCalender/
├── app.py                          # FastAPI server with /agent endpoint
├── agent/
│   ├── graph.py                    # LangGraph state machine + system prompt
│   └── tools.py                    # LangChain tool definitions (7 tools)
├── services/
│   ├── auth.py                     # Service account credential loader
│   ├── calendar_service.py         # Google Calendar API operations
│   └── gmail_service.py            # Gmail API operations
├── gCalender_credentials.json      # Service account key file (not committed)
├── requirements.txt
├── .env                            # Environment variables
├── QUICKSTART.md
└── README.md
```

---

## Environment Setup

### 1. Install Dependencies

```bash
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
```

### 2. Create `.env` File

Create a `.env` file in the project root:

```env
GROQ_API_KEY=gsk_your_groq_api_key_here
TIMEZONE=Asia/Kolkata
GOOGLE_CREDENTIALS_FILE=gCalender_credentials.json
```

Get your Groq API key from [console.groq.com](https://console.groq.com).

---

## Google Credentials Setup

This project uses a **Google Service Account** for authentication. There is no browser-based login flow.

### Step 1: Create a Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the **Google Calendar API** and **Gmail API** under **APIs & Services > Library**
4. Navigate to **APIs & Services > Credentials**
5. Click **Create Credentials > Service Account**
6. Enter a name (e.g. `calendar-agent`) and click **Done**

### Step 2: Generate JSON Key

1. Click on the newly created service account
2. Go to the **Keys** tab
3. Click **Add Key > Create new key > JSON**
4. Download the file
5. Rename it to `gCalender_credentials.json`
6. Place it in the project root directory

### Step 3: Share Your Calendar with the Service Account

1. Open the downloaded JSON file and locate the `client_email` field  
   (e.g. `calendar-agent@your-project.iam.gserviceaccount.com`)
2. Open [Google Calendar](https://calendar.google.com)
3. In the left sidebar, find your calendar > click the three-dot menu > **Settings and sharing**
4. Scroll to **Share with specific people or groups**
5. Click **Add people and groups**
6. Paste the `client_email` value
7. Set permission to **Make changes to events**
8. Click **Send**

> **WARNING:** Do NOT make your calendar public. Only share it directly with the service account email address using the steps above. Public calendars expose all event data to anyone.

---

## Running the Server

```bash
uvicorn app:app --reload
```

The server starts at `http://localhost:8000`.

| URL | Description |
|-----|-------------|
| `http://localhost:8000` | Health check |
| `http://localhost:8000/docs` | Swagger API documentation |
| `POST http://localhost:8000/agent` | Agent endpoint |

---

## API Usage

Send natural language queries to `POST /agent`:

```bash
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"query": "Schedule a team sync tomorrow at 3pm"}'
```

Response:

```json
{
  "response": "Event created successfully! ...",
  "success": true
}
```

### Example Queries

| Intent | Query |
|--------|-------|
| Schedule event | `"Schedule a meeting tomorrow at 3pm titled Team Sync"` |
| Schedule with attendees | `"Set up a call with john@example.com on Monday at 10am"` |
| View today's events | `"What's on my calendar today?"` |
| View upcoming week | `"Show my schedule for the next 7 days"` |
| Delete by description | `"Cancel my gym"` |
| Delete by description | `"Remove the dentist appointment"` |
| Reschedule event | `"Move my meeting to 5pm"` |
| Reschedule event | `"Postpone the gym to tomorrow at 7am"` |
| Check availability | `"When am I free tomorrow?"` |
| Find specific slot | `"Find me a 2-hour slot on Monday"` |
| Send email | `"Email john@example.com about the project update"` |

---

## Date and Time Behavior

- All datetimes are forced to **Asia/Kolkata (IST)** — no UTC conversion is performed
- The current IST date and time are injected into every LLM call as runtime context
- Relative dates are resolved deterministically:
  - `today` resolves to the current date from the server clock
  - `tomorrow` resolves to the current date + 1 day
- Supported input formats: ISO 8601, `YYYY-MM-DD HH:MM`, `todayT22:00:00`, `tomorrowT19:00`, and others
- Vague time references (e.g. `evening`, `morning`) cause the assistant to ask for a specific time
- The agent never invents or fabricates datetime values

---

## Architecture Overview

The agent is built as a **LangGraph state machine** with a cyclic tool-calling loop:

```
START --> call_model --+--> tool_calls? --> call_tools --> call_model --+
                       |                                               |
                       +--> no tool calls ----------------------> END <-+
```

### Execution Flow

1. User sends a query to `POST /agent`
2. `call_model` — Groq LLM processes the query with system prompt and bound tools
3. `should_continue` — routes to `call_tools` if tool calls are detected, otherwise ends
4. `call_tools` — validates required arguments, executes the tool, returns result
5. `call_model` — LLM reads the tool result and either responds or makes another call
6. Hard cap of **3 tool-call rounds** prevents infinite loops

### Tools

| Tool | Required Arguments | Description |
|------|--------------------|-------------|
| `schedule_event` | `title`, `datetime_str` | Create event with Meet link + reminders |
| `get_events` | `days` | List upcoming events |
| `delete_event` | `event_id` | Delete event by explicit ID |
| `delete_by_description` | `query` | Fuzzy-match delete by title |
| `modify_event` | `query`, `new_datetime_str` | Reschedule event by title match |
| `find_free_slots` | `date` | Find open time slots (08:00–22:00 IST) |
| `send_gmail` | `to`, `subject`, `body` | Send email via Gmail API |

---

## Troubleshooting

### `403 insufficientPermissions`

- Confirm **Google Calendar API** and **Gmail API** are enabled in your Cloud project
- Confirm the service account `client_email` has been shared with your calendar
- Confirm the permission level is **Make changes to events** (not view-only)

### Credentials file not found

- Ensure `gCalender_credentials.json` exists in the project root
- Verify `GOOGLE_CREDENTIALS_FILE` in `.env` matches the filename exactly

### `GROQ_API_KEY not set` or authentication errors

- Verify `.env` exists in the project root with a valid key
- Groq keys start with `gsk_`
- Check your quota at [console.groq.com](https://console.groq.com)

### Google Meet link not generated

- The Google account must have Meet enabled (personal Google accounts or Workspace)
- `conferenceDataVersion=1` is set automatically — no manual configuration needed

### Events created in wrong timezone

- All times are hardcoded to `Asia/Kolkata`
- If you need a different timezone, update `TIMEZONE_NAME` and `IST` in `services/calendar_service.py`

### Datetime parsing errors

- Use ISO 8601 format when possible: `2026-02-15T14:00:00`
- The system supports `todayT14:00:00` and `tomorrowT09:00:00` hybrid formats
- Avoid ambiguous formats like `02/03/2026` (month/day ordering is unclear)

### Agent returning repeated errors

- The agent has a hard cap of 3 tool-call rounds per request
- Check the server terminal for detailed error logs
- Restart the server: `uvicorn app:app --reload`
