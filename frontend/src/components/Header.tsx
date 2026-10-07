import React from 'react';
import { ConnectionState } from '../types';
import { HealthIndicator } from './HealthIndicator';

interface HeaderProps {
  activeTab: string;
  connectionState: ConnectionState;
  onRefreshHealth: () => void;
  dataset?: string;
  onDatasetChange?: (ds: 'hdfs' | 'bgl') => void;
  timeRange?: string;
  onTimeRangeChange?: (range: string) => void;
  environment?: string;
  onEnvironmentChange?: (env: string) => void;
  isDemo?: boolean;
  onToggleDemo?: (isDemo: boolean) => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  connectionState,
  onRefreshHealth,
  dataset = 'hdfs',
  onDatasetChange,
  timeRange = '24h',
  onTimeRangeChange,
  environment = 'demo',
  onEnvironmentChange,
  isDemo = true,
  onToggleDemo,
}) => {
  const getPageTitleAndDesc = (tab: string) => {
    switch (tab) {
      case 'overview':
        return {
          title: 'FaultSentinel Command Center',
          subtitle: 'AI-assisted incident triage with calibrated escalation',
        };
      case 'analyze':
        return {
          title: 'Live Incident Triage',
          subtitle: 'Bounded operational log inspection with selective conformal escalation',
        };
      case 'incidents':
        return {
          title: 'Incident Directory & Registry',
          subtitle: 'Deterministic incident records, historical lineage, and audit trails',
        };
      case 'anomaly-explorer':
        return {
          title: 'Anomaly Explorer',
          subtitle: 'Chronological anomaly scoring with conformal risk boundary (α = 0.05)',
        };
      case 'review':
        return {
          title: 'Evidence Audit & Citations',
          subtitle: 'Cryptographic provenance and claim-level grounding verification',
        };
      case 'evaluation':
        return {
          title: 'Scientific Evaluation Lab',
          subtitle: 'Controlled benchmarks over frozen test partitions (Phase 12)',
        };
      case 'cost':
        return {
          title: 'Cost Intelligence & Efficiency',
          subtitle: 'Selective escalation operational metrics and LLM compute reduction',
        };
      case 'observatory':
        return {
          title: 'Model Observatory',
          subtitle: 'Subsystem health, parser latency, and scorer parameter invariants',
        };
      case 'architecture':
        return {
          title: 'System Architecture & Dataflow',
          subtitle: 'End-to-end processing pipeline from raw logs to verified explanations',
        };
      case 'walkthrough':
        return {
          title: 'Engineering Walkthrough Tour',
          subtitle: 'A structured 3-minute architectural demonstration of FaultSentinel',
        };
      case 'replay':
        return {
          title: 'Incident Replay Lab',
          subtitle: 'Observable step-by-step playback of recorded pipeline decisions',
        };
      case 'fault-lab':
        return {
          title: 'Reliability & Fault Injection Lab',
          subtitle: 'Controlled dependency failure simulations and safety assertion verifications',
        };
      case 'calibration-health':
        return {
          title: 'Calibration Health & Drift Monitor',
          subtitle: 'Observational Population Stability Index tracking over anomaly score distributions',
        };
      case 'evidence-graph':
        return {
          title: 'Evidence Graph & Provenance DAG',
          subtitle: 'Cryptographic inspection connecting decisions to citations and source logs',
        };
      case 'passport':
        return {
          title: 'Decision Passport & Audit Record',
          subtitle: 'Cryptographically signed audit document binding triage decisions to provenance',
        };
      case 'status':
        return {
          title: 'Configuration & Telemetry',
          subtitle: 'FastAPI probe endpoints, Prometheus metrics, and candidate SLIs',
        };
      default:
        return {
          title: 'FaultSentinel Command Center',
          subtitle: 'AI-assisted incident triage with calibrated escalation',
        };
    }
  };

  const { title, subtitle } = getPageTitleAndDesc(activeTab);

  return (
    <header className="app-header" data-testid="app-header">
      <div className="header-title-section">
        <h1 className="header-title">{title}</h1>
        <p className="header-subtitle">{subtitle}</p>
      </div>

      <div className="header-controls-section">
        {/* Dataset selector */}
        <div className="header-select-wrapper">
          <select
            className="header-select"
            value={dataset}
            onChange={(e) => onDatasetChange && onDatasetChange(e.target.value as 'hdfs' | 'bgl')}
            aria-label="Dataset partition selection"
          >
            <option value="hdfs">HDFS Partition</option>
            <option value="bgl">BGL Partition</option>
          </select>
        </div>

        {/* Time range selector */}
        <div className="header-select-wrapper">
          <select
            className="header-select"
            value={timeRange}
            onChange={(e) => onTimeRangeChange && onTimeRangeChange(e.target.value)}
            aria-label="Time range selection"
          >
            <option value="1h">Last 1 hour</option>
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
            <option value="all">Full Chronological</option>
          </select>
        </div>

        {/* Environment selector */}
        <div className="header-select-wrapper">
          <select
            className="header-select"
            value={environment}
            onChange={(e) => onEnvironmentChange && onEnvironmentChange(e.target.value)}
            aria-label="Target deployment environment"
          >
            <option value="demo">Demo Fixture</option>
            <option value="staging">Staging</option>
            <option value="production">Production</option>
          </select>
        </div>

        {/* Mode indicator */}
        <button
          type="button"
          className={`header-mode-btn ${isDemo ? 'demo' : 'live'}`}
          onClick={() => onToggleDemo && onToggleDemo(!isDemo)}
          title="Toggle Live / Demo mode"
        >
          <span className={`header-mode-dot ${isDemo ? 'demo' : 'live'}`} />
          <span>{isDemo ? 'DEMO' : 'LIVE'}</span>
        </button>

        {/* Health probe & refresh */}
        <HealthIndicator connectionState={connectionState} onRefresh={onRefreshHealth} />
      </div>
    </header>
  );
};
