from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

def utcnow():
    return datetime.now(timezone.utc)

class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(200))
    resume_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="active")  # "active", "completed", "cancelled"
    total_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    turns = relationship(
        "InterviewTurn",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InterviewTurn.turn_number"
    )

class InterviewTurn(Base):
    __tablename__ = "interview_turns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("interview_sessions.id"))
    turn_number: Mapped[int] = mapped_column(Integer, default=1)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Evaluation fields
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    completeness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    depth_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    clarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    ideal_answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    session = relationship("InterviewSession", back_populates="turns")

