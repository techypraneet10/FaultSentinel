import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ReviewPage } from '../pages/ReviewPage';
import { OverviewPage } from '../pages/OverviewPage';
import { ApiStatusPage } from '../pages/ApiStatusPage';
import { AnalyzeResponse } from '../types';
import { apiService } from '../services/api';

describe('Page Views & Navigation Tests', () => {
  const mockAnalysis: AnalyzeResponse = {
    request_id: 'test-req-001',
    status: 'success',
    dataset: 'hdfs',
    decision: 'INCIDENT',
    severity: 'HIGH',
    confidence: 0.98,
    explanation_status: 'GENERATED',
    summary: 'DataNode communication failure detected.',
    explanation: 'Detailed analysis of HDFS sequence.',
    claims: [
      {
        claim_id: 'CLM-01',
        claim_type: 'OBSERVATION',
        text: 'DataNode failed during block transmission.',
        citation_ids: ['CIT-01'],
        supported: true,
        support_score: 1.0,
      },
    ],
    citations: [
      {
        citation_id: 'CIT-01',
        dataset: 'hdfs',
        split: 'train',
        source_window_id: 'blk_111',
        line_start: 1,
        line_end: 5,
        citation_text: 'ERROR block blk_111 invalid',
      },
    ],
    evidence_sufficiency: 'SUFFICIENT',
    provenance_status: 'VERIFIED',
    faithfulness_status: 'VERIFIED',
    processing_metadata: { record_count: 7 },
  };

  describe('ReviewPage', () => {
    it('renders empty message when no active analysis exists', () => {
      const handleNavigate = vi.fn();
      render(<ReviewPage currentAnalysis={null} onNavigateAnalyze={handleNavigate} />);

      expect(screen.getByTestId('review-empty')).toBeInTheDocument();
      fireEvent.click(screen.getByTestId('go-to-analyze-btn'));
      expect(handleNavigate).toHaveBeenCalled();
    });

    it('renders citation audit table when analysis is present', () => {
      render(<ReviewPage currentAnalysis={mockAnalysis} onNavigateAnalyze={vi.fn()} />);

      expect(screen.getByTestId('review-page')).toBeInTheDocument();
      expect(screen.getByTestId('citations-table')).toBeInTheDocument();
      expect(screen.getByText('CIT-01')).toBeInTheDocument();
      expect(screen.getByText('blk_111')).toBeInTheDocument();
      expect(screen.getByText('1–5')).toBeInTheDocument();
    });

    it('opens evidence drawer when citation row button is clicked', () => {
      render(<ReviewPage currentAnalysis={mockAnalysis} onNavigateAnalyze={vi.fn()} />);

      fireEvent.click(screen.getByTestId('citation-btn-cit-01'));
      expect(screen.getByTestId('evidence-drawer')).toBeInTheDocument();
      expect(screen.getByText('ERROR block blk_111 invalid')).toBeInTheDocument();
    });
  });

  describe('OverviewPage', () => {
    it('renders system architecture pipeline and governance hierarchy', () => {
      render(<OverviewPage />);
      expect(screen.getByTestId('overview-page')).toBeInTheDocument();
      expect(screen.getByText('System Architecture & Operator Governance')).toBeInTheDocument();
      expect(screen.getByText(/Phase 8: Authoritative Deterministic Reasoning Engine/i)).toBeInTheDocument();
      expect(screen.getByText(/BGL Calibration Safety/i)).toBeInTheDocument();
    });
  });

  describe('ApiStatusPage', () => {
    it('calls health endpoints and renders subsystem checks', async () => {
      vi.spyOn(apiService, 'healthLive').mockResolvedValue({ status: 'ok' });
      vi.spyOn(apiService, 'healthReady').mockResolvedValue({
        status: 'ready',
        checks: { configuration: 'ok', pipeline: 'ok' },
      });
      vi.spyOn(apiService, 'fetchRootMetadata').mockResolvedValue({
        service_name: 'SentinelLog',
        api_version: 'v1',
        app_version: '0.10.0',
        status: 'operational',
      });

      render(<ApiStatusPage />);

      expect(await screen.findByText('Process Active')).toBeInTheDocument();
      expect(await screen.findByText('Ready for triage requests')).toBeInTheDocument();
      expect(await screen.findByTestId('check-configuration')).toBeInTheDocument();
      expect(await screen.findByTestId('check-pipeline')).toBeInTheDocument();
    });

    it('renders error alert when health check fails', async () => {
      vi.spyOn(apiService, 'healthLive').mockRejectedValue(new Error('Connection refused'));

      render(<ApiStatusPage />);

      expect(await screen.findByTestId('status-error-alert')).toHaveTextContent('Connection refused');
    });
  });
});
