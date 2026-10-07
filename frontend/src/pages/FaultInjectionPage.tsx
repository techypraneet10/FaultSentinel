import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Play,
  Lock,
} from 'lucide-react';
import { apiService } from '../services/api';

interface ScenarioInfo {
  id: string;
  name: string;
  target_component: string;
  injected_fault: string;
  expected_resilience: string;
}

export const FaultInjectionPage: React.FC = () => {
  const [environment, setEnvironment] = useState<string>('local');
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('llm_unavailable');
  const [running, setRunning] = useState<boolean>(false);
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    const fetchScenarios = async () => {
      try {
        const res = await apiService.listFaultScenarios();
        setScenarios(res.supported_scenarios || []);
        if (res.supported_scenarios?.length > 0) {
          setSelectedScenarioId(res.supported_scenarios[0].id);
        }
      } catch {
        // Fallback default list
        setScenarios([
          {
            id: 'llm_unavailable',
            name: 'LLM Provider Unavailable',
            target_component: 'ExplanationOrchestrator',
            injected_fault: 'Simulates timeout/connection failure to Gemini 2.5 Flash API.',
            expected_resilience: 'Deterministic triage succeeds, returning authoritative diagnosis without LLM prose.',
          },
          {
            id: 'retrieval_unavailable',
            name: 'Retrieval Unavailable',
            target_component: 'IncidentRetriever',
            injected_fault: 'Vector retrieval yields zero historical matches.',
            expected_resilience: 'System enters INSUFFICIENT_EVIDENCE state. Never invents precedents.',
          },
          {
            id: 'invalid_log_input',
            name: 'Invalid / Oversized Log Input',
            target_component: 'Ingestion Boundary',
            injected_fault: 'Submits 4097-byte log line exceeding schema limit.',
            expected_resilience: 'Early rejection with HTTP 422 Unprocessable Entity.',
          },
          {
            id: 'parser_failure',
            name: 'Parser Malformed Payload',
            target_component: 'Drain3 Preprocessor',
            injected_fault: 'Submits non-JSON malformed body.',
            expected_resilience: 'Rejected with HTTP 422.',
          },
          {
            id: 'faithfulness_failure',
            name: 'Faithfulness Grounding Failure',
            target_component: 'FaithfulnessChecker',
            injected_fault: 'LLM generated text without supporting citation references.',
            expected_resilience: 'Grounding check fails; system switches to deterministic fallback narrative.',
          },
          {
            id: 'invalid_auth',
            name: 'Invalid Authentication Token',
            target_component: 'SecurityHardeningMiddleware',
            injected_fault: 'Missing or corrupted Bearer token.',
            expected_resilience: 'HTTP 401 Authentication Required.',
          },
          {
            id: 'invalid_authz',
            name: 'Role Authorization Denial',
            target_component: 'RBAC Access Controller',
            injected_fault: 'Analyst token requesting Operator diagnostics route.',
            expected_resilience: 'HTTP 403 Forbidden.',
          },
          {
            id: 'config_failure',
            name: 'Configuration Schema Invalidation',
            target_component: 'ConfigurationValidator',
            injected_fault: 'Supplies alpha <= 0 or invalid negative threshold.',
            expected_resilience: 'ConfigurationValidationError raised on startup.',
          },
          {
            id: 'timeout_simulation',
            name: 'Execution Timeout Simulation',
            target_component: 'TriagePipelineService',
            injected_fault: 'Simulates slow external dependency exceeding 30s timeout.',
            expected_resilience: 'Pipeline returns within bounded timeout SLA.',
          },
        ]);
      }
    };
    fetchScenarios();
  }, []);

  const selectedScenario = scenarios.find((s) => s.id === selectedScenarioId);
  const isProduction = environment === 'production';

  const handleRunScenario = async () => {
    if (isProduction) return;
    setRunning(true);
    setResult(null);
    try {
      const res = await apiService.runFaultScenario(selectedScenarioId, environment);
      setResult(res);
    } catch (err: any) {
      setResult({
        scenario_id: selectedScenarioId,
        status: 'FAIL',
        safe: false,
        actual_behavior: err.message || 'Execution failed',
        assertions: [{ name: 'safe_execution', passed: false }],
      });
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="page-container" data-testid="fault-injection-page">
      {/* Title Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 className="page-title" style={{ margin: 0 }}>Reliability & Fault Injection Lab</h1>
            <span className="badge badge-warning" style={{ fontSize: '11px', border: '1px solid #78350F' }}>
              Non-Destructive Testing
            </span>
          </div>
          <p className="page-subtitle" style={{ margin: '4px 0 0 0' }}>
            Demonstrate how FaultSentinel safely degrades when individual dependencies fail.
          </p>
        </div>

        {/* Environment Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: '#888' }}>Environment:</span>
          <select
            value={environment}
            onChange={(e) => setEnvironment(e.target.value)}
            style={{
              background: '#141414',
              color: '#FFF',
              border: isProduction ? '1px solid #EF4444' : '1px solid #333',
              borderRadius: '4px',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 600,
            }}
          >
            <option value="local">Local (Testing)</option>
            <option value="demo">Demo (Recruiter)</option>
            <option value="staging">Staging (Pre-Prod)</option>
            <option value="production">Production (Locked)</option>
          </select>
        </div>
      </div>

      {/* Production Warning Banner */}
      {isProduction && (
        <div
          style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid #EF4444',
            borderRadius: '6px',
            padding: '14px 18px',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <Lock size={20} color="#EF4444" />
          <div>
            <div style={{ fontWeight: 600, color: '#EF4444', fontSize: '13px' }}>
              PRODUCTION ENVIRONMENT DETECTED — FAULT INJECTION DISABLED
            </div>
            <div style={{ fontSize: '12px', color: '#D4D4D8', marginTop: '2px' }}>
              In accordance with Rule 16, destructive and simulated chaos testing is permanently prohibited in production mode.
            </div>
          </div>
        </div>
      )}

      {/* Scenario Selection Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '20px', marginBottom: '24px' }}>
        {/* Left: Scenarios List */}
        <div className="card" style={{ padding: '16px', background: '#0A0A0A', border: '1px solid #1E1E1E' }}>
          <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#777', marginBottom: '10px' }}>
            Available Scenarios ({scenarios.length})
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {scenarios.map((sc) => {
              const isSelected = sc.id === selectedScenarioId;
              return (
                <div
                  key={sc.id}
                  onClick={() => {
                    setSelectedScenarioId(sc.id);
                    setResult(null);
                  }}
                  style={{
                    background: isSelected ? '#1A1A1A' : '#101010',
                    border: `1px solid ${isSelected ? '#FFF' : '#222'}`,
                    borderRadius: '4px',
                    padding: '10px 12px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ fontSize: '12px', fontWeight: 600, color: isSelected ? '#FFF' : '#AAA' }}>
                    {sc.name}
                  </div>
                  <div style={{ fontSize: '11px', color: '#666', marginTop: '2px' }}>
                    Target: {sc.target_component}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Selected Scenario Details & Run Action */}
        {selectedScenario && (
          <div className="card" style={{ padding: '20px', background: '#0A0A0A', border: '1px solid #1E1E1E' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
              <div>
                <span style={{ fontSize: '11px', color: '#777', textTransform: 'uppercase' }}>Target Dependency</span>
                <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#FFF', margin: '2px 0 6px 0' }}>
                  {selectedScenario.name}
                </h2>
                <span className="badge badge-neutral" style={{ fontSize: '11px' }}>
                  Component: {selectedScenario.target_component}
                </span>
              </div>

              <button
                className="btn btn-primary"
                disabled={isProduction || running}
                onClick={handleRunScenario}
                style={{ padding: '8px 18px', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                {running ? (
                  <>Running Simulation...</>
                ) : (
                  <>
                    <Play size={14} /> Run Scenario
                  </>
                )}
              </button>
            </div>

            {/* Injected Fault Description */}
            <div style={{ background: '#121212', padding: '14px', borderRadius: '4px', marginBottom: '14px', fontSize: '12px' }}>
              <div style={{ color: '#888', marginBottom: '4px', fontWeight: 600 }}>Injected Fault Condition:</div>
              <div style={{ color: '#D4D4D8' }}>{selectedScenario.injected_fault}</div>
            </div>

            {/* Expected System Resilience */}
            <div style={{ background: '#121212', padding: '14px', borderRadius: '4px', marginBottom: '20px', fontSize: '12px' }}>
              <div style={{ color: '#888', marginBottom: '4px', fontWeight: 600 }}>Expected System Response:</div>
              <div style={{ color: '#D4D4D8' }}>{selectedScenario.expected_resilience}</div>
            </div>

            {/* Execution Result Box */}
            {result && (
              <div
                style={{
                  border: `1px solid ${result.status === 'PASS' ? '#22C55E' : '#EF4444'}`,
                  borderRadius: '6px',
                  background: result.status === 'PASS' ? 'rgba(34, 197, 94, 0.05)' : 'rgba(239, 68, 68, 0.05)',
                  padding: '16px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {result.status === 'PASS' ? <ShieldCheck size={20} color="#22C55E" /> : <ShieldAlert size={20} color="#EF4444" />}
                    <span style={{ fontWeight: 700, fontSize: '14px', color: result.status === 'PASS' ? '#22C55E' : '#EF4444' }}>
                      {result.status === 'PASS' ? 'SAFE FALLBACK VERIFIED' : 'TEST FAILED'}
                    </span>
                  </div>
                  <span className="badge badge-neutral" style={{ fontSize: '11px' }}>
                    Status: {result.status}
                  </span>
                </div>

                <div style={{ fontSize: '12px', display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '14px' }}>
                  <div>
                    <span style={{ color: '#888' }}>Expected: </span>
                    <span style={{ color: '#CCC' }}>{result.expected_behavior}</span>
                  </div>
                  <div>
                    <span style={{ color: '#888' }}>Actual: </span>
                    <span style={{ color: '#FFF', fontWeight: 600 }}>{result.actual_behavior}</span>
                  </div>
                </div>

                {/* Assertions Matrix */}
                <div style={{ borderTop: '1px solid #222', paddingTop: '10px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 600, color: '#888', marginBottom: '6px', textTransform: 'uppercase' }}>
                    Safety Assertions
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {result.assertions?.map((ass: any, idx: number) => (
                      <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
                        {ass.passed ? <CheckCircle2 size={14} color="#22C55E" /> : <XCircle size={14} color="#EF4444" />}
                        <span style={{ fontFamily: 'monospace', color: ass.passed ? '#D4D4D8' : '#EF4444' }}>
                          {ass.name}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
