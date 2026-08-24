'use client';
import React, { useState, useRef } from 'react';
import { ResumeParseResponse } from '../types';

interface CandidateSetupProps {
  candidateName: string;
  role: string;
  resume: ResumeParseResponse | null;
  loading: boolean;
  error: string | null;
  onNameChange: (name: string) => void;
  onRoleChange: (role: string) => void;
  onFileUpload: (file: File) => void;
  onStartInterview: () => void;
}

const AVAILABLE_ROLES = [
  'AI/ML Engineer',
  'Backend Engineer',
  'Data Scientist',
];

export default function CandidateSetup({
  candidateName,
  role,
  resume,
  loading,
  error,
  onNameChange,
  onRoleChange,
  onFileUpload,
  onStartInterview,
}: CandidateSetupProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      onFileUpload(files[0]);
    }
  };

  return (
    <div className="card">
      <h2 className="card-title">1. Candidate Setup & Resume Onboarding</h2>

      {error && (
        <div className="alert alert-danger">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      <div className="form-grid">
        <div className="form-group">
          <label htmlFor="candidate-name">Candidate Name</label>
          <input
            id="candidate-name"
            type="text"
            placeholder="e.g. Alex Morgan"
            value={candidateName}
            onChange={(e) => onNameChange(e.target.value)}
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="target-role">Target Engineering Role</label>
          <select
            id="target-role"
            value={role}
            onChange={(e) => onRoleChange(e.target.value)}
            disabled={loading}
          >
            {AVAILABLE_ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="form-group">
        <label>Resume PDF Document</label>
        <div
          className={`dropzone ${isDragging ? 'active' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            style={{ display: 'none' }}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onFileUpload(file);
            }}
            disabled={loading}
          />
          <div className="dropzone-icon">📄</div>
          <div className="dropzone-text">
            {resume
              ? `Selected: ${resume.filename}`
              : 'Drag & drop candidate resume (PDF) here, or click to browse'}
          </div>
          <div className="dropzone-hint">
            Supports technical PDFs up to 15MB. Text extraction and signal analysis will run automatically.
          </div>
        </div>
      </div>

      {resume && (
        <div className="feedback-card" style={{ marginTop: 0, marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '15px', color: '#69e7dc', fontWeight: 600 }}>
              ✓ Resume Signals Extracted
            </h3>
            <span className="tag seniority">
              Level: {resume.seniority_level}
              {resume.years_of_experience ? ` (${resume.years_of_experience}+ yrs)` : ''}
            </span>
          </div>

          <div style={{ marginTop: 12 }}>
            <span style={{ fontSize: '12px', color: '#94a3b8' }}>Detected Skills:</span>
            <div className="tag-container">
              {resume.skills.length > 0 ? (
                resume.skills.map((s) => (
                  <span key={s} className="tag">
                    {s}
                  </span>
                ))
              ) : (
                <span className="tag" style={{ opacity: 0.6 }}>
                  No specific skills matched
                </span>
              )}
            </div>
          </div>

          <div style={{ marginTop: 12 }}>
            <span style={{ fontSize: '12px', color: '#94a3b8' }}>Technologies & Tools:</span>
            <div className="tag-container">
              {resume.technologies.length > 0 ? (
                resume.technologies.map((t) => (
                  <span key={t} className="tag tech">
                    {t}
                  </span>
                ))
              ) : (
                <span className="tag tech" style={{ opacity: 0.6 }}>
                  No specific technologies matched
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 10 }}>
        <button
          className="btn btn-primary"
          onClick={onStartInterview}
          disabled={!resume || loading}
        >
          {loading ? 'Initializing Session...' : 'Start Technical Interview →'}
        </button>
      </div>
    </div>
  );
}
