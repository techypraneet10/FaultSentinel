import React, { useState } from 'react';

interface AnomalyDataPoint {
  id: string;
  time: string;
  score: number;
  threshold: number;
  isEscalated: boolean;
  verdict: 'INCIDENT' | 'SUSPICIOUS' | 'NORMAL';
  windowId: string;
}

// 25 chronological evaluation windows sampled from HDFS test/calibration partition
const SAMPLE_WINDOW_SERIES: AnomalyDataPoint[] = [
  { id: 'w-01', time: '20:30:00', score: 0.12, threshold: 1.15, isEscalated: false, verdict: 'NORMAL', windowId: 'blk_01' },
  { id: 'w-02', time: '20:31:00', score: 0.15, threshold: 1.15, isEscalated: false, verdict: 'NORMAL', windowId: 'blk_02' },
  { id: 'w-03', time: '20:32:00', score: 0.18, threshold: 1.15, isEscalated: false, verdict: 'NORMAL', windowId: 'blk_03' },
  { id: 'w-04', time: '20:33:00', score: 0.22, threshold: 1.15, isEscalated: false, verdict: 'NORMAL', windowId: 'blk_04' },
  { id: 'w-05', time: '20:34:00', score: 0.14, threshold: 1.15, isEscalated: false, verdict: 'NORMAL', windowId: 'blk_05' },
  { id: 'w-06', time: '20:35:00', score: 1.48, threshold: 1.15, isEscalated: true, verdict: 'INCIDENT', windowId: 'blk_-1608999687' },
  { id: 'w-07', time: '20:36:00', score: 1.32, threshold: 1.15, isEscalated: true, verdict: 'INCIDENT', windowId: 'blk_-1608999688' },
  { id: 'w-08', time: '20:37:00', score: 0.88, threshold: 1.15, isEscalated: false, verdict: 'NORMAL', windowId: 'blk_08' },
  { id: 'w-09', time: '20:38:00', score: 0.25, threshold: 1.15, isEscalated: false, verdict: 'NORMAL', windowId: 'blk_09' },
  { id: 'w-10', time: '20:39:00', score: 0.19, threshold: 1.15, isEscalated: false, verdict: 'NORMAL', windowId: 'blk_10' },
  { id: 'w-11', time: '20:40:00', score: 0.16, threshold: 1.15, isEscalated: false, verdict: 'NORMAL', windowId: 'blk_11' },
  { id: 'w-12', time: '20:41:00', score: 0.21, threshold: 1.15, isEscalated: false, verdict: 'NORMAL', windowId: 'blk_12' },
  { id: 'w-13', time: '20:42:00', score: 0.35, threshold: 1.15, isEscalated: false, verdict: 'NORMAL', windowId: 'blk_13' },
  { id: 'w-14', time: '20:43:00', score: 1.42, threshold: 1.15, isEscalated: true, verdict: 'INCIDENT', windowId: 'blk_34192049' },
  { id: 'w-15', time: '20:44:00', score: 0.72, threshold: 1.15, isEscalated: false, verdict: 'NORMAL', windowId: 'blk_15' },
  { id: 'w-16', time: '20:45:00', score: 0.18, threshold: 1.15, isEscalated: false, verdict: 'NORMAL', windowId: 'blk_16' },
  { id: 'w-17', time: '20:46:00', score: 0.15, threshold: 1.15, isEscalated: false, verdict: 'NORMAL', windowId: 'blk_17' },
  { id: 'w-18', time: '20:47:00', score: 0.19, threshold: 1.15, isEscalated: false, verdict: 'NORMAL', windowId: 'blk_18' },
  { id: 'w-19', time: '20:48:00', score: 0.24, threshold: 1.15, isEscalated: false, verdict: 'NORMAL', windowId: 'blk_19' },
  { id: 'w-20', time: '20:49:00', score: 0.28, threshold: 1.15, isEscalated: false, verdict: 'NORMAL', windowId: 'blk_20' },
];

