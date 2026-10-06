import React, { useState } from 'react';
import { ProcessingMetadata as ProcessingMetadataType } from '../types';

interface ProcessingMetadataProps {
  metadata: ProcessingMetadataType;
  requestId: string;
}

export const ProcessingMetadata: React.FC<ProcessingMetadataProps> = ({
  metadata,
  requestId,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="panel" data-testid="processing-metadata-panel">
      <div
        className="panel-header"
        style={{ cursor: 'pointer', marginBottom: isOpen ? 12 : 0, borderBottom: isOpen ? '1px solid var(--color-border-subtle)' : 'none' }}
        onClick={() => setIsOpen(!isOpen)}
        data-testid="toggle-metadata-btn"
      >
        <span className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span>{isOpen ? '▼' : '▶'}</span> Execution Telemetry & Diagnostic Metadata
        </span>
        <span style={{ fontSize: 11, color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
          REQ: {requestId}
        </span>
      </div>

      {isOpen && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }} data-testid="metadata-content">
          <div>
            <span className="decision-metric-label">Parsed Record Count</span>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--color-text-primary)' }}>
              {typeof metadata.record_count === 'number' ? metadata.record_count : 'N/A'}
            </div>
          </div>
          <div>
            <span className="decision-metric-label">Orchestration Model</span>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--color-text-primary)' }}>
              {metadata.model_name ? String(metadata.model_name) : 'Phase 9 Mock Provider'}
            </div>
          </div>
          <div>
            <span className="decision-metric-label">Provider Subsystem</span>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--color-text-primary)' }}>
              {metadata.provider ? String(metadata.provider) : 'Deterministic Offline Mock'}
            </div>
          </div>
          <div>
            <span className="decision-metric-label">Tracing Identifier</span>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--color-text-code)' }}>
              {requestId}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
