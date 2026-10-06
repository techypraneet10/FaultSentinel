import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { StatusBadge } from '../components/StatusBadge';
import { SeverityBadge } from '../components/SeverityBadge';
import { DecisionCard } from '../components/DecisionCard';
import { EvidenceStatus } from '../components/EvidenceStatus';
import { ExplanationPanel } from '../components/ExplanationPanel';
import { ClaimCard } from '../components/ClaimCard';
import { CitationBadge } from '../components/CitationBadge';
import { EvidenceDrawer } from '../components/EvidenceDrawer';
import { RequestIdDisplay } from '../components/RequestIdDisplay';
import { HealthIndicator } from '../components/HealthIndicator';
import { LogEditor } from '../components/LogEditor';
import { ProcessingMetadata } from '../components/ProcessingMetadata';
import { Claim, Citation } from '../types';

describe('Component Library Tests', () => {
  describe('StatusBadge', () => {
    it('renders verified variant correctly', () => {
      render(<StatusBadge status="VERIFIED" />);
      const badge = screen.getByTestId('badge-verified');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('badge-verified');
    });

    it('renders rejected variant correctly', () => {
      render(<StatusBadge status="REJECTED" />);
      const badge = screen.getByTestId('badge-rejected');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('badge-rejected');
    });

    it('renders incident badge correctly', () => {
      render(<StatusBadge status="INCIDENT" />);
      const badge = screen.getByTestId('badge-incident');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('badge-incident');
    });

    it('renders custom label if supplied', () => {
      render(<StatusBadge status="VERIFIED" label="CUSTOM LABEL" />);
      expect(screen.getByText('CUSTOM LABEL')).toBeInTheDocument();
    });
  });

  describe('SeverityBadge', () => {
    it('renders HIGH severity with incident styling', () => {
      render(<SeverityBadge severity="HIGH" />);
      const badge = screen.getByTestId('severity-badge');
      expect(badge).toHaveTextContent('Severity: HIGH');
      expect(badge).toHaveClass('badge-incident');
    });

    it('renders LOW severity with insufficient styling', () => {
      render(<SeverityBadge severity="LOW" />);
      const badge = screen.getByTestId('severity-badge');
      expect(badge).toHaveTextContent('Severity: LOW');
      expect(badge).toHaveClass('badge-insufficient');
    });
  });

  describe('DecisionCard', () => {
    it('renders authoritative INCIDENT decision card', () => {
      render(
        <DecisionCard
          decision="INCIDENT"
          severity="HIGH"
          confidence={0.95}
          dataset="hdfs"
        />
      );
      expect(screen.getByTestId('decision-card')).toBeInTheDocument();
      expect(screen.getByTestId('incident-confirmed-alert')).toBeInTheDocument();
      expect(screen.getByText('Phase 8 Deterministic Engine')).toBeInTheDocument();
      expect(screen.getByText('95.0%')).toBeInTheDocument();
    });

    it('renders INSUFFICIENT_EVIDENCE without incident confirmation styling', () => {
      render(
        <DecisionCard
          decision="INSUFFICIENT_EVIDENCE"
          severity="LOW"
          confidence={0.2}
          dataset="bgl"
        />
      );
      expect(screen.getByTestId('insufficient-evidence-alert')).toBeInTheDocument();
      expect(screen.queryByTestId('incident-confirmed-alert')).not.toBeInTheDocument();
      expect(screen.getByText(/The available log sequence does not support a stronger incident classification/i)).toBeInTheDocument();
    });

    it('renders SUSPICIOUS decision alert', () => {
      render(
        <DecisionCard
          decision="SUSPICIOUS"
          severity="MEDIUM"
          confidence={0.65}
          dataset="hdfs"
        />
      );
      expect(screen.getByTestId('suspicious-alert')).toBeInTheDocument();
    });
  });

  describe('EvidenceStatus', () => {
    it('renders verified provenance and faithfulness without alerts', () => {
      render(
        <EvidenceStatus
          evidenceSufficiency="SUFFICIENT"
          provenanceStatus="VERIFIED"
          faithfulnessStatus="VERIFIED"
        />
      );
      expect(screen.getByTestId('evidence-status-panel')).toBeInTheDocument();
      expect(screen.queryByTestId('provenance-rejected-alert')).not.toBeInTheDocument();
      expect(screen.queryByTestId('faithfulness-failed-alert')).not.toBeInTheDocument();
    });

    it('renders warning alert when provenance is rejected', () => {
      render(
        <EvidenceStatus
          evidenceSufficiency="INSUFFICIENT"
          provenanceStatus="REJECTED"
          faithfulnessStatus="VERIFIED"
        />
      );
      expect(screen.getByTestId('provenance-rejected-alert')).toBeInTheDocument();
    });

    it('renders warning alert when faithfulness fails', () => {
      render(
        <EvidenceStatus
          evidenceSufficiency="SUFFICIENT"
          provenanceStatus="VERIFIED"
          faithfulnessStatus="UNFAITHFUL"
        />
      );
      expect(screen.getByTestId('faithfulness-failed-alert')).toBeInTheDocument();
      expect(screen.getAllByText(/Grounding verification failed/i).length).toBeGreaterThan(0);
    });
  });

  describe('ExplanationPanel', () => {
    it('renders generated explanation and summary', () => {
      render(
        <ExplanationPanel
          explanationStatus="GENERATED"
          summary="An anomaly was detected."
          explanation="### Details&#10;Repeated failure in DataNode."
        />
      );
      expect(screen.getByTestId('explanation-summary')).toHaveTextContent('An anomaly was detected.');
      expect(screen.getByText('Repeated failure in DataNode.')).toBeInTheDocument();
    });

    it('renders failed state message when status is FAILED', () => {
      render(
        <ExplanationPanel
          explanationStatus="FAILED"
          summary={null}
          explanation={null}
        />
      );
      expect(screen.getByTestId('explanation-failed-message')).toBeInTheDocument();
    });

    it('renders skipped state message when status is SKIPPED', () => {
      render(
        <ExplanationPanel
          explanationStatus="SKIPPED"
          summary={null}
          explanation={null}
        />
      );
      expect(screen.getByTestId('explanation-skipped-message')).toBeInTheDocument();
    });
  });

  describe('ClaimCard & CitationBadge', () => {
    const mockClaim: Claim = {
      claim_id: 'CLM-001',
      claim_type: 'OBSERVATION',
      text: 'Repeated DataNode connection timeout.',
      citation_ids: ['CIT-001', 'CIT-002'],
      supported: true,
      support_score: 1.0,
    };

    it('renders claim details and citation buttons', () => {
      const handleCitationClick = vi.fn();
      render(<ClaimCard claim={mockClaim} onCitationClick={handleCitationClick} />);

      expect(screen.getByText('CLM-001')).toBeInTheDocument();
      expect(screen.getByText('OBSERVATION')).toBeInTheDocument();
      expect(screen.getByText('Repeated DataNode connection timeout.')).toBeInTheDocument();

      const btn1 = screen.getByTestId('citation-btn-cit-001');
      expect(btn1).toBeInTheDocument();
      fireEvent.click(btn1);
      expect(handleCitationClick).toHaveBeenCalledWith('CIT-001');
    });

    it('renders unverified citation styling when provenance is not verified', () => {
      render(<CitationBadge citationId="CIT-099" isVerified={false} />);
      const btn = screen.getByTestId('citation-btn-cit-099');
      expect(btn).toHaveAttribute('title', expect.stringContaining('Unverified'));
    });
  });

  describe('EvidenceDrawer', () => {
    const mockCitation: Citation = {
      citation_id: 'CIT-001',
      dataset: 'hdfs',
      split: 'train',
      source_window_id: 'blk_12345',
      line_start: 10,
      line_end: 15,
      citation_text: 'ERROR Connection refused to /10.0.0.1:50010',
    };

    it('renders citation metadata and excerpt', () => {
      const handleClose = vi.fn();
      render(
        <EvidenceDrawer
          citation={mockCitation}
          provenanceStatus="VERIFIED"
          onClose={handleClose}
        />
      );

      expect(screen.getByTestId('evidence-drawer')).toBeInTheDocument();
      expect(screen.getByText('Citation: CIT-001')).toBeInTheDocument();
      expect(screen.getByText('blk_12345')).toBeInTheDocument();
      expect(screen.getByText('10 – 15')).toBeInTheDocument();
      expect(screen.getByTestId('citation-excerpt')).toHaveTextContent('ERROR Connection refused');

      fireEvent.click(screen.getByTestId('drawer-close-btn'));
      expect(handleClose).toHaveBeenCalled();
    });

    it('does not render when citation is null', () => {
      const { container } = render(
        <EvidenceDrawer citation={null} provenanceStatus="VERIFIED" onClose={vi.fn()} />
      );
      expect(container.firstChild).toBeNull();
    });
  });

  describe('RequestIdDisplay', () => {
    it('renders request ID with copy button', () => {
      render(<RequestIdDisplay requestId="req-abc-123" />);
      expect(screen.getByTestId('request-id-display')).toHaveTextContent('REQ: req-abc-123');
      expect(screen.getByTestId('copy-request-id-btn')).toBeInTheDocument();
    });
  });

  describe('HealthIndicator', () => {
    it('renders connected dot and label', () => {
      render(<HealthIndicator connectionState="connected" />);
      expect(screen.getByTestId('health-dot-connected')).toBeInTheDocument();
      expect(screen.getByText('API Connected')).toBeInTheDocument();
    });

    it('renders offline dot and label', () => {
      render(<HealthIndicator connectionState="offline" />);
      expect(screen.getByTestId('health-dot-offline')).toBeInTheDocument();
      expect(screen.getByText('Offline')).toBeInTheDocument();
    });
  });

  describe('LogEditor', () => {
    it('calculates records and displays telemetry', () => {
      const handleDatasetChange = vi.fn();
      const handleRawTextChange = vi.fn();

      render(
        <LogEditor
          dataset="hdfs"
          onDatasetChange={handleDatasetChange}
          rawText={'line1\nline2\nline3'}
          onRawTextChange={handleRawTextChange}
        />
      );

      expect(screen.getByTestId('record-count')).toHaveTextContent('3 / 200');
      expect(screen.getByTestId('logs-textarea')).toHaveValue('line1\nline2\nline3');
    });

    it('shows validation warning when record count exceeds 200', () => {
      const excessiveLogs = Array.from({ length: 205 }, (_, i) => `log line ${i}`).join('\n');
      render(
        <LogEditor
          dataset="hdfs"
          onDatasetChange={vi.fn()}
          rawText={excessiveLogs}
          onRawTextChange={vi.fn()}
        />
      );

      expect(screen.getByTestId('validation-errors')).toHaveTextContent(
        'Record count (205) exceeds maximum allowed (200).'
      );
    });

    it('loads demo samples when sample buttons are clicked', () => {
      const handleDataset = vi.fn();
      const handleText = vi.fn();

      render(
        <LogEditor
          dataset="hdfs"
          onDatasetChange={handleDataset}
          rawText=""
          onRawTextChange={handleText}
        />
      );

      fireEvent.click(screen.getByTestId('load-bgl-sample-btn'));
      expect(handleDataset).toHaveBeenCalledWith('bgl');
      expect(handleText).toHaveBeenCalledWith(expect.stringContaining('RAS KERNEL INFO'));
    });
  });

  describe('ProcessingMetadata', () => {
    it('renders collapsible metadata panel', () => {
      const meta = { record_count: 7, model_name: 'test-model', provider: 'test-provider' };
      render(<ProcessingMetadata metadata={meta} requestId="test-req-999" />);

      expect(screen.queryByTestId('metadata-content')).not.toBeInTheDocument();

      fireEvent.click(screen.getByTestId('toggle-metadata-btn'));
      expect(screen.getByTestId('metadata-content')).toBeInTheDocument();
      expect(screen.getByText('7')).toBeInTheDocument();
      expect(screen.getByText('test-model')).toBeInTheDocument();
    });
  });
});
