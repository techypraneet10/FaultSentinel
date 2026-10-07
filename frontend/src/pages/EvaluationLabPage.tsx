import React, { useState } from 'react';
import { ShieldAlert } from 'lucide-react';

interface BenchmarkRow {
  system: string;
  dataset: string;
  windows: number;
  tp: number;
  fp: number;
  tn: number;
  fn: number;
  precision: string;
  recall: string;
  f1: string;
  fpr: string;
  escalationRate: string;
  expensiveCalls: number;
  isProposed?: boolean;
}

const HDFS_BENCHMARK: BenchmarkRow[] = [
  { system: 'B0 Frequency Scorer', dataset: 'HDFS', windows: 823, tp: 27, fp: 385, tn: 408, fn: 3, precision: '0.0655', recall: '0.9000', f1: '0.1222', fpr: '0.4855', escalationRate: '50.06%', expensiveCalls: 0 },
  { system: 'B1 PCA Baseline', dataset: 'HDFS', windows: 823, tp: 30, fp: 793, tn: 0, fn: 0, precision: '0.0365', recall: '1.0000', f1: '0.0703', fpr: '1.0000', escalationRate: '100.00%', expensiveCalls: 0 },
  { system: 'B1 Isolation Forest', dataset: 'HDFS', windows: 823, tp: 30, fp: 793, tn: 0, fn: 0, precision: '0.0365', recall: '1.0000', f1: '0.0703', fpr: '1.0000', escalationRate: '100.00%', expensiveCalls: 0 },
  { system: 'B2 Sequential GRU', dataset: 'HDFS', windows: 823, tp: 12, fp: 31, tn: 762, fn: 18, precision: '0.2791', recall: '0.4000', f1: '0.3288', fpr: '0.0391', escalationRate: '5.22%', expensiveCalls: 0 },
  { system: 'B3 LLM Every Window', dataset: 'HDFS', windows: 823, tp: 12, fp: 31, tn: 762, fn: 18, precision: '0.2791', recall: '0.4000', f1: '0.3288', fpr: '0.0391', escalationRate: '100.00%', expensiveCalls: 823 },
  { system: 'Proposed FaultSentinel', dataset: 'HDFS', windows: 823, tp: 12, fp: 31, tn: 762, fn: 18, precision: '0.2791', recall: '0.4000', f1: '0.3288', fpr: '0.0391', escalationRate: '5.22%', expensiveCalls: 43, isProposed: true },
];

const BGL_BENCHMARK: BenchmarkRow[] = [
  { system: 'B0 Frequency Scorer', dataset: 'BGL', windows: 100, tp: 0, fp: 0, tn: 100, fn: 0, precision: 'N/A', recall: 'N/A', f1: 'N/A', fpr: '0.0000', escalationRate: '0.00%', expensiveCalls: 0 },
  { system: 'B1 PCA Baseline', dataset: 'BGL', windows: 100, tp: 0, fp: 0, tn: 100, fn: 0, precision: 'N/A', recall: 'N/A', f1: 'N/A', fpr: '0.0000', escalationRate: '100.00%', expensiveCalls: 0 },
  { system: 'B1 Isolation Forest', dataset: 'BGL', windows: 100, tp: 0, fp: 2, tn: 98, fn: 0, precision: '0.0000', recall: 'N/A', f1: 'N/A', fpr: '0.0200', escalationRate: '2.00%', expensiveCalls: 0 },
  { system: 'B2 Sequential GRU', dataset: 'BGL', windows: 100, tp: 0, fp: 0, tn: 100, fn: 0, precision: 'N/A', recall: 'N/A', f1: 'N/A', fpr: '0.0000', escalationRate: '0.00%', expensiveCalls: 0 },
  { system: 'B3 LLM Every Window', dataset: 'BGL', windows: 100, tp: 0, fp: 0, tn: 100, fn: 0, precision: 'N/A', recall: 'N/A', f1: 'N/A', fpr: '0.0000', escalationRate: '100.00%', expensiveCalls: 100 },
  { system: 'Proposed FaultSentinel', dataset: 'BGL', windows: 100, tp: 0, fp: 0, tn: 100, fn: 0, precision: 'N/A', recall: 'N/A', f1: 'N/A', fpr: '0.0000', escalationRate: '0.00%', expensiveCalls: 0, isProposed: true },
];

