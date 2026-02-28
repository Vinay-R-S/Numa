# Slack Control Agent - System Architecture

## 🏗 High-Level Overview

The Slack Control Agent is a deterministic automation backend designed for speed, reliability, and zero hallucination. It uses a single-pass LLM call for intent classification and parameter extraction, followed by a deterministic Python router for executing actions via the Slack SDK.

```ascii
+-------------+      +-------------+      +-----------------+
|   Slack     | ---> |   FastAPI   | ---> |  Intent Parser  |
|  (User)     |      |   Backend   |      |  (Groq LLM)     |
+-------------+      +-------------+      +--------+--------+
                                                   |
                                                   v
+-------------+      +-------------+      +-----------------+
|  Slack API  | <--- | Slack Router| <--- | Structured JSON |
|  (Cloud)    |      | (Python)    |      | (Intent/Params) |
+-------------+      +-------------+      +-----------------+
```

## 🧩 Component Breakdown

### 1. FastAPI Backend (`app/main.py`)
- **Role**: Entry point for the application.
- **Function**: Receives HTTP POST requests, orchestrates the parsing and execution flow.
- **Endpoints**:
  - `POST /chat`: Main interaction endpoint.

### 2. Intent Parser (`app/intent_parser.py`)
- **Role**: The "Brain" of the operation.
- **Technology**: Groq (`llama-3.1-8b-instant`).
- **Function**:
  - Accepts natural language input.
  - Classifies proper user intent (e.g., `send_message`, `create_channel`).
  - Extracts parameters into a strict Pydantic schema (`app/models.py`).
  - **Constraints**: Single-pass, no retry loops, strict JSON output.

### 3. Slack Router (`app/slack_router.py`)
- **Role**: The "Hands" of the operation.
- **Technology**: Slack SDK (`WebClient`).
- **Function**:
  - Receives the structured intent.
  - **Deterministically** resolves channel/user names to IDs by querying the Slack API (no guessing).
  - Executes the corresponding Slack API method.
  - Handles API errors and specific logic (e.g., cleaning emoji names).

### 4. Data Models (`app/models.py`)
- **Role**: The Contract.
- **Function**: Defines strict types for Intents and Parameters using Pydantic, ensuring type safety across the application.

## 🔄 Data Flow

1.  **Input**: User sends "Send hello to #gen-z".
2.  **Parsing**:
    *   LLM receives prompt + schema.
    *   LLM outputs: `{"intent": "send_message", "parameters": {"channel_name": "gen-z", "text": "hello"}}`.
3.  **Routing**:
    *   Router receives the object.
    *   Router calls `list_channels` -> finds matches -> gets ID `C12345`.
    *   Router calls `chat.postMessage(channel="C12345", text="hello")`.
4.  **Output**: Returns `{"ok": true, "message": "Message sent..."}`.

## 🛡️ Error Handling Strategy

-   **Parsing Errors**: If the LLM fails to return valid JSON, the system defaults to an `unknown` intent with a helpful error message.
-   **Resolution Errors**: If a channel or user cannot be found, the system stops immediately and returns a clear "Not Found" error. It does **not** hallucinate IDs.
-   **API Errors**: Slack API errors (e.g., `missing_scope`, `invalid_name`) are caught, parsed, and returned as user-friendly error messages.

## ⚡ Performance & Security

-   **Deterministic Execution**: By resolving IDs via API lookup rather than LLM guessing, we eliminate "hallucinations" (sending messages to non-existent channels).
-   **Token Usage**: Extremely efficient. Only one LLM call per user request. No history, no scratchpad, no agent loop overhead.
-   **Security**:
    -   Slack Tokens are loaded from `.env`.
    -   No sensitive data is logged permanently (standard debug logs only).
    -   FastAPI handles input validation via Pydantic.
