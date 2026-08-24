from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_db
from ..models import InterviewSession, InterviewTurn
from ..schemas import (
    AnswerEvaluationResponse,
    AnswerRequest,
    CompetencyBreakdown,
    FinalSummaryResponse,
    SessionCreate,
    SessionDetailResponse,
    TurnResponse,
)
from ..services.evaluator import evaluate_answer, generate_final_summary
from ..services.question_generator import generate_question
from ..services.rag_service import RAGService
from ..services.resume_parser import extract_resume_signals

router = APIRouter(prefix="/interview", tags=["interview"])

@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)):
    """Create a new active interview session."""
    session = InterviewSession(
        candidate_name=payload.candidate_name.strip(),
        role=payload.role.strip(),
        resume_text=payload.resume_text.strip(),
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {
        "session_id": session.id,
        "candidate_name": session.candidate_name,
        "role": session.role,
        "status": session.status,
        "created_at": session.created_at,
    }

@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: int, db: Session = Depends(get_db)):
    """Retrieve an interview session with full history of turns."""
    s = db.get(InterviewSession, session_id)
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found.")

    turns_data = []
    for t in s.turns:
        sources = []
        if t.retrieved_context:
            for line in t.retrieved_context.splitlines():
                if line.startswith("[") and "]" in line:
                    sources.append(line.split("]")[0].strip("["))
        sources = sorted(set(sources)) if sources else ["knowledge_base"]

        turns_data.append(
            TurnResponse(
                turn_id=t.id,
                session_id=s.id,
                turn_number=t.turn_number,
                question=t.question,
                topic=t.topic,
                answer=t.answer,
                sources=sources,
                score=t.score,
                accuracy_score=t.accuracy_score,
                completeness_score=t.completeness_score,
                depth_score=t.depth_score,
                clarity_score=t.clarity_score,
                feedback=t.feedback,
                ideal_answer=t.ideal_answer,
                created_at=t.created_at,
            )
        )

    return SessionDetailResponse(
        id=s.id,
        candidate_name=s.candidate_name,
        role=s.role,
        status=s.status,
        total_score=s.total_score,
        final_feedback=s.final_feedback,
        created_at=s.created_at,
        completed_at=s.completed_at,
        turns=turns_data,
    )

@router.post("/sessions/{session_id}/next")
async def next_question(session_id: int, db: Session = Depends(get_db)):
    """Generate or retrieve the next grounded interview question."""
    s = db.get(InterviewSession, session_id)
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found.")

    if s.status in ["completed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot generate question for a {s.status} session. Please start a new session."
        )

    existing_turns = list(s.turns)
    if len(existing_turns) >= settings.max_turns:
        return {
            "turn_id": None,
            "session_id": s.id,
            "is_complete": True,
            "message": f"Maximum turns limit ({settings.max_turns}) reached. Please finish the interview to view your final summary."
        }

    signals = extract_resume_signals(s.resume_text)
    previous = [{"question": t.question, "answer": t.answer, "score": t.score} for t in existing_turns]

    query_skills = " ".join(signals.get("skills", []))
    query_tech = " ".join(signals.get("technologies", []))
    query = f"{s.role} interview topics {query_skills} {query_tech}".strip()

    rag = RAGService()
    retrieved = rag.retrieve(role=s.role, query=query, top_k=settings.top_k)

    q = await generate_question(s.role, signals, retrieved, previous)

    skills_list = signals.get("skills", [])
    topic = skills_list[len(existing_turns) % len(skills_list)] if skills_list else s.role

    turn_number = len(existing_turns) + 1
    turn = InterviewTurn(
        session_id=s.id,
        turn_number=turn_number,
        question=q,
        retrieved_context="\n\n".join(x["text"] for x in retrieved),
        topic=topic,
    )
    db.add(turn)
    db.commit()
    db.refresh(turn)

    sources = sorted({x["source"] for x in retrieved if x.get("source")}) or ["knowledge_base"]

    return {
        "turn_id": turn.id,
        "session_id": s.id,
        "turn_number": turn.turn_number,
        "question": q,
        "topic": turn.topic,
        "sources": sources,
        "is_complete": False,
    }

