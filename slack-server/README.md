# 🤖 Slack Control Agent

> A deterministic, production-ready Slack automation backend powered by FastAPI, Groq (Llama 3), and the official Slack SDK.

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.10+-yellow.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)

## 📖 Overview

This project is a high-performance backend for controlling a Slack workspace via natural language. Unlike traditional "agents" that loop and hallucinate, this system uses a **Deterministic Router** architecture.

1.  **Intent Parsing**: A single LLM call maps natural language -> Structured JSON.
2.  **Deterministic Execution**: Python logic resolves Channel/User IDs via exact lookup (No guessing).
3.  **Direct Action**: The Slack SDK executes the command immediately.

**Key Benefits:**
-   🚀 **Fast**: Actions take ~1 second.
-   🔒 **Safe**: 0% hallucination rate for IDs.
-   💰 **Cheap**: 1 LLM call per request.

## ✨ Features

-   **Messaging**: Send DMs, post to channels, reply to threads.
-   **Channel Management**: Create, Rename, Archive, List.
-   **User Management**: Invite, Kick (Remove), List users.
-   **Reactions**: Add/Remove emojis (Smart mapping: `thumbs_up` -> `:+1:`).
-   **Files**: Upload files/snippets.
-   **Scheduling**: Schedule messages for future delivery.
-   **Smart Context**: Auto-fetches the latest message if you ask to "react to the last message".

## 🏗 Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for a deep dive.

## 🛠 Tech Stack

-   **Framework**: FastAPI
-   **LLM**: Groq (Llama-3.1-8b-instant)
-   **Integration**: Slack SDK (Official)
-   **Validation**: Pydantic

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/slack-control-agent.git
cd slack-control-agent
```

### 2. Set up Virtual Environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configuration
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Update it with your credentials:
```ini
GROQ_API_KEY=gsk_...
SLACK_BOT_TOKEN=xoxb-...
LOG_LEVEL=INFO
```

### 5. Slack App Setup
Your Slack Bot needs the following **Bot Token Scopes** under "OAuth & Permissions":
-   `channels:read`, `channels:manage`, `channels:history`
-   `groups:read`, `groups:history`
-   `im:read`, `im:history`, `im:write`
-   `users:read`
-   `chat:write`
-   `files:write`
-   `reactions:write`

**Don't forget to 'Reinstall to Workspace' after adding scopes!**

## 🏃 Running the Application

### Local Development

1. **Activate Virtual Environment:**
   ```bash
   # Windows
   venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   ```

2. **Start the API Server:**
   ```bash
   uvicorn app.main:app --reload --port 9000
   ```
   The server will start at `http://localhost:9000`.

### 🖥️ CLI Chat Tool

A built-in interactive CLI tool is included for easy testing without Postman.

1. **Ensure the server is running** (in a separate terminal).
2. **Activate Virtual Environment** (if not already active).
3. **Run the CLI:**
   ```bash
   python cli_chat.py
   ```

**Example interaction:**
```
🤖 Slack Control Agent CLI
-----------------------------------
Type your instruction below. Type 'exit' or 'quit' to stop.

💡 Examples:
 - Send hello to #general
 - Create a channel called #project-alpha
 - Add thumbs_up reaction to last message in #general

You: send happy friday to #general
Agent: (Thinking...)
Agent: Message sent to general
```

## 🐳 Docker Support

Build and run with Docker:
```bash
docker build -t slack-agent .
docker run -p 9000:9000 --env-file .env slack-agent
```

## 📚 Usage Examples

**Send a Message:**
```json
POST /chat
{
  "message": "Send hello team to #general"
}
```

**Create a Channel:**
```json
POST /chat
{
  "message": "Create a channel called #project-alpha"
}
```

**Add Reaction:**
```json
POST /chat
{
  "message": "Add a check reaction to the last message in #general"
}
```

## 📂 Project Structure

```
slack-control-agent/
├── app/
│   ├── main.py          # FastAPI Entry Point
│   ├── config.py        # Settings & Env handling
│   ├── intent_parser.py # LLM Logic (LangChain + Groq)
│   ├── slack_router.py  # Slack SDK Logic (The execution engine)
│   └── models.py        # Pydantic Schemas
├── cli_chat.py          # Interactive CLI for testing
├── requirements.txt     # Dependencies
├── .env.example         # Template for env vars
├── README.md            # You are here
├── ARCHITECTURE.md      # System design doc
└── WORKFLOW.md          # Step-by-step logic doc
```

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a Pull Request.

## 📄 License

MIT License.
