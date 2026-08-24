import io
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.main import app

client = TestClient(app)

def create_dummy_pdf_bytes(text: str = "Senior AI Engineer with Python and PyTorch experience.") -> bytes:
    """Helper to create a minimal in-memory valid PDF file."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    # We can write text directly or blank page
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

def test_resume_upload_valid_pdf():
    """Verify uploading a valid PDF returns parsed signals and 200 OK."""
    pdf_bytes = create_dummy_pdf_bytes("Senior Machine Learning Engineer with Python, PyTorch, and RAG.")
    files = {"file": ("test_resume.pdf", pdf_bytes, "application/pdf")}
    
    response = client.post("/resume/parse", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_resume.pdf"
    assert "skills" in data
    assert "technologies" in data
    assert "seniority_level" in data

def test_resume_upload_non_pdf_rejected():
    """Verify uploading a non-PDF file returns 400 Bad Request."""
    files = {"file": ("resume.txt", b"Plain text resume", "text/plain")}
    response = client.post("/resume/parse", files=files)
    assert response.status_code == 400
    assert "Only PDF" in response.json()["detail"]

def test_resume_upload_corrupt_pdf_rejected():
    """Verify uploading a corrupt PDF without %PDF header returns 400 Bad Request."""
    files = {"file": ("corrupt.pdf", b"Not a valid PDF header content", "application/pdf")}
    response = client.post("/resume/parse", files=files)
    assert response.status_code == 400
    assert "Corrupted or invalid PDF" in response.json()["detail"]

def test_resume_upload_empty_file_rejected():
    """Verify uploading an empty 0-byte file returns 400 Bad Request."""
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    response = client.post("/resume/parse", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]

def test_complete_interview_api_lifecycle():
    """Verify end-to-end API lifecycle: create -> get -> next -> answer -> finish -> summary."""
    # 1. Create Session
    create_payload = {
        "candidate_name": "Marcus Aurelius",
        "role": "AI/ML Engineer",
        "resume_text": "Senior ML Engineer specializing in RAG, PyTorch, and Vector Databases with 7 years experience."
    }
    create_res = client.post("/interview/sessions", json=create_payload)
    assert create_res.status_code == 201
    session_data = create_res.json()
    session_id = session_data["session_id"]
    assert session_data["status"] == "active"
    assert session_data["candidate_name"] == "Marcus Aurelius"

    # 2. Get Session Details
    get_res = client.get(f"/interview/sessions/{session_id}")
    assert get_res.status_code == 200
    session_details = get_res.json()
    assert session_details["id"] == session_id
    assert session_details["turns"] == []

    # 3. Next Question Turn 1
    next_res = client.post(f"/interview/sessions/{session_id}/next")
    assert next_res.status_code == 200
    turn1_data = next_res.json()
    assert turn1_data["turn_id"] is not None
    assert turn1_data["session_id"] == session_id
    assert turn1_data["turn_number"] == 1
    assert len(turn1_data["question"]) > 10
    assert "sources" in turn1_data
    turn1_id = turn1_data["turn_id"]

    # 4. Submit Answer for Turn 1
    answer_payload = {
        "answer": "We use dense embeddings and HNSW vector indexing to achieve sub-10ms nearest neighbor search latency with high precision."
    }
    ans_res = client.post(f"/interview/turns/{turn1_id}/answer", json=answer_payload)
    assert ans_res.status_code == 200
    eval_data = ans_res.json()
    assert eval_data["status"] == "saved"
    assert eval_data["turn_id"] == turn1_id
    assert eval_data["score"] > 0
    assert "accuracy_score" in eval_data
    assert "feedback" in eval_data
    assert "strengths" in eval_data
    assert "ideal_answer" in eval_data

    # 5. Finish Interview Session
    finish_res = client.post(f"/interview/sessions/{session_id}/finish")
    assert finish_res.status_code == 200
    summary_data = finish_res.json()
    assert summary_data["session_id"] == session_id
    assert summary_data["status"] == "completed"
    assert summary_data["total_questions"] == 1
    assert summary_data["answered_questions"] == 1
    assert summary_data["overall_score"] > 0
    assert summary_data["recommendation"] in ["Strong Hire", "Hire", "Lean Hire", "No Hire"]
    assert "competency_breakdown" in summary_data

    # 6. Retrieve Summary
    sum_res = client.get(f"/interview/sessions/{session_id}/summary")
    assert sum_res.status_code == 200
    assert sum_res.json()["session_id"] == session_id

    # 7. Disallow next question on completed session
    rej_next = client.post(f"/interview/sessions/{session_id}/next")
    assert rej_next.status_code == 400
    assert "completed session" in rej_next.json()["detail"]

def test_session_not_found_errors():
    """Verify 404 error responses for invalid session and turn IDs."""
    assert client.get("/interview/sessions/999999").status_code == 404
    assert client.post("/interview/sessions/999999/next").status_code == 404
    assert client.post("/interview/sessions/999999/finish").status_code == 404
    assert client.get("/interview/sessions/999999/summary").status_code == 404
    assert client.post("/interview/turns/999999/answer", json={"answer": "hello"}).status_code == 404

def test_list_sessions_endpoint():
    """Verify listing interview sessions with pagination."""
    response = client.get("/interview/sessions?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "sessions" in data
    assert isinstance(data["sessions"], list)
    assert data["skip"] == 0
    assert data["limit"] == 10