@router.post("/turns/{turn_id}/answer", response_model=AnswerEvaluationResponse)
async def save_answer(turn_id: int, payload: AnswerRequest, db: Session = Depends(get_db)):
    """Submit candidate answer, run LLM/heuristic rubric evaluation, and persist score."""
    t = db.get(InterviewTurn, turn_id)
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview turn not found.")

    s = t.session
    if s.status in ["completed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit answer for a {s.status} session."
        )

    clean_answer = payload.answer.strip()
    if not clean_answer:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Answer cannot be empty.")

    t.answer = clean_answer

    # Evaluate answer against rubric
    evaluation = await evaluate_answer(
        role=s.role,
        question=t.question,
        answer=clean_answer,
        retrieved_context=t.retrieved_context or "",
    )

    t.score = evaluation["overall_score"]
    t.accuracy_score = evaluation["accuracy_score"]
    t.completeness_score = evaluation["completeness_score"]
    t.depth_score = evaluation["depth_score"]
    t.clarity_score = evaluation["clarity_score"]
    t.feedback = evaluation["feedback"]
    t.ideal_answer = evaluation["ideal_answer"]

    db.commit()
    db.refresh(t)

    return AnswerEvaluationResponse(
        status="saved",
        turn_id=t.id,
        score=t.score,
        accuracy_score=t.accuracy_score,
        completeness_score=t.completeness_score,
        depth_score=t.depth_score,
        clarity_score=t.clarity_score,
        feedback=t.feedback,
        strengths=evaluation.get("strengths", []),
        weaknesses=evaluation.get("weaknesses", []),
        ideal_answer=t.ideal_answer,
    )

@router.post("/sessions/{session_id}/finish", response_model=FinalSummaryResponse)
def finish_session(session_id: int, db: Session = Depends(get_db)):
    """Complete an interview session and generate the final comprehensive summary."""
    s = db.get(InterviewSession, session_id)
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found.")

    turns = list(s.turns)
    turn_dicts = [
        {
            "turn_number": t.turn_number,
            "topic": t.topic,
            "question": t.question,
            "answer": t.answer,
            "score": t.score,
            "accuracy_score": t.accuracy_score,
            "completeness_score": t.completeness_score,
            "depth_score": t.depth_score,
            "clarity_score": t.clarity_score,
            "feedback": t.feedback,
        }
        for t in turns
    ]

    summary_data = generate_final_summary(
        role=s.role,
        candidate_name=s.candidate_name,
        turns=turn_dicts,
        resume_signals=extract_resume_signals(s.resume_text) if s.resume_text else None,
    )

    s.status = "completed"
    s.total_score = summary_data["overall_score"]
    s.final_feedback = summary_data["summary"]
    s.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(s)

    return FinalSummaryResponse(
        session_id=s.id,
        candidate_name=s.candidate_name,
        role=s.role,
        status=s.status,
        total_questions=summary_data["total_questions"],
        answered_questions=summary_data["answered_questions"],
        overall_score=summary_data["overall_score"],
        recommendation=summary_data["recommendation"],
        competency_breakdown=CompetencyBreakdown(**summary_data["competency_breakdown"]),
        strengths=summary_data["strengths"],
        areas_for_improvement=summary_data["areas_for_improvement"],
        topics=summary_data["topics"],
        summary=s.final_feedback,
        completed_at=s.completed_at,
    )

@router.get("/sessions/{session_id}/summary", response_model=FinalSummaryResponse)
def get_session_summary(session_id: int, db: Session = Depends(get_db)):
    """Retrieve or compute the structured final interview report."""
    s = db.get(InterviewSession, session_id)
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found.")

    turns = list(s.turns)
    turn_dicts = [
        {
            "turn_number": t.turn_number,
            "topic": t.topic,
            "question": t.question,
            "answer": t.answer,
            "score": t.score,
            "accuracy_score": t.accuracy_score,
            "completeness_score": t.completeness_score,
            "depth_score": t.depth_score,
            "clarity_score": t.clarity_score,
            "feedback": t.feedback,
        }
        for t in turns
    ]

    summary_data = generate_final_summary(
        role=s.role,
        candidate_name=s.candidate_name,
        turns=turn_dicts,
        resume_signals=extract_resume_signals(s.resume_text) if s.resume_text else None,
    )

    return FinalSummaryResponse(
        session_id=s.id,
        candidate_name=s.candidate_name,
        role=s.role,
        status=s.status,
        total_questions=summary_data["total_questions"],
        answered_questions=summary_data["answered_questions"],
        overall_score=summary_data["overall_score"],
        recommendation=summary_data["recommendation"],
        competency_breakdown=CompetencyBreakdown(**summary_data["competency_breakdown"]),
        strengths=summary_data["strengths"],
        areas_for_improvement=summary_data["areas_for_improvement"],
        topics=summary_data["topics"],
        summary=s.final_feedback or summary_data["summary"],
        completed_at=s.completed_at,
    )

@router.get("/sessions")
def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    """List previous interview sessions with pagination and status filtering."""
    query = db.query(InterviewSession)
    if status_filter:
        query = query.filter(InterviewSession.status == status_filter)

    total = query.count()
    sessions = query.order_by(InterviewSession.id.desc()).offset(skip).limit(limit).all()

    items = [
        {
            "id": s.id,
            "candidate_name": s.candidate_name,
            "role": s.role,
            "status": s.status,
            "total_score": s.total_score,
            "turns_count": len(s.turns),
            "created_at": s.created_at,
            "completed_at": s.completed_at,
        }
        for s in sessions
    ]

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "sessions": items,
    }

