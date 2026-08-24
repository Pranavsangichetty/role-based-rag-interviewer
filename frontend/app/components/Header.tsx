'use client';
import React from 'react';

interface HeaderProps {
  backendConnected: boolean;
}

export default function Header({ backendConnected }: HeaderProps) {
  return (
    <header className="app-header">
      <div>
        <h1 className="brand-title">Role-Based RAG Interviewer</h1>
        <p className="brand-subtitle">
          Resume-aware technical interviews grounded in a role-specific knowledge base.
        </p>
      </div>
      <div>
        <span className="status-pill">
          <span
            className="status-dot"
            style={{
              background: backendConnected ? '#10b981' : '#ef4444',
              boxShadow: backendConnected ? '0 0 8px #10b981' : '0 0 8px #ef4444',
            }}
          />
          {backendConnected ? 'Backend Connected' : 'Connecting...'}
        </span>
      </div>
    </header>
  );
}
