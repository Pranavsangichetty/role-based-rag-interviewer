from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ResumeParseResponse(BaseModel):
    filename: str
    text: str
    skills: list[str] = []
    technologies: list[str] = []
    domain_exposure: list[str] = []
    seniority_level: str = "Mid-Level"
    years_of_experience: int | None = None

# Backward compatibility alias
ResumeResponse = ResumeParseResponse

class RoleOption(BaseModel):
    role_id: str
    title: str
    description: str
    recommended_skills: list[str] = []

class SessionCreate(BaseModel):
    candidate_name: str = Field(..., min_length=1, description="Name of the candidate")
    role: str = Field(..., min_length=1, description="Target job role")
    resume_text: str = Field(..., description="Parsed resume text")


class AnswerRequest(BaseModel):
    answer: str = Field(min_length=1)

class TurnResponse(BaseModel):
    turn_id: int
    session_id: int
    turn_number: int = 1
    question: str
    topic: str | None = None
    answer: str | None = None
    sources: list[str] = []
    score: float | None = None
    accuracy_score: float | None = None
    completeness_score: float | None = None
    depth_score: float | None = None
    clarity_score: float | None = None
    feedback: str | None = None
    ideal_answer: str | None = None
    created_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)

class AnswerEvaluationResponse(BaseModel):
    status: str = "saved"
    turn_id: int
    score: float
    accuracy_score: float
    completeness_score: float
    depth_score: float
    clarity_score: float
    feedback: str
    strengths: list[str] = []
    weaknesses: list[str] = []
    ideal_answer: str

class CompetencyBreakdown(BaseModel):
    accuracy: float = 0.0
    completeness: float = 0.0
    depth: float = 0.0
    clarity: float = 0.0

class FinalSummaryResponse(BaseModel):
    session_id: int
    candidate_name: str
    role: str
    status: str = "completed"
    total_questions: int
    answered_questions: int
    overall_score: float = 0.0
    recommendation: str = "No Hire"
    competency_breakdown: CompetencyBreakdown
    strengths: list[str] = []
    areas_for_improvement: list[str] = []
    topics: list[str] = []
    summary: str
    completed_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)

class SessionDetailResponse(BaseModel):
    id: int
    candidate_name: str
    role: str
    status: str
    total_score: float | None = None
    final_feedback: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    turns: list[TurnResponse] = []
    model_config = ConfigDict(from_attributes=True)

