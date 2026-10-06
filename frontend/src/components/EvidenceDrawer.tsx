import React from 'react';
import { Citation, ProvenanceStatus } from '../types';
import { StatusBadge } from './StatusBadge';

interface EvidenceDrawerProps {
  citation: Citation | null;
  provenanceStatus: ProvenanceStatus;
  onClose: () => void;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({
  citation,
  provenanceStatus,
  onClose,
}) => {
  if (!citation) return null;

  const isVerified = provenanceStatus === 'VERIFIED';

  return (
    <div
      className="drawer-backdrop"
      onClick={onClose}
      data-testid="evidence-drawer-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="drawer-citation-title"
    >
      <div
        className="drawer-content"
        onClick={(e) => e.stopPropagation()}
        data-testid="evidence-drawer"
      >
        <div className="drawer-header">
          <div>
            <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
              Citation Lineage & Evidence
            </span>
            <h3 id="drawer-citation-title" style={{ fontSize: 18, color: 'var(--color-text-primary)', marginTop: 2 }}>
              Citation: {citation.citation_id}
            </h3>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onClose}
            data-testid="drawer-close-btn"
            aria-label="Close evidence panel"
          >
            ✕ Close
          </button>
        </div>

        <div className="drawer-body">
          <div style={{ marginBottom: 16 }}>
            <span className="decision-metric-label">Source Trust Status</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
              <StatusBadge
                status={isVerified ? 'VERIFIED SOURCE' : 'UNVERIFIED / REJECTED'}
                variant={isVerified ? 'verified' : 'rejected'}
              />
            </div>
          </div>

          <div className="panel" style={{ backgroundColor: 'var(--color-bg-base)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <span className="decision-metric-label">Dataset</span>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--color-text-primary)' }}>
                  {citation.dataset.toUpperCase()}
                </div>
              </div>
              <div>
                <span className="decision-metric-label">Split</span>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--color-text-primary)' }}>
                  {citation.split}
                </div>
              </div>
              <div>
                <span className="decision-metric-label">Source Window</span>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--color-text-code)' }}>
                  {citation.source_window_id}
                </div>
              </div>
              <div>
                <span className="decision-metric-label">Line Range</span>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--color-text-primary)' }}>
                  {citation.line_start !== null && citation.line_start !== undefined
                    ? `${citation.line_start} – ${citation.line_end}`
                    : 'N/A'}
                </div>
              </div>
            </div>
          </div>

          <div style={{ marginTop: 16 }}>
            <span className="decision-metric-label">Source Log Excerpt</span>
            {citation.citation_text ? (
              <pre
                style={{
                  background: 'var(--color-bg-base)',
                  border: '1px solid var(--color-border-subtle)',
                  padding: 12,
                  borderRadius: 4,
                  fontFamily: 'var(--font-mono)',
                  fontSize: 12,
                  color: 'var(--color-text-primary)',
                  whiteSpace: 'pre-wrap',
                  maxHeight: 300,
                  overflowY: 'auto',
                  marginTop: 6,
                }}
                data-testid="citation-excerpt"
              >
                {citation.citation_text}
              </pre>
            ) : (
              <div
                style={{
                  padding: 12,
                  backgroundColor: 'var(--color-bg-base)',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 4,
                  fontSize: 12,
                  color: 'var(--color-text-muted)',
                  fontStyle: 'italic',
                  marginTop: 6,
                }}
              >
                Raw citation excerpt not included in API response contract. Refer to source window ID and line range.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
