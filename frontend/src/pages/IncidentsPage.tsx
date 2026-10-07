import React, { useState, useMemo } from 'react';
import { StatusBadge } from '../components/StatusBadge';
import { SeverityBadge } from '../components/SeverityBadge';
import { CitationBadge } from '../components/CitationBadge';
import { EvidenceDrawer } from '../components/EvidenceDrawer';
import { DecisionTrace } from '../components/DecisionTrace';
import {
  Search,
  ArrowRight,
  X,
  CheckCircle2,
} from 'lucide-react';
import { Citation } from '../types';

interface IncidentRecord {
  id: string;
  dataset: 'hdfs' | 'bgl';
  partition: 'train' | 'calibration';
  timestamp: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  anomalyScore: number;
  decision: 'INCIDENT' | 'SUSPICIOUS' | 'INSUFFICIENT_EVIDENCE';
  faithfulness: 'VERIFIED' | 'UNFAITHFUL';
  latencyMs: number;
  summary: string;
  rootCause: string;
  logSnippet: string[];
  citations: Citation[];
}

const HISTORICAL_INCIDENTS: IncidentRecord[] = [
  {
    id: 'INC-HDFS-1082',
    dataset: 'hdfs',
    partition: 'calibration',
    timestamp: '2008-11-09 20:35:19',
    severity: 'HIGH',
    anomalyScore: 1.48,
    decision: 'INCIDENT',
    faithfulness: 'VERIFIED',
    latencyMs: 462,
    summary: 'DataNode PacketResponder termination triggered by corrupted block payload.',
    rootCause: 'Corrupted HDFS block blk_-1608999687919862906 during inter-node socket stream transmission.',
    logSnippet: [
      '081109 203518 143 INFO dfs.DataNode$DataXceiver: Receiving block blk_-1608999687919862906 src: /10.250.19.102:54106',
      '081109 203519 145 INFO dfs.DataNode$PacketResponder: PacketResponder 1 for block terminating',
      '081109 203519 148 WARN dfs.DataNode$DataXceiver: Got exception while serving blk: java.io.IOException: Block is not valid.',
    ],
    citations: [
      {
        citation_id: 'CIT-HDFS-001',
        dataset: 'hdfs',
        split: 'calibration',
        source_window_id: 'blk_-1608999687919862906',
        line_start: 1,
        line_end: 3,
        citation_text: 'WARN dfs.DataNode: Block is not valid',
      },
    ],
  },
  {
    id: 'INC-HDFS-1049',
    dataset: 'hdfs',
    partition: 'calibration',
    timestamp: '2008-11-09 19:12:04',
    severity: 'HIGH',
    anomalyScore: 1.34,
    decision: 'INCIDENT',
    faithfulness: 'VERIFIED',
    latencyMs: 448,
    summary: 'Unexpected EOFException in NameNode heartbeat lease monitor.',
    rootCause: 'DataNode lease expired prematurely during replica re-balancing.',
    logSnippet: [
      '081109 191203 102 INFO dfs.FSNamesystem: Number of transactions: 3412',
      '081109 191204 104 ERROR dfs.NameNode: Lease monitor failed for block: java.io.EOFException',
      '081109 191204 105 WARN dfs.StateChange: BLOCK* NameNode.register: Registration failed',
    ],
    citations: [
      {
        citation_id: 'CIT-HDFS-002',
        dataset: 'hdfs',
        split: 'calibration',
        source_window_id: 'blk_3419204918239019',
        line_start: 2,
        line_end: 3,
        citation_text: 'ERROR dfs.NameNode: Lease monitor failed',
      },
    ],
  },
  {
    id: 'INC-BGL-0891',
    dataset: 'bgl',
    partition: 'calibration',
    timestamp: '2005-06-03 15:42:50',
    severity: 'MEDIUM',
    anomalyScore: 0.94,
    decision: 'SUSPICIOUS',
    faithfulness: 'VERIFIED',
    latencyMs: 388,
    summary: 'Instruction cache parity error corrected by hardware RAS kernel on midplane R02.',
    rootCause: 'Single-bit instruction cache parity error detected in node card J12-U11.',
    logSnippet: [
      '- 1117838570 2005.06.03 R02-M1-N0-C:J12-U11 RAS KERNEL INFO generating core.1284',
      '- 1117838570 2005.06.03 R02-M1-N0-C:J12-U11 RAS KERNEL INFO instruction cache parity error corrected',
      '- 1117838570 2005.06.03 R02-M1-N0-C:J12-U11 RAS KERNEL INFO idoproxy: communications failure with ciod',
    ],
    citations: [
      {
        citation_id: 'CIT-BGL-001',
        dataset: 'bgl',
        split: 'calibration',
        source_window_id: 'slice_20050603_1542',
        line_start: 1,
        line_end: 2,
        citation_text: 'RAS KERNEL INFO instruction cache parity error corrected',
      },
    ],
  },
  {
    id: 'INC-BGL-0412',
    dataset: 'bgl',
    partition: 'calibration',
    timestamp: '2005-06-03 12:10:14',
    severity: 'LOW',
    anomalyScore: 0.22,
    decision: 'INSUFFICIENT_EVIDENCE',
    faithfulness: 'VERIFIED',
    latencyMs: 24,
    summary: 'Normal scheduled torus diagnostic pulse across compute racks.',
    rootCause: 'Standard background network telemetry polling (auto-cleared).',
    logSnippet: [
      '- 1117825814 2005.06.03 R00-M0-N0-C:J00-U00 RAS KERNEL INFO torus check ok',
      '- 1117825814 2005.06.03 R00-M0-N0-C:J00-U00 RAS KERNEL INFO barrier synchronize passed',
    ],
    citations: [],
  },
];

