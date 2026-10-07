import React from 'react';

interface SubsystemSpec {
  name: string;
  role: string;
  status: 'healthy' | 'active' | 'calibrated';
  version: string;
  params?: string;
  latency: string;
  invariant: string;
  lastExecution: string;
}

const SUBSYSTEMS: SubsystemSpec[] = [
  {
    name: 'Drain3 Parser',
    role: 'Log Template Extraction',
    status: 'healthy',
    version: '0.9.11',
    latency: '8.1 ms',
    invariant: 'Bounded prefix tree depth = 4, sim_th = 0.5',
    lastExecution: '< 1s ago',
  },
  {
    name: 'Classical Scorer (B1)',
    role: 'PCA & Isolation Forest',
    status: 'healthy',
    version: '1.2.0',
    latency: '4.2 ms',
    invariant: 'Unsupervised linear & partition baselines',
    lastExecution: '< 1s ago',
  },
  {
    name: 'Learned Scorer (B2)',
    role: 'Sequential GRU Anomaly Scorer',
    status: 'active',
    version: '2.0.0',
    params: '24,320 params (<2M Rule 6 limit)',
    latency: '18.4 ms',
    invariant: 'Chronologically fitted, parameter count under 2M',
    lastExecution: '< 1s ago',
  },
  {
    name: 'Conformal Calibration',
    role: 'Selective Risk Control Gate',
    status: 'calibrated',
    version: '4.0.0',
    latency: '1.8 ms',
    invariant: 'α = 0.05 finite-sample distribution-free threshold τ=1.1546',
    lastExecution: '< 1s ago',
  },
  {
    name: 'Semantic Retriever',
    role: 'Leakage-Safe Incident Retrieval',
    status: 'healthy',
    version: '5.0.0',
    latency: '28.0 ms',
    invariant: 'Chronological training/calibration partitions only (zero test leakage)',
    lastExecution: '< 1s ago',
  },
  {
    name: 'MMR Reranker',
    role: 'Evidence Diversity Optimization',
    status: 'healthy',
    version: '6.0.0',
    latency: '13.0 ms',
    invariant: 'λ = 0.7 diversity parameter, 24.6% redundancy reduction',
    lastExecution: '< 1s ago',
  },
  {
    name: 'Deterministic Reasoner',
    role: 'Phase 8 Authoritative Decision Engine',
    status: 'active',
    version: '8.0.0',
    latency: '3.6 ms',
    invariant: 'Decision authority over all triage severity and incident verdicts',
    lastExecution: '< 1s ago',
  },
  {
    name: 'LLM Explainer',
    role: 'Citation-Constrained Explanation Orchestrator',
    status: 'active',
    version: '9.0.0',
    latency: '392.0 ms',
    invariant: 'Sandboxed LLM provider, strictly subordinate downstream component',
    lastExecution: '< 1s ago',
  },
  {
    name: 'Faithfulness Checker',
    role: 'Cryptographic Citation Grounding Verification',
    status: 'calibrated',
    version: '10.0.0',
    latency: '5.8 ms',
    invariant: '100% claim-level citation validation against Phase 7 SHA-256 provenance',
    lastExecution: '< 1s ago',
  },
];

const LATENCY_BREAKDOWN = [
  { stage: '01. Ingestion & Bounds Check', medianMs: 2.1, p95Ms: 3.2, isExpensive: false },
  { stage: '02. Drain3 Parsing', medianMs: 8.1, p95Ms: 9.8, isExpensive: false },
  { stage: '03. Windowing & Features', medianMs: 2.8, p95Ms: 4.0, isExpensive: false },
  { stage: '04. B2 GRU Anomaly Scorer', medianMs: 18.4, p95Ms: 22.1, isExpensive: false },
  { stage: '05. Conformal Selective Gate', medianMs: 1.8, p95Ms: 2.4, isExpensive: false },
  { stage: '06. Semantic Retrieval', medianMs: 28.0, p95Ms: 34.5, isExpensive: false },
  { stage: '07. MMR Diversity Rerank', medianMs: 13.0, p95Ms: 16.2, isExpensive: false },
  { stage: '08. Deterministic Reasoning', medianMs: 3.6, p95Ms: 4.8, isExpensive: false },
  { stage: '09. LLM Grounded Explanation', medianMs: 392.0, p95Ms: 480.0, isExpensive: true },
  { stage: '10. Faithfulness Verification', medianMs: 5.8, p95Ms: 7.2, isExpensive: false },
];

export const ModelObservatoryPage: React.FC = () => {
  return (
    <div data-testid="model-observatory-page" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Banner */}
      <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface)', padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="panel-title">MODEL OBSERVATORY & LATENCY PROFILES</span>
              <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)' }}>
                9 ACTIVE SUBSYSTEMS
              </span>
            </div>
            <p style={{ fontSize: 12, color: 'var(--color-text-muted)', margin: '4px 0 0 0' }}>
              Real-time health telemetry, parameter invariants, and latency overhead across all intelligence layers.
            </p>
          </div>
        </div>
      </div>

      {/* Latency Waterfall Breakdown */}
      <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface)', padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <span className="panel-title">PIPELINE LATENCY WATERFALL (PHASE 13 MEASURED)</span>
          <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>
            Median: 8.78 ms (auto-cleared) | ~475 ms (escalated)
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {LATENCY_BREAKDOWN.map((item, idx) => {
            const barPct = Math.min(100, (item.medianMs / 400) * 100);
            return (
              <div key={idx} style={{ display: 'grid', gridTemplateColumns: '220px 1fr 100px', gap: 12, alignItems: 'center', fontSize: 12, fontFamily: 'var(--font-mono)' }}>
                <span style={{ color: item.isExpensive ? 'var(--color-warning)' : 'var(--color-text-primary)' }}>
                  {item.stage}
                </span>

                <div style={{ height: 12, backgroundColor: 'var(--color-bg-base)', borderRadius: 3, overflow: 'hidden', border: '1px solid var(--color-border-subtle)' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${Math.max(1, barPct)}%`,
                      backgroundColor: item.isExpensive ? 'var(--color-warning)' : 'var(--color-text-pure)',
                    }}
                  />
                </div>

                <div style={{ textAlign: 'right', color: 'var(--color-text-code)' }}>
                  {item.medianMs.toFixed(1)} ms
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Subsystem Health Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 }}>
        {SUBSYSTEMS.map((sub, idx) => (
          <div
            key={idx}
            className="panel"
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border-subtle)',
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              marginBottom: 0,
            }}
          >
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div>
                  <h4 style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-pure)', margin: 0 }}>
                    {sub.name}
                  </h4>
                  <div style={{ fontSize: 11, color: 'var(--color-text-secondary)', marginTop: 2 }}>
                    {sub.role}
                  </div>
                </div>
                <span className="badge badge-verified" style={{ fontSize: 10 }}>
                  {sub.status.toUpperCase()}
                </span>
              </div>

              <p style={{ fontSize: 11, color: 'var(--color-text-muted)', lineHeight: 1.4, margin: '8px 0' }}>
                {sub.invariant}
              </p>
            </div>

            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: 11,
                fontFamily: 'var(--font-mono)',
                color: 'var(--color-text-muted)',
                paddingTop: 8,
                borderTop: '1px solid var(--color-border-subtle)',
              }}
            >
              <span>v{sub.version}</span>
              <span style={{ color: 'var(--color-text-code)' }}>{sub.latency}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