export const EvaluationLabPage: React.FC = () => {
  const [selectedDataset, setSelectedDataset] = useState<'hdfs' | 'bgl'>('hdfs');

  const benchmarkData = selectedDataset === 'hdfs' ? HDFS_BENCHMARK : BGL_BENCHMARK;

  return (
    <div data-testid="evaluation-lab-page" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header & Controls */}
      <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface)', padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="panel-title">EVALUATION LAB</span>
              <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)' }}>
                PHASE 12 VERIFIED BENCHMARKS
              </span>
            </div>
            <p style={{ fontSize: 12, color: 'var(--color-text-muted)', margin: '4px 0 0 0' }}>
              Rigorous comparative evaluation over frozen chronological test partitions. Zero threshold tuning on test.
            </p>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <select
              className="form-select"
              style={{ width: 'auto', padding: '4px 10px', fontSize: 12 }}
              value={selectedDataset}
              onChange={(e) => setSelectedDataset(e.target.value as 'hdfs' | 'bgl')}
            >
              <option value="hdfs">HDFS Test Partition (N=823, Pos=30)</option>
              <option value="bgl">BGL Test Slice (N=100, Pos=0)</option>
            </select>
          </div>
        </div>

        {/* Primary Insight Bar */}
        <div
          style={{
            backgroundColor: 'var(--color-bg-base)',
            padding: '10px 14px',
            borderRadius: 4,
            border: '1px solid var(--color-border-subtle)',
            fontSize: 12,
            color: 'var(--color-text-secondary)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span>
            <strong style={{ color: 'var(--color-text-pure)' }}>Key Scientific Finding:</strong> Proposed selective cascade eliminates{' '}
            <strong style={{ color: 'var(--color-success)' }}>94.78% of expensive LLM calls</strong> (43 vs 823) compared to LLM-every-window,
            while matching B2 detection and achieving 100% claim-level citation grounding.
          </span>
          <span className="badge badge-neutral" style={{ fontSize: 10 }}>RULE 7 COMPLIANT</span>
        </div>
      </div>

      {/* Comparative Benchmark Table */}
      <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface)', padding: 0, overflowX: 'auto' }}>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--color-border-subtle)' }}>
          <span style={{ fontSize: 12, fontWeight: 700, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', color: 'var(--color-text-pure)' }}>
            System Benchmark Comparison ({selectedDataset.toUpperCase()} Frozen Test Partition)
          </span>
        </div>

        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, fontFamily: 'var(--font-mono)', textAlign: 'left' }}>
          <thead>
            <tr style={{ backgroundColor: 'var(--color-bg-base)', borderBottom: '1px solid var(--color-border-default)', color: 'var(--color-text-muted)' }}>
              <th style={{ padding: '10px 14px' }}>System</th>
              <th style={{ padding: '10px 14px' }}>Windows</th>
              <th style={{ padding: '10px 14px' }}>TP</th>
              <th style={{ padding: '10px 14px' }}>FP</th>
              <th style={{ padding: '10px 14px' }}>TN</th>
              <th style={{ padding: '10px 14px' }}>FN</th>
              <th style={{ padding: '10px 14px' }}>Precision</th>
              <th style={{ padding: '10px 14px' }}>Recall</th>
              <th style={{ padding: '10px 14px' }}>F1 Score</th>
              <th style={{ padding: '10px 14px' }}>Escalation %</th>
              <th style={{ padding: '10px 14px', textAlign: 'right' }}>LLM Calls</th>
            </tr>
          </thead>
          <tbody>
            {benchmarkData.map((row, idx) => (
              <tr
                key={idx}
                style={{
                  borderBottom: '1px solid var(--color-border-subtle)',
                  backgroundColor: row.isProposed ? 'rgba(34, 197, 94, 0.05)' : 'transparent',
                }}
              >
                <td style={{ padding: '10px 14px', fontWeight: row.isProposed ? 700 : 500, color: row.isProposed ? 'var(--color-success)' : 'var(--color-text-pure)' }}>
                  {row.system}
                </td>
                <td style={{ padding: '10px 14px', color: 'var(--color-text-secondary)' }}>{row.windows}</td>
                <td style={{ padding: '10px 14px', color: 'var(--color-text-secondary)' }}>{row.tp}</td>
                <td style={{ padding: '10px 14px', color: 'var(--color-text-secondary)' }}>{row.fp}</td>
                <td style={{ padding: '10px 14px', color: 'var(--color-text-secondary)' }}>{row.tn}</td>
                <td style={{ padding: '10px 14px', color: 'var(--color-text-secondary)' }}>{row.fn}</td>
                <td style={{ padding: '10px 14px', color: row.isProposed ? 'var(--color-success)' : 'var(--color-text-pure)' }}>{row.precision}</td>
                <td style={{ padding: '10px 14px', color: 'var(--color-text-pure)' }}>{row.recall}</td>
                <td style={{ padding: '10px 14px', color: 'var(--color-text-pure)' }}>{row.f1}</td>
                <td style={{ padding: '10px 14px', color: row.isProposed ? 'var(--color-warning)' : 'var(--color-text-secondary)' }}>{row.escalationRate}</td>
                <td style={{ padding: '10px 14px', textAlign: 'right', fontWeight: 700, color: row.expensiveCalls > 100 ? 'var(--color-critical)' : 'var(--color-text-pure)' }}>
                  {row.expensiveCalls}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Research Integrity & Equivalence Notes */}
      <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface)', padding: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
          <ShieldAlert size={14} color="var(--color-warning)" />
          <span className="panel-title" style={{ color: 'var(--color-warning)', margin: 0 }}>
            Authoritative Equivalence & Research Transparency
          </span>
        </div>
        <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.5, margin: 0 }}>
          Because FaultSentinel's selective gate threshold at α=0.05 is calibrated directly on B2's scores (threshold τ = 1.1546),
          the binary anomaly classification metrics on HDFS (Precision=0.2791, Recall=0.4000) for B2 and FaultSentinel are identical.
          The primary scientific contribution is therefore NOT superior raw anomaly detection over B2, but rather:
          (1) Calibrated selective escalation auto-clearing 94.78% of normal windows,
          (2) Historical evidence retrieval with 24.6% MMR redundancy reduction,
          (3) Cryptographic SHA-256 provenance verification, and
          (4) 94.78% compute savings in expensive LLM calls compared to indiscriminate processing.
        </p>
      </div>
    </div>
  );
};
