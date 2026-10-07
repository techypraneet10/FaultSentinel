import React, { useState, useEffect } from 'react';
import { apiService, ApiError } from '../services/api';
import { HealthReadyResponse, RootMetadataResponse, DiagnosticsResponse } from '../types';
import { StatusBadge } from '../components/StatusBadge';

export const ApiStatusPage: React.FC = () => {
  const [liveStatus, setLiveStatus] = useState<string>('checking');
  const [readyData, setReadyData] = useState<HealthReadyResponse | null>(null);
  const [metadata, setMetadata] = useState<RootMetadataResponse | null>(null);
  const [diagnostics, setDiagnostics] = useState<DiagnosticsResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchStatus = async () => {
    setLoading(true);
    setErrorMessage(null);

    try {
      const live = await apiService.healthLive();
      setLiveStatus(live.status);

      const ready = await apiService.healthReady();
      setReadyData(ready);

      const meta = await apiService.fetchRootMetadata();
      setMetadata(meta);

      try {
        const diag = await apiService.fetchDiagnostics();
        setDiagnostics(diag);
      } catch {
        // Diagnostics optional
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMessage(`HTTP ${err.status}: ${err.message} (${err.code})`);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to connect to FaultSentinel API backend.');
      }
      setLiveStatus('offline');
      setReadyData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  return (
    <div data-testid="api-status-page" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">FastAPI Backend Health & Service Telemetry</span>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={fetchStatus}
            disabled={loading}
            data-testid="refresh-status-btn"
          >
            {loading ? 'Checking...' : 'Refresh Status'}
          </button>
        </div>

        {errorMessage && (
          <div
            style={{
              padding: '12px 16px',
              backgroundColor: 'var(--color-rejected-bg)',
              border: '1px solid var(--color-rejected-border)',
              borderRadius: 4,
              color: 'var(--color-rejected-text)',
              fontSize: 13,
              marginBottom: 16,
            }}
            data-testid="status-error-alert"
          >
            <strong>Backend Unreachable:</strong> {errorMessage}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16, marginBottom: 20 }}>
          <div className="panel" style={{ backgroundColor: 'var(--color-bg-base)' }}>
            <span className="decision-metric-label">Liveness Probe (/health/live)</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
              <StatusBadge status={liveStatus === 'ok' ? 'OPERATIONAL' : 'OFFLINE'} />
              <span style={{ fontSize: 13, color: 'var(--color-text-primary)' }}>
                {liveStatus === 'ok' ? 'Process Active' : 'Unresponsive'}
              </span>
            </div>
          </div>

          <div className="panel" style={{ backgroundColor: 'var(--color-bg-base)' }}>
            <span className="decision-metric-label">Readiness Probe (/health/ready)</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
              <StatusBadge status={readyData?.status === 'ready' ? 'READY' : 'NOT READY'} />
              <span style={{ fontSize: 13, color: 'var(--color-text-primary)' }}>
                {readyData?.status === 'ready' ? 'Ready for triage requests' : 'Dependencies uninitialized'}
              </span>
            </div>
          </div>

          <div className="panel" style={{ backgroundColor: 'var(--color-bg-base)' }}>
            <span className="decision-metric-label">API Root (/api/v1)</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
              <StatusBadge status={metadata?.status || 'UNKNOWN'} />
              <span style={{ fontSize: 13, color: 'var(--color-text-primary)' }}>
                {metadata ? `${metadata.service_name} v${metadata.api_version}` : 'Unavailable'}
              </span>
            </div>
          </div>
        </div>

        {readyData && readyData.checks && (
          <div style={{ marginTop: 12 }}>
            <h4 style={{ fontSize: 12, textTransform: 'uppercase', color: 'var(--color-text-secondary)', marginBottom: 8 }}>
              Subsystem Dependency State Checks
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
              {Object.entries(readyData.checks).map(([checkKey, checkVal]) => (
                <div
                  key={checkKey}
                  style={{
                    padding: '8px 12px',
                    backgroundColor: 'var(--color-bg-base)',
                    borderRadius: 4,
                    border: '1px solid var(--color-border-subtle)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                  data-testid={`check-${checkKey}`}
                >
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--color-text-primary)' }}>
                    {checkKey}
                  </span>
                  <StatusBadge status={checkVal === 'ok' ? 'OPERATIONAL' : 'ERROR'} />
                </div>
              ))}
            </div>
          </div>
        )}

        {diagnostics && diagnostics.candidate_slis && (
          <div style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid var(--color-border-subtle)' }}>
            <h4 style={{ fontSize: 12, textTransform: 'uppercase', color: 'var(--color-text-secondary)', marginBottom: 12 }}>
              Observed Telemetry Candidate SLIs (/api/v1/diagnostics)
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
              <div className="panel" style={{ backgroundColor: 'var(--color-bg-base)', marginBottom: 0 }}>
                <span className="decision-metric-label">Request Success Rate</span>
                <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-success)', marginTop: 4 }}>
                  {(diagnostics.candidate_slis.request_success_rate * 100).toFixed(1)}%
                </div>
              </div>
              <div className="panel" style={{ backgroundColor: 'var(--color-bg-base)', marginBottom: 0 }}>
                <span className="decision-metric-label">Observed Analyses</span>
                <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-text-pure)', marginTop: 4 }}>
                  {diagnostics.candidate_slis.total_analyses_observed}
                </div>
              </div>
              <div className="panel" style={{ backgroundColor: 'var(--color-bg-base)', marginBottom: 0 }}>
                <span className="decision-metric-label">Observed Escalation Rate</span>
                <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-warning)', marginTop: 4 }}>
                  {(diagnostics.candidate_slis.observed_escalation_rate * 100).toFixed(1)}%
                </div>
              </div>
              <div className="panel" style={{ backgroundColor: 'var(--color-bg-base)', marginBottom: 0 }}>
                <span className="decision-metric-label">Process Uptime</span>
                <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-text-code)', marginTop: 4 }}>
                  {diagnostics.uptime_seconds.toFixed(0)}s
                </div>
              </div>
            </div>
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', marginTop: 8 }}>
              {diagnostics.notice}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
