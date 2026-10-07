import React, { useState, useEffect } from 'react';
import {
  RefreshCw,
  ShieldCheck,
  ListOrdered,
} from 'lucide-react';
import { apiService } from '../services/api';

export const CalibrationDriftPage: React.FC = () => {
  const [simulateDrift, setSimulateDrift] = useState<boolean>(false);
  const [dataset] = useState<string>('hdfs');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchDrift = async () => {
    setLoading(true);
    try {
      const res = await apiService.evaluateCalibrationDrift(dataset, simulateDrift);
      setData(res);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDrift();
  }, [simulateDrift, dataset]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'STABLE':
        return '#22C55E';
      case 'WATCH':
        return '#F59E0B';
      case 'DRIFT DETECTED':
        return '#EF4444';
      default:
        return '#9CA3AF';
    }
  };

  return (
    <div className="page-container" data-testid="calibration-drift-page">
      {/* Title & Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 className="page-title" style={{ margin: 0 }}>Calibration Health & Drift Monitor</h1>
            <span className="badge badge-neutral" style={{ fontSize: '11px', border: '1px solid #333' }}>
              Population Stability Index
            </span>
          </div>
          <p className="page-subtitle" style={{ margin: '4px 0 0 0' }}>
            Tracks empirical anomaly score distributions against frozen Phase 4 calibration baselines. Observational only.
          </p>
        </div>

        {/* Simulation Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '12px', color: '#888' }}>Test Mode:</span>
          <button
            className={`btn ${!simulateDrift ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '12px', padding: '6px 12px' }}
            onClick={() => setSimulateDrift(false)}
          >
            Stable Distribution
          </button>
          <button
            className={`btn ${simulateDrift ? 'btn-danger' : 'btn-secondary'}`}
            style={{ fontSize: '12px', padding: '6px 12px' }}
            onClick={() => setSimulateDrift(true)}
          >
            Simulate Drift Shift
          </button>
          <button className="btn btn-secondary" style={{ padding: '6px 10px' }} onClick={fetchDrift} title="Refresh">
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Safety Notice Banner */}
      <div
        style={{
          background: 'rgba(59, 130, 246, 0.05)',
          border: '1px solid #2563EB',
          borderRadius: '6px',
          padding: '12px 16px',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
        }}
      >
        <ShieldCheck size={18} color="#60A5FA" />
        <div style={{ fontSize: '12px', color: '#BFDBFE' }}>
          <strong>SCIENTIFIC SAFETY INVARIANT (Rule 25):</strong> Drift detection does NOT automatically recalibrate or retune $\alpha$ or $\tau_\alpha$. It flags a formal engineering review requirement to prevent silent model mutation.
        </div>
      </div>

      {loading && (
        <div style={{ padding: '40px', textAlign: 'center', color: '#888' }}>
          Evaluating calibration empirical distribution...
        </div>
      )}

      {!loading && data && (
        <>
          {/* Top Metric Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '14px', marginBottom: '20px' }}>
            {/* Status Card */}
            <div className="card" style={{ padding: '16px', background: '#0A0A0A', border: `1px solid ${getStatusColor(data.drift_status)}` }}>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#888', marginBottom: '6px' }}>
                Drift Status
              </div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: getStatusColor(data.drift_status) }}>
                {data.drift_status}
              </div>
              <div style={{ fontSize: '11px', color: '#777', marginTop: '4px' }}>
                {data.recommendation}
              </div>
            </div>

            {/* PSI Card */}
            <div className="card" style={{ padding: '16px', background: '#0A0A0A', border: '1px solid #1E1E1E' }}>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#888', marginBottom: '6px' }}>
                PSI Metric
              </div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#FFF', fontFamily: 'monospace' }}>
                {data.metrics?.population_stability_index}
              </div>
              <div style={{ fontSize: '11px', color: '#777', marginTop: '4px' }}>
                Threshold: &lt; 0.10 Stable
              </div>
            </div>

            {/* Alpha & Threshold */}
            <div className="card" style={{ padding: '16px', background: '#0A0A0A', border: '1px solid #1E1E1E' }}>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#888', marginBottom: '6px' }}>
                Conformal $\tau_\alpha$ (at $\alpha={data.metrics?.current_alpha}$)
              </div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#FFF', fontFamily: 'monospace' }}>
                {data.metrics?.calibration_threshold}
              </div>
              <div style={{ fontSize: '11px', color: '#777', marginTop: '4px' }}>
                Target $\alpha = {data.metrics?.current_alpha}$
              </div>
            </div>

            {/* Escalation Rate Comparison */}
            <div className="card" style={{ padding: '16px', background: '#0A0A0A', border: '1px solid #1E1E1E' }}>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#888', marginBottom: '6px' }}>
                Escalation Rate
              </div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#FFF', fontFamily: 'monospace' }}>
                {(data.metrics?.current_escalation_rate * 100).toFixed(2)}%
              </div>
              <div style={{ fontSize: '11px', color: '#777', marginTop: '4px' }}>
                Ref: {(data.metrics?.reference_escalation_rate * 100).toFixed(2)}%
              </div>
            </div>

            {/* Sample Size */}
            <div className="card" style={{ padding: '16px', background: '#0A0A0A', border: '1px solid #1E1E1E' }}>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#888', marginBottom: '6px' }}>
                Sample Size
              </div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#FFF', fontFamily: 'monospace' }}>
                {data.metrics?.sample_size}
              </div>
              <div style={{ fontSize: '11px', color: '#777', marginTop: '4px' }}>
                Ref Calib: {data.metrics?.reference_sample_size}
              </div>
            </div>
          </div>

          {/* Histogram Chart Comparison */}
          <div className="card" style={{ padding: '20px', background: '#0A0A0A', border: '1px solid #1E1E1E', marginBottom: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#FFF', margin: 0 }}>
                  Score Distribution Drift (Histogram Comparison)
                </h3>
                <span style={{ fontSize: '12px', color: '#777' }}>
                  White bars = Reference Calibration Distribution; Colored bars = Current Window Scores
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '11px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <div style={{ width: '10px', height: '10px', background: '#FFFFFF', borderRadius: '2px' }} />
                  <span style={{ color: '#CCC' }}>Reference Calibration</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <div style={{ width: '10px', height: '10px', background: getStatusColor(data.drift_status), borderRadius: '2px' }} />
                  <span style={{ color: '#CCC' }}>Current Windows</span>
                </div>
              </div>
            </div>

            {/* Bar Chart Representation */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: `repeat(${data.histogram?.length || 1}, 1fr)`,
                alignItems: 'flex-end',
                height: '180px',
                gap: '8px',
                paddingTop: '20px',
                borderBottom: '1px solid #222',
              }}
            >
              {data.histogram?.map((bar: any, idx: number) => {
                const maxDensity = 1.5;
                const refHeight = Math.min(100, (bar.reference_density / maxDensity) * 100);
                const currHeight = Math.min(100, (bar.current_density / maxDensity) * 100);

                return (
                  <div key={idx} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
                    <div style={{ display: 'flex', gap: '3px', alignItems: 'flex-end', height: '140px' }}>
                      {/* Reference Bar (White) */}
                      <div
                        style={{
                          width: '12px',
                          height: `${refHeight}%`,
                          background: '#FFFFFF',
                          borderRadius: '2px 2px 0 0',
                          opacity: 0.85,
                        }}
                        title={`Ref Density: ${bar.reference_density}`}
                      />
                      {/* Current Bar (Gray/Amber/Red) */}
                      <div
                        style={{
                          width: '12px',
                          height: `${currHeight}%`,
                          background: bar.status_color,
                          borderRadius: '2px 2px 0 0',
                        }}
                        title={`Current Density: ${bar.current_density}`}
                      />
                    </div>
                    <div style={{ fontSize: '9px', fontFamily: 'monospace', color: '#666', marginTop: '6px' }}>
                      {bar.midpoint}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Quantile Shift & Suggested Workflow */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            {/* Left: Quantile Shift Table */}
            <div className="card" style={{ padding: '18px', background: '#0A0A0A', border: '1px solid #1E1E1E' }}>
              <h3 style={{ fontSize: '13px', fontWeight: 600, textTransform: 'uppercase', color: '#888', marginBottom: '12px' }}>
                Quantile Shift vs. Reference
              </h3>
              <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #222', color: '#666' }}>
                    <th style={{ textAlign: 'left', padding: '6px 0' }}>Quantile</th>
                    <th style={{ textAlign: 'right', padding: '6px 0' }}>Delta Shift</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.quantile_shifts || {}).map(([q, val]: any) => (
                    <tr key={q} style={{ borderBottom: '1px solid #141414' }}>
                      <td style={{ padding: '8px 0', color: '#CCC', textTransform: 'uppercase' }}>{q}</td>
                      <td style={{ padding: '8px 0', textAlign: 'right', fontFamily: 'monospace', color: Math.abs(val) > 0.1 ? '#F59E0B' : '#FFF' }}>
                        {val > 0 ? `+${val}` : val}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Right: Suggested 8-Step Review Workflow */}
            <div className="card" style={{ padding: '18px', background: '#0A0A0A', border: '1px solid #1E1E1E' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <ListOrdered size={16} color="#A1A1AA" />
                <h3 style={{ fontSize: '13px', fontWeight: 600, textTransform: 'uppercase', color: '#888', margin: 0 }}>
                  Calibration Review Protocol
                </h3>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                {data.suggested_review_workflow?.map((step: string, idx: number) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                    <span style={{ fontFamily: 'monospace', color: '#666', minWidth: '16px' }}>0{idx + 1}</span>
                    <span style={{ color: '#D4D4D8', lineHeight: 1.4 }}>{step.substring(3)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
