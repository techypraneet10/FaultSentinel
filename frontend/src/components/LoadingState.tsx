import React from 'react';

export const LoadingState: React.FC = () => {
  return (
    <div
      className="panel"
      style={{
        textAlign: 'center',
        padding: '48px 24px',
        backgroundColor: 'var(--color-bg-surface)',
      }}
      data-testid="loading-state"
      role="status"
      aria-live="polite"
    >
      <div
        style={{
          width: 32,
          height: 32,
          border: '3px solid var(--color-border-subtle)',
          borderTopColor: 'var(--color-info-text)',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
          margin: '0 auto 16px auto',
        }}
      />
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
      <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8, color: 'var(--color-text-primary)' }}>
        Analyzing System Logs...
      </h3>
      <p style={{ color: 'var(--color-text-secondary)', fontSize: 13, maxWidth: 440, margin: '0 auto' }}>
        Executing Drain parsing, calibrated conformal gate, MMR retrieval, Phase 8 deterministic reasoning, and Phase 9 grounded explanation.
      </p>
    </div>
  );
};
