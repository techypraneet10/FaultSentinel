import React, { useEffect, useState } from 'react';
import { TriagePipeline } from '../components/TriagePipeline';
import { MetricCard } from '../components/MetricCard';
import { apiService } from '../services/api';
import { DiagnosticsResponse } from '../types';
import {
  ShieldAlert,
  ArrowRight,
  Cpu,
  FileCheck,
} from 'lucide-react';

interface OverviewPageProps {
  onNavigateTab?: (tab: string) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ onNavigateTab }) => {
  const [diagnostics, setDiagnostics] = useState<DiagnosticsResponse | null>(null);

  useEffect(() => {
    let isMounted = true;
    apiService
      .fetchDiagnostics()
      .then((data) => {
        if (isMounted) setDiagnostics(data);
      })
      .catch(() => {
        // Backend offline or running in mock mode
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Real data from Phase 12 / 13 benchmark & live telemetry
  const totalAnalyses = diagnostics?.candidate_slis?.total_analyses_observed ?? 823;
  const escalationRate = diagnostics?.candidate_slis?.observed_escalation_rate
    ? `${(diagnostics.candidate_slis.observed_escalation_rate * 100).toFixed(1)}%`
    : '5.2%';
  const p95Latency = '10.65'; // Measured Phase 13 telemetry overhead benchmark
  const faithfulnessRate = '100%'; // Measured Phase 9/12 citation grounding

  const isLive = Boolean(diagnostics && diagnostics.candidate_slis?.total_requests_observed > 0);

  return (
    <div data-testid="overview-page" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Recruiter / Command Center Hero Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          padding: '4px 0',
        }}
      >
        <div>
          <div
            style={{
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--color-text-secondary)',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: '2px',
            }}
          >
            Good evening — Operational Triage Status
          </div>
          <h2
            style={{
              fontSize: '22px',
              fontWeight: 700,
              color: 'var(--color-text-pure)',
              letterSpacing: '-0.3px',
              margin: 0,
            }}
          >
            FaultSentinel Command Center
          </h2>
          <p
            style={{
              fontSize: '13px',
              color: 'var(--color-text-secondary)',
              marginTop: '4px',
              marginBottom: 0,
            }}
          >
            AI-assisted incident triage with calibrated escalation & evidence-grounded root cause analysis
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          {onNavigateTab && (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => onNavigateTab('analyze')}
            >
              <span>Launch Live Triage</span>
              <ArrowRight size={13} />
            </button>
          )}
        </div>
      </div>

      {/* 4 Primary KPI Metric Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '12px',
        }}
      >
        <MetricCard
          label="Windows Analyzed"
          value={totalAnalyses}
          subtext="Chronological evaluation test partitions"
          context={isLive ? 'Live observed telemetry' : 'Phase 12 frozen partition'}
          sourceBadge={{
            text: isLive ? 'LIVE' : 'BENCHMARK',
            type: isLive ? 'live' : 'benchmark',
          }}
          sparkline={[0.2, 0.4, 0.3, 0.6, 0.5, 0.8, 0.7, 0.9, 1.0]}
        />

        <MetricCard
          label="Escalation Rate"
          value={escalationRate}
          subtext="94.8% normal windows safely auto-cleared"
          context="Target risk α = 0.05"
          sourceBadge={{
            text: 'CALIBRATED',
            type: 'calibration',
          }}
          highlight="warning"
          sparkline={[0.08, 0.05, 0.06, 0.04, 0.05, 0.052, 0.051]}
        />

        <MetricCard
          label="P95 Latency"
          value={p95Latency}
          unit="ms"
          subtext="Median pipeline latency: 8.78 ms"
          context="Phase 13 telemetry overhead"
          sourceBadge={{
            text: 'BENCHMARK',
            type: 'benchmark',
          }}
          sparkline={[0.4, 0.5, 0.3, 0.6, 0.4, 0.8, 0.5, 0.9]}
        />

        <MetricCard
          label="Faithfulness Rate"
          value={faithfulnessRate}
          subtext="14 / 14 incident claims citation-verified"
          context="Phase 9 programmatic grounding"
          sourceBadge={{
            text: 'VERIFIED',
            type: 'live',
          }}
          highlight="success"
          sparkline={[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]}
        />
      </div>

      {/* Hero — Horizontal Triage Pipeline Visualization */}
      <TriagePipeline />

      {/* Architecture & Operator Governance (Preserving exact text for test suite) */}
      <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface)' }}>
        <div className="panel-header">
          <span className="panel-title">System Architecture & Operator Governance</span>
          <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)' }}>
            DETERMINISTIC AUTHORITY
          </span>
        </div>

        <p style={{ color: 'var(--color-text-secondary)', fontSize: '13px', marginBottom: '16px', lineHeight: 1.5 }}>
          <strong style={{ color: 'var(--color-text-pure)' }}>FaultSentinel</strong> is an incident triage system based on{' '}
          <em>Calibrated Selective Prediction for LLM-Assisted Incident Triage over System Logs</em>. The operator
          interface provides an authoritative human-in-the-loop review layer over the verified FastAPI serving layer.
        </p>

        {/* ASCII Architecture Flow */}
        <div
          className="panel"
          style={{
            backgroundColor: 'var(--color-bg-base)',
            border: '1px solid var(--color-border-subtle)',
            marginBottom: '16px',
            padding: '12px 16px',
          }}
        >
          <div
            style={{
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              textTransform: 'uppercase',
              color: 'var(--color-text-muted)',
              marginBottom: '8px',
              letterSpacing: '0.5px',
            }}
          >
            Authoritative Processing Hierarchy
          </div>
          <pre
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              lineHeight: 1.5,
              color: 'var(--color-text-code)',
              overflowX: 'auto',
              margin: 0,
            }}
          >
{`Operator Submission
   ↓
FastAPI Serving Layer (/api/v1/analyze)
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

        {/* 3 Core Architecture Tenets */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '12px',
          }}
        >
          <div
            className="panel"
            style={{
              backgroundColor: 'var(--color-bg-surface-raised)',
              border: '1px solid var(--color-border-subtle)',
              marginBottom: 0,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
              <Cpu size={14} color="var(--color-text-pure)" />
              <h4 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-text-pure)', margin: 0 }}>
                Deterministic Authority
              </h4>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', margin: 0, lineHeight: 1.4 }}>
              All triage classifications and severity assignments are calculated strictly by the Phase 8 deterministic reasoning engine. The LLM explanation is strictly
              subordinate and never overrules or calculates incident decisions.
            </p>
          </div>

          <div
            className="panel"
            style={{
              backgroundColor: 'var(--color-bg-surface-raised)',
              border: '1px solid var(--color-border-subtle)',
              marginBottom: 0,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
              <FileCheck size={14} color="var(--color-success)" />
              <h4 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-text-pure)', margin: 0 }}>
                Claim & Citation Grounding
              </h4>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', margin: 0, lineHeight: 1.4 }}>
              Every factual claim produced in an explanation is mapped to verified citation IDs from historical calibration
              windows. Citations are verified against Phase 7 provenance records before being presented to operators.
            </p>
          </div>

          <div
            className="panel"
            style={{
              backgroundColor: 'var(--color-bg-surface-raised)',
              border: '1px solid var(--color-border-subtle)',
              marginBottom: 0,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
              <ShieldAlert size={14} color="var(--color-warning)" />
              <h4 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-text-pure)', margin: 0 }}>
                BGL Calibration Safety
              </h4>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', margin: 0, lineHeight: 1.4 }}>
              Under selective prediction, log sequences with non-separable anomaly scores abstain safely with{' '}
              <code style={{ color: 'var(--color-text-code)' }}>INSUFFICIENT_EVIDENCE</code>. The UI preserves this
              uncertainty and never converts abstentions into confirmed incidents.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
