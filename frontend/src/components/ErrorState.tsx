import React from 'react';
import { RequestIdDisplay } from './RequestIdDisplay';

interface ErrorStateProps {
  code?: string;
  message: string;
  requestId?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  code = 'PIPELINE_ERROR',
  message,
  requestId,
  onRetry,
}) => {
  return (
    <div
      className="panel"
      style={{
        backgroundColor: 'var(--color-incident-bg)',
        borderColor: 'var(--color-incident-border)',
        padding: '24px',
      }}
      data-testid="error-state"
      role="alert"
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <span className="badge badge-rejected" style={{ marginBottom: 6 }}>
            {code}
          </span>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--color-incident-text)' }}>
            Analysis Request Failed
          </h3>
        </div>
        {requestId && <RequestIdDisplay requestId={requestId} />}
      </div>

      <p style={{ color: 'var(--color-text-primary)', fontSize: 13, marginBottom: 16 }}>
        {message}
      </p>

      {onRetry && (
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={onRetry}
          data-testid="retry-btn"
        >
          Retry Analysis
        </button>
      )}
    </div>
  );
};
