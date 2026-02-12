# NUMA - Intelligent Agent for Productivity & Health

An AI-powered web application that intelligently tracks, analyzes, and optimizes productivity and health through autonomous agents and the Model Context Protocol (MCP).

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Usage](#usage)
- [Future Enhancements](#future-enhancements)
- [Contributors](#contributors)
- [License](#license)

---

## Overview

**NUMA** (powered by Antigravity AI) is a next-generation productivity, health, and wellbeing platform designed around explainable, safe, and user-centric decision making. Unlike traditional trackers, NUMA uses autonomous AI agents that understand user habits, predict patterns, and proactively assist in achieving personal and professional goals while maintaining strict privacy and data protection standards.

### Problem Statement

In today's fast-paced world, individuals struggle to balance productivity with health and well-being. Existing tracking solutions operate in silos, lack intelligent insights, and require significant manual effort. There is a need for an integrated system that autonomously monitors, analyzes, and provides actionable recommendations while respecting user privacy and maintaining full explainability.

### Proposed Solution

NUMA addresses these challenges by implementing:

- **Autonomous AI Agents** that handle specialized tasks without constant user intervention
- **Model Context Protocol (MCP)** for seamless integration and communication between AI components
- **Unified Dashboard** that consolidates productivity and health metrics in one interface
- **Privacy-First Architecture** where AI agents read only aggregated data, never raw user inputs
- **Explainable AI** with every recommendation traceable to aggregate metrics

---

## Key Features

### Core Design Principles

- **Privacy-First Architecture**: AI agents never read raw user inputs, only aggregated data
- **Explainable AI**: Every recommendation is traceable to aggregate metrics
- **User Control**: Users maintain full control over their data and AI autonomy levels
- **Immutable Data**: Raw inputs are never modified once stored
- **Auditable Decisions**: All AI decisions are fully auditable and transparent

### AI Agent Framework

| Agent                        | Responsibility                                                                        |
| ---------------------------- | ------------------------------------------------------------------------------------- |
| **Productivity Agent**       | Monitors work patterns, suggests optimal schedules, and automates task prioritization |
| **Health Agent**             | Tracks health metrics, provides wellness recommendations, and sends timely reminders  |
| **Analytics Agent**          | Generates intelligent reports and predictive insights based on collected data         |
| **Personal Assistant Agent** | Handles natural language queries and provides conversational interactions             |

### AI Framework Architecture

**Model Context Protocol (MCP)**

- Seamless communication between AI agents and external tools
- Extensible architecture for connecting to third-party services
- Real-time context sharing across all system components
- Standardized protocol for AI tool orchestration

**LangChain & LangGraph**

- Advanced agentic workflow orchestration and state management
- Multi-agent collaboration and task delegation
- Memory systems for context-aware conversations
- Custom tool integration and function calling
- Graph-based execution flows for complex agent behaviors

### AI and LLM Infrastructure

- **Cloud LLM Providers**: Groq API, Google Gemini API for fast inference
- **Local LLMs**: Qwen 7B and Mistral 7B models via Ollama for offline/private processing
- **Agentic Frameworks**: LangChain for agent orchestration, LangGraph for stateful workflows
- **RAG Pipeline**: Retrieval-Augmented Generation for context-aware responses

### Product Integrations

NUMA seamlessly connects with your favorite productivity and health tools:

| Product             | Integration Purpose   | Features                                                  |
| ------------------- | --------------------- | --------------------------------------------------------- |
| **Google Calendar** | Schedule optimization | Event syncing, conflict detection, smart scheduling       |
| **Google Fit**      | Health data tracking  | Activity metrics, step counts, workout data               |
| **Google Docs**     | Documentation & notes | Journal entries, report generation, note syncing          |
| **Strava**          | Fitness tracking      | Workout analysis, performance metrics, activity logs      |
| **Slack**           | Team communication    | Status updates, notifications, team productivity insights |
| **LeetCode**        | Coding progress       | Problem-solving tracking, skill development monitoring    |
| **GitHub**          | Development activity  | Commit tracking, project progress, contribution analytics |

All integrations respect NUMA's privacy-first architecture, with data aggregated before AI analysis.

### Data Architecture

- **Raw Inputs**: User-entered or device-synced data representing subjective state and intent
- **Aggregated Data**: Computed trends, ratios, and baselines accessible to AI agents
- **AI Decision Layer**: Reads only aggregated data to produce recommendations and alerts

### Productivity Tracking

- Energy-based task prioritization matching task difficulty to user capacity
- Dependency-aware task scheduling and management
- Calendar optimization with conflict resolution
- Goal progress tracking with alignment maintenance
- Routine optimization based on completion patterns

### Health and Wellbeing Monitoring

- **Physical Health**: Sleep tracking, activity monitoring, workout logging, fatigue detection
- **Mental Health**: Mood tracking, stress assessment, anxiety monitoring, cognitive load management
- **Recovery**: Sleep debt calculation, burnout prevention, recovery scheduling
- **Smartwatch Integration**: Real-time health data syncing and analysis

### Intelligent Analytics

- AI-powered insights based on aggregated metrics only
- Trend analysis with 7-day and 30-day rolling windows
- Risk detection for burnout and overload
- Personalized baseline establishment for individualized recommendations
- Explainable recommendations with full metric traceability

---

## System Architecture

```
+---------------------------------------------------------------------+
|                           CLIENT LAYER                               |
|                    (React/Next.js Web Application)                   |
+---------------------------------------------------------------------+
                                    |
                                    v
+---------------------------------------------------------------------+
|                           API GATEWAY                                |
|                    (RESTful API / WebSocket)                         |
+---------------------------------------------------------------------+
                                    |
                                    v
+---------------------------------------------------------------------+
|                         BACKEND SERVICES                             |
|  +----------------+  +----------------+  +----------------------+    |
|  | Authentication |  |  API Handlers  |  | Data Access Layer    |   |
|  |    Service     |  |                |  |     (MongoDB)        |   |
|  +----------------+  +----------------+  +----------------------+    |
+---------------------------------------------------------------------+
                                    |
                                    v
+---------------------------------------------------------------------+
|                     MODEL CONTEXT PROTOCOL LAYER                     |
|  +---------------------------------------------------------------+  |
|  |                      MCP Server                                |  |
|  |         (Tool Orchestration & Context Management)              |  |
|  +---------------------------------------------------------------+  |
+---------------------------------------------------------------------+
                                    |
                                    v
+---------------------------------------------------------------------+
|                          AI AGENT LAYER                              |
|  +--------------+ +--------------+ +--------------+ +------------+  |
|  | Productivity | |    Health    |  |  Analytics  | |  Personal  |  |
|  |    Agent     | |    Agent     |  |    Agent    | |  Assistant |  |
|  +--------------+ +--------------+ +--------------+ +------------+  |
+---------------------------------------------------------------------+
```

---

## Technology Stack

| Layer              | Technologies                                                |
| ------------------ | ----------------------------------------------------------- |
| **Frontend**       | Next.js 16, React 19, TypeScript, Tailwind CSS 4, shadcn/ui |
| **Backend**        | Python, FastAPI, Uvicorn                                    |
| **Database**       | MongoDB, Redis (Caching)                                    |
| **AI/ML**          | LangChain, LangGraph, RAG                                   |
| **LLM Providers**  | Groq API, Google Gemini API                                 |
| **Local LLMs**     | Ollama (Qwen 7B, Mistral 7B)                                |
| **MCP**            | Model Context Protocol SDK                                  |
| **Integrations**   | Google Calendar, Google Fit, Google Docs, Strava, Slack, LeetCode, GitHub |
| **Authentication** | JWT, OAuth 2.0                                              |
| **DevOps**         | Docker, Git, CI/CD Pipelines                                |

---

## Installation

### Prerequisites

- Node.js v18.0 or higher
- Python 3.10 or higher
- MongoDB 6.0 or higher
- npm or yarn package manager

### Setup Instructions

1. **Clone the Repository**

   ```bash
   git clone https://github.com/Vinay-R-S/Numa.git
   cd Numa
   ```

2. **Install Client Dependencies**

   ```bash
   cd client
   npm install
   ```

3. **Install Server Dependencies**

   ```bash
   cd ../server
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**

   ```bash
   cp .env.example .env
   ```

   Update the `.env` file with the required API keys and database connection strings.

5. **Start Development Servers**

   ```bash
   # Terminal 1 - Client (Frontend)
   cd client && npm run dev

   # Terminal 2 - Server (Backend)
   cd server
   .venv\Scripts\activate
   uvicorn main:app --reload
   ```

6. **Access the Application**

   Open a browser and navigate to `http://localhost:3000`

---

## Project Structure

```
numa/
├── client/                   # Next.js frontend application
│   ├── src/
│   │   ├── app/             # App router pages and layouts
│   │   │   ├── globals.css  # Global styles with Tailwind
│   │   │   ├── layout.tsx   # Root layout component
│   │   │   └── page.tsx     # Home page
│   │   └── lib/             # Utilities (shadcn cn helper)
│   ├── public/              # Static assets
│   ├── components.json      # shadcn/ui configuration
│   ├── tailwind.config.ts   # Tailwind configuration
│   └── package.json
├── server/                   # FastAPI backend server
│   ├── routers/             # API route definitions
│   ├── models/              # Pydantic models and schemas
│   ├── services/            # Business logic layer
│   ├── main.py              # FastAPI application entry
│   └── requirements.txt     # Python dependencies
├── docs/                     # Project documentation
│   ├── markdown.md          # Antigravity AI technical specification
│   └── Features.pdf         # Feature documentation
└── README.md
```

---

## Usage

### Dashboard Overview

Upon logging in, users are presented with a unified dashboard displaying:

- Task summary and priority items
- Health metrics and daily goals
- AI-generated insights and recommendations
- Quick action buttons for common operations

### Interacting with AI Agents

Users can interact with agents through:

- Natural language commands via the chat interface
- Automated scheduled tasks and reminders
- Context-aware suggestions based on current activity

### Backend API

The backend server exposes the following endpoints:

- **Health Check**: `GET /health`
  - Returns the status of the server.
  - URL: `http://localhost:8000/health`
  - Response: `{"status": "ok"}`

- **Root**: `GET /`
  - Returns a welcome message.
  - URL: `http://localhost:8000/`

---

## Future Enhancements

- Mobile application development (iOS and Android)
- Wearable device integration for real-time health monitoring
- Advanced machine learning models for improved predictions
- Social features for team productivity tracking
- Integration with popular productivity tools (Notion, Trello, etc.)

---

## Contributors

| Name            | Role      | Contact             |
| --------------- | --------- | ------------------- |
| [Your Name]     | Developer | [email@example.com] |
| [Team Member 2] | Developer | [email@example.com] |
| [Team Member 3] | Developer | [email@example.com] |

**Institution**: [Your College/University Name]  
**Course**: 6th Semester Mini Project  
**Academic Year**: 2025-2026

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- OpenAI for providing the GPT API infrastructure
- Anthropic for the Model Context Protocol specification
- The open-source community for various libraries and tools used in this project

---

_For detailed documentation, refer to the [docs](./docs) folder._
