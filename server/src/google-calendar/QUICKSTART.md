# Quick Start Guide

Concise setup guide for running the Agentic AI Google Calendar Assistant locally.

---

## 1. Prerequisites

- Python 3.8+
- Groq API key ([console.groq.com](https://console.groq.com))
- Google Cloud project with **Calendar API** and **Gmail API** enabled
- Google Service Account JSON credentials file

---

## 2. Installation

```bash
git clone <repo-url>
cd AgenticAi-GoogleCalender

python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
```

---

## 3. Environment Variables

Create `.env` in the project root:

```env
GROQ_API_KEY=gsk_your_groq_api_key_here
TIMEZONE=Asia/Kolkata
GOOGLE_CREDENTIALS_FILE=gCalender_credentials.json
```

---

## 4. Google Service Account Setup

### Create the Service Account

1. Open [Google Cloud Console](https://console.cloud.google.com) > **APIs & Services > Credentials**
2. Click **Create Credentials > Service Account**
3. Name it (e.g. `calendar-agent`) and click **Done**

### Generate JSON Key

1. Click the service account > **Keys** tab
2. **Add Key > Create new key > JSON**
3. Rename the downloaded file to `gCalender_credentials.json`
4. Place it in the project root

### Share Calendar with Service Account

1. Open the JSON file and copy the `client_email` value
2. Open [Google Calendar](https://calendar.google.com)
3. Your calendar > three-dot menu > **Settings and sharing**
4. Under **Share with specific people or groups**, click **Add people and groups**
5. Paste the `client_email`
6. Set permission to **Make changes to events**
7. Click **Send**

> **Do NOT make your calendar public.** Share only with the service account email.

---

## 5. Running the Server

```bash
uvicorn app:app --reload
```

Server starts at `http://localhost:8000`.

---

## 6. Testing the API

### Swagger Docs

Open `http://localhost:8000/docs` in your browser.

### Example Request

```bash
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"query": "Schedule a team sync tomorrow at 3pm"}'
```

### Sample Queries

```
"What's on my calendar today?"
"Cancel my gym"
"Move my meeting to 5pm"
"When am I free tomorrow?"
"Email john@example.com about the report"
```

---

## 7. Common Failure Cases

| Issue | Cause | Fix |
|-------|-------|-----|
| `FileNotFoundError` on credentials | JSON file missing or misnamed | Ensure `gCalender_credentials.json` exists in project root |
| `403 insufficientPermissions` | Calendar not shared with service account | Share calendar with `client_email` and grant **Make changes to events** |
| `GROQ_API_KEY` errors | Missing or invalid key | Verify key in `.env` starts with `gsk_` |
| Wrong timezone on events | System misconfiguration | All times are hardcoded to `Asia/Kolkata` in `calendar_service.py` |
| Meet link not generated | Account lacks Meet access | Ensure Google account has Meet enabled |
