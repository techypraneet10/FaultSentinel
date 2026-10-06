import React from 'react';

export const OverviewPage: React.FC = () => {
  return (
    <div data-testid="overview-page">
      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">System Architecture & Operator Governance</span>
        </div>

        <p style={{ color: 'var(--color-text-secondary)', fontSize: 13, marginBottom: 16 }}>
          <strong>SentinelLog</strong> is an incident triage system based on <em>Calibrated Selective Prediction for LLM-Assisted Incident Triage over System Logs</em>.
          The operator interface is strictly a human review layer over the verified Phase 10 REST API.
        </p>

        <div className="panel" style={{ backgroundColor: 'var(--color-bg-base)', marginBottom: 20 }}>
          <h4 style={{ fontSize: 13, textTransform: 'uppercase', color: 'var(--color-text-secondary)', marginBottom: 10 }}>
            Authoritative Processing Hierarchy
          </h4>
          <pre
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              lineHeight: 1.5,
              color: 'var(--color-text-code)',
              overflowX: 'auto',
            }}
          >
{`Operator Submission
   ↓
Phase 10 FastAPI Serving Layer (/api/v1/analyze)
   ↓
Log Ingestion & Drain Template Parsing
   ↓
Phase 4: Conformal Selective Anomaly Gating (α=0.05)
   ↓
Phase 5: Leakage-Safe Semantic Retrieval
   ↓
Phase 6: Deterministic MMR Evidence Reranking
   ↓
Phase 7: Lineage & Provenance Engine (Precision=1.0, Coverage=1.0)
   ↓
Phase 8: Authoritative Deterministic Reasoning Engine (INCIDENT / SUSPICIOUS / INSUFFICIENT_EVIDENCE)
   ↓
Phase 9: Grounded LLM Explanation Orchestration (Claim-Level Verification)
   ↓
Phase 11: Human Operator Review Console`}
          </pre>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
          <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface-raised)' }}>
            <h4 style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 6 }}>
              Deterministic Authority
            </h4>
            <p style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
              All triage classifications and severity assignments are calculated strictly by the Phase 8 deterministic reasoning engine.
              The LLM explanation is strictly subordinate and never overrules or calculates incident decisions.
            </p>
          </div>

          <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface-raised)' }}>
            <h4 style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 6 }}>
              Claim & Citation Grounding
            </h4>
            <p style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
              Every factual claim produced in an explanation is mapped to verified citation IDs from historical calibration windows.
              Citations are verified against Phase 7 provenance records before being presented to operators.
            </p>
          </div>

          <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface-raised)' }}>
            <h4 style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 6 }}>
              BGL Calibration Safety
            </h4>
            <p style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
              Under selective prediction, log sequences with non-separable anomaly scores abstain safely with <code>INSUFFICIENT_EVIDENCE</code>.
              The UI preserves this uncertainty and never converts abstentions into confirmed incidents.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
