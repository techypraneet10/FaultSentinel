import React from 'react';
import { X, CheckCircle2, AlertTriangle } from 'lucide-react';

export interface PipelineStageInfo {
  id: string;
  name: string;
  label: string;
  purpose: string;
  input: string;
  output: string;
  status: 'healthy' | 'active' | 'calibrated' | 'verified' | 'bypassed';
  latency: string;
  implementation: string;
  dependencies: string[];
  failureModes: string[];
  isDownstreamOfGate: boolean;
}

interface StageInspectorProps {
  stage: PipelineStageInfo | null;
  onClose: () => void;
}

export const StageInspector: React.FC<StageInspectorProps> = ({ stage, onClose }) => {
  if (!stage) return null;

  return (
    <div
      className="drawer-backdrop"
      onClick={onClose}
      data-testid="stage-inspector-drawer"
      style={{ zIndex: 120 }}
    >
      <div
        className="drawer-content"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '540px',
          maxWidth: '92vw',
          backgroundColor: 'var(--color-bg-surface)',
          borderLeft: '1px solid var(--color-border-default)',
        }}
      >
        <div className="drawer-header" style={{ paddingBottom: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)' }}>
                STAGE: {stage.id.toUpperCase()}
              </span>
              {stage.isDownstreamOfGate ? (
                <span
                  className="badge"
                  style={{
                    backgroundColor: '#171717',
                    border: '1px solid #333333',
                    color: '#e5e5e5',
                    fontSize: '10px',
                  }}
                >
                  DOWNSTREAM OF GATE
                </span>
              ) : (
                <span
                  className="badge"
                  style={{
                    backgroundColor: '#101b13',
                    border: '1px solid #1c4728',
                    color: 'var(--color-success)',
                    fontSize: '10px',
                  }}
                >
                  UPSTREAM CORE
                </span>
              )}
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-text-pure)' }}>
              {stage.name}
            </h3>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onClose}
            aria-label="Close inspector"
            style={{ padding: '6px 10px' }}
          >
            <X size={14} />
          </button>
        </div>

        <div className="drawer-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface-raised)' }}>
            <span className="decision-metric-label">Purpose</span>
            <p style={{ fontSize: '13px', color: 'var(--color-text-primary)', marginTop: '4px', lineHeight: 1.5 }}>
              {stage.purpose}
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface-raised)', marginBottom: 0 }}>
              <span className="decision-metric-label">Operational Status</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
                <CheckCircle2 size={14} color="var(--color-success)" />
                <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-pure)', textTransform: 'capitalize' }}>
                  {stage.status}
                </span>
              </div>
            </div>

            <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface-raised)', marginBottom: 0 }}>
              <span className="decision-metric-label">Nominal Latency</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 700, color: 'var(--color-text-pure)' }}>
                  {stage.latency}
                </span>
              </div>
            </div>
          </div>

          <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface-raised)' }}>
            <span className="decision-metric-label">Input / Output Contract</span>
            <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div>
                <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Input:</span>
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '12px',
                    color: 'var(--color-text-primary)',
                    backgroundColor: 'var(--color-bg-base)',
                    padding: '6px 10px',
                    borderRadius: '4px',
                    border: '1px solid var(--color-border-subtle)',
                    marginTop: '2px',
                  }}
                >
                  {stage.input}
                </div>
              </div>
              <div>
                <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Output:</span>
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '12px',
                    color: 'var(--color-text-primary)',
                    backgroundColor: 'var(--color-bg-base)',
                    padding: '6px 10px',
                    borderRadius: '4px',
                    border: '1px solid var(--color-border-subtle)',
                    marginTop: '2px',
                  }}
                >
                  {stage.output}
                </div>
              </div>
            </div>
          </div>

          <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface-raised)' }}>
            <span className="decision-metric-label">Implementation & Architecture</span>
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '12px',
                color: 'var(--color-text-code)',
                marginTop: '6px',
                backgroundColor: 'var(--color-bg-base)',
                padding: '8px 10px',
                borderRadius: '4px',
                border: '1px solid var(--color-border-subtle)',
              }}
            >
              {stage.implementation}
            </div>
          </div>

          <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface-raised)' }}>
            <span className="decision-metric-label">Subsystem Dependencies</span>
            <ul style={{ listStyle: 'none', padding: 0, marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {stage.dependencies.map((dep, idx) => (
                <li
                  key={idx}
                  style={{
                    fontSize: '12px',
                    color: 'var(--color-text-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <span style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: 'var(--color-border-active)' }} />
                  {dep}
                </li>
              ))}
            </ul>
          </div>

          <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface-raised)', borderColor: 'var(--color-border-default)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
              <AlertTriangle size={13} color="var(--color-warning)" />
              <span className="decision-metric-label" style={{ color: 'var(--color-warning)', margin: 0 }}>
                Known Failure Modes & Guardrails
              </span>
            </div>
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {stage.failureModes.map((fm, idx) => (
                <li
                  key={idx}
                  style={{
                    fontSize: '12px',
                    color: 'var(--color-text-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <span style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: 'var(--color-warning)' }} />
                  {fm}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
