import React from 'react';

export const EmptyState: React.FC = () => {
  return (
    <div
      className="panel"
      style={{
        textAlign: 'center',
        padding: '48px 24px',
        backgroundColor: 'var(--color-bg-surface)',
      }}
      data-testid="empty-state"
    >
      <div style={{ fontSize: 32, marginBottom: 12 }}>🛡️</div>
      <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8, color: 'var(--color-text-primary)' }}>
        No Analysis Generated Yet
      </h3>
      <p style={{ color: 'var(--color-text-secondary)', maxWidth: 500, margin: '0 auto', fontSize: 13 }}>
        Submit a bounded sequence of system logs above or load a sample dataset to begin selective incident triage.
        The system will evaluate conformal anomaly gates, retrieve historical incident context, and produce a grounded explanation.
      </p>
    </div>
  );
};
