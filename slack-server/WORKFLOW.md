# Slack Control Agent - System Workflow

This document details the step-by-step lifecycle of a request within the Slack Control Agent system.

## 🌊 Request Lifecycle

### 1. Reception
- **Source**: `POST /chat`
- **Payload**: `{"message": "user input string"}`
- **Handler**: `app.main.chat`

### 2. Intent Classification (The "Brain")
- **Component**: `app.intent_parser.parse_intent`
- **Process**:
  1.  Constructs a prompt with the user query + strict system instructions.
  2.  Calls Groq (`llama-3.1-8b-instant`).
  3.  Forces output to match the `IntentResponse` Pydantic schema.
- **Outcome**: A structured object containing the `intent` (e.g., `add_reaction`) and `parameters` (e.g., `channel_name`, `reaction_name`).

### 3. Routing & Execution (The "Action")
- **Component**: `app.slack_router.router.execute`
- **Logic**: Switches based on the `intent` field.

#### A. ID Resolution Flow (Deterministic)
Before any action, names must be resolved to Slack IDs.
1.  **Channel Resolution**:
    -   Input: `channel_name` (e.g., "general")
    -   Action: `client.conversations_list(types="public_channel,private_channel")`
    -   Logic: Iterate through list -> match `name` exactly (case-insensitive).
    -   Result: Channel ID (e.g., `C123AB`) or `None`.
2.  **User Resolution**:
    -   Input: `user_name` (e.g., "alice")
    -   Action: `client.users_list()`
    -   Logic: Match against `name`, `real_name`, or `display_name`.
    -   Result: User ID (e.g., `U987XY`) or `None`.

**STOP CONDITION**: If resolution returns `None`, the process aborts immediately with a "Not Found" error.

#### B. Action Flows

**1. Send Message** (`send_message`)
- Verify `text`.
- Resolve Target (Channel or User).
- Call `chat.postMessage`.

**2. Create Channel** (`create_channel`)
- Call `conversations.create`.
- (Auto) Invite Bot to the new channel.

**3. Reaction Handling** (`add_reaction` / `remove_reaction`)
- Clean Emoji Name: Map `thumbs_up` -> `+1`, remove colons.
- Resolve Channel ID.
- **Timestamp Resolution**:
  - If `thread_ts` provided: Use it.
  - If NOT provided: Fetch channel history (`conversations.history`, limit=1) to get the latest message timestamp.
- Call `reactions.add` or `reactions.remove`.

**4. Scheduling** (`schedule_message`)
- Parse `post_at` (Unix Timestamp).
- Call `chat.scheduleMessage`.

### 4. Response Formation
- Standardized return format:
  ```json
  {
      "response": "Human readable success/error message",
      "intent": "classified_intent",
      "debug_info": { ...raw execution result... }
  }
  ```

## 🚨 Error Handling Flows

| Error Type | Trigger | System Response |
| :--- | :--- | :--- |
| **Parsing Error** | LLM outputs invalid JSON | Intent becomes `unknown`. User told "Could not understand." |
| **Resolution Error** | Channel/User not found | Abort. Return `"{target} not found"`. |
| **Slack API Error** | Token invalid / Scope missing | Catch `SlackApiError`. Return specific error details (e.g., "Missing Scope"). |
| **Validation Error** | Missing required param | Abort. Return `"Missing {param}"`. |

## 📊 Logging
- **INFO**: Incoming requests, parsed intents, execution results.
- **ERROR**: Exceptions, API failures.
