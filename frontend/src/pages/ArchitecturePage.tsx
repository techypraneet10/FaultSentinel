import React, { useState } from 'react';
import { StageInspector, PipelineStageInfo } from '../components/StageInspector';
import { PIPELINE_STAGES } from '../utils/pipelineStages';
import { ShieldAlert, ArrowDown } from 'lucide-react';

export const ArchitecturePage: React.FC = () => {
  const [selectedStage, setSelectedStage] = useState<PipelineStageInfo | null>(null);

  const findStage = (id: string) => PIPELINE_STAGES.find((s) => s.id === id) || null;

  return (
    <div data-testid="architecture-page" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Banner */}
      <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface)', padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="panel-title">SYSTEM ARCHITECTURE & TECHNICAL DATAFLOW</span>
              <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)' }}>
                INTERACTIVE GRAPH
              </span>
            </div>
            <p style={{ fontSize: 12, color: 'var(--color-text-muted)', margin: '4px 0 0 0' }}>
              Interactive topology of the calibrated anomaly detection and evidence-grounded explanation pipeline.
            </p>
          </div>
          <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--color-text-secondary)' }}>
            Click any node to inspect subsystem specifications
          </span>
        </div>
      </div>

      {/* Visual Topology Diagram */}
      <div className="panel" style={{ backgroundColor: '#070707', padding: '24px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
        {/* Stage 1: Ingestion */}
        <div
          role="button"
          tabIndex={0}
          onClick={() => setSelectedStage(findStage('ingest'))}
          className="arch-node"
          style={{ width: '320px', padding: '12px 16px', backgroundColor: '#0f0f0f', border: '1px solid #282828', borderRadius: '6px', textAlign: 'center', cursor: 'pointer' }}
        >
          <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>01. INGESTION</div>
          <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-text-pure)' }}>Raw Log Stream & Ingestion Bounds</div>
          <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>Max 500 lines • Path traversal & Label protection</div>
        </div>

        <ArrowDown size={16} color="#444444" />

        {/* Stage 2: Drain3 */}
        <div
          role="button"
          tabIndex={0}
          onClick={() => setSelectedStage(findStage('parse'))}
          className="arch-node"
          style={{ width: '320px', padding: '12px 16px', backgroundColor: '#0f0f0f', border: '1px solid #282828', borderRadius: '6px', textAlign: 'center', cursor: 'pointer' }}
        >
          <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>02. PARSING</div>
          <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-text-pure)' }}>Drain3 Prefix-Tree Template Miner</div>
          <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>Online clustering • Variable token masking (8 ms)</div>
        </div>

        <ArrowDown size={16} color="#444444" />

        {/* Stage 3: Scoring */}
        <div
          role="button"
          tabIndex={0}
          onClick={() => setSelectedStage(findStage('score'))}
          className="arch-node"
          style={{ width: '320px', padding: '12px 16px', backgroundColor: '#0f0f0f', border: '1px solid #282828', borderRadius: '6px', textAlign: 'center', cursor: 'pointer' }}
        >
          <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>03. ANOMALY SCORING</div>
          <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-text-pure)' }}>B2 Sequential GRU Scorer</div>
          <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>24,320 parameters (&lt;2M Rule 6 limit) (18 ms)</div>
        </div>

        <ArrowDown size={16} color="#444444" />

        {/* Stage 4: Conformal Gate (Branching Node) */}
        <div
          role="button"
          tabIndex={0}
          onClick={() => setSelectedStage(findStage('conformal-gate'))}
          className="arch-node"
          style={{ width: '380px', padding: '14px 18px', backgroundColor: '#140e06', border: '1px solid #573d09', borderRadius: '6px', textAlign: 'center', cursor: 'pointer' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', color: 'var(--color-warning)' }}>
            <ShieldAlert size={14} />
            <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
              04. CONFORMAL SELECTIVE GATE (α = 0.05)
            </span>
          </div>
          <div style={{ fontSize: '14px', fontWeight: 800, color: 'var(--color-text-pure)', marginTop: '2px' }}>
            Selective Risk Decision (τ = 1.1546)
          </div>
          <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
            Auto-clears normal windows • Strictly gates expensive escalation
          </div>
        </div>

        {/* Branch: Left = Auto-clear, Right = Escalate */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '48px', width: '100%', maxWidth: '780px' }}>
          {/* Left Branch: Auto-Clear */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
            <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-success)', fontWeight: 700 }}>
              ↙ AUTO-CLEAR (94.78%)
            </div>
            <div
              style={{
                width: '100%',
                padding: '16px',
                backgroundColor: '#07160d',
                border: '1px solid #144722',
                borderRadius: '6px',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-success)' }}>
                Normal Operating Window
              </div>
              <p style={{ fontSize: '11px', color: 'var(--color-text-secondary)', marginTop: '4px', lineHeight: 1.4 }}>
                Window marked healthy. Pipeline completes in &lt;10 ms. Zero LLM API calls incurred.
              </p>
            </div>
          </div>

          {/* Right Branch: Escalate to Retrieval & LLM */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
            <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-warning)', fontWeight: 700 }}>
              ↘ ESCALATE (5.22%)
            </div>

            {/* Retrieval */}
            <div
              role="button"
              tabIndex={0}
              onClick={() => setSelectedStage(findStage('retrieve'))}
              style={{ width: '100%', padding: '10px 14px', backgroundColor: '#0f0f0f', border: '1px solid #282828', borderRadius: '6px', textAlign: 'center', cursor: 'pointer' }}
            >
              <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>05. RETRIEVAL & MMR</div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-text-pure)' }}>Semantic Retrieval + λ=0.7 MMR</div>
              <div style={{ fontSize: '10px', color: 'var(--color-text-secondary)' }}>24.6% redundancy reduction (41 ms)</div>
            </div>

            <ArrowDown size={14} color="#444444" />

            {/* Deterministic Reasoning */}
            <div
              style={{ width: '100%', padding: '10px 14px', backgroundColor: '#0f0f0f', border: '1px solid #282828', borderRadius: '6px', textAlign: 'center' }}
            >
              <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>06. PHASE 8 REASONING</div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-text-pure)' }}>Deterministic Classification</div>
              <div style={{ fontSize: '10px', color: 'var(--color-text-secondary)' }}>Authoritative severity assignment (4 ms)</div>
            </div>

            <ArrowDown size={14} color="#444444" />

            {/* LLM Explainer */}
            <div
              role="button"
              tabIndex={0}
              onClick={() => setSelectedStage(findStage('explain'))}
              style={{ width: '100%', padding: '10px 14px', backgroundColor: '#0f0f0f', border: '1px solid #282828', borderRadius: '6px', textAlign: 'center', cursor: 'pointer' }}
            >
              <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-info)' }}>07. SUBORDINATE EXPLAINER</div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-text-pure)' }}>Grounded LLM Orchestration</div>
              <div style={{ fontSize: '10px', color: 'var(--color-text-secondary)' }}>Constrained citation generation (392 ms)</div>
            </div>

            <ArrowDown size={14} color="#444444" />

            {/* Faithfulness Verification */}
            <div
              role="button"
              tabIndex={0}
              onClick={() => setSelectedStage(findStage('verify'))}
              style={{ width: '100%', padding: '10px 14px', backgroundColor: '#07160d', border: '1px solid #144722', borderRadius: '6px', textAlign: 'center', cursor: 'pointer' }}
            >
              <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-success)' }}>08. VERIFICATION CHECK</div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-success)' }}>Cryptographic Lineage Audit</div>
              <div style={{ fontSize: '10px', color: 'var(--color-text-secondary)' }}>100% citation grounding required (6 ms)</div>
            </div>
          </div>
        </div>
      </div>

      <StageInspector
        stage={selectedStage}
        onClose={() => setSelectedStage(null)}
      />
    </div>
  );
};
