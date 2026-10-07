import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { App } from '../App';
import { apiService, ApiError } from '../services/api';
import { AnalyzeResponse } from '../types';

describe('FaultSentinel Operator Dashboard Integration Tests', () => {
  const mockHdfsResponse: AnalyzeResponse = {
    request_id: 'hdfs-req-12345',
    status: 'success',
    dataset: 'hdfs',
    decision: 'INCIDENT',
    severity: 'HIGH',
    confidence: 0.99,
    explanation_status: 'GENERATED',
    summary: 'Critical NameNode/DataNode invalid block state.',
    explanation: '### Incident Grounding&#10;DataNode encountered IOException on block.',
    claims: [
      {
        claim_id: 'CLM-001',
        claim_type: 'OBSERVATION',
        text: 'DataNode failed during block transmission.',
        citation_ids: ['CIT-HDFS-001'],
        supported: true,
        support_score: 1.0,
      },
      {
        claim_id: 'CLM-002',
        claim_type: 'RECOMMENDATION',
        text: 'Check network routing to DataNode.',
        citation_ids: ['CIT-HDFS-001'],
        supported: true,
        support_score: 1.0,
      },
    ],
    citations: [
      {
        citation_id: 'CIT-HDFS-001',
        dataset: 'hdfs',
        split: 'train',
        source_window_id: 'blk_99999',
        line_start: 10,
        line_end: 14,
        citation_text: 'WARN dfs.DataNode: Block is not valid',
      },
    ],
    evidence_sufficiency: 'SUFFICIENT',
    provenance_status: 'VERIFIED',
    faithfulness_status: 'VERIFIED',
    processing_metadata: { record_count: 7, model_name: 'mock-llm', provider: 'deterministic' },
  };

  const mockBglResponse: AnalyzeResponse = {
    request_id: 'bgl-req-67890',
    status: 'abstention',
    dataset: 'bgl',
    decision: 'INSUFFICIENT_EVIDENCE',
    severity: 'LOW',
    confidence: 0.15,
    explanation_status: 'GENERATED',
    summary: 'Sparse telemetry does not satisfy conformal anomaly gate.',
    explanation: 'Log records do not display statistically significant incident correlation.',
    claims: [
      {
        claim_id: 'CLM-BGL-01',
        claim_type: 'UNCERTAINTY',
        text: 'Telemetry volume below conformal incident threshold.',
        citation_ids: ['CIT-BGL-01'],
        supported: true,
        support_score: 1.0,
      },
    ],
    citations: [
      {
        citation_id: 'CIT-BGL-01',
        dataset: 'bgl',
        split: 'train',
        source_window_id: 'bgl_win_01',
        line_start: 1,
        line_end: 3,
        citation_text: 'RAS KERNEL INFO instruction cache parity error corrected',
      },
    ],
    evidence_sufficiency: 'INSUFFICIENT',
    provenance_status: 'VERIFIED',
    faithfulness_status: 'VERIFIED',
    processing_metadata: { record_count: 3 },
  };

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(apiService, 'healthLive').mockResolvedValue({ status: 'ok' });
    vi.spyOn(apiService, 'healthReady').mockResolvedValue({
      status: 'ready',
      checks: { configuration: 'ok', pipeline: 'ok' },
    });
  });

  it('renders application shell and navigation items', async () => {
    render(<App />);

    expect(screen.getByTestId('app-layout')).toBeInTheDocument();
    expect(screen.getByTestId('app-header')).toBeInTheDocument();
    expect(screen.getByTestId('nav-analyze')).toBeInTheDocument();
    expect(screen.getByTestId('nav-review')).toBeInTheDocument();
    expect(screen.getByTestId('nav-status')).toBeInTheDocument();
    expect(screen.getByTestId('nav-overview')).toBeInTheDocument();
  });

  it('switches navigation tabs cleanly', async () => {
    render(<App />);

    fireEvent.click(screen.getByTestId('nav-overview'));
    expect(await screen.findByTestId('overview-page')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('nav-status'));
    expect(await screen.findByTestId('api-status-page')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('nav-analyze'));
    expect(await screen.findByTestId('analyze-page')).toBeInTheDocument();
  });

  it('submits HDFS analysis and displays authoritative INCIDENT result', async () => {
    const analyzeSpy = vi.spyOn(apiService, 'analyzeLogs').mockResolvedValue(mockHdfsResponse);

    render(<App />);

    // Load HDFS demo
    fireEvent.click(screen.getByTestId('load-hdfs-sample-btn'));

    // Submit analysis
    const submitBtn = screen.getByTestId('analyze-btn');
    expect(submitBtn).not.toBeDisabled();
    fireEvent.click(submitBtn);

    // Verify loading and invocation
    expect(analyzeSpy).toHaveBeenCalledWith({
      dataset: 'hdfs',
      logs: expect.any(Array),
      options: {
        include_citations: true,
        include_raw_excerpts: true,
      },
    });

    // Verify response rendering
    expect(await screen.findByTestId('analysis-results-container')).toBeInTheDocument();
    expect(screen.getByTestId('decision-card')).toBeInTheDocument();
    expect(screen.getAllByText('INCIDENT').length).toBeGreaterThan(0);
    expect(screen.getByTestId('severity-badge')).toHaveTextContent('Severity: HIGH');
    expect(screen.getByTestId('incident-confirmed-alert')).toBeInTheDocument();
    expect(screen.getByTestId('evidence-status-panel')).toBeInTheDocument();
    expect(screen.getByTestId('explanation-panel')).toBeInTheDocument();
    expect(screen.getByTestId('claims-section')).toBeInTheDocument();
  });

  it('BGL SAFETY CASE: preserves INSUFFICIENT_EVIDENCE and prevents INCIDENT display', async () => {
    vi.spyOn(apiService, 'analyzeLogs').mockResolvedValue(mockBglResponse);

    render(<App />);

    // Load BGL demo
    fireEvent.click(screen.getByTestId('load-bgl-sample-btn'));
    fireEvent.click(screen.getByTestId('analyze-btn'));

    expect(await screen.findByTestId('analysis-results-container')).toBeInTheDocument();

    // Verify INSUFFICIENT_EVIDENCE is displayed prominently
    expect(screen.getByTestId('insufficient-evidence-alert')).toBeInTheDocument();
    expect(screen.getByText(/The available log sequence does not support a stronger incident classification/i)).toBeInTheDocument();

    // Mandatory negative assertions: MUST NOT show incident confirmed
    expect(screen.queryByTestId('incident-confirmed-alert')).not.toBeInTheDocument();
    expect(screen.queryByText(/Incident Confirmed/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/HIGH CONFIDENCE INCIDENT/i)).not.toBeInTheDocument();
  });

  it('filters claims by type properly', async () => {
    vi.spyOn(apiService, 'analyzeLogs').mockResolvedValue(mockHdfsResponse);

    render(<App />);

    fireEvent.click(screen.getByTestId('load-hdfs-sample-btn'));
    fireEvent.click(screen.getByTestId('analyze-btn'));

    expect(await screen.findByTestId('claims-section')).toBeInTheDocument();
    expect(screen.getByTestId('claim-card-clm-001')).toBeInTheDocument();
    expect(screen.getByTestId('claim-card-clm-002')).toBeInTheDocument();

    // Filter to RECOMMENDATION only
    fireEvent.change(screen.getByTestId('claim-type-filter'), { target: { value: 'RECOMMENDATION' } });
    expect(screen.queryByTestId('claim-card-clm-001')).not.toBeInTheDocument();
    expect(screen.getByTestId('claim-card-clm-002')).toBeInTheDocument();
  });

  it('opens citation evidence drawer from claim and closes cleanly', async () => {
    vi.spyOn(apiService, 'analyzeLogs').mockResolvedValue(mockHdfsResponse);

    render(<App />);

    fireEvent.click(screen.getByTestId('load-hdfs-sample-btn'));
    fireEvent.click(screen.getByTestId('analyze-btn'));

    expect(await screen.findByTestId('claims-section')).toBeInTheDocument();

    const citBtn = screen.getAllByTestId('citation-btn-cit-hdfs-001')[0];
    fireEvent.click(citBtn);

    expect(screen.getByTestId('evidence-drawer')).toBeInTheDocument();
    expect(screen.getByText('Citation: CIT-HDFS-001')).toBeInTheDocument();
    expect(screen.getByTestId('citation-excerpt')).toHaveTextContent('WARN dfs.DataNode');

    fireEvent.click(screen.getByTestId('drawer-close-btn'));
    await waitFor(() => {
      expect(screen.queryByTestId('evidence-drawer')).not.toBeInTheDocument();
    });
  });

  it('handles backend 400/422 validation errors with request ID preserved', async () => {
    vi.spyOn(apiService, 'analyzeLogs').mockRejectedValue(
      new ApiError('Dataset must be one of hdfs or bgl', 'INVALID_REQUEST', 'err-req-422', 422)
    );

    render(<App />);

    fireEvent.change(screen.getByTestId('logs-textarea'), { target: { value: 'some invalid log' } });
    fireEvent.click(screen.getByTestId('analyze-btn'));

    expect(await screen.findByTestId('error-state')).toBeInTheDocument();
    expect(screen.getByText('Dataset must be one of hdfs or bgl')).toBeInTheDocument();
    expect(screen.getByText('INVALID_REQUEST')).toBeInTheDocument();
    expect(screen.getByText('REQ: err-req-422')).toBeInTheDocument();
  });

  it('handles backend 500/503 service errors gracefully without leaking tracebacks', async () => {
    vi.spyOn(apiService, 'analyzeLogs').mockRejectedValue(
      new ApiError('Incident triage pipeline encountered an unrecoverable internal error.', 'PIPELINE_ERROR', 'err-500-trace', 500)
    );

    render(<App />);

    fireEvent.change(screen.getByTestId('logs-textarea'), { target: { value: 'log line' } });
    fireEvent.click(screen.getByTestId('analyze-btn'));

    expect(await screen.findByTestId('error-state')).toBeInTheDocument();
    expect(screen.getByText('Incident triage pipeline encountered an unrecoverable internal error.')).toBeInTheDocument();

    // Verify no raw tracebacks or filesystem paths are displayed
    expect(screen.queryByText(/Traceback/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/d:\\FaultSentinel/i)).not.toBeInTheDocument();
  });

  it('prevents submission when log input is empty', () => {
    render(<App />);

    const submitBtn = screen.getByTestId('analyze-btn');
    expect(submitBtn).toBeDisabled();
  });

  it('resets analysis when New Analysis button is clicked', async () => {
    vi.spyOn(apiService, 'analyzeLogs').mockResolvedValue(mockHdfsResponse);

    render(<App />);

    fireEvent.click(screen.getByTestId('load-hdfs-sample-btn'));
    fireEvent.click(screen.getByTestId('analyze-btn'));

    expect(await screen.findByTestId('analysis-results-container')).toBeInTheDocument();

    const newBtn = screen.getByTestId('new-analysis-btn');
    fireEvent.click(newBtn);

    expect(screen.queryByTestId('analysis-results-container')).not.toBeInTheDocument();
    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
  });

  it('updates Review page with completed analysis', async () => {
    vi.spyOn(apiService, 'analyzeLogs').mockResolvedValue(mockHdfsResponse);

    render(<App />);

    fireEvent.click(screen.getByTestId('load-hdfs-sample-btn'));
    fireEvent.click(screen.getByTestId('analyze-btn'));

    expect(await screen.findByTestId('analysis-results-container')).toBeInTheDocument();

    // Switch to Review page
    fireEvent.click(screen.getByTestId('nav-review'));
    expect(await screen.findByTestId('review-page')).toBeInTheDocument();
    expect(screen.getByTestId('citations-table')).toBeInTheDocument();
    expect(screen.getByText('CIT-HDFS-001')).toBeInTheDocument();
  });
});
