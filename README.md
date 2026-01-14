# Persona - Intelligent Productivity and Health Tracker

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

**Persona** is a next-generation productivity and health tracking platform that leverages cutting-edge AI technologies to provide personalized insights, smart recommendations, and automated workflows. Unlike traditional trackers, Persona uses autonomous AI agents that understand user habits, predict patterns, and proactively assist in achieving personal and professional goals.

### Problem Statement

In today's fast-paced world, individuals struggle to balance productivity with health and well-being. Existing tracking solutions operate in silos, lack intelligent insights, and require significant manual effort. There is a need for an integrated system that autonomously monitors, analyzes, and provides actionable recommendations.

### Proposed Solution

Persona addresses these challenges by implementing:

- **Autonomous AI Agents** that handle specialized tasks without constant user intervention
- **Model Context Protocol (MCP)** for seamless integration and communication between AI components
- **Unified Dashboard** that consolidates productivity and health metrics in one interface

---

## Key Features

### AI Agent Framework

| Agent                        | Responsibility                                                                        |
| ---------------------------- | ------------------------------------------------------------------------------------- |
| **Productivity Agent**       | Monitors work patterns, suggests optimal schedules, and automates task prioritization |
| **Health Agent**             | Tracks health metrics, provides wellness recommendations, and sends timely reminders  |
| **Analytics Agent**          | Generates intelligent reports and predictive insights based on collected data         |
| **Personal Assistant Agent** | Handles natural language queries and provides conversational interactions             |

### Model Context Protocol (MCP) Integration

- Seamless communication between AI agents and external tools
- Extensible architecture for connecting to third-party services
- Real-time context sharing across all system components
- Standardized protocol for AI tool orchestration

### AI and LLM Infrastructure

- **Cloud LLM Providers**: Groq API, Google Gemini API for fast inference
- **Local LLMs**: Qwen 7B and Mistral 7B models via Ollama for offline/private processing
- **Agentic Frameworks**: LangChain and LangGraph for workflow orchestration
- **RAG Pipeline**: Retrieval-Augmented Generation for context-aware responses

### Productivity Tracking

- Task management with intelligent prioritization algorithms
- Automated time tracking with activity categorization
- Focus mode with distraction analysis
- Goal setting with progress visualization
- Habit tracking with streak maintenance and analytics

### Health Monitoring

- Activity and exercise logging with pattern recognition
- Sleep quality analysis and recommendations
- Stress level assessment through behavioral patterns
- Mood tracking with sentiment analysis
- Automated break reminders based on work intensity

### Intelligent Analytics

- AI-powered insights and personalized recommendations
- Trend analysis and behavioral pattern recognition
- Predictive analytics for goal achievement probability
- Customizable dashboards with exportable reports

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
   git clone https://github.com/Vinay-R-S/Persona.git
   cd Persona
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
persona/
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