export const IncidentsPage: React.FC = () => {
  const [search, setSearch] = useState('');
  const [datasetFilter, setDatasetFilter] = useState<'all' | 'hdfs' | 'bgl'>('all');
  const [severityFilter, setSeverityFilter] = useState<'all' | 'HIGH' | 'MEDIUM' | 'LOW'>('all');
  const [decisionFilter, setDecisionFilter] = useState<'all' | 'INCIDENT' | 'SUSPICIOUS' | 'INSUFFICIENT_EVIDENCE'>('all');
  const [selectedIncident, setSelectedIncident] = useState<IncidentRecord | null>(null);
  const [inspectedCitation, setInspectedCitation] = useState<Citation | null>(null);

  const filteredIncidents = useMemo(() => {
    return HISTORICAL_INCIDENTS.filter((inc) => {
      if (datasetFilter !== 'all' && inc.dataset !== datasetFilter) return false;
      if (severityFilter !== 'all' && inc.severity !== severityFilter) return false;
      if (decisionFilter !== 'all' && inc.decision !== decisionFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        const matchesId = inc.id.toLowerCase().includes(q);
        const matchesSummary = inc.summary.toLowerCase().includes(q);
        const matchesLogs = inc.logSnippet.some((l) => l.toLowerCase().includes(q));
        if (!matchesId && !matchesSummary && !matchesLogs) return false;
      }
      return true;
    });
  }, [search, datasetFilter, severityFilter, decisionFilter]);

  return (
    <div data-testid="incidents-page" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header controls & Filters */}
      <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface)', padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div>
            <span className="panel-title">Incident Directory & Audit Registry</span>
            <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 2 }}>
              Verified historical incident records from calibration partitions
            </div>
          </div>
          <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)' }}>
            {filteredIncidents.length} RECORDS FOUND
          </span>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center' }}>
          {/* Search bar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              backgroundColor: 'var(--color-bg-base)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 4,
              padding: '6px 10px',
              flex: '1 1 240px',
            }}
          >
            <Search size={14} color="var(--color-text-muted)" />
            <input
              type="text"
              placeholder="Search incident ID, log text, or root cause..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--color-text-pure)',
                fontFamily: 'var(--font-mono)',
                fontSize: 12,
                width: '100%',
                outline: 'none',
              }}
            />
          </div>

          {/* Dataset filter */}
          <select
            className="form-select"
            style={{ width: 'auto', padding: '6px 10px', fontSize: 12 }}
            value={datasetFilter}
            onChange={(e) => setDatasetFilter(e.target.value as 'all' | 'hdfs' | 'bgl')}
          >
            <option value="all">All Datasets</option>
            <option value="hdfs">HDFS Only</option>
            <option value="bgl">BGL Only</option>
          </select>

          {/* Severity filter */}
          <select
            className="form-select"
            style={{ width: 'auto', padding: '6px 10px', fontSize: 12 }}
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value as 'all' | 'HIGH' | 'MEDIUM' | 'LOW')}
          >
            <option value="all">All Severities</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          {/* Decision filter */}
          <select
            className="form-select"
            style={{ width: 'auto', padding: '6px 10px', fontSize: 12 }}
            value={decisionFilter}
            onChange={(e) => setDecisionFilter(e.target.value as 'all' | 'INCIDENT' | 'SUSPICIOUS' | 'INSUFFICIENT_EVIDENCE')}
          >
            <option value="all">All Decisions</option>
            <option value="INCIDENT">INCIDENT</option>
            <option value="SUSPICIOUS">SUSPICIOUS</option>
            <option value="INSUFFICIENT_EVIDENCE">INSUFFICIENT_EVIDENCE</option>
          </select>
        </div>
      </div>

      {/* Incident Investigation Table */}
      <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface)', padding: 0, overflow: 'hidden' }}>
        <table
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: 13,
            textAlign: 'left',
          }}
        >
          <thead>
            <tr
              style={{
                borderBottom: '1px solid var(--color-border-default)',
                backgroundColor: 'var(--color-bg-base)',
                color: 'var(--color-text-muted)',
                fontSize: 11,
                fontFamily: 'var(--font-mono)',
                textTransform: 'uppercase',
              }}
            >
              <th style={{ padding: '10px 14px' }}>Incident ID</th>
              <th style={{ padding: '10px 14px' }}>Dataset</th>
              <th style={{ padding: '10px 14px' }}>Timestamp</th>
              <th style={{ padding: '10px 14px' }}>Severity</th>
              <th style={{ padding: '10px 14px' }}>Anomaly Score</th>
              <th style={{ padding: '10px 14px' }}>Decision</th>
              <th style={{ padding: '10px 14px' }}>Faithfulness</th>
              <th style={{ padding: '10px 14px' }}>Latency</th>
              <th style={{ padding: '10px 14px', textAlign: 'right' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredIncidents.map((inc) => (
              <tr
                key={inc.id}
                onClick={() => setSelectedIncident(inc)}
                style={{
                  borderBottom: '1px solid var(--color-border-subtle)',
                  cursor: 'pointer',
                  transition: 'background-color 0.15s ease',
                  backgroundColor:
                    selectedIncident?.id === inc.id ? 'var(--color-bg-surface-raised)' : 'transparent',
                }}
                className="incident-row"
              >
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--color-text-pure)' }}>
                  {inc.id}
                </td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)' }}>
                  <span className="badge badge-neutral">{inc.dataset.toUpperCase()}</span>
                </td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', color: 'var(--color-text-secondary)', fontSize: 12 }}>
                  {inc.timestamp}
                </td>
                <td style={{ padding: '12px 14px' }}>
                  <SeverityBadge severity={inc.severity} />
                </td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', color: inc.anomalyScore > 1.15 ? 'var(--color-critical)' : 'var(--color-text-secondary)' }}>
                  {inc.anomalyScore.toFixed(2)}
                </td>
                <td style={{ padding: '12px 14px' }}>
                  <StatusBadge status={inc.decision} />
                </td>
                <td style={{ padding: '12px 14px' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--color-success)', fontSize: 12, fontFamily: 'var(--font-mono)' }}>
                    <CheckCircle2 size={12} />
                    {inc.faithfulness}
                  </span>
                </td>
                <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)', fontSize: 12 }}>
                  {inc.latencyMs} ms
                </td>
                <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedIncident(inc);
                    }}
                  >
                    <span>Investigate</span>
                    <ArrowRight size={12} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Incident Detail Drawer / Modal */}
      {selectedIncident && (
        <div className="drawer-backdrop" onClick={() => setSelectedIncident(null)}>
          <div
            className="drawer-content"
            onClick={(e) => e.stopPropagation()}
            style={{ width: '640px', maxWidth: '94vw' }}
          >
            <div className="drawer-header">
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)' }}>
                    {selectedIncident.id}
                  </span>
                  <StatusBadge status={selectedIncident.decision} />
                  <SeverityBadge severity={selectedIncident.severity} />
                </div>
                <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-text-pure)', marginTop: 4 }}>
                  {selectedIncident.summary}
                </h3>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setSelectedIncident(null)}
              >
                <X size={14} />
              </button>
            </div>

            <div className="drawer-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Root Cause Card */}
              <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface-raised)' }}>
                <span className="decision-metric-label">Root Cause Assessment</span>
                <p style={{ fontSize: 13, color: 'var(--color-text-pure)', marginTop: 4, lineHeight: 1.5 }}>
                  {selectedIncident.rootCause}
                </p>
              </div>

              {/* Source Log Evidence */}
              <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface-raised)' }}>
                <span className="decision-metric-label">Source Log Evidence Sequence</span>
                <div
                  style={{
                    backgroundColor: 'var(--color-bg-base)',
                    padding: '10px',
                    borderRadius: 4,
                    border: '1px solid var(--color-border-subtle)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 11,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 4,
                    marginTop: 6,
                  }}
                >
                  {selectedIncident.logSnippet.map((line, idx) => (
                    <div key={idx} style={{ color: line.includes('WARN') || line.includes('ERROR') ? 'var(--color-critical)' : 'var(--color-text-secondary)' }}>
                      <span style={{ color: 'var(--color-text-muted)', marginRight: 8 }}>0{idx + 1}</span>
                      {line}
                    </div>
                  ))}
                </div>
              </div>

              {/* Decision Trace */}
              <DecisionTrace
                decision={selectedIncident.decision}
                isEscalated={selectedIncident.decision !== 'INSUFFICIENT_EVIDENCE'}
                faithfulnessStatus={selectedIncident.faithfulness}
                recordCount={selectedIncident.logSnippet.length}
              />

              {/* Citations */}
              <div className="panel" style={{ backgroundColor: 'var(--color-bg-surface-raised)' }}>
                <span className="decision-metric-label">Verified Citations</span>
                <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                  {selectedIncident.citations.map((c) => (
                    <CitationBadge
                      key={c.citation_id}
                      citationId={c.citation_id}
                      onClick={() => setInspectedCitation(c)}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <EvidenceDrawer
        citation={inspectedCitation}
        provenanceStatus="VERIFIED"
        onClose={() => setInspectedCitation(null)}
      />
    </div>
  );
};
