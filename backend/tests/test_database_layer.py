import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import InterviewSession, InterviewTurn
from app.schemas import (
    ResumeParseResponse,
    ResumeResponse,
    RoleOption,
    SessionCreate,
    AnswerRequest,
    TurnResponse,
    AnswerEvaluationResponse,
    FinalSummaryResponse,
    SessionDetailResponse,
    CompetencyBreakdown,
)

@pytest.fixture
def in_memory_db():
    """Create a temporary in-memory SQLite database for testing data models."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_session_model_creation_and_status(in_memory_db):
    """Verify InterviewSession creation, default fields, score persistence, and completion."""
    session = InterviewSession(
        candidate_name="Jane Doe",
        role="AI/ML Engineer",
        resume_text="Senior ML Engineer with RAG experience.",
    )
    in_memory_db.add(session)
    in_memory_db.commit()
    in_memory_db.refresh(session)

    assert session.id is not None
    assert session.candidate_name == "Jane Doe"
    assert session.role == "AI/ML Engineer"
    assert session.status == "active"
    assert session.total_score is None
    assert session.final_feedback is None
    assert isinstance(session.created_at, datetime)
    assert session.completed_at is None

    # Update session status and completion
    session.status = "completed"
    session.total_score = 8.7
    session.final_feedback = "Strong performance across technical RAG questions."
    session.completed_at = datetime.now(timezone.utc)
    in_memory_db.commit()
    in_memory_db.refresh(session)

    assert session.status == "completed"
    assert session.total_score == 8.7
    assert session.completed_at is not None

def test_turn_model_creation_and_evaluations(in_memory_db):
    """Verify InterviewTurn creation, turn number, scoring metrics, and relationship."""
    session = InterviewSession(
        candidate_name="Bob Builder",
        role="Backend Engineer",
        resume_text="FastAPI, PostgreSQL, Docker"
    )
    in_memory_db.add(session)
    in_memory_db.commit()
    in_memory_db.refresh(session)

    turn = InterviewTurn(
        session_id=session.id,
        turn_number=1,
        question="Explain ACID properties in PostgreSQL.",
        answer="Atomicity, Consistency, Isolation, Durability ensure reliable transactions.",
        retrieved_context="PostgreSQL uses MVCC and WAL for ACID compliance.",
        topic="Database Transactions",
        score=8.5,
        accuracy_score=9.0,
        completeness_score=8.0,
        depth_score=8.5,
        clarity_score=9.0,
        feedback="Accurate summary of ACID transaction semantics.",
        ideal_answer="ACID guarantees data validity despite errors or crashes via WAL."
    )
    in_memory_db.add(turn)
    in_memory_db.commit()
    in_memory_db.refresh(turn)

    assert turn.id is not None
    assert turn.session_id == session.id
    assert turn.turn_number == 1
    assert turn.score == 8.5
    assert turn.accuracy_score == 9.0
    assert turn.completeness_score == 8.0
    assert turn.depth_score == 8.5
    assert turn.clarity_score == 9.0
    assert "ACID" in turn.feedback
    assert len(session.turns) == 1
    assert session.turns[0].id == turn.id

def test_session_cascade_delete(in_memory_db):
    """Verify deleting a session automatically cascades to its turns."""
    session = InterviewSession(candidate_name="Alice", role="Data Scientist", resume_text="Pandas, SQL")
    in_memory_db.add(session)
    in_memory_db.commit()
    in_memory_db.refresh(session)

    turn1 = InterviewTurn(session_id=session.id, turn_number=1, question="Q1")
    turn2 = InterviewTurn(session_id=session.id, turn_number=2, question="Q2")
    in_memory_db.add_all([turn1, turn2])
    in_memory_db.commit()

    assert in_memory_db.query(InterviewTurn).filter_by(session_id=session.id).count() == 2

    in_memory_db.delete(session)
    in_memory_db.commit()

    assert in_memory_db.query(InterviewTurn).filter_by(session_id=session.id).count() == 0

def test_pydantic_schemas():
    """Verify all Pydantic schemas validate inputs and convert from ORM models."""
    # ResumeParseResponse
    resume_resp = ResumeParseResponse(
        filename="cv.pdf",
        text="Sample text",
        skills=["python"],
        technologies=["fastapi"],
        domain_exposure=["Backend"],
        seniority_level="Senior",
        years_of_experience=5
    )
    assert resume_resp.seniority_level == "Senior"
    assert ResumeResponse == ResumeParseResponse

    # RoleOption
    role_opt = RoleOption(
        role_id="ai_ml",
        title="AI/ML Engineer",
        description="Machine learning and deep learning systems.",
        recommended_skills=["python", "pytorch"]
    )
    assert role_opt.role_id == "ai_ml"

    # AnswerEvaluationResponse
    eval_resp = AnswerEvaluationResponse(
        turn_id=1,
        score=8.5,
        accuracy_score=9.0,
        completeness_score=8.0,
        depth_score=8.5,
        clarity_score=9.0,
        feedback="Well explained.",
        strengths=["Clear logic."],
        weaknesses=["None."],
        ideal_answer="Reference answer."
    )
    assert eval_resp.score == 8.5

    # FinalSummaryResponse
    summary_resp = FinalSummaryResponse(
        session_id=1,
        candidate_name="Jane",
        role="AI/ML Engineer",
        status="completed",
        total_questions=5,
        answered_questions=5,
        overall_score=8.5,
        recommendation="Strong Hire",
        competency_breakdown=CompetencyBreakdown(accuracy=8.5, completeness=8.5, depth=8.5, clarity=8.5),
        strengths=["Strong RAG knowledge"],
        areas_for_improvement=[],
        topics=["RAG"],
        summary="Excellent interview."
    )
    assert summary_resp.recommendation == "Strong Hire"
