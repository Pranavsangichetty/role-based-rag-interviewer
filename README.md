# Role-Based RAG Interviewer

AI-powered role-based technical interview system.

## Flow
Resume PDF -> parsing -> skills/technologies -> role + resume query -> role-specific RAG -> grounded question -> answer -> persistent session -> summary.

## Architecture
- Frontend: Next.js / React
- Backend: FastAPI
- Database: SQLite + SQLAlchemy
- Vector DB: Chroma
- Embeddings: Sentence Transformers
- Knowledge ingestion: PDF -> chunks -> embeddings -> Chroma
- LLM: OpenAI-compatible endpoint configured through environment variables

The assignment requires the supplied book to be the primary RAG knowledge source. Place the supplied PDF locally in `backend/data/knowledge_base/`; do not publish the book PDF in GitHub unless redistribution is permitted.

## Run
### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

### Ingest the supplied knowledge-base PDF
```bash
python scripts/ingest_knowledge.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Docker Compose (Recommended)
To build and run both Backend and Frontend containers with persistence:
```bash
# 1. (Optional) Ingest knowledge base PDFs into backend/data/knowledge_base/
# 2. Start the full application stack
docker compose up --build -d
```
- Frontend UI: http://localhost:3000
- Backend REST API / Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

To stop containers:
```bash
docker compose down
```

Open http://localhost:3000 and the FastAPI docs at http://127.0.0.1:8000/docs.

