import React from 'react';
import { ExplanationStatus } from '../types';
import { SafeMarkdown } from '../utils/markdown';
import { StatusBadge } from './StatusBadge';
import { AlertCircle } from 'lucide-react';

interface ExplanationPanelProps {
  explanationStatus: ExplanationStatus;
  explanation?: string | null;
  summary?: string | null;
  faithfulnessStatus?: string;
}

export const ExplanationPanel: React.FC<ExplanationPanelProps> = ({
  explanationStatus,
  explanation,
  summary,
  faithfulnessStatus = 'VERIFIED',
}) => {
  const isFailed = explanationStatus === 'FAILED';
  const isSkipped = explanationStatus === 'SKIPPED';
  const isGenerated = explanationStatus === 'GENERATED';

  return (
    <div
      className="panel"
      data-testid="explanation-panel"
      style={{
        backgroundColor: 'var(--color-bg-surface)',
        border: '1px solid var(--color-border-subtle)',
      }}
    >
      <div className="panel-header" style={{ marginBottom: '14px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
                fontWeight: 700,
                color: 'var(--color-text-pure)',
                letterSpacing: '0.5px',
                textTransform: 'uppercase',
              }}
            >
              VERIFIED INCIDENT ASSESSMENT
            </span>
            <span
              style={{
                fontSize: '10px',
                fontFamily: 'var(--font-mono)',
                color: 'var(--color-text-muted)',
                backgroundColor: 'var(--color-bg-base)',
                padding: '1px 6px',
                borderRadius: '3px',
                border: '1px solid var(--color-border-subtle)',
              }}
            >
              DOWNSTREAM EXPLANATION
            </span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', margin: '2px 0 0 0' }}>
            Evidence-grounded technical root cause assessment (constrained to verified citation IDs)
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="badge badge-verified" style={{ fontSize: 10 }}>
            {faithfulnessStatus}
          </span>
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
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}
          data-testid="explanation-failed-message"
        >
          <AlertCircle size={16} />
          <div>
            <strong>Verification Failed / Fallback Active:</strong> Explanation service encountered a provider error or failed grounding validation. Deterministic incident decision is preserved.
          </div>
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
          <strong>Explanation Bypassed:</strong> Log sequence was auto-cleared at the conformal gate or abstained due to insufficient evidence. LLM compute was saved.
        </div>
      )}

      {isGenerated && (
        <div>
          {summary && (
            <div
              style={{
                padding: '12px 16px',
                backgroundColor: 'var(--color-bg-surface-raised)',
                borderLeft: '3px solid var(--color-border-active)',
                borderRadius: 4,
                marginBottom: 16,
                fontSize: 13,
                color: 'var(--color-text-primary)',
              }}
              data-testid="explanation-summary"
            >
              <div
                style={{
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--color-text-muted)',
                  textTransform: 'uppercase',
                  marginBottom: '4px',
                  letterSpacing: '0.5px',
                }}
              >
                Executive Signal & Triage Summary
              </div>
              <div>{summary}</div>
            </div>
          )}

          <div
            className="explanation-content"
            data-testid="explanation-content"
            style={{
              backgroundColor: 'var(--color-bg-base)',
              padding: '16px',
              borderRadius: '6px',
              border: '1px solid var(--color-border-subtle)',
            }}
          >
            {explanation ? (
              <SafeMarkdown content={explanation} />
            ) : (
              <div style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>
                No detailed explanation body provided.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
