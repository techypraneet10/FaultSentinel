import React from 'react';
import { EvidenceSufficiencyStatus, ProvenanceStatus, FaithfulnessStatus } from '../types';
import { StatusBadge } from './StatusBadge';

interface EvidenceStatusProps {
  evidenceSufficiency: EvidenceSufficiencyStatus;
  provenanceStatus: ProvenanceStatus;
  faithfulnessStatus: FaithfulnessStatus;
}

export const EvidenceStatus: React.FC<EvidenceStatusProps> = ({
  evidenceSufficiency,
  provenanceStatus,
  faithfulnessStatus,
}) => {
  const isFaithful = faithfulnessStatus === 'VERIFIED';
  const isProvenanceVerified = provenanceStatus === 'VERIFIED';

  return (
    <div className="panel" data-testid="evidence-status-panel">
      <div className="panel-header">
        <span className="panel-title">Verification & Provenance Governance</span>
      </div>

      <div className="decision-grid" style={{ marginBottom: 12 }}>
        <div>
          <div className="decision-metric-label">Evidence Sufficiency</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
            <StatusBadge status={evidenceSufficiency} />
            <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
              {evidenceSufficiency === 'SUFFICIENT' ? 'Adequate for triage' : 'Sparse log context'}
            </span>
          </div>
        </div>

        <div>
          <div className="decision-metric-label">Source Provenance</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
            <StatusBadge status={provenanceStatus} />
            <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
              {isProvenanceVerified ? 'Verified Phase 7 Lineage' : 'Provenance Rejected'}
            </span>
          </div>
        </div>

        <div>
          <div className="decision-metric-label">Grounding Faithfulness</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
            <StatusBadge status={faithfulnessStatus} />
            <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
              {isFaithful ? 'Claims grounded in citations' : 'Grounding verification failed'}
            </span>
          </div>
        </div>
      </div>

      {!isProvenanceVerified && (
        <div
          style={{
            padding: '8px 12px',
            backgroundColor: 'var(--color-rejected-bg)',
            border: '1px solid var(--color-rejected-border)',
            borderRadius: 4,
            fontSize: 12,
            color: 'var(--color-rejected-text)',
            marginBottom: 8,
          }}
          data-testid="provenance-rejected-alert"
        >
          <strong>Warning:</strong> Citation source provenance could not be verified against the canonical index. Evidence is unverified.
        </div>
      )}

      {!isFaithful && (
        <div
          style={{
            padding: '8px 12px',
            backgroundColor: 'var(--color-rejected-bg)',
            border: '1px solid var(--color-rejected-border)',
            borderRadius: 4,
            fontSize: 12,
            color: 'var(--color-rejected-text)',
          }}
          data-testid="faithfulness-failed-alert"
        >
          <strong>Grounding verification failed:</strong> Generated explanation contains unsupported claims or citation mismatches.
        </div>
      )}
    </div>
  );
};
