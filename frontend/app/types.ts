export interface ResumeParseResponse {
  filename: string;
  text: string;
  skills: string[];
  technologies: string[];
  domain_exposure: string[];
  seniority_level: string;
  years_of_experience: number | null;
}

export interface SessionCreatePayload {
  candidate_name: string;
  role: string;
  resume_text: string;
}

export interface SessionCreateResponse {
  session_id: number;
  candidate_name: string;
  role: string;
  status: string;
  created_at: string;
}

export interface NextQuestionResponse {
  turn_id: number | null;
  session_id: number;
  turn_number?: number;
  question?: string;
  topic?: string | null;
  sources?: string[];
  is_complete?: boolean;
  message?: string;
}

export interface AnswerEvaluationResponse {
  status: string;
  turn_id: number;
  score: number;
  accuracy_score: number;
  completeness_score: number;
  depth_score: number;
  clarity_score: number;
  feedback: string;
  strengths: string[];
  weaknesses: string[];
  ideal_answer: string;
}

export interface CompetencyBreakdown {
  accuracy: number;
  completeness: number;
  depth: number;
  clarity: number;
}

export interface FinalSummaryResponse {
  session_id: number;
  candidate_name: string;
  role: string;
  status: string;
  total_questions: number;
  answered_questions: number;
  overall_score: number;
  recommendation: 'Strong Hire' | 'Hire' | 'Lean Hire' | 'No Hire';
  competency_breakdown: CompetencyBreakdown;
  strengths: string[];
  areas_for_improvement: string[];
  topics: string[];
  summary: string;
  completed_at: string | null;
}

export interface TurnHistoryItem {
  turn_number: number;
  turn_id: number;
  question: string;
  topic: string | null;
  sources: string[];
  answer?: string;
  evaluation?: AnswerEvaluationResponse | null;
}
