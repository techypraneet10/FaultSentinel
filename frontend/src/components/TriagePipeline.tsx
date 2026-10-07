import React, { useState } from 'react';
import {
  FileText,
  Binary,
  Gauge,
  ShieldAlert,
  Search,
  Sparkles,
  CheckCircle,
  ChevronRight,
  Info,
} from 'lucide-react';
import { StageInspector, PipelineStageInfo } from './StageInspector';
import { PIPELINE_STAGES } from '../utils/pipelineStages';

interface TriagePipelineProps {
  activeStageId?: string;
  onSelectStage?: (stageId: string) => void;
}

export const TriagePipeline: React.FC<TriagePipelineProps> = ({
  activeStageId,
  onSelectStage,
}) => {
  const [inspectedStage, setInspectedStage] = useState<PipelineStageInfo | null>(null);

  const handleStageClick = (stage: PipelineStageInfo) => {
    setInspectedStage(stage);
    if (onSelectStage) {
      onSelectStage(stage.id);
    }
  };

  const getStageIcon = (id: string) => {
    switch (id) {
      case 'ingest':
        return <FileText size={15} />;
      case 'parse':
        return <Binary size={15} />;
      case 'score':
        return <Gauge size={15} />;
      case 'conformal-gate':
        return <ShieldAlert size={15} />;
      case 'retrieve':
        return <Search size={15} />;
      case 'explain':
        return <Sparkles size={15} />;
      case 'verify':
        return <CheckCircle size={15} />;
      default:
        return <Info size={15} />;
    }
  };

  return (
    <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface)', padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
                fontWeight: 700,
                color: 'var(--color-text-pure)',
                letterSpacing: '1px',
                textTransform: 'uppercase',
              }}
            >
              TRIAGE PIPELINE
            </span>
            <span
              style={{
                fontSize: '10px',
                fontFamily: 'var(--font-mono)',
                color: 'var(--color-text-muted)',
                backgroundColor: 'var(--color-bg-base)',
                padding: '1px 6px',
                borderRadius: '3px',
                border: '1px solid var(--color-border-subtle)',
              }}
            >
              INTERACTIVE ARCHITECTURE
            </span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', margin: 0 }}>
            From raw logs to verified explanations — selective conformal gate controls expensive downstream processing
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--color-border-active)' }} />
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
              Deterministic Core
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--color-info)' }} />
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
              Downstream Escalation
            </span>
          </div>
        </div>
      </div>

      {/* Horizontal Pipeline Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(7, 1fr)',
          gap: '8px',
          alignItems: 'stretch',
          position: 'relative',
        }}
      >
        {PIPELINE_STAGES.map((stage, idx) => {
          const isSelected = activeStageId === stage.id || inspectedStage?.id === stage.id;
          const isGate = stage.id === 'conformal-gate';
          const isDownstream = stage.isDownstreamOfGate;

          return (
            <div
              key={stage.id}
              onClick={() => handleStageClick(stage)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  handleStageClick(stage);
                }
              }}
              style={{
                backgroundColor: isSelected
                  ? 'var(--color-bg-surface-elevated)'
                  : isGate
                  ? '#130d08'
                  : 'var(--color-bg-base)',
                border: isSelected
                  ? '1px solid #525252'
                  : isGate
                  ? '1px solid var(--color-warning)'
                  : isDownstream
                  ? '1px solid #292929'
                  : '1px solid var(--color-border-subtle)',
                borderRadius: '6px',
                padding: '12px 10px',
                cursor: 'pointer',
                transition: 'all 0.15s ease-in-out',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                minHeight: '120px',
                position: 'relative',
              }}
              title={`Click to inspect ${stage.name}`}
            >
              {/* Connector arrow indicator */}
              {idx < PIPELINE_STAGES.length - 1 && (
                <div
                  style={{
                    position: 'absolute',
                    right: '-7px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    zIndex: 2,
                    color: 'var(--color-border-active)',
                    pointerEvents: 'none',
                  }}
                >
                  <ChevronRight size={12} />
                </div>
              )}

              <div>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '8px',
                  }}
                >
                  <div
                    style={{
                      color: isGate
                        ? 'var(--color-warning)'
                        : isDownstream
                        ? 'var(--color-info)'
                        : 'var(--color-text-pure)',
                    }}
                  >
                    {getStageIcon(stage.id)}
                  </div>
                  <span
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '10px',
                      color: 'var(--color-text-muted)',
                    }}
                  >
                    0{idx + 1}
                  </span>
                </div>

                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '11px',
                    fontWeight: 700,
                    color: 'var(--color-text-pure)',
                    letterSpacing: '0.5px',
                    marginBottom: '2px',
                  }}
                >
                  {stage.label}
                </div>

                <div
                  style={{
                    fontSize: '11px',
                    color: 'var(--color-text-secondary)',
                    lineHeight: 1.2,
                  }}
                >
                  {stage.id === 'conformal-gate'
                    ? 'α = 0.05 Gate'
                    : stage.id === 'score'
                    ? 'B2 GRU Scorer'
                    : stage.id === 'explain'
                    ? 'LLM Explainer'
                    : stage.name.split(' ')[0]}
                </div>
              </div>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-end',
                  marginTop: '10px',
                  paddingTop: '6px',
                  borderTop: '1px solid var(--color-border-subtle)',
                }}
              >
                <span
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '10px',
                    color: isGate ? 'var(--color-warning)' : 'var(--color-success)',
                    textTransform: 'uppercase',
                    fontWeight: 600,
                  }}
                >
                  {stage.status}
                </span>
                <span
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '10px',
                    color: 'var(--color-text-muted)',
                  }}
                >
                  {stage.latency}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div
        style={{
          marginTop: '12px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '11px',
          color: 'var(--color-text-muted)',
          fontFamily: 'var(--font-mono)',
          padding: '6px 10px',
          backgroundColor: 'var(--color-bg-base)',
          borderRadius: '4px',
          border: '1px solid var(--color-border-subtle)',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <ShieldAlert size={12} color="var(--color-warning)" />
          <strong>GATING GUARANTEE:</strong> Normal windows (94.78%) are auto-cleared at Stage 04 without triggering Stages 05–07.
        </span>
        <span style={{ color: 'var(--color-text-secondary)' }}>
          Click any stage to open Technical Inspector
        </span>
      </div>

      <StageInspector
        stage={inspectedStage}
        onClose={() => setInspectedStage(null)}
      />
    </div>
  );
};
