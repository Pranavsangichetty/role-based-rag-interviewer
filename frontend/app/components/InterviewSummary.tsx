'use client';
import React from 'react';
import { FinalSummaryResponse, TurnHistoryItem } from '../types';

interface InterviewSummaryProps {
  summary: FinalSummaryResponse;
  history: TurnHistoryItem[];
  onRestart: () => void;
}

export default function InterviewSummary({
  summary,
  history,
  onRestart,
}: InterviewSummaryProps) {
  const getRecommendationClass = (rec: string) => {
    switch (rec) {
      case 'Strong Hire':
        return 'strong-hire';
      case 'Hire':
        return 'hire';
      case 'Lean Hire':
        return 'lean-hire';
      default:
        return 'no-hire';
    }
  };

  return (
    <div>
      {/* Top Banner Card */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 14 }}>
          <div>
            <h2 style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc' }}>
              Technical Interview Summary Report
            </h2>
            <p style={{ color: '#94a3b8', fontSize: '14px', marginTop: 4 }}>
              Candidate: <strong>{summary.candidate_name}</strong> · Role: <strong>{summary.role}</strong> · Session #{summary.session_id}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase' }}>Overall Score</div>
              <div style={{ fontSize: '28px', fontWeight: 800, color: '#69e7dc' }}>
                {summary.overall_score} <span style={{ fontSize: '16px', color: '#94a3b8' }}>/ 10</span>
              </div>
            </div>
            <div className={`rec-badge ${getRecommendationClass(summary.recommendation)}`}>
              {summary.recommendation}
            </div>
          </div>
        </div>

        {/* Competency Breakdown Grid */}
        <div style={{ marginTop: 24 }}>
          <h3 style={{ fontSize: '14px', textTransform: 'uppercase', color: '#cbd5e1', marginBottom: 10, letterSpacing: '0.5px' }}>
            Competency Breakdown
          </h3>
          <div className="rubric-grid">
            <div className="rubric-item">
              <div className="rubric-label">Technical Accuracy</div>
              <div className="rubric-val" style={{ color: '#34d399' }}>
                {summary.competency_breakdown.accuracy} / 10
              </div>
            </div>
            <div className="rubric-item">
              <div className="rubric-label">Completeness</div>
              <div className="rubric-val" style={{ color: '#60a5fa' }}>
                {summary.competency_breakdown.completeness} / 10
              </div>
            </div>
            <div className="rubric-item">
              <div className="rubric-label">Technical Depth</div>
              <div className="rubric-val" style={{ color: '#c084fc' }}>
                {summary.competency_breakdown.depth} / 10
              </div>
            </div>
            <div className="rubric-item">
              <div className="rubric-label">Communication Clarity</div>
              <div className="rubric-val" style={{ color: '#fbbf24' }}>
                {summary.competency_breakdown.clarity} / 10
              </div>
            </div>
          </div>
        </div>

        {/* Executive Summary Narrative */}
        <div style={{ marginTop: 20, padding: 18, background: 'rgba(15, 23, 42, 0.6)', borderRadius: 10, borderLeft: '4px solid #7c5cff' }}>
          <h4 style={{ fontSize: '13px', textTransform: 'uppercase', color: '#a78bfa', marginBottom: 6 }}>
            Executive Assessment
          </h4>
          <p style={{ fontSize: '14px', color: '#e2e8f0', lineHeight: 1.6 }}>
            {summary.summary}
          </p>
        </div>

        {/* Strengths & Weaknesses */}
        <div className="form-grid" style={{ marginTop: 20 }}>
          <div style={{ background: 'rgba(16, 185, 129, 0.05)', padding: 16, borderRadius: 10, border: '1px solid rgba(16, 185, 129, 0.2)' }}>
            <h4 style={{ fontSize: '13px', textTransform: 'uppercase', color: '#34d399', marginBottom: 8 }}>
              Candidate Strengths
            </h4>
            <ul className="bullet-list strengths">
              {summary.strengths.length > 0 ? (
                summary.strengths.map((s, idx) => <li key={idx}>{s}</li>)
              ) : (
                <li>Demonstrated baseline technical comprehension.</li>
              )}
            </ul>
          </div>

          <div style={{ background: 'rgba(245, 158, 11, 0.05)', padding: 16, borderRadius: 10, border: '1px solid rgba(245, 158, 11, 0.2)' }}>
            <h4 style={{ fontSize: '13px', textTransform: 'uppercase', color: '#fbbf24', marginBottom: 8 }}>
              Areas for Growth
            </h4>
            <ul className="bullet-list weaknesses">
              {summary.areas_for_improvement.length > 0 ? (
                summary.areas_for_improvement.map((w, idx) => <li key={idx}>{w}</li>)
              ) : (
                <li>Continue deepening knowledge of production failure cases.</li>
              )}
            </ul>
          </div>
        </div>

        {/* Topics Covered */}
        {summary.topics.length > 0 && (
          <div style={{ marginTop: 18 }}>
            <span style={{ fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase' }}>Topics Evaluated: </span>
            <div className="tag-container" style={{ display: 'inline-flex', marginLeft: 8 }}>
              {summary.topics.map((t, idx) => (
                <span key={idx} className="tag">
                  {t}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Turn by Turn Detailed Review */}
      {history.length > 0 && (
        <div className="card">
          <h3 className="card-title">Detailed Turn-by-Turn Evaluation</h3>
          {history.map((turn) => (
            <div key={turn.turn_id} className="transcript-item" style={{ marginBottom: 16 }}>
              <div className="transcript-header">
                <div>
                  <strong style={{ color: '#f8fafc' }}>
                    Turn {turn.turn_number}: {turn.topic || 'Interview Question'}
                  </strong>
                </div>
                {turn.evaluation && (
                  <span
                    className={`score-badge ${
                      turn.evaluation.score >= 7.5 ? 'high' : turn.evaluation.score >= 5.5 ? 'mid' : 'low'
                    }`}
                    style={{ fontSize: '13px', padding: '2px 8px' }}
                  >
                    Score: {turn.evaluation.score} / 10
                  </span>
                )}
              </div>
              <div className="transcript-body">
                <div style={{ marginBottom: 10 }}>
                  <span style={{ color: '#69e7dc', fontWeight: 600 }}>Question:</span>
                  <p style={{ color: '#f1f5f9', marginTop: 2 }}>{turn.question}</p>
                </div>
                <div style={{ marginBottom: 10 }}>
                  <span style={{ color: '#94a3b8', fontWeight: 600 }}>Candidate Answer:</span>
                  <p style={{ color: '#cbd5e1', marginTop: 2, fontStyle: 'italic' }}>
                    {turn.answer || '[No answer submitted]'}
                  </p>
                </div>
                {turn.evaluation && (
                  <div style={{ marginTop: 12, padding: 12, background: 'rgba(15, 23, 42, 0.7)', borderRadius: 8 }}>
                    <span style={{ color: '#34d399', fontWeight: 600 }}>Rubric Feedback:</span>
                    <p style={{ color: '#cbd5e1', marginTop: 2 }}>{turn.evaluation.feedback}</p>
                    <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: '12px', color: '#94a3b8' }}>
                      <span>Accuracy: <strong>{turn.evaluation.accuracy_score}</strong></span>
                      <span>Completeness: <strong>{turn.evaluation.completeness_score}</strong></span>
                      <span>Depth: <strong>{turn.evaluation.depth_score}</strong></span>
                      <span>Clarity: <strong>{turn.evaluation.clarity_score}</strong></span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Bottom Actions */}
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 24 }}>
        <button className="btn btn-primary" onClick={onRestart}>
          ↺ Start a New Interview Session
        </button>
      </div>
    </div>
  );
}
