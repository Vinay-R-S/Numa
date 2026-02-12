# Quick Start Guide

## Prerequisites
- Python 3.8 or higher
- Groq API key (get from [Groq Console](https://console.groq.com/keys))
- Google Cloud project with Calendar & Gmail APIs enabled
- `gCalender_credentials.json` file from Google Cloud Console

## Installation Steps

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Edit `.env` and add your Groq API key:
```
GROQ_API_KEY=gsk_...
TIMEZONE=Asia/Kolkata
```

### 3. Run the application
```bash
python app.py
```

### 4. First-time OAuth Setup
- A browser window will open automatically
- Sign in with your Google account
- Grant permissions for Calendar and Gmail access
- The `token.json` file will be created for future use including the refreshing of the token.

### 5. Test the API
Visit: http://localhost:8000/docs

Or use curl:
```bash
curl -X POST "http://localhost:8000/agent" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"Schedule a test meeting tomorrow at 3pm\"}"
```

## Example Queries

**Calendar:**
- "Schedule a dentist appointment on Feb 15 at 10am"
- "Create a 2-hour meeting called 'Project Review' next Monday at 2pm"
- "Book a lunch meeting tomorrow at 1pm"
- "Show me my upcoming events"
- "Cancel the meeting with Rahul"

**Email:**
- "Send an email to john@example.com about the meeting"
- "Email team@company.com with subject 'Weekly Update'"

## Troubleshooting

**Groq API Error:**
- Make sure your `.env` file has a valid `GROQ_API_KEY`
- Get your API key from Groq Console (https://console.groq.com/keys)

**Google OAuth Error:**
- Ensure `gCalender_credentials.json` is present in the root directory
- Delete `token.json` and re-authenticate if you have permission issues
- Check that Calendar and Gmail APIs are enabled in Google Cloud Console

**Import Errors:**
- Run `pip install -r requirements.txt` again
- Make sure you're using Python 3.8+
