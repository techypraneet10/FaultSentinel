import React from 'react';
import { CheckCircle2, AlertTriangle, Clock } from 'lucide-react';
import { DecisionType } from '../types';

interface DecisionTraceStep {
  step: string;
  name: string;
  latency: string;
  status: 'success' | 'warning' | 'info' | 'skipped';
  detail: string;
}

interface DecisionTraceProps {
  decision?: DecisionType;
  isEscalated?: boolean;
  faithfulnessStatus?: string;
  recordCount?: number;
}

export const DecisionTrace: React.FC<DecisionTraceProps> = ({
  decision = 'INCIDENT',
  isEscalated = true,
  faithfulnessStatus = 'VERIFIED',
  recordCount = 7,
}) => {
  const steps: DecisionTraceStep[] = [
    {
      step: '01',
      name: 'Parsed by Drain3 TemplateMiner',
      latency: '8 ms',
      status: 'success',
      detail: `${recordCount} records clustered into canonical event IDs`,
    },
    {
      step: '02',
      name: 'Window Representation Constructed',
      latency: '3 ms',
      status: 'success',
      detail: 'Chronological event count & transition feature vectors',
    },
    {
      step: '03',
      name: 'B2 Sequential GRU Anomaly Scorer',
      latency: '18 ms',
      status: 'success',
      detail: 'Score evaluated (<2M parameter learned model)',
    },
    {
      step: '04',
      name: isEscalated ? 'Conformal Gate → ESCALATE' : 'Conformal Gate → AUTO-CLEAR',
      latency: '2 ms',
      status: isEscalated ? 'warning' : 'success',
      detail: isEscalated
        ? 'Risk threshold exceeded (α = 0.05, s > 1.1546)'
        : 'Score below cutoff, auto-cleared without LLM invocation',
    },
    {
      step: '05',
      name: 'Historical MMR Incident Retrieval',
      latency: '41 ms',
      status: isEscalated ? 'success' : 'skipped',
      detail: isEscalated
        ? 'Retrieved 3 calibration windows, λ=0.7 MMR reranked'
        : 'Bypassed (window auto-cleared at conformal gate)',
    },
    {
      step: '06',
      name: 'Phase 8 Deterministic Reasoning Engine',
      latency: '4 ms',
      status: 'success',
      detail: `Verdict: ${decision} (authoritative classification)`,
    },
    {
      step: '07',
      name: 'Phase 9 Grounded LLM Explanation',
      latency: '392 ms',
      status: isEscalated ? 'success' : 'skipped',
      detail: isEscalated
        ? 'Executive summary and claim generation with citations'
        : 'Zero LLM calls made (selective budget preserved)',
    },
    {
      step: '08',
      name: `Faithfulness Grounding Check → ${faithfulnessStatus}`,
      latency: '6 ms',
      status: faithfulnessStatus === 'VERIFIED' ? 'success' : 'warning',
      detail:
        faithfulnessStatus === 'VERIFIED'
          ? '100% claim-level citations validated against provenance store'
          : 'Grounding discrepancy detected; fallback reasoning retained',
    },
  ];

  return (
    <div
      className="panel"
      data-testid="decision-trace-container"
      style={{
        backgroundColor: 'var(--color-bg-surface)',
        border: '1px solid var(--color-border-subtle)',
      }}
    >
      <div className="panel-header" style={{ marginBottom: '12px' }}>
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
            DECISION EXECUTION TRACE
          </span>
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              backgroundColor: 'var(--color-bg-base)',
              padding: '1px 6px',
              borderRadius: '3px',
              border: '1px solid var(--color-border-subtle)',
              color: 'var(--color-text-muted)',
            }}
          >
            TRACEABLE PROVENANCE
          </span>
        </div>
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            color: 'var(--color-text-muted)',
          }}
        >
          Total Latency: ~474 ms
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {steps.map((s, idx) => {
          const isSkipped = s.status === 'skipped';
          return (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 10px',
                borderRadius: '4px',
                backgroundColor: isSkipped ? 'transparent' : 'var(--color-bg-base)',
                border: '1px solid',
                borderColor: isSkipped
                  ? 'transparent'
                  : s.status === 'warning'
                  ? '#4e3506'
                  : 'var(--color-border-subtle)',
                opacity: isSkipped ? 0.45 : 1,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '11px',
                    color: 'var(--color-text-muted)',
                    fontWeight: 700,
                  }}
                >
                  {s.step}
                </span>

                <div>
                  {s.status === 'warning' ? (
                    <AlertTriangle size={13} color="var(--color-warning)" style={{ verticalAlign: 'middle' }} />
                  ) : isSkipped ? (
                    <Clock size={13} color="var(--color-text-muted)" style={{ verticalAlign: 'middle' }} />
                  ) : (
                    <CheckCircle2 size={13} color="var(--color-success)" style={{ verticalAlign: 'middle' }} />
                  )}
                </div>

                <div>
                  <div
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '12px',
                      fontWeight: 600,
                      color:
                        s.status === 'warning'
                          ? 'var(--color-warning)'
                          : 'var(--color-text-primary)',
                    }}
                  >
                    {s.name}
                  </div>
                  <div
                    style={{
                      fontSize: '11px',
                      color: 'var(--color-text-muted)',
                      marginTop: '1px',
                    }}
                  >
                    {s.detail}
                  </div>
                </div>
              </div>

              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '11px',
                  color: isSkipped ? 'var(--color-text-muted)' : 'var(--color-text-code)',
                  textAlign: 'right',
                  whiteSpace: 'nowrap',
                }}
              >
                {isSkipped ? 'BYPASSED' : s.latency}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
