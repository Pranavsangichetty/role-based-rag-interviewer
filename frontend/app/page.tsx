'use client';
import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import CandidateSetup from './components/CandidateSetup';
import InterviewConsole from './components/InterviewConsole';
import InterviewSummary from './components/InterviewSummary';
import {
  ResumeParseResponse,
  AnswerEvaluationResponse,
  FinalSummaryResponse,
  TurnHistoryItem,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
const MAX_TURNS = 5;

export default function HomePage() {
  // Global & Connection State
  const [backendConnected, setBackendConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Setup Stage State
  const [candidateName, setCandidateName] = useState('');
  const [role, setRole] = useState('AI/ML Engineer');
  const [resume, setResume] = useState<ResumeParseResponse | null>(null);

  // Interview Stage State
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [turnId, setTurnId] = useState<number | null>(null);
  const [turnNumber, setTurnNumber] = useState<number>(1);
  const [question, setQuestion] = useState<string>('');
  const [topic, setTopic] = useState<string | null>(null);
  const [sources, setSources] = useState<string[]>([]);
  const [answer, setAnswer] = useState<string>('');
  const [latestEvaluation, setLatestEvaluation] = useState<AnswerEvaluationResponse | null>(null);
  const [history, setHistory] = useState<TurnHistoryItem[]>([]);

  // Summary Stage State
  const [summary, setSummary] = useState<FinalSummaryResponse | null>(null);

  // Check backend health on initial load
  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch(`${API_BASE}/health`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === 'ok') {
            setBackendConnected(true);
          }
        }
      } catch (err) {
        setBackendConnected(false);
      }
    }
    checkHealth();
  }, []);

  // 1. Upload & Parse Resume
  const handleFileUpload = async (file: File) => {
    setError(null);
    setLoading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/resume/parse`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: 'Failed to parse resume.' }));
        throw new Error(errData.detail || 'Resume upload failed.');
      }

      const data: ResumeParseResponse = await res.json();
      setResume(data);
    } catch (err: any) {
      setError(err.message || 'An error occurred while uploading the resume.');
    } finally {
      setLoading(false);
    }
  };

  // 2. Start Interview Session
  const handleStartInterview = async () => {
    if (!resume) {
      setError('Please upload a resume PDF before starting.');
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const sessionRes = await fetch(`${API_BASE}/interview/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_name: candidateName.trim() || 'Candidate',
          role,
          resume_text: resume.text,
        }),
      });

      if (!sessionRes.ok) {
        const errData = await sessionRes.json().catch(() => ({ detail: 'Failed to create session.' }));
        throw new Error(errData.detail || 'Failed to initialize interview session.');
      }

      const sessionData = await sessionRes.json();
      const newSessionId = sessionData.session_id;
      setSessionId(newSessionId);

      // Fetch Turn 1 Question
      await fetchNextQuestion(newSessionId);
    } catch (err: any) {
      setError(err.message || 'An error occurred while starting the interview.');
    } finally {
      setLoading(false);
    }
  };

  // Fetch Next Question
  const fetchNextQuestion = async (currSessionId: number) => {
    try {
      const nextRes = await fetch(`${API_BASE}/interview/sessions/${currSessionId}/next`, {
        method: 'POST',
      });

      if (!nextRes.ok) {
        const errData = await nextRes.json().catch(() => ({ detail: 'Failed to get next question.' }));
        throw new Error(errData.detail || 'Failed to fetch question.');
      }

      const nextData = await nextRes.json();

      if (nextData.is_complete || !nextData.turn_id) {
        // Max turns reached -> auto finish
        await handleFinishInterview(currSessionId);
        return;
      }

      setTurnId(nextData.turn_id);
      setTurnNumber(nextData.turn_number || history.length + 1);
      setQuestion(nextData.question);
      setTopic(nextData.topic || role);
      setSources(nextData.sources || []);
      setAnswer('');
    } catch (err: any) {
      setError(err.message || 'Error retrieving question.');
    }
  };

  // 3. Submit Answer
  const handleSubmitAnswer = async () => {
    if (!turnId || !answer.trim()) return;

    setError(null);
    setLoading(true);

    try {
      const ansRes = await fetch(`${API_BASE}/interview/turns/${turnId}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer: answer.trim() }),
      });

      if (!ansRes.ok) {
        const errData = await ansRes.json().catch(() => ({ detail: 'Failed to submit answer.' }));
        throw new Error(errData.detail || 'Answer submission failed.');
      }

      const evalData: AnswerEvaluationResponse = await ansRes.json();
      setLatestEvaluation(evalData);

      // Update History
      const turnItem: TurnHistoryItem = {
        turn_number: turnNumber,
        turn_id: turnId,
        question,
        topic,
        sources,
        answer: answer.trim(),
        evaluation: evalData,
      };
      setHistory((prev) => [...prev, turnItem]);

      // If last turn, finish automatically after answering
      if (turnNumber >= MAX_TURNS && sessionId) {
        await handleFinishInterview(sessionId);
      } else if (sessionId) {
        // Fetch next question
        await fetchNextQuestion(sessionId);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to evaluate answer.');
    } finally {
      setLoading(false);
    }
  };

  // 4. Finish Interview
  const handleFinishInterview = async (activeSessionId?: number) => {
    const targetId = activeSessionId || sessionId;
    if (!targetId) return;

    setError(null);
    setLoading(true);

    try {
      const finishRes = await fetch(`${API_BASE}/interview/sessions/${targetId}/finish`, {
        method: 'POST',
      });

      if (!finishRes.ok) {
        const errData = await finishRes.json().catch(() => ({ detail: 'Failed to finish interview.' }));
        throw new Error(errData.detail || 'Failed to generate interview summary.');
      }

      const summaryData: FinalSummaryResponse = await finishRes.json();
      setSummary(summaryData);
    } catch (err: any) {
      setError(err.message || 'Error finalizing interview.');
    } finally {
      setLoading(false);
    }
  };

  // 5. Restart New Session
  const handleRestart = () => {
    setSessionId(null);
    setTurnId(null);
    setTurnNumber(1);
    setQuestion('');
    setTopic(null);
    setSources([]);
    setAnswer('');
    setLatestEvaluation(null);
    setHistory([]);
    setSummary(null);
    setError(null);
    setResume(null);
  };

  return (
    <main>
      <div className="container">
        <Header backendConnected={backendConnected} />

        {/* Stage 1: Candidate Onboarding & Setup */}
        {!sessionId && (
          <CandidateSetup
            candidateName={candidateName}
            role={role}
            resume={resume}
            loading={loading}
            error={error}
            onNameChange={setCandidateName}
            onRoleChange={setRole}
            onFileUpload={handleFileUpload}
            onStartInterview={handleStartInterview}
          />
        )}

        {/* Stage 2: Active Technical Interview */}
        {sessionId && !summary && (
          <InterviewConsole
            sessionId={sessionId}
            role={role}
            candidateName={candidateName}
            turnNumber={turnNumber}
            maxTurns={MAX_TURNS}
            question={question}
            topic={topic}
            sources={sources}
            answer={answer}
            latestEvaluation={latestEvaluation}
            history={history}
            loading={loading}
            error={error}
            onAnswerChange={setAnswer}
            onSubmitAnswer={handleSubmitAnswer}
            onNextQuestion={() => sessionId && fetchNextQuestion(sessionId)}
            onFinishInterview={() => handleFinishInterview()}
          />
        )}

        {/* Stage 3: Summary Report */}
        {summary && (
          <InterviewSummary
            summary={summary}
            history={history}
            onRestart={handleRestart}
          />
        )}
      </div>
    </main>
  );
}