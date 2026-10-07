import React, { useState, useEffect, useRef } from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  RotateCcw,
} from 'lucide-react';
import { apiService } from '../services/api';

interface StageData {
  stage_id: string;
  stage_name: string;
  order: number;
  status: string;
  skipped: boolean;
  latency_ms: number;
  timestamp: string;
  implementation: string;
  dependencies: string[];
  failure_mode: string;
  inputs: Record<string, any>;
  outputs: Record<string, any>;
}

export const IncidentReplayPage: React.FC = () => {
  const [incidentType, setIncidentType] = useState<'incident' | 'normal'>('incident');
  const [replayData, setReplayData] = useState<any>(null);
  const [currentStageIdx, setCurrentStageIdx] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);
  const [loading, setLoading] = useState<boolean>(false);
  const [counterfactualScore, setCounterfactualScore] = useState<number>(0.95);
  const [cfResult, setCfResult] = useState<any>(null);
  const playTimerRef = useRef<any>(null);

  const fetchReplay = async (type: 'incident' | 'normal') => {
    setLoading(true);
    try {
      const data = await apiService.fetchSampleReplay(type);
      setReplayData(data);
      setCurrentStageIdx(0);
      setIsPlaying(false);
    } catch {
      // Fallback local mock if offline
      setReplayData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReplay(incidentType);
  }, [incidentType]);

  useEffect(() => {
    if (isPlaying) {
      const interval = 1200 / playbackSpeed;
      playTimerRef.current = setInterval(() => {
        setCurrentStageIdx((prev) => {
          if (!replayData?.stages || prev >= replayData.stages.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, interval);
    } else {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    }
    return () => {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    };
  }, [isPlaying, playbackSpeed, replayData]);

  const stages: StageData[] = replayData?.stages || [];
  const currentStage: StageData | undefined = stages[currentStageIdx];

  const handleSimulateCounterfactual = async () => {
    try {
      const res = await apiService.simulateCounterfactual({
        actual_score: replayData?.incident_summary?.anomaly_score || 1.3742,
        hypothetical_score: counterfactualScore,
        conformal_threshold: 1.15459,
        target_alpha: 0.05,
      });
      setCfResult(res);
    } catch {
      setCfResult({
        hypothetical_score: counterfactualScore,
        hypothetical_decision: counterfactualScore > 1.15459 ? 'ESCALATE' : 'AUTO_CLEAR',
        margin: counterfactualScore - 1.15459,
      });
    }
  };

  return (
    <div className="page-container" data-testid="incident-replay-page">
      {/* Top Header Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 className="page-title" style={{ margin: 0 }}>Incident Replay Lab</h1>
            <span className="badge badge-neutral" style={{ fontSize: '11px', border: '1px solid #333' }}>v1.1 Deterministic Trace</span>
          </div>
          <p className="page-subtitle" style={{ margin: '4px 0 0 0' }}>
            Step-by-step observable playback of historical incident decisions. Zero re-training or metric fabrication.
          </p>
        </div>

        {/* Incident Selector */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ fontSize: '12px', color: 'var(--color-text-dim)' }}>Simulation Scenario:</span>
          <button
            className={`btn ${incidentType === 'incident' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '12px', padding: '6px 12px' }}
            onClick={() => setIncidentType('incident')}
          >
            Escalated Incident
          </button>
          <button
            className={`btn ${incidentType === 'normal' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '12px', padding: '6px 12px' }}
            onClick={() => setIncidentType('normal')}
          >
            Routine Auto-Clear
          </button>
        </div>
      </div>

      {loading && (
        <div style={{ padding: '40px', textAlign: 'center', color: '#888' }}>
          Loading recorded execution trace...
        </div>
      )}

      {!loading && replayData && (
        <>
          {/* Controls Bar */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: '#0D0D0D',
              border: '1px solid #222',
              borderRadius: '6px',
              padding: '12px 18px',
              marginBottom: '20px',
            }}
          >
            {/* Playback Transport Buttons */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                className="btn btn-secondary"
                style={{ padding: '6px 10px' }}
                onClick={() => setCurrentStageIdx(0)}
                disabled={currentStageIdx === 0}
                title="First Stage"
              >
                <SkipBack size={14} /> First
              </button>
              <button
                className="btn btn-secondary"
                style={{ padding: '6px 10px' }}
                onClick={() => setCurrentStageIdx((p) => Math.max(0, p - 1))}
                disabled={currentStageIdx === 0}
                title="Previous Stage"
              >
                <ChevronLeft size={14} /> Prev
              </button>

              <button
                className={`btn ${isPlaying ? 'btn-danger' : 'btn-primary'}`}
                style={{ padding: '6px 16px', minWidth: '90px' }}
                onClick={() => setIsPlaying(!isPlaying)}
              >
                {isPlaying ? <><Pause size={14} style={{ marginRight: '6px' }} /> Pause</> : <><Play size={14} style={{ marginRight: '6px' }} /> Play</>}
              </button>

              <button
                className="btn btn-secondary"
                style={{ padding: '6px 10px' }}
                onClick={() => setCurrentStageIdx((p) => Math.min(stages.length - 1, p + 1))}
                disabled={currentStageIdx === stages.length - 1}
                title="Next Stage"
              >
                Next <ChevronRight size={14} />
              </button>
              <button
                className="btn btn-secondary"
                style={{ padding: '6px 10px' }}
                onClick={() => setCurrentStageIdx(stages.length - 1)}
                disabled={currentStageIdx === stages.length - 1}
                title="Last Stage"
              >
                Last <SkipForward size={14} />
              </button>
            </div>

            {/* Stage Counter & Speed */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <span style={{ fontFamily: 'monospace', fontSize: '13px', color: '#BBB' }}>
                Stage {currentStageIdx + 1} of {stages.length}: <strong style={{ color: '#FFF' }}>{currentStage?.stage_name}</strong>
              </span>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '11px', color: '#888' }}>Speed:</span>
                {[0.5, 1.0, 2.0].map((s) => (
                  <button
                    key={s}
                    className={`btn ${playbackSpeed === s ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '3px 8px', fontSize: '11px' }}
                    onClick={() => setPlaybackSpeed(s)}
                  >
                    {s}x
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Timeline Visualizer (11 stages) */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: `repeat(${stages.length}, 1fr)`,
              gap: '6px',
              marginBottom: '20px',
              overflowX: 'auto',
              paddingBottom: '4px',
            }}
          >
            {stages.map((stg, idx) => {
              const isActive = idx === currentStageIdx;
              const isPassed = idx < currentStageIdx;
              const isSkipped = stg.skipped;

              let borderColor = '#222';
              let bgColor = '#0A0A0A';
              if (isActive) {
                borderColor = '#FFFFFF';
                bgColor = '#1A1A1A';
              } else if (isPassed) {
                borderColor = '#333';
                bgColor = '#111';
              }

              return (
                <div
                  key={stg.stage_id}
                  onClick={() => {
                    setCurrentStageIdx(idx);
                    setIsPlaying(false);
                  }}
                  style={{
                    background: bgColor,
                    border: `1px solid ${borderColor}`,
                    borderRadius: '4px',
                    padding: '8px 6px',
                    cursor: 'pointer',
                    textAlign: 'center',
                    transition: 'all 0.15s ease',
                    boxShadow: isActive ? '0 0 10px rgba(255,255,255,0.1)' : 'none',
                  }}
                >
                  <div style={{ fontSize: '10px', fontFamily: 'monospace', color: isActive ? '#FFF' : '#666' }}>
                    0{idx + 1}
                  </div>
                  <div
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      color: isSkipped ? '#666' : isActive ? '#FFF' : '#AAA',
                      textDecoration: isSkipped ? 'line-through' : 'none',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      marginTop: '2px',
                    }}
                  >
                    {stg.stage_name}
                  </div>
                  <div style={{ marginTop: '4px' }}>
                    {isSkipped ? (
                      <span style={{ fontSize: '9px', color: '#666' }}>SKIPPED</span>
                    ) : (
                      <span style={{ fontSize: '9px', color: stg.status === 'VERIFIED' ? '#22C55E' : '#9CA3AF' }}>
                        {stg.latency_ms}ms
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Main Content Layout: Left = Metadata/Summary, Right = Stage Inspector */}
          <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '20px', marginBottom: '20px' }}>
            {/* Left: Incident Metadata & Summary */}
            <div className="card" style={{ padding: '16px', background: '#0A0A0A', border: '1px solid #1E1E1E' }}>
              <h3 style={{ fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#888', marginBottom: '12px' }}>
                Incident Summary
              </h3>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #181818', paddingBottom: '6px' }}>
                  <span style={{ color: '#777' }}>Incident ID:</span>
                  <span style={{ fontFamily: 'monospace', color: '#FFF' }}>{replayData.incident_id}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #181818', paddingBottom: '6px' }}>
                  <span style={{ color: '#777' }}>Dataset:</span>
                  <span style={{ color: '#FFF' }}>{replayData.dataset.toUpperCase()}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #181818', paddingBottom: '6px' }}>
                  <span style={{ color: '#777' }}>Anomaly Score:</span>
                  <span style={{ fontFamily: 'monospace', fontWeight: 600, color: replayData.incident_summary.anomaly_score > 1.15 ? '#EF4444' : '#22C55E' }}>
                    {replayData.incident_summary.anomaly_score}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #181818', paddingBottom: '6px' }}>
                  <span style={{ color: '#777' }}>Conformal Threshold:</span>
                  <span style={{ fontFamily: 'monospace', color: '#BBB' }}>{replayData.incident_summary.conformal_threshold}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #181818', paddingBottom: '6px' }}>
                  <span style={{ color: '#777' }}>Conformal Decision:</span>
                  <span className={`badge ${replayData.incident_summary.conformal_decision === 'ESCALATE' ? 'badge-danger' : 'badge-success'}`}>
                    {replayData.incident_summary.conformal_decision}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #181818', paddingBottom: '6px' }}>
                  <span style={{ color: '#777' }}>Final Decision:</span>
                  <span style={{ fontWeight: 600, color: '#FFF' }}>{replayData.incident_summary.final_decision}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #181818', paddingBottom: '6px' }}>
                  <span style={{ color: '#777' }}>Assigned Severity:</span>
                  <span style={{ color: '#FFF' }}>{replayData.incident_summary.severity}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #181818', paddingBottom: '6px' }}>
                  <span style={{ color: '#777' }}>Total Latency:</span>
                  <span style={{ fontFamily: 'monospace', color: '#BBB' }}>{replayData.total_latency_ms} ms</span>
                </div>
              </div>

              {/* Counterfactual Mini-Simulator */}
              <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid #222' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <RotateCcw size={13} color="#F59E0B" />
                  <span style={{ fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', color: '#F59E0B' }}>
                    Counterfactual Simulation
                  </span>
                </div>
                <p style={{ fontSize: '11px', color: '#777', margin: '0 0 10px 0' }}>
                  Test what would happen if the anomaly score shifted across the threshold.
                </p>

                <div style={{ display: 'flex', gap: '8px', marginBottom: '10px' }}>
                  <input
                    type="number"
                    step="0.05"
                    value={counterfactualScore}
                    onChange={(e) => setCounterfactualScore(parseFloat(e.target.value) || 0)}
                    style={{
                      background: '#141414',
                      border: '1px solid #333',
                      color: '#FFF',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      width: '80px',
                    }}
                  />
                  <button className="btn btn-secondary" style={{ fontSize: '11px', flex: 1 }} onClick={handleSimulateCounterfactual}>
                    Simulate
                  </button>
                </div>

                {cfResult && (
                  <div style={{ background: '#111', padding: '8px', borderRadius: '4px', border: '1px solid #282828', fontSize: '11px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ color: '#888' }}>Decision:</span>
                      <strong style={{ color: cfResult.hypothetical_decision === 'ESCALATE' ? '#EF4444' : '#22C55E' }}>
                        {cfResult.hypothetical_decision}
                      </strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#888' }}>Delta from Actual:</span>
                      <span style={{ color: cfResult.decision_changed ? '#F59E0B' : '#888' }}>
                        {cfResult.decision_changed ? 'DECISION CHANGED' : 'UNCHANGED'}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Right: Stage Inspector (Detailed View of Active Stage) */}
            {currentStage && (
              <div className="card" style={{ padding: '20px', background: '#0A0A0A', border: '1px solid #1E1E1E' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                  <div>
                    <span style={{ fontSize: '11px', color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Stage {currentStage.order} of {stages.length}
                    </span>
                    <h2 style={{ fontSize: '18px', fontWeight: 600, margin: '2px 0 4px 0', color: '#FFF' }}>
                      {currentStage.stage_name}
                    </h2>
                    <span style={{ fontSize: '12px', color: '#9CA3AF' }}>{currentStage.failure_mode}</span>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <span className="badge badge-success" style={{ fontSize: '11px' }}>{currentStage.status}</span>
                    <div style={{ fontSize: '11px', fontFamily: 'monospace', color: '#888', marginTop: '4px' }}>
                      {currentStage.latency_ms} ms
                    </div>
                  </div>
                </div>

                {/* Stage Metadata Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', background: '#121212', padding: '12px', borderRadius: '4px', marginBottom: '16px', fontSize: '11px' }}>
                  <div>
                    <div style={{ color: '#666' }}>Implementation</div>
                    <div style={{ fontFamily: 'monospace', color: '#BBB', marginTop: '2px', wordBreak: 'break-all' }}>
                      {currentStage.implementation}
                    </div>
                  </div>
                  <div>
                    <div style={{ color: '#666' }}>Dependencies</div>
                    <div style={{ color: '#BBB', marginTop: '2px' }}>
                      {currentStage.dependencies.join(', ') || 'None (In-process)'}
                    </div>
                  </div>
                  <div>
                    <div style={{ color: '#666' }}>Timestamp</div>
                    <div style={{ fontFamily: 'monospace', color: '#BBB', marginTop: '2px' }}>
                      {currentStage.timestamp}
                    </div>
                  </div>
                </div>

                {/* Inputs & Outputs JSON Visualizer */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: '#888', marginBottom: '6px', textTransform: 'uppercase' }}>
                      Stage Inputs
                    </div>
                    <pre
                      style={{
                        background: '#050505',
                        border: '1px solid #1E1E1E',
                        borderRadius: '4px',
                        padding: '10px',
                        fontSize: '11px',
                        color: '#D4D4D8',
                        fontFamily: 'monospace',
                        maxHeight: '260px',
                        overflowY: 'auto',
                        margin: 0,
                      }}
                    >
                      {JSON.stringify(currentStage.inputs, null, 2)}
                    </pre>
                  </div>

                  <div>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: '#888', marginBottom: '6px', textTransform: 'uppercase' }}>
                      Stage Outputs
                    </div>
                    <pre
                      style={{
                        background: '#050505',
                        border: '1px solid #1E1E1E',
                        borderRadius: '4px',
                        padding: '10px',
                        fontSize: '11px',
                        color: '#D4D4D8',
                        fontFamily: 'monospace',
                        maxHeight: '260px',
                        overflowY: 'auto',
                        margin: 0,
                      }}
                    >
                      {JSON.stringify(currentStage.outputs, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Bottom: Why This Incident Reached The Final Decision */}
          <div className="card" style={{ padding: '18px 22px', background: '#0D0D0D', border: '1px solid #222' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <ShieldCheck size={16} color="#22C55E" />
              <h3 style={{ fontSize: '13px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#FFF', margin: 0 }}>
                Why This Incident Reached The Final Decision
              </h3>
            </div>

            <div style={{ fontSize: '13px', lineHeight: 1.6, color: '#CCC', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div>• <strong>Conformal Gating:</strong> {replayData.analytical_synthesis.why_escalated}</div>
              <div>• <strong>Deterministic Diagnosis:</strong> {replayData.analytical_synthesis.why_decision}</div>
              <div>• <strong>Faithfulness Verification:</strong> {replayData.analytical_synthesis.why_faithfulness}</div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
