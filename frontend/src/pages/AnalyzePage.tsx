import React, { useState, useMemo } from 'react';
import { AnalyzeResponse } from '../types';
import { useAnalysis } from '../hooks/useAnalysis';
import { LogEditor } from '../components/LogEditor';
import { DecisionCard } from '../components/DecisionCard';
import { EvidenceStatus } from '../components/EvidenceStatus';
import { ExplanationPanel } from '../components/ExplanationPanel';
import { ClaimCard } from '../components/ClaimCard';
import { EvidenceDrawer } from '../components/EvidenceDrawer';
import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { ProcessingMetadata } from '../components/ProcessingMetadata';
import { RequestIdDisplay } from '../components/RequestIdDisplay';
import { DecisionTrace } from '../components/DecisionTrace';

interface AnalyzePageProps {
  onAnalysisComplete?: (result: AnalyzeResponse) => void;
}

export const AnalyzePage: React.FC<AnalyzePageProps> = ({ onAnalysisComplete }) => {
  const {
    dataset,
    setDataset,
    rawText,
    setRawText,
    workflowState,
    result,
    error,
    selectedCitation,
    analyze,
    reset,
    selectCitationById,
    closeCitationDrawer,
  } = useAnalysis();

  React.useEffect(() => {
    if (result && onAnalysisComplete) {
      onAnalysisComplete(result);
    }
  }, [result, onAnalysisComplete]);

  const [claimTypeFilter, setClaimTypeFilter] = useState<string>('ALL');

  const filteredClaims = useMemo(() => {
    if (!result || !result.claims) return [];
    if (claimTypeFilter === 'ALL') return result.claims;
    return result.claims.filter(
      (c) => c.claim_type.toUpperCase() === claimTypeFilter.toUpperCase()
    );
  }, [result, claimTypeFilter]);

  const isAnalyzing = workflowState === 'analyzing';
  const hasInput = rawText.trim().length > 0;

  return (
    <div data-testid="analyze-page" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Top Action Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <button
            type="button"
            className="btn btn-primary"
            onClick={analyze}
            disabled={isAnalyzing || !hasInput}
            data-testid="analyze-btn"
          >
            {isAnalyzing ? 'Analyzing Log Sequence...' : 'Analyze Logs'}
          </button>
          {result && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={reset}
              data-testid="new-analysis-btn"
            >
              New Analysis
            </button>
          )}
        </div>

        {result && <RequestIdDisplay requestId={result.request_id} />}
      </div>

      {/* Main Investigation Workspace */}
      <div style={{ display: 'grid', gridTemplateColumns: result ? '1fr 1fr' : '1fr', gap: '16px' }}>
        {/* Left Column: Log Editor / Terminal Viewer with highlighted citation lines */}
        <div>
          <LogEditor
            dataset={dataset}
            onDatasetChange={setDataset}
            rawText={rawText}
            onRawTextChange={setRawText}
            disabled={isAnalyzing}
            highlightedLineRange={
              selectedCitation
                ? { start: selectedCitation.line_start, end: selectedCitation.line_end }
                : null
            }
          />

          {result && (
            <DecisionTrace
              decision={result.decision}
              isEscalated={result.decision !== 'INSUFFICIENT_EVIDENCE'}
              faithfulnessStatus={result.faithfulness_status}
              recordCount={rawText.split('\n').filter((l) => l.trim().length > 0).length}
            />
          )}
        </div>

        {/* Right Column: Decision, Explanation, Claims & Grounding */}
        <div>
          {workflowState === 'idle' && !result && <EmptyState />}
          {workflowState === 'analyzing' && <LoadingState />}
          {workflowState === 'failed' && error && (
            <ErrorState
              code={error.code}
              message={error.message}
              requestId={error.requestId}
              onRetry={analyze}
            />
          )}

          {result && workflowState === 'completed' && (
            <div data-testid="analysis-results-container" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <DecisionCard
                decision={result.decision}
                severity={result.severity}
                confidence={result.confidence}
                dataset={result.dataset}
                conformalDecision={result.decision === 'INSUFFICIENT_EVIDENCE' ? 'AUTO-CLEAR' : 'ESCALATE'}
                faithfulnessStatus={result.faithfulness_status}
                llmInvocation={result.explanation_status === 'GENERATED'}
              />

              <EvidenceStatus
                evidenceSufficiency={result.evidence_sufficiency}
                provenanceStatus={result.provenance_status}
                faithfulnessStatus={result.faithfulness_status}
              />

              <ExplanationPanel
                explanationStatus={result.explanation_status}
                explanation={result.explanation}
                summary={result.summary}
                faithfulnessStatus={result.faithfulness_status}
              />

              <div className="panel" data-testid="claims-section" style={{ backgroundColor: 'var(--color-bg-surface)' }}>
                <div className="panel-header" style={{ marginBottom: 12 }}>
                  <div>
                    <span className="panel-title">Extracted Incident Claims & Grounding</span>
                    <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 2 }}>
                      Click source citations to highlight corresponding lines in log viewer
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 11, color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>
                      FILTER:
                    </span>
                    <select
                      className="form-select"
                      style={{ width: 'auto', padding: '2px 8px', fontSize: 12 }}
                      value={claimTypeFilter}
                      onChange={(e) => setClaimTypeFilter(e.target.value)}
                      data-testid="claim-type-filter"
                    >
                      <option value="ALL">All Types</option>
                      <option value="OBSERVATION">Observation</option>
                      <option value="EVIDENCE">Evidence</option>
                      <option value="CORRELATION">Correlation</option>
                      <option value="INTERPRETATION">Interpretation</option>
                      <option value="UNCERTAINTY">Uncertainty</option>
                      <option value="RECOMMENDATION">Recommendation</option>
                    </select>
                  </div>
                </div>

                {filteredClaims.length > 0 ? (
                  filteredClaims.map((claim) => (
                    <ClaimCard
                      key={claim.claim_id}
                      claim={claim}
                      onCitationClick={selectCitationById}
                      provenanceVerified={result.provenance_status === 'VERIFIED'}
                    />
                  ))
                ) : (
                  <div style={{ color: 'var(--color-text-muted)', fontSize: 13, padding: '12px 0' }}>
                    No claims match the selected filter category.
                  </div>
                )}
              </div>

              <ProcessingMetadata
                metadata={result.processing_metadata}
                requestId={result.request_id}
              />
            </div>
          )}
        </div>
      </div>

      <EvidenceDrawer
        citation={selectedCitation}
        provenanceStatus={result?.provenance_status || 'VERIFIED'}
        onClose={closeCitationDrawer}
      />
    </div>
  );
};
