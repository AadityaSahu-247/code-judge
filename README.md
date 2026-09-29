# CodeJudge — AI-Assisted Online Judge & Learning System

CodeJudge is an enterprise-grade, full-stack automated code grading, sandboxed execution, and AI-assisted learning platform. It allows students to solve programming problems in a secure sandbox, receive real-time execution results, get automated qualitative AI feedback on code style and efficiency, post programming doubts, and receive teacher-reviewed AI-generated answers.

---

## Table of Contents
1. [Key Features & Modules](#key-features--modules)
2. [Architecture Overview](#architecture-overview)
3. [Tech Stack](#tech-stack)
4. [Security & Sandboxing Architecture](#security--sandboxing-architecture)
5. [Directory Structure](#directory-structure)
6. [Prerequisites](#prerequisites)
7. [Installation & Setup Guide](#installation--setup-guide)
   - [1. Infrastructure (Docker & Databases)](#1-infrastructure-docker--databases)
   - [2. Backend Setup](#2-backend-setup)
   - [3. Frontend Setup](#3-frontend-setup)
8. [Environment Variables](#environment-variables)
9. [Running Tests](#running-tests)
10. [API Documentation](#api-documentation)

---

## Key Features & Modules

### 1. Code Submission & History (Module 1)
- Multi-language code submission support (Python, JavaScript, etc.).
- Real-time submission tracking and execution status.
- Comprehensive submission history per student and problem.

### 2. Code Execution & Sandboxed Grading (Module 2)
- **Isolated Execution**: Every submission executes inside a dedicated, ephemeral Docker container.
- **Resource Enforcement**: Container limits for memory, CPU allocation, process IDs (PID limit), read-only filesystems, and strict network isolation (`--network none`).
- Automated test-case execution comparing stdout with expected outputs, computing execution runtime and memory usage.

### 3. AI Code Feedback (Module 3)
- Asynchronous qualitative evaluation using **Gemini 2.5 Flash** (via LangChain).
- Feedback structure includes:
  - **Readability & Style**
  - **Time & Space Complexity Analysis**
  - **Best Practice Recommendations**
  - **Optimization Suggestions**

### 4. Community Doubt Board (Module 4)
- Interactive Q&A discussion board for students to post doubts regarding specific problems or general concepts.
- Code snippet embedding and problem linking.

### 5. Asynchronous AI Answer Drafting (Module 5)
- Automated AI draft answer generation triggered upon doubt creation via **ARQ background workers**.
- Structured AI drafting engineered with strict safety and content filtering.

### 6. Teacher Review Workflow (Module 6)
- **Human-in-the-Loop AI Governance**: AI-generated doubt answers transition through a strict approval lifecycle:
  `DRAFT` ➔ `PENDING_REVIEW` ➔ `APPROVED` / `REJECTED`.
- Teachers can review, edit, approve, or reject draft answers from a dedicated Teacher Review Dashboard.
- Only teacher-approved answers are visible on the public doubt board.

### 7. Analytics & Notifications
- Analytics dashboard tracking submission pass rates, language distributions, and common error patterns.
- Real-time user notifications for review approvals and feedback ready state.

---

## Architecture Overview

```
                        +----------------------+
                        |   Frontend (React)   |
                        +----------+-----------+
                                   |
                                   v
                        +----------------------+
                        |   FastAPI Backend    |
                        +-----+----------+-----+
                              |          |
               +--------------+          +--------------+
               |                                        |
               v                                        v
     +-------------------+                    +-------------------+
     | PostgreSQL (Data) |                    |   Redis Queue     |
     +-------------------+                    +---------+---------+
                                                        |
                                                        v
                                              +-------------------+
                                              | ARQ Worker Process|
                                              +----+--------+-----+
                                                   |        |
                         +-------------------------+        +--------------------------+
                         |                                                             |
                         v                                                             v
              +--------------------+                                       +------------------------+
              | Docker Engine      |                                       | Google Gemini AI       |
              | (Isolated Sandbox) |                                       | (LangChain Integration)|
              +--------------------+                                       +------------------------+
```

---

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.10+)
- **ORM & Database**: SQLAlchemy 2.0, PostgreSQL 16, Alembic (Database Migrations)
- **Task Queue & Async Processing**: ARQ, Redis 7
- **Authentication & Security**: PyJWT (JWT bearer tokens), Passlib/Bcrypt password hashing
- **Validation**: Pydantic v2 & Pydantic-Settings

### AI & LLM Engine
- **Provider**: Google Gemini 2.5 Flash via Google AI Studio API
- **Framework**: LangChain (`langchain-google-genai`, `langchain-core`)

### Execution Sandbox
- **Engine**: Docker Engine / Docker-in-Docker SDK
- **Security Protocols**: Non-root user, `--network none`, `--read-only`, cgroup resource constraints

### Frontend
- **Framework**: React 18, TypeScript, Vite
- **Styling**: Tailwind CSS
- **Code Editor**: Monaco Editor (`@monaco-editor/react`)

---

## Security & Sandboxing Architecture

1. **Docker Container Hardening**:
   - Network isolation (`--network none`).
   - Hard memory limit (e.g., 256MB) & CPU quotas (e.g., 0.5 CPU cores).
   - PID limiting (`--pids-limit 64`) to prevent fork-bomb attacks.
   - Non-root user execution inside container.
   - Transient `tmpfs` mounts for write operations; base root filesystem is read-only.
2. **Prompt Injection Defense**:
   - User inputs (code snippets, doubt queries) are enclosed within explicit delimiter tags in LLM prompts.
   - System prompts enforce output schemas (JSON mode) and treat user inputs strictly as passive data rather than executable instructions.
   - Zero LLM tool execution capabilities—models can only output raw text/JSON payloads.
3. **API Rate Limiting & Validation**:
   - Sliding-window rate limiting per endpoint bucket (submissions, doubts, authentication).
   - Input sanitization against script tags and payload overload.

---

## Directory Structure

```
.
├── Architecture.md           # Architectural specification document
├── prd.md                    # Product Requirements Document
├── phase.md                  # Development phase roadmap
├── docker-compose.yml        # Development infrastructure (Postgres & Redis)
├── pytest.ini                # Pytest configuration
├── backend/
│   ├── alembic/              # Database migration scripts
│   ├── app/
│   │   ├── main.py           # FastAPI entrypoint & router initialization
│   │   ├── config.py         # Application settings via Pydantic
│   │   ├── database.py       # SQLAlchemy engine & session setup
│   │   ├── models.py         # DB models (Users, Problems, Submissions, Doubts, etc.)
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── security.py       # Password hashing & JWT generation
│   │   ├── deps.py           # Dependency injection (Auth, DB session)
│   │   ├── ratelimit.py      # Rate limiting logic
│   │   ├── sanitize.py       # Input sanitization helper
│   │   ├── logging_config.py # Structured logging configuration
│   │   ├── routers/          # API Route handlers
│   │   ├── services/         # Business logic (Sandbox, AI service, etc.)
│   │   └── jobs/             # ARQ background worker tasks
│   ├── seed_db.py            # Database seeder script
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── src/                  # React components, pages, and API clients
│   ├── package.json          # Node dependencies
│   └── vite.config.ts        # Vite build configuration
├── sandbox/                  # Dockerfiles and run scripts for sandbox containers
└── tests/                    # Unit, integration, e2e, and performance tests
```

---

## Prerequisites

- **Docker Desktop** (or Docker Engine with Docker Compose)
- **Python 3.10+**
- **Node.js 18+** & `npm`
- **Google Gemini API Key** (Get one from [Google AI Studio](https://aistudio.google.com/))

---

## Installation & Setup Guide

### 1. Infrastructure (Docker & Databases)

Start PostgreSQL and Redis services using Docker Compose:

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL**: `localhost:5433` (DB: `codejudge`, User: `codejudge`, Pass: `codejudge`)
- **Redis**: `localhost:6379`

### 2. Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**:
   - **Linux/macOS**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. **Install backend dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and update key parameters (specifically `GEMINI_API_KEY`):
   ```bash
   cp .env.example .env
   ```

5. **Run Database Migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Seed Initial Database Data** (optional but recommended):
   ```bash
   python seed_db.py
   ```

7. **Start the API Server**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

8. **Start the ARQ Background Worker** (in a separate terminal window):
   ```bash
   arq app.jobs.worker.WorkerSettings
   ```

### 3. Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install Node dependencies**:
   ```bash
   npm install
   ```

3. **Start the Development Server**:
   ```bash
   npm run dev
   ```
   The frontend will be accessible at `http://localhost:5173`.

---

## Environment Variables

Key backend environment variables configured in `backend/.env`:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PROJECT_NAME` | `CodeJudge` | Application Name |
| `DATABASE_URL` | `postgresql://codejudge:codejudge@localhost:5433/codejudge` | PostgreSQL Connection URI |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis Connection URI |
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Secret key for signing JWT tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | JWT Token expiration (in minutes) |
| `GEMINI_API_KEY` | `your-gemini-api-key-here` | Google AI Studio API Key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini LLM model identifier |
| `DOCKER_SANDBOX_MEMORY_MB` | `256` | Sandbox container memory limit |
| `DOCKER_SANDBOX_CPU_QUOTA` | `0.5` | Sandbox CPU limit |

---

## Running Tests

The repository contains unit, integration, end-to-end, and performance tests built with `pytest`.

To execute all tests from the project root:

```bash
pytest
```

To run a specific test suite:
```bash
# Unit tests
pytest tests/unit

# Integration tests
pytest tests/integration

# End-to-End tests
pytest tests/e2e
```

---

## API Documentation

Once the backend server is running, interactive API documentation is available at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
