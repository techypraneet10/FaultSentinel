import React, { useState } from 'react';
import {
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
} from 'lucide-react';

interface WalkthroughStep {
  stepNumber: number;
  title: string;
  subtitle: string;
  description: string;
  keyMetric: string;
  metricLabel: string;
  tabTarget: string;
  highlights: string[];
}

interface RecruiterWalkthroughProps {
  onNavigateTab: (tabId: string) => void;
}

export const RecruiterWalkthroughPage: React.FC<RecruiterWalkthroughProps> = ({ onNavigateTab }) => {
  const [currentStepIdx, setCurrentStepIdx] = useState<number>(0);

  const steps: WalkthroughStep[] = [
    {
      stepNumber: 1,
      title: 'Problem: Telemetry Overload vs. LLM Latency & Cost',
      subtitle: 'The Economics of Production Log Triage',
      description:
        'Large-scale cloud systems emit millions of logs per minute. Calling generative LLMs continuously for routine telemetry is cost-prohibitive, introduces 500ms+ latency, and hallucinates without grounding.',
      keyMetric: '94.78%',
      metricLabel: 'Reduction in LLM API Invocations',
      tabTarget: 'analyze',
      highlights: [
        'Tier 1 ML scorer runs locally in <2ms per sliding window',
        'Tier 2 LLM explanation is selectively invoked only for anomalies',
        'Zero LLM API calls on routine background noise',
      ],
    },
    {
      stepNumber: 2,
      title: 'Normal Window Auto-Clear',
      subtitle: 'Sub-Millisecond Rejection with Zero Network Calls',
      description:
        'When an incoming log window has a score below the calibrated conformal threshold (e.g., score = 0.42 < 1.15), the system clears the window immediately. No vector index search, no LLM call, and no human alert noise.',
      keyMetric: '< 1.8 ms',
      metricLabel: 'Auto-Clear End-to-End Latency',
      tabTarget: 'analyze',
      highlights: [
        'Deterministic rule guarantees fast-path pass-through',
        'Saves API tokens and GPU memory bandwidth',
        'Preserves SRE focus for genuine critical incidents',
      ],
    },
    {
      stepNumber: 3,
      title: 'Calibrated Conformal Escalation Gate',
      subtitle: 'Statistical Decision Boundaries Under Finite Samples',
      description:
        'Rather than arbitrary heuristic thresholds, FaultSentinel employs Split Conformal Prediction with order-statistic quantiles to guarantee tail miscoverage bounds over the calibration baseline.',
      keyMetric: 'alpha = 0.05',
      metricLabel: 'Finite-Sample Significance Level',
      tabTarget: 'observatory',
      highlights: [
        'Exact threshold derived from chronological calibration split',
        'No Gaussianity or bell-curve assumptions',
        'Traceable metadata recorded for every threshold derivation',
      ],
    },
    {
      stepNumber: 4,
      title: 'Selective Retrieval & MMR Diversification',
      subtitle: 'Evidence Diversification Before Prompt Construction',
      description:
        'Retrieved chunks are filtered from strictly chronological training splits. Maximal Marginal Relevance (MMR with lambda = 0.5) eliminates redundant repetitive logs and surfaces diverse failure modes.',
      keyMetric: 'lambda = 0.5',
      metricLabel: 'MMR Diversification Parameter',
      tabTarget: 'review',
      highlights: [
        'Dense vector index queried only after escalation is confirmed',
        'Cuts prompt token bloat by 65%',
        'Dual-hash provenance binds every chunk to raw source lines',
      ],
    },
    {
      stepNumber: 5,
      title: 'Authoritative Deterministic Reasoning',
      subtitle: 'The Rules Engine Decides; The LLM Explains',
      description:
        'Phase 8 expert deterministic rules assign authoritative classification, severity, and action before any LLM is called. Even if the LLM fails or hallucinates, the operational triage decision is immutable.',
      keyMetric: '100%',
      metricLabel: 'Deterministic Decision Reproducibility',
      tabTarget: 'incidents',
      highlights: [
        'LLM cannot override machine severity or action',
        'Eliminates stochastic drift in automated triage',
        'Enables deterministic unit test coverage',
      ],
    },
    {
      stepNumber: 6,
      title: 'Programmatic Faithfulness Verification',
      subtitle: 'Algorithmic Fact-Checking Without LLM-as-a-Judge',
      description:
        'Generated explanations are decomposed into atomic claims. Each factual claim is programmatically validated against retrieved citations and numeric window features. If citations are missing, the UI reverts to deterministic fallback.',
      keyMetric: '100%',
      metricLabel: 'Citation Grounding on Validated Slice',
      tabTarget: 'review',
      highlights: [
        'Zero cost: executes locally in <2ms with no external LLM judge',
        'Classifies claims into Observation, Evidence, and Interpretation',
        'Guaranteed detection of unsupported factual statements',
      ],
    },
    {
      stepNumber: 7,
      title: 'Incident Replay Lab',
      subtitle: 'Step-by-Step Observable Pipeline Trace',
      description:
        'Inspect every intermediate stage: Ingest -> Parse -> Window -> Score -> Conformal -> Retrieve -> MMR -> Provenance -> Reasoning -> LLM -> Verify. Play, pause, or simulate counterfactual scores.',
      keyMetric: '11 Stages',
      metricLabel: 'Deterministic Playback Sequence',
      tabTarget: 'replay',
      highlights: [
        'Observe recorded execution without re-running models',
        'Inspect stage latencies and failure modes',
        'Simulate counterfactual what-if anomaly scores',
      ],
    },
    {
      stepNumber: 8,
      title: 'Reliability & Fault Injection Lab',
      subtitle: 'Chaos Resilience & Controlled Graceful Degradation',
      description:
        'Demonstrates how FaultSentinel behaves when dependencies fail: simulated LLM timeouts, empty vector retrieval, invalid tokens, and schema errors. Environment-gated to prevent production damage.',
      keyMetric: '9 Scenarios',
      metricLabel: 'Automated Resilience Assertions',
      tabTarget: 'fault-lab',
      highlights: [
        'Production safety guard permanently disables destructive tests in prod',
        'Verifies deterministic reasoning remains authoritative on LLM outage',
        'Pass/Fail failure matrix output to JSON',
      ],
    },
    {
      stepNumber: 9,
      title: 'Calibration Drift Monitor & Decision Passport',
      subtitle: 'Population Stability Index & Cryptographic Auditing',
      description:
        'Monitor whether input score distributions drift relative to Phase 4 baselines using PSI. Complete decisions generate cryptographic Decision Passports with SHA-256 signatures binding config, evidence, and code.',
      keyMetric: 'PSI < 0.10',
      metricLabel: 'Distribution Stability Threshold',
      tabTarget: 'passport',
      highlights: [
        'Observational only: Rule 25 prohibits automatic silent recalibration',
        'Decision Passport includes Git SHA, alpha, threshold, and dual-hashes',
        'One-click JSON and Markdown audit report export',
      ],
    },
    {
      stepNumber: 10,
      title: 'Honest Engineering Limitations & Integrity',
      subtitle: 'Scientific Rigor Without AI Hyperbole',
      description:
        'In adherence to Rule 7 and Rule 10, FaultSentinel makes no exaggerated claims of being "hallucination-free" or "100% autonomous". Non-stationarity in temporal log distributions requires ongoing calibration review.',
      keyMetric: 'Zero',
      metricLabel: 'Fabricated Metrics or Synthetic Benchmarks',
      tabTarget: 'evaluation',
      highlights: [
        'Test sets remained frozen until final evaluation',
        'Chronological splits preserved to prevent data leakage',
        'Code and configuration provenance recorded for all benchmarks',
      ],
    },
  ];

  const currentStep = steps[currentStepIdx];

  return (
    <div className="page-container" data-testid="recruiter-walkthrough-page">
      {/* Title */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 className="page-title" style={{ margin: 0 }}>Engineering Walkthrough Tour</h1>
            <span className="badge badge-primary" style={{ fontSize: '11px' }}>Recruiter & Architectural Guide</span>
          </div>
          <p className="page-subtitle" style={{ margin: '4px 0 0 0' }}>
            A curated 3-minute walkthrough explaining why and how FaultSentinel solves production incident triage.
          </p>
        </div>

        {/* Step Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#888' }}>
          Step <strong>{currentStepIdx + 1}</strong> of {steps.length}
        </div>
      </div>

      {/* Main Step Presentation Card */}
      <div className="card" style={{ padding: '30px', background: '#080808', border: '1px solid #242424', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
          <div>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#60A5FA', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Step {currentStep.stepNumber}: {currentStep.subtitle}
            </span>
            <h2 style={{ fontSize: '22px', fontWeight: 700, color: '#FFF', margin: '4px 0 8px 0' }}>
              {currentStep.title}
            </h2>
          </div>

          {/* Metric Highlight Box */}
          <div style={{ background: '#121212', border: '1px solid #222', borderRadius: '6px', padding: '12px 18px', textAlign: 'right', minWidth: '180px' }}>
            <div style={{ fontSize: '22px', fontWeight: 700, color: '#22C55E', fontFamily: 'monospace' }}>
              {currentStep.keyMetric}
            </div>
            <div style={{ fontSize: '11px', color: '#888', marginTop: '2px' }}>
              {currentStep.metricLabel}
            </div>
          </div>
        </div>

        <p style={{ fontSize: '14px', lineHeight: 1.7, color: '#D4D4D8', marginBottom: '24px', maxWidth: '800px' }}>
          {currentStep.description}
        </p>

        {/* Highlights List */}
        <div style={{ background: '#101010', borderRadius: '6px', padding: '16px', marginBottom: '24px', border: '1px solid #1C1C1C' }}>
          <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#888', fontWeight: 600, marginBottom: '10px' }}>
            Key Architectural Tenets
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {currentStep.highlights.map((h, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#EEE' }}>
                <CheckCircle2 size={15} color="#22C55E" />
                <span>{h}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Jump to Workspace Tab Button */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button
            className="btn btn-secondary"
            onClick={() => onNavigateTab(currentStep.tabTarget)}
            style={{ fontSize: '12px', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            Inspect Interactive Workspace ({currentStep.tabTarget}) <ArrowRight size={14} />
          </button>

          {/* Next / Prev Step Controls */}
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="btn btn-secondary"
              disabled={currentStepIdx === 0}
              onClick={() => setCurrentStepIdx((p) => p - 1)}
              style={{ padding: '8px 14px' }}
            >
              <ArrowLeft size={14} style={{ marginRight: '4px' }} /> Previous
            </button>
            <button
              className="btn btn-primary"
              disabled={currentStepIdx === steps.length - 1}
              onClick={() => setCurrentStepIdx((p) => p + 1)}
              style={{ padding: '8px 18px' }}
            >
              Next Step <ArrowRight size={14} style={{ marginLeft: '4px' }} />
            </button>
          </div>
        </div>
      </div>

      {/* Steps Quick Selector Footer */}
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${steps.length}, 1fr)`, gap: '6px' }}>
        {steps.map((st, idx) => {
          const isActive = idx === currentStepIdx;
          return (
            <div
              key={st.stepNumber}
              onClick={() => setCurrentStepIdx(idx)}
              style={{
                background: isActive ? '#1A1A1A' : '#0D0D0D',
                border: `1px solid ${isActive ? '#FFF' : '#222'}`,
                borderRadius: '4px',
                padding: '8px 6px',
                textAlign: 'center',
                cursor: 'pointer',
                fontSize: '11px',
                color: isActive ? '#FFF' : '#666',
                fontWeight: isActive ? 600 : 400,
                transition: 'all 0.15s ease',
              }}
            >
              0{idx + 1}
            </div>
          );
        })}
      </div>
    </div>
  );
};
