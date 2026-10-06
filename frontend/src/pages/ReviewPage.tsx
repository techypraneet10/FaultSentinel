import React, { useState } from 'react';
import { AnalyzeResponse } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { CitationBadge } from '../components/CitationBadge';
import { EvidenceDrawer } from '../components/EvidenceDrawer';

interface ReviewPageProps {
  currentAnalysis: AnalyzeResponse | null;
  onNavigateAnalyze: () => void;
}

export const ReviewPage: React.FC<ReviewPageProps> = ({
  currentAnalysis,
  onNavigateAnalyze,
}) => {
  const [selectedCitationId, setSelectedCitationId] = useState<string | null>(null);

  if (!currentAnalysis) {
    return (
      <div className="panel" style={{ textAlign: 'center', padding: '48px 24px' }} data-testid="review-empty">
        <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>
          No Active Analysis to Review
        </h3>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: 13, marginBottom: 16 }}>
          Run an incident analysis first from the Incident Analysis workspace before conducting deep-dive evidence reviews.
        </p>
        <button
          type="button"
          className="btn btn-primary"
          onClick={onNavigateAnalyze}
          data-testid="go-to-analyze-btn"
        >
          Go to Incident Analysis
        </button>
      </div>
    );
  }

  const selectedCitation = selectedCitationId
    ? currentAnalysis.citations.find((c) => c.citation_id === selectedCitationId) || {
        citation_id: selectedCitationId,
        dataset: currentAnalysis.dataset,
        split: 'train',
        source_window_id: 'unknown',
      }
    : null;

  return (
    <div data-testid="review-page">
      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">Incident Evidence Audit & Citations</span>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span className="badge badge-neutral">REQ: {currentAnalysis.request_id}</span>
            <StatusBadge status={currentAnalysis.decision} />
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          <h4 style={{ fontSize: 13, textTransform: 'uppercase', color: 'var(--color-text-secondary)', marginBottom: 8 }}>
            Authoritative Citation Register ({currentAnalysis.citations.length} Verified Sources)
          </h4>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: 13,
              fontFamily: 'var(--font-mono)',
            }}
            data-testid="citations-table"
          >
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border-default)', textAlign: 'left', color: 'var(--color-text-muted)' }}>
                <th style={{ padding: '8px 4px' }}>Citation ID</th>
                <th style={{ padding: '8px 4px' }}>Dataset</th>
                <th style={{ padding: '8px 4px' }}>Split</th>
                <th style={{ padding: '8px 4px' }}>Source Window</th>
                <th style={{ padding: '8px 4px' }}>Lines</th>
                <th style={{ padding: '8px 4px' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {currentAnalysis.citations.map((c) => (
                <tr
                  key={c.citation_id}
                  style={{ borderBottom: '1px solid var(--color-border-subtle)' }}
                  data-testid={`citation-row-${c.citation_id.toLowerCase()}`}
                >
                  <td style={{ padding: '8px 4px', color: 'var(--color-text-code)', fontWeight: 700 }}>
                    {c.citation_id}
                  </td>
                  <td style={{ padding: '8px 4px' }}>{c.dataset.toUpperCase()}</td>
                  <td style={{ padding: '8px 4px' }}>{c.split}</td>
                  <td style={{ padding: '8px 4px' }}>{c.source_window_id}</td>
                  <td style={{ padding: '8px 4px' }}>
                    {c.line_start !== null && c.line_start !== undefined ? `${c.line_start}–${c.line_end}` : 'N/A'}
                  </td>
                  <td style={{ padding: '8px 4px' }}>
                    <CitationBadge
                      citationId={c.citation_id}
                      onClick={(id) => setSelectedCitationId(id)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <EvidenceDrawer
        citation={selectedCitation}
        provenanceStatus={currentAnalysis.provenance_status}
        onClose={() => setSelectedCitationId(null)}
      />
    </div>
  );
};
