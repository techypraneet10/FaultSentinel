import React from 'react';
import { ExplanationStatus } from '../types';
import { SafeMarkdown } from '../utils/markdown';
import { StatusBadge } from './StatusBadge';

interface ExplanationPanelProps {
  explanationStatus: ExplanationStatus;
  explanation?: string | null;
  summary?: string | null;
}

export const ExplanationPanel: React.FC<ExplanationPanelProps> = ({
  explanationStatus,
  explanation,
  summary,
}) => {
  const isFailed = explanationStatus === 'FAILED';
  const isSkipped = explanationStatus === 'SKIPPED';
  const isGenerated = explanationStatus === 'GENERATED';

  return (
    <div className="panel" data-testid="explanation-panel">
      <div className="panel-header">
        <span className="panel-title">Grounded Incident Explanation (Phase 9)</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <StatusBadge status={explanationStatus} />
        </div>
      </div>

      {isFailed && (
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: 'var(--color-rejected-bg)',
            border: '1px solid var(--color-rejected-border)',
            borderRadius: 4,
            color: 'var(--color-rejected-text)',
            fontSize: 13,
          }}
          data-testid="explanation-failed-message"
        >
          <strong>Explanation Unavailable:</strong> The explanation service encountered an internal provider error or failed grounding validation.
        </div>
      )}

      {isSkipped && (
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: 'var(--color-insufficient-bg)',
            border: '1px solid var(--color-insufficient-border)',
            borderRadius: 4,
            color: 'var(--color-text-secondary)',
            fontSize: 13,
          }}
          data-testid="explanation-skipped-message"
        >
          Explanation was skipped due to abstention or minimal evidence threshold.
        </div>
      )}

      {isGenerated && (
        <div>
          {summary && (
            <div
              style={{
                padding: '10px 14px',
                backgroundColor: 'var(--color-bg-surface-raised)',
                borderLeft: '3px solid var(--color-info-border)',
                borderRadius: 4,
                marginBottom: 16,
                fontSize: 13,
                color: 'var(--color-text-primary)',
              }}
              data-testid="explanation-summary"
            >
              <strong>Summary:</strong> {summary}
            </div>
          )}

          {explanation ? (
            <SafeMarkdown content={explanation} />
          ) : (
            <div style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>
              No detailed explanation body provided.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
