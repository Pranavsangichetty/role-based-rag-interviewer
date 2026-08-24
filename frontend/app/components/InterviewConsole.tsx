'use client';
import React, { useState } from 'react';
import { AnswerEvaluationResponse, TurnHistoryItem } from '../types';

interface InterviewConsoleProps {
  sessionId: number;
  role: string;
  candidateName: string;
  turnNumber: number;
  maxTurns: number;
  question: string;
  topic: string | null;
  sources: string[];
  answer: string;
  latestEvaluation: AnswerEvaluationResponse | null;
  history: TurnHistoryItem[];
  loading: boolean;
  error: string | null;
  onAnswerChange: (answer: string) => void;
  onSubmitAnswer: () => void;
  onNextQuestion: () => void;
  onFinishInterview: () => void;
}

export default function InterviewConsole({
  sessionId,
  role,
  candidateName,
  turnNumber,
  maxTurns,
  question,
  topic,
  sources,
  answer,
  latestEvaluation,
  history,
  loading,
  error,
  onAnswerChange,
  onSubmitAnswer,
  onNextQuestion,
  onFinishInterview,
}: InterviewConsoleProps) {
  const [showHistory, setShowHistory] = useState(false);
  const [showIdealAnswer, setShowIdealAnswer] = useState(false);

  const wordCount = answer.trim() ? answer.trim().split(/\s+/).length : 0;
  const charCount = answer.length;
  const progressPercent = Math.min(100, Math.round(((turnNumber - 1) / maxTurns) * 100));

  return (
    <div>
      {/* Session Progress Header */}
      <div className="card" style={{ padding: '18px 24px', marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
          <div>
            <span style={{ fontSize: '13px', color: '#94a3b8' }}>Session #{sessionId} · </span>
            <strong style={{ color: '#f8fafc' }}>{candidateName || 'Candidate'}</strong>
            <span style={{ fontSize: '13px', color: '#69e7dc', marginLeft: 8 }}>({role})</span>
          </div>
          <div>
            <span className="tag" style={{ background: 'rgba(124, 92, 255, 0.2)' }}>
              Question {Math.min(turnNumber, maxTurns)} of {maxTurns}
            </span>
          </div>
        </div>

        <div className="progress-wrap" style={{ marginTop: 12, marginBottom: 0 }}>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
          </div>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* Main Question & Answer Card */}
      <div className="card">
        {/* Grounded Question Display */}
        <div className="question-banner">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, alignItems: 'center' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#00d2be', textTransform: 'uppercase' }}>
              Topic: {topic || role}
            </span>
            {sources.length > 0 && (
              <div>
                {sources.map((src, i) => (
                  <span key={i} className="citation-pill" title={src}>
                    📖 {src}
                  </span>
                ))}
              </div>
            )}
          </div>
          <p className="question-text">{question}</p>
        </div>

        {/* Live Evaluation Feedback from Submitted Turn */}
        {latestEvaluation && (
          <div className="feedback-card" style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
              <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#f1f5f9' }}>
                Turn Evaluation Result
              </h3>
              <span
                className={`score-badge ${
                  latestEvaluation.score >= 7.5 ? 'high' : latestEvaluation.score >= 5.5 ? 'mid' : 'low'
                }`}
              >
                ★ {latestEvaluation.score} / 10
              </span>
            </div>

            <div className="rubric-grid">
              <div className="rubric-item">
                <div className="rubric-label">Accuracy</div>
                <div className="rubric-val">{latestEvaluation.accuracy_score}</div>
              </div>
              <div className="rubric-item">
                <div className="rubric-label">Completeness</div>
                <div className="rubric-val">{latestEvaluation.completeness_score}</div>
              </div>
              <div className="rubric-item">
                <div className="rubric-label">Depth</div>
                <div className="rubric-val">{latestEvaluation.depth_score}</div>
              </div>
              <div className="rubric-item">
                <div className="rubric-label">Clarity</div>
                <div className="rubric-val">{latestEvaluation.clarity_score}</div>
              </div>
            </div>

            <p style={{ fontSize: '13px', color: '#cbd5e1', lineHeight: 1.6 }}>
              {latestEvaluation.feedback}
            </p>

            {latestEvaluation.strengths.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <strong style={{ fontSize: '12px', color: '#34d399', textTransform: 'uppercase' }}>
                  Strengths:
                </strong>
                <ul className="bullet-list strengths">
                  {latestEvaluation.strengths.map((s, idx) => (
                    <li key={idx}>{s}</li>
                  ))}
                </ul>
              </div>
            )}

            {latestEvaluation.weaknesses.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <strong style={{ fontSize: '12px', color: '#fbbf24', textTransform: 'uppercase' }}>
                  Areas for Improvement:
                </strong>
                <ul className="bullet-list weaknesses">
                  {latestEvaluation.weaknesses.map((w, idx) => (
                    <li key={idx}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            <div style={{ marginTop: 14 }}>
              <button
                className="btn btn-secondary"
                style={{ padding: '6px 12px', fontSize: '12px' }}
                onClick={() => setShowIdealAnswer(!showIdealAnswer)}
              >
                {showIdealAnswer ? 'Hide Reference Answer' : '💡 View Reference Answer'}
              </button>

              {showIdealAnswer && (
                <div
                  style={{
                    marginTop: 10,
                    padding: 12,
                    background: 'rgba(15, 23, 42, 0.8)',
                    borderRadius: 8,
                    fontSize: '13px',
                    color: '#94a3b8',
                    borderLeft: '3px solid #7c5cff',
                  }}
                >
                  {latestEvaluation.ideal_answer}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Answer Input Textarea */}
        <div className="form-group">
          <label htmlFor="answer-input">Your Technical Answer</label>
          <textarea
            id="answer-input"
            rows={7}
            value={answer}
            onChange={(e) => onAnswerChange(e.target.value)}
            placeholder="Type your structured technical explanation, architecture trade-offs, and implementation considerations here..."
            disabled={loading}
            autoFocus
          />
          <div className="meta-counter">
            <span>{wordCount} words</span>
            <span style={{ margin: '0 6px' }}>·</span>
            <span>{charCount} characters</span>
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 18, flexWrap: 'wrap', gap: 10 }}>
          <div style={{ display: 'flex', gap: 10 }}>
            <button
              className="btn btn-primary"
              onClick={onSubmitAnswer}
              disabled={!answer.trim() || loading}
            >
              {loading ? 'Evaluating with Rubric...' : 'Submit Answer & Get Next Question →'}
            </button>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            {history.length > 0 && (
              <button
                className="btn btn-secondary"
                onClick={() => setShowHistory(!showHistory)}
              >
                {showHistory ? 'Hide Transcript' : `📜 View History (${history.length})`}
              </button>
            )}
            <button className="btn btn-secondary" onClick={onFinishInterview} disabled={loading}>
              Finish Interview
            </button>
          </div>
        </div>
      </div>

      {/* Past Turns History Accordion */}
      {showHistory && history.length > 0 && (
        <div className="card">
          <h3 className="card-title">Interview Transcript & Turn History</h3>
          {history.map((item, idx) => (
            <div key={item.turn_id || idx} className="transcript-item">
              <div className="transcript-header">
                <div>
                  <strong>Turn {item.turn_number}: {item.topic || 'Technical Topic'}</strong>
                </div>
                {item.evaluation && (
                  <span
                    className={`score-badge ${
                      item.evaluation.score >= 7.5 ? 'high' : item.evaluation.score >= 5.5 ? 'mid' : 'low'
                    }`}
                    style={{ fontSize: '13px', padding: '2px 8px' }}
                  >
                    ★ {item.evaluation.score}
                  </span>
                )}
              </div>
              <div className="transcript-body">
                <p style={{ color: '#e2e8f0', marginBottom: 8 }}>
                  <strong>Q:</strong> {item.question}
                </p>
                <p style={{ color: '#94a3b8', fontStyle: 'italic', marginBottom: 8 }}>
                  <strong>A:</strong> {item.answer || '[Not answered]'}
                </p>
                {item.evaluation && (
                  <div style={{ color: '#6ee7b7', fontSize: '12px', marginTop: 6 }}>
                    <strong>Feedback:</strong> {item.evaluation.feedback}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