export const AnomalyExplorerPage: React.FC = () => {
  const [selectedPoint, setSelectedPoint] = useState<AnomalyDataPoint | null>(SAMPLE_WINDOW_SERIES[5]);
  const [targetAlpha, setTargetAlpha] = useState<number>(0.05);

  const thresholdValue = 1.1546;
  const svgWidth = 840;
  const svgHeight = 280;
  const padLeft = 50;
  const padRight = 30;
  const padTop = 30;
  const padBottom = 40;

  const chartW = svgWidth - padLeft - padRight;
  const chartH = svgHeight - padTop - padBottom;
  const maxScore = 2.0;

  const getX = (idx: number) => padLeft + (idx / (SAMPLE_WINDOW_SERIES.length - 1)) * chartW;
  const getY = (val: number) => padTop + chartH - (val / maxScore) * chartH;

  const pathD = SAMPLE_WINDOW_SERIES.reduce((acc, pt, idx) => {
    const x = getX(idx);
    const y = getY(pt.score);
    return idx === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
  }, '');

  const thresholdY = getY(thresholdValue);

  return (
    <div data-testid="anomaly-explorer-page" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Top Banner & Control */}
      <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface)', padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div>
            <span className="panel-title">Chronological Anomaly Explorer</span>
            <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 2 }}>
              Anomaly score sequence evaluated against conformal boundary (α = {targetAlpha})
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 11, color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>
              TARGET RISK α:
            </span>
            <select
              className="form-select"
              style={{ width: 'auto', padding: '4px 8px', fontSize: 12 }}
              value={targetAlpha}
              onChange={(e) => setTargetAlpha(parseFloat(e.target.value))}
            >
              <option value="0.01">α = 0.01 (Strict, τ = 1.48)</option>
              <option value="0.05">α = 0.05 (Calibrated, τ = 1.15)</option>
              <option value="0.10">α = 0.10 (Permissive, τ = 0.92)</option>
            </select>
          </div>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', gap: 18, fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--color-text-secondary)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 14, height: 2, backgroundColor: '#ffffff' }} />
            <span>Anomaly Score (B2 GRU)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 14, height: 2, borderTop: '2px dashed #888888' }} />
            <span>Conformal Threshold (τ = 1.1546)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: 'var(--color-critical)' }} />
            <span>Escalated Incident (LLM Invoked)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#444444' }} />
            <span>Auto-cleared Normal (LLM Bypassed)</span>
          </div>
        </div>
      </div>

      {/* Primary SVG Chart */}
      <div className="panel" style={{ backgroundColor: '#050505', padding: '16px', overflowX: 'auto' }}>
        <svg width="100%" height={svgHeight} viewBox={`0 0 ${svgWidth} ${svgHeight}`} style={{ display: 'block' }}>
          {/* Grid lines */}
          {[0.0, 0.5, 1.0, 1.5, 2.0].map((val) => {
            const y = getY(val);
            return (
              <g key={val}>
                <line x1={padLeft} y1={y} x2={svgWidth - padRight} y2={y} stroke="#1a1a1a" strokeWidth={1} />
                <text x={padLeft - 8} y={y + 4} fill="#666666" fontSize={10} fontFamily="monospace" textAnchor="end">
                  {val.toFixed(1)}
                </text>
              </g>
            );
          })}

          {/* Time axis ticks */}
          {SAMPLE_WINDOW_SERIES.map((pt, idx) => {
            if (idx % 4 !== 0) return null;
            const x = getX(idx);
            return (
              <g key={pt.id}>
                <line x1={x} y1={svgHeight - padBottom} x2={x} y2={svgHeight - padBottom + 4} stroke="#333333" />
                <text x={x} y={svgHeight - padBottom + 16} fill="#666666" fontSize={10} fontFamily="monospace" textAnchor="middle">
                  {pt.time}
                </text>
              </g>
            );
          })}

          {/* Threshold line */}
          <line
            x1={padLeft}
            y1={thresholdY}
            x2={svgWidth - padRight}
            y2={thresholdY}
            stroke="#888888"
            strokeWidth={1.5}
            strokeDasharray="4 4"
          />
          <text x={svgWidth - padRight} y={thresholdY - 6} fill="#a3a3a3" fontSize={10} fontFamily="monospace" textAnchor="end">
            Threshold τ = {thresholdValue.toFixed(2)}
          </text>

          {/* Anomaly score line */}
          <path d={pathD} fill="none" stroke="#ffffff" strokeWidth={1.75} />

          {/* Points */}
          {SAMPLE_WINDOW_SERIES.map((pt, idx) => {
            const x = getX(idx);
            const y = getY(pt.score);
            const isSelected = selectedPoint?.id === pt.id;

            return (
              <circle
                key={pt.id}
                cx={x}
                cy={y}
                r={isSelected ? 6 : pt.isEscalated ? 4.5 : 3}
                fill={pt.isEscalated ? 'var(--color-critical)' : '#333333'}
                stroke={isSelected ? '#ffffff' : pt.isEscalated ? '#ff8080' : '#555555'}
                strokeWidth={isSelected ? 2 : 1}
                cursor="pointer"
                onClick={() => setSelectedPoint(pt)}
              />
            );
          })}
        </svg>
      </div>

      {/* Selected Point Inspector */}
      {selectedPoint && (
        <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface)', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span className="panel-title">Window Telemetry Inspector</span>
            <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)' }}>
              {selectedPoint.windowId}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
            <div>
              <div className="decision-metric-label">Timestamp</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--color-text-pure)' }}>
                {selectedPoint.time}
              </div>
            </div>
            <div>
              <div className="decision-metric-label">Anomaly Score (B2)</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: selectedPoint.isEscalated ? 'var(--color-critical)' : 'var(--color-text-pure)' }}>
                {selectedPoint.score.toFixed(2)}
              </div>
            </div>
            <div>
              <div className="decision-metric-label">Conformal Margin</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--color-text-secondary)' }}>
                {(selectedPoint.score - thresholdValue).toFixed(2)}
              </div>
            </div>
            <div>
              <div className="decision-metric-label">Conformal Gating Action</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: selectedPoint.isEscalated ? 'var(--color-warning)' : 'var(--color-success)' }}>
                {selectedPoint.isEscalated ? 'ESCALATE (To LLM)' : 'AUTO-CLEAR (Normal)'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
