# Role-Based RAG Interviewer

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14%20App%20Router-black.svg?logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6%2B-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Store-orange.svg)](https://www.trychroma.com/)
[![Tests](https://img.shields.io/badge/Pytest-40%2F40%20Passing-brightgreen.svg?logo=pytest&logoColor=white)](https://pytest.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose%20Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An intelligent, resume-aware technical interview system powered by **Role-Specific Retrieval-Augmented Generation (RAG)**, automated multi-rubric evaluation, and persistent interview sessions.

---

## 🌐 Live Demo & Repository

- **Live Application:** [https://frontend-eight-green-24.vercel.app/](https://frontend-eight-green-24.vercel.app/)
- **GitHub Repository:** [https://github.com/Pranavsangichetty/role-based-rag-interviewer](https://github.com/Pranavsangichetty/role-based-rag-interviewer)
- **Architecture:** Decoupled deployment with the **Next.js frontend hosted on Vercel** communicating via client-side REST calls to the **FastAPI backend deployed on Render**.

---

## 📌 Overview

Automated technical assessments typically suffer from two major flaws:
1. **Generic, canned question banks** that fail to adapt to a candidate's specific seniority level, tech stack, and background.
2. **Hallucinated or ungrounded questions** that deviate from authoritative internal documentation or engineering rubrics.

**Role-Based RAG Interviewer** solves this by dynamically extracting candidate signals from PDF resumes (skills, tools, seniority level, domain exposure) and querying a role-partitioned vector store (`ChromaDB`). Questions are strictly grounded in reference engineering literature with exact page citations. Candidate answers are scored in real time across four rubric criteria (**Technical Accuracy, Completeness, Depth, Clarity**), concluding with a structured executive summary and hiring recommendation.

---

## 🚀 Key Features

- **Resume Parsing & Signal Extraction:** PDF extraction using `pypdf` with word-boundary matching and synonym resolution for modern technologies (`C++`, `C#`, `Next.js`, `CI/CD`, `PostgreSQL`, `Kubernetes`, `Sklearn`, `LLMs`, `RAGs`, `REST APIs`).
- **Role-Partitioned RAG Pipeline:** Multi-collection vector management (`kb_ai_ml_engineer`, `kb_backend_engineer`, `kb_data_scientist`, `kb_global`) using `Sentence-Transformers` (`all-MiniLM-L6-v2`) and ChromaDB with cosine similarity scoring.
- **Citation Grounding:** Enforces verified citations (`[source.pdf (p. X, chunk Y)]`) in all generated questions to eliminate LLM hallucinations.
- **Adaptive Difficulty & Context Tracking:** Scales question depth based on candidate seniority (`Junior`, `Mid-Level`, `Senior`, `Staff/Lead`) and tracks conversation history to generate dynamic follow-up questions.
- **Deterministic 5-Phase Fallback:** Full offline capability with deterministic question generation and rubric evaluation when no external LLM API key is configured.
- **4-Criterion Real-Time Scoring Rubric:** Evaluates responses on **Accuracy (40%)**, **Depth (30%)**, **Completeness (15%)**, and **Clarity (15%)** on a 1–10 scale with automated strengths, weaknesses, and ideal answers.
- **Session Continuity & Persistence:** Relational session and turn state management backed by **SQLAlchemy** and **SQLite**, allowing candidate sessions to be restored across browser refreshes.
- **Modern Next.js 14 UI:** App Router interface with live backend health monitoring, drag-and-drop resume upload, skill chip tags, progress bars, live scorecards, and executive reports.
- **100% Test Coverage:** 40 automated unit, API, database, and RAG integration tests passing in complete test isolation.
- **Containerized Deployment:** Production-ready multi-stage Dockerfiles and `docker-compose.yml` for unified local and staging environments.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Client["Frontend (Next.js 14 on Vercel)"]
        UI["Interactive UI / Console"]
        Setup["Candidate Setup & Resume Upload"]
        Interview["Live Interview Console"]
        Summary["Executive Report & Scorecards"]
    end

    subgraph Backend["Backend (FastAPI on Render)"]
        API["FastAPI REST Routers"]
        HealthRouter["/health"]
        ResumeRouter["/resume/parse"]
        InterviewRouter["/interview/sessions/*"]

        Parser["Resume Parsing Service<br/>(pypdf + Regex Synonyms)"]
        RAG["RAG Service<br/>(Sentence-Transformers)"]
        QGen["Adaptive Question Generator<br/>(LLM / 5-Phase Fallback)"]
        Evaluator["Answer Evaluator<br/>(4-Criterion Rubric)"]
    end

    subgraph Storage["Data & Vector Layer"]
        Chroma["ChromaDB Vector Store<br/>(kb_ai_ml, kb_backend, kb_global)"]
        SQLite["SQLite Database<br/>(interview.db via SQLAlchemy)"]
        KBFiles["Knowledge Base PDFs<br/>(data/knowledge_base/)"]
    end

    UI --> Setup
    Setup -->|POST /resume/parse| ResumeRouter
    ResumeRouter --> Parser
    Setup -->|POST /interview/sessions| InterviewRouter

    Interview -->|POST /sessions/{id}/next| InterviewRouter
    InterviewRouter --> RAG
    RAG -->|Similarity Search| Chroma
    InterviewRouter --> QGen

    Interview -->|POST /turns/{id}/answer| InterviewRouter
    InterviewRouter --> Evaluator
    Evaluator --> SQLite

    Summary -->|POST /sessions/{id}/finish| InterviewRouter
    InterviewRouter --> SQLite
```

---

## 🔍 RAG Pipeline Deep Dive

1. **Ingestion & Sliding-Window Chunking:**
   Knowledge PDFs placed in `backend/data/knowledge_base/` are parsed using `scripts/ingest_knowledge.py`. Text is segmented into sliding windows of **500 words with 100-word overlap**, tagged with source metadata (`filename`, `page_number`, `chunk_index`, `role`).
2. **Dense Vector Embeddings:**
   Chunks are embedded into 384-dimensional dense vectors using HuggingFace's `all-MiniLM-L6-v2` Sentence-Transformer model.
3. **Partitioned Collection Upsert:**
   Vectors are stored in isolated role collections:
   - `kb_ai_ml_engineer`
   - `kb_backend_engineer`
   - `kb_data_scientist`
   - `kb_global` (Fallback pool)
4. **Hierarchical Semantic Retrieval:**
   When generating an interview turn, the candidate's target role and resume skills are formatted into a semantic query. The system queries the role collection; if empty or below a cosine similarity threshold (`0.25`), it falls back to `kb_global`.

---

## 📄 Resume Processing Engine

The resume parser ([`backend/app/services/resume_parser.py`](file:///backend/app/services/resume_parser.py)) executes a multi-stage signal extraction pipeline:
- **Format & Security Validation:** Enforces PDF size limits (15 MB), checks file extensions, and verifies magic bytes (`%PDF` header per ISO 32000-1).
- **Text Extraction:** Uses `pypdf` with fallback to `PyMuPDF` (fitz).
- **Synonym & Shorthand Matching:** Uses regular expressions with lookaround assertions (`(?<![\w#+])...(?![\w#+])`) to prevent false positives (e.g., `"rag"` in `"courage"` or `"go"` in `"algorithm"`), while recognizing industry synonyms:
  - `Postgres` / `psql` $\to$ `postgresql`
  - `K8s` $\to$ `kubernetes`
  - `Sklearn` $\to$ `scikit-learn`
  - `NextJS` / `Next js` $\to$ `next.js`
  - `CPP` $\to$ `c++`
  - `CSharp` $\to$ `c#`
  - `LLMs`, `RAGs`, `REST APIs`, `microservices` (plural normalization)
- **Seniority & Experience Classification:** Extracts explicit numeric experience patterns (e.g., `"6+ years of experience"`) and classifies candidates into **Junior**, **Mid-Level**, **Senior**, or **Staff/Lead**.
- **Domain Mapping:** Identifies exposure across **AI/ML**, **Backend**, **Cloud/DevOps**, **Data**, and **Frontend**.

---

## 🧠 Question Generation & Fallback Mechanics

The question generator creates adaptive, role-specific questions:
- **LLM Mode (when `LLM_API_KEY` is provided):** Calls OpenAI-compatible endpoints (`/v1/chat/completions`) using persona instructions, candidate seniority constraints, and retrieved RAG context.
- **Deterministic 5-Phase Fallback (when no key is set):**
  - **Turn 1 (Core Concepts):** Fundamental mechanisms and trade-offs grounded in the knowledge base.
  - **Turn 2 (Performance & Bottlenecks):** High-throughput latency, memory, and scaling trade-offs.
  - **Turn 3 (Debugging & Observability):** Production failure modes, metrics, and root-cause analysis.
  - **Turn 4 (Architecture & Reliability):** Fault tolerance, data consistency, and distributed integration.
  - **Turn 5 (Applied System Design):** End-to-end real-world design integrating resume technologies.

---

## 📊 Answer Evaluation & Scoring Rubric

Candidate answers are evaluated in real time against a 4-criterion rubric (1.0–10.0 scale):

$$\text{Overall Score} = 0.40 \times \text{Accuracy} + 0.30 \times \text{Depth} + 0.15 \times \text{Completeness} + 0.15 \times \text{Clarity}$$

| Score Range | Hiring Recommendation | Assessment Description |
|:---:|:---:|---|
| **8.5 – 10.0** | **Strong Hire** | Exceptional accuracy, architectural depth, and crisp communication. |
| **7.0 – 8.4** | **Hire** | Solid technical foundation with minor omissions in edge-case handling. |
| **5.5 – 6.9** | **Lean Hire** | Understands core concepts but lacks depth in performance or scaling. |
| **< 5.5** | **No Hire** | Significant gaps in technical accuracy or incomplete answers. |

Each evaluation response includes specific **Strengths**, **Weaknesses**, and an **Ideal Answer** benchmark.

---

## 🛠️ Tech Stack

### Backend
- **Framework:** FastAPI 0.115+, Uvicorn
- **Language:** Python 3.11+
- **Database & ORM:** SQLite, SQLAlchemy 2.0+
- **Vector Database:** ChromaDB 0.5+
- **Embeddings:** Sentence-Transformers (`all-MiniLM-L6-v2`)
- **PDF Processing:** PyPDF 5.0+, PyMuPDF
- **Validation:** Pydantic v2 / Pydantic-Settings
- **Testing:** Pytest 8.0+, HTTPX

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript 5.6+, React 18
- **Styling:** Modern Responsive CSS / Dark Mode Support

### DevOps & Deployment
- **Containerization:** Docker, Docker Compose
- **Cloud Hosting:** Vercel (Frontend), Render (Backend)

---

## 📁 Repository Structure

```
.
├── .gitignore
├── ASSIGNMENT_MAPPING.md
├── docker-compose.yml
├── LICENSE
├── README.md
├── backend/
│   ├── .dockerignore
│   ├── .env.example
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── config.py              # Environment configuration & settings
│   │   ├── database.py            # SQLAlchemy database engine & session maker
│   │   ├── main.py                # FastAPI app initialization & CORS middleware
│   │   ├── models.py              # InterviewSession and InterviewTurn ORM models
│   │   ├── schemas.py             # Pydantic request/response validation schemas
│   │   ├── routers/
│   │   │   ├── health.py          # GET /health healthcheck endpoint
│   │   │   ├── interview.py       # Session lifecycle, turns, answers, and summaries
│   │   │   └── resume.py          # POST /resume/parse PDF extraction endpoint
│   │   └── services/
│   │       ├── evaluator.py       # Rubric scoring formula & report generator
│   │       ├── question_generator.py # Adaptive prompts & deterministic fallback
│   │       ├── rag_service.py     # ChromaDB vector store & sliding-window chunks
│   │       └── resume_parser.py   # PDF text & regex synonym extraction engine
│   ├── data/
│   │   ├── chroma/                # ChromaDB vector embeddings
│   │   └── knowledge_base/        # Reference PDFs for RAG ingestion
│   ├── scripts/
│   │   └── ingest_knowledge.py    # Knowledge base ingestion CLI script
│   └── tests/
│       ├── test_ai_integration.py # Adaptive prompts, fallback, and rubric tests
│       ├── test_database_layer.py # ORM models, cascade delete, and schema tests
│       ├── test_foundation.py     # Settings, CORS origins, and health check tests
│       ├── test_interview_api.py  # End-to-end API lifecycle and validation tests
│       ├── test_rag_pipeline.py   # Ingestion, chunking, retrieval, and fallback tests
│       └── test_resume_parser.py  # PDF parsing, synonyms, plurals, and seniority tests
└── frontend/
    ├── .dockerignore
    ├── .env.example
    ├── Dockerfile                 # Multi-stage production build container
    ├── package.json
    ├── package-lock.json
    ├── tsconfig.json
    └── app/
        ├── globals.css            # Dark/light theme styles and layout rules
        ├── layout.tsx             # Root layout with metadata
        ├── page.tsx               # Main multi-stage interview controller
        ├── types.ts               # TypeScript interface contracts
        └── components/
            ├── CandidateSetup.tsx # Resume upload, role select, skill chips
            ├── Header.tsx         # Brand header and backend connection badge
            ├── InterviewConsole.tsx # Grounded question card, answer editor
            └── InterviewSummary.tsx # Scorecards, competency breakdown, report
```

---

## 📡 REST API Documentation

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Application and database healthcheck status. |
| `GET` | `/` | Root API status and interactive docs link. |
| `POST` | `/resume/parse` | Upload and parse a candidate resume PDF; returns structured signals. |
| `POST` | `/interview/sessions` | Create a new persistent interview session. |
| `GET` | `/interview/sessions/{session_id}` | Retrieve session details, current status, and turn history. |
| `POST` | `/interview/sessions/{session_id}/next` | Generate the next grounded question for the active session. |
| `POST` | `/interview/turns/{turn_id}/answer` | Submit candidate answer and receive real-time rubric evaluation. |
| `POST` | `/interview/sessions/{session_id}/finish` | Finalize interview session and generate the executive summary report. |
| `GET` | `/interview/sessions/{session_id}/summary` | Retrieve the generated final summary report. |
| `GET` | `/interview/sessions` | List interview sessions with pagination (`skip`, `limit`). |

Interactive Swagger documentation is available locally at `http://localhost:8000/docs`.

---

## 💻 Local Development Guide

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- (Optional) Docker and Docker Compose

### 2. Backend Setup
```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Run FastAPI server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Ingest Knowledge Base
Place your reference PDF (e.g., textbook or engineering guide) into `backend/data/knowledge_base/`, then run:
```bash
python scripts/ingest_knowledge.py
```

### 4. Frontend Setup
```bash
# Navigate to frontend in a new terminal
cd frontend

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🐳 Docker Deployment

To build and run the entire stack with a single command:

```bash
docker compose up --build -d
```

- **Frontend UI:** `http://localhost:3000`
- **Backend API:** `http://localhost:8000`
- **API Documentation:** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/health`

To stop containers:
```bash
docker compose down
```

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

| Variable | Default Value | Description |
|---|---|---|
| `APP_NAME` | `Role-Based RAG Interviewer` | Application display name. |
| `APP_VERSION` | `1.0.0` | API version string. |
| `DEBUG` | `false` | Enable verbose debugging and error stack traces. |
| `DATABASE_URL` | `sqlite:///data/interview.db` | SQLAlchemy database connection string. |
| `CHROMA_PATH` | `data/chroma` | Directory for persistent ChromaDB embeddings. |
| `KNOWLEDGE_BASE_DIR` | `data/knowledge_base` | Directory containing source PDFs for RAG ingestion. |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-Transformers model name. |
| `TOP_K` | `5` | Number of context chunks retrieved per query. |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Base URL for OpenAI-compatible LLM providers. |
| `LLM_API_KEY` | *(empty)* | Optional API key. If unset, deterministic fallback is used. |
| `LLM_MODEL` | `gpt-4o-mini` | LLM model identifier. |
| `MAX_TURNS` | `5` | Maximum number of turns per interview session. |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Comma-separated list of allowed frontend origins. |

### Frontend (`frontend/.env.local`)

| Variable | Default Value | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL reachable by the browser client. |

---

## 🧪 Testing

The backend includes a comprehensive test suite executed with Pytest:

```bash
cd backend
python -m pytest tests/ -v
```

**Verified Test Result:**
```
collected 40 items

tests/test_ai_integration.py ........                                    [ 20%]
tests/test_database_layer.py ....                                        [ 30%]
tests/test_foundation.py ......                                          [ 45%]
tests/test_interview_api.py .......                                      [ 62%]
tests/test_rag_pipeline.py .......                                       [ 80%]
tests/test_resume_parser.py ........                                     [100%]

======================= 40 passed, 2 warnings in 34.18s =======================
```

---

## ☁️ Cloud Deployment Architecture

- **Frontend on Vercel:** Hosted on Vercel's global Edge network. Configured with `NEXT_PUBLIC_API_URL` pointing to the public Render backend URL.
- **Backend on Render:** Hosted as a Python Web Service running FastAPI with Uvicorn.
- **Cross-Origin Security:** The backend's `CORS_ORIGINS` environment variable is configured to permit requests from the Vercel domain (`https://frontend-eight-green-24.vercel.app`).

---

## ⚠️ Known Limitations

- **Free-Tier Cold Starts:** On free hosting tiers (such as Render free instances), the backend may take 30–50 seconds to spin up after periods of inactivity.
- **Ephemeral Storage on Free Cloud Instances:** SQLite and ChromaDB data persist locally on disk during container runtime, but will reset upon container redeployment unless attached to a persistent cloud volume or managed database.
- **Deterministic Heuristic Evaluation:** In environments without an active `LLM_API_KEY`, evaluation scores and ideal answers are generated using semantic overlap heuristics and deterministic reference templates.

---

## 🔮 Future Improvements

- **Audio & Speech Interface:** Integration with OpenAI Whisper for voice-based technical interviews and real-time speech-to-text response recording.
- **Interactive Coding Sandbox:** Embedded Monaco code editor with a sandboxed Python/JS execution runtime for live coding challenges.
- **Multi-Tenant User Accounts:** OAuth2/JWT authentication allowing candidates and hiring managers to view historical candidate leaderboards.
- **Advanced Hybrid Search:** Combining dense vector retrieval with BM25 sparse keyword search for improved retrieval precision on specialized code snippets.

---

## 📜 License

This project is open-source and licensed under the [MIT License](LICENSE).
