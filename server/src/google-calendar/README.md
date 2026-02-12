# Google Calendar & Gmail Agent API

A FastAPI-based intelligent agent that uses LangChain and LangGraph to manage Google Calendar events and Gmail emails through natural language.

## Project Structure

```
├── app.py                    # FastAPI application
├── .env                      # Environment variables
├── gCalender_credentials.json # Google OAuth credentials
├── requirements.txt          # Python dependencies
├── agent/
│   ├── graph.py             # LangGraph state machine
│   ├── tools.py             # LangChain tools (calendar, email)
│   ├── state.py             # Agent state definition
│   └── llm.py               # LLM configuration
└── services/
    ├── google_auth.py       # Google OAuth handler
    ├── calendar_service.py  # Google Calendar API
    ├── gmail_service.py     # Gmail API
    └── datetime_parser.py   # Deterministic date parsing
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Edit `.env` and add your Groq API key:

```
TIMEZONE=Asia/Kolkata
GROQ_API_KEY=gsk_...
```

**Get your API Key here:** [Groq Console](https://console.groq.com/keys)

### 3. Set Up Google OAuth

To use Google Calendar and Gmail, you need `gCalender_credentials.json`:

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project.
3.  **Enable APIs:** Search for and enable **Google Calendar API** and **Gmail API**.
4.  **Configure OAuth Consent Screen:**
    *   Select **External**.
    *   Fill in required app information.
    *   Add your email as a **Test User**.
5.  **Create Credentials:**
    *   Go to **Credentials** > **Create Credentials** > **OAuth client ID**.
    *   Application type: **Desktop app**.
    *   Name it "Calendar Agent".
    *   Click **Create**.
6.  **Download JSON:**
    *   Download the JSON file.
    *   Rename it to `gCalender_credentials.json`.
    *   Place it in the root directory of this project.

On the first run, a browser window will open to authorize access. A `token.json` file will be created automatically.

### 4. Run the Server

```bash
python app.py
```

The server will start on `http://localhost:8000`

## Usage

### API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

### Send a Query

**Endpoint:** `POST /agent`

**Example Request:**

```bash
curl -X POST "http://localhost:8000/agent" \
  -H "Content-Type: application/json" \
  -d '{"query": "Schedule a team meeting tomorrow at 2pm"}'
```

**Example Response:**

```json
{
  "response": "✓ Event created successfully!\nTitle: Team Meeting\nStart: 2026-02-13T14:00:00+05:30\nLink: https://calendar.google.com/...",
  "success": true
}
```

## Available Tools

The agent can execute the following actions:

### 1. Schedule Calendar Event

**Natural language examples:**
- "Schedule a meeting tomorrow at 2pm titled 'Team Sync'"
- "Create a dentist appointment on Feb 20 at 10am"
- "Book a 2-hour workshop next Monday at 3pm"

**Tool:** `schedule_event`

### 2. Get Upcoming Events

**Natural language examples:**
- "What do I have today?"
- "Show my schedule for the next 3 days"
- "Any meetings tomorrow?"

**Tool:** `get_events`

### 3. Delete Event (Natural Language)

**Natural language examples:**
- "Cancel my gym tomorrow"
- "Remove the dentist appointment"
- "Delete meeting with Rahul"

**Tool:** `delete_by_text`

### 4. Send Email

**Natural language examples:**
- "Send an email to john@example.com with subject 'Meeting Reminder'"
- "Email the team about tomorrow's standup"

**Tool:** `send_gmail`

## How It Works

1.  **User Query** → FastAPI receives natural language request
2.  **LangGraph Agent** → Processes query and determines required actions
3.  **Tool Execution** → Calls Google Calendar/Gmail APIs
4.  **Response** → Returns formatted results to user

The agent uses:
-   **LangChain** for tool definitions and LLM integration
-   **LangGraph** for state machine orchestration
-   **Groq Llama 3.3 70B** for fast, high-performance inference
-   **Google APIs** for actual calendar/email operations

## Notes

-   **Timezone:** Configured via `TIMEZONE` in `.env` (default: Asia/Kolkata).
-   **OAuth:** First run requires browser authentication.
-   **Token Storage:** `token.json` stores credentials securely.
-   **Error Handling:** All tools include try-catch with user-friendly messages.
-   **LLM:** Uses Groq (requires `GROQ_API_KEY`).

## Security

-   Never commit `.env` or `token.json` to version control.
-   Keep `gCalender_credentials.json` secure (contains OAuth client secret).
-   Use environment variables for all sensitive data.

## Dependencies

-   **FastAPI** - Modern web framework
-   **LangChain** - LLM orchestration and tools
-   **LangGraph** - Agent state machine
-   **Groq** - High-performance LLM provider
-   **Google APIs** - Calendar and Gmail integration
