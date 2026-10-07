import React from 'react';
import { MetricCard } from '../components/MetricCard';

export const CostIntelligencePage: React.FC = () => {
  const windowsProcessed = 823;
  const llmCalls = 43;
  const llmCallsAvoided = 780;
  const escalationRate = '5.22%';
  const llmCallPercentage = '5.22%';
  const reductionPercentage = '94.78%';

  return (
    <div data-testid="cost-intelligence-page" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Banner */}
      <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface)', padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="panel-title">COST INTELLIGENCE & SELECTIVE EFFICIENCY</span>
              <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)' }}>
                OPERATIONAL PROXY
              </span>
            </div>
            <p style={{ fontSize: 12, color: 'var(--color-text-muted)', margin: '4px 0 0 0' }}>
              FaultSentinel does not send every window to the LLM. Selective conformal gating enforces strict compute discipline.
            </p>
          </div>
        </div>
      </div>

      {/* 4 Primary Operational Proxy Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
        <MetricCard
          label="Windows Processed"
          value={windowsProcessed}
          subtext="Total evaluated operational windows"
          context="HDFS test partition"
          sourceBadge={{ text: 'BENCHMARK', type: 'benchmark' }}
        />

        <MetricCard
          label="LLM Calls"
          value={llmCalls}
          subtext="Selective escalations triggered"
          context="α = 0.05 conformal gate"
          sourceBadge={{ text: 'MEASURED', type: 'calibration' }}
          highlight="warning"
        />

        <MetricCard
          label="LLM Calls Avoided"
          value={llmCallsAvoided}
          subtext={`${reductionPercentage} compute reduction vs LLM-every-window`}
          context="Defensible operational proxy"
          sourceBadge={{ text: 'EFFICIENCY', type: 'live' }}
          highlight="success"
        />

        <MetricCard
          label="LLM Call Percentage"
          value={llmCallPercentage}
          subtext="Only 1 in 19 windows invokes LLM"
          context={`Escalation coverage: ${escalationRate}`}
          sourceBadge={{ text: 'CALIBRATED', type: 'calibration' }}
        />
      </div>

      {/* Selective Escalation Efficiency Comparison */}
      <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface)', padding: '20px' }}>
        <span className="panel-title" style={{ marginBottom: 16, display: 'block' }}>
          SELECTIVE ESCALATION EFFICIENCY BREAKDOWN
        </span>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Baseline B3 (Every Window) */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, fontFamily: 'var(--font-mono)', marginBottom: 6 }}>
              <span style={{ color: 'var(--color-text-secondary)' }}>Baseline B3 (LLM Every Window)</span>
              <span style={{ color: 'var(--color-critical)', fontWeight: 700 }}>823 calls / 823 windows (100.0%)</span>
            </div>
            <div style={{ height: 16, backgroundColor: 'var(--color-bg-base)', borderRadius: 4, overflow: 'hidden', border: '1px solid var(--color-border-subtle)' }}>
              <div style={{ width: '100%', height: '100%', backgroundColor: 'var(--color-critical)' }} />
            </div>
          </div>

          {/* FaultSentinel Proposed */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, fontFamily: 'var(--font-mono)', marginBottom: 6 }}>
              <span style={{ color: 'var(--color-success)', fontWeight: 700 }}>FaultSentinel (Calibrated Conformal Cascade)</span>
              <span style={{ color: 'var(--color-success)', fontWeight: 700 }}>43 calls / 823 windows (5.22%)</span>
            </div>
            <div style={{ height: 16, backgroundColor: 'var(--color-bg-base)', borderRadius: 4, overflow: 'hidden', border: '1px solid var(--color-border-subtle)', position: 'relative' }}>
              <div style={{ width: '5.22%', height: '100%', backgroundColor: 'var(--color-success)' }} />
            </div>
          </div>
        </div>

        <div
          style={{
            marginTop: 20,
            padding: '12px 16px',
            backgroundColor: 'var(--color-bg-base)',
            borderRadius: 4,
            border: '1px solid var(--color-border-subtle)',
            fontSize: 12,
            color: 'var(--color-text-secondary)',
            lineHeight: 1.5,
          }}
        >
          <strong style={{ color: 'var(--color-text-pure)' }}>Operational Rationale:</strong> In commercial cloud operations, sending every log window to an LLM creates untenable latency, token budgets, and rate-limiting bottlenecks. FaultSentinel's split-conformal gate auto-clears 94.78% of normal traffic with guaranteed statistical risk control, invoking the explanation orchestrator solely when anomalous evidence warrants deep investigation.
        </div>
      </div>
    </div>
  );
};
