import { useState, useCallback } from 'react';
import {
  DatasetType,
  AnalyzeResponse,
  Citation,
} from '../types';
import { apiService, ApiError } from '../services/api';

export type AnalysisWorkflowState = 'idle' | 'validating' | 'analyzing' | 'completed' | 'failed';

export interface AnalysisErrorState {
  code: string;
  message: string;
  requestId?: string;
}

export function useAnalysis() {
  const [dataset, setDataset] = useState<DatasetType>('hdfs');
  const [rawText, setRawText] = useState<string>('');
  const [workflowState, setWorkflowState] = useState<AnalysisWorkflowState>('idle');
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<AnalysisErrorState | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  const reset = useCallback(() => {
    setWorkflowState('idle');
    setResult(null);
    setError(null);
    setSelectedCitation(null);
  }, []);

  const analyze = useCallback(async () => {
    if (workflowState === 'analyzing') return;

    const lines = rawText
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    if (lines.length === 0) {
      setError({
        code: 'VALIDATION_ERROR',
        message: 'Log sequence must not be empty. Please enter at least one log line.',
      });
      setWorkflowState('failed');
      return;
    }

    if (lines.length > 200) {
      setError({
        code: 'PAYLOAD_TOO_LARGE',
        message: `Log record count (${lines.length}) exceeds maximum allowable limit of 200 records.`,
      });
      setWorkflowState('failed');
      return;
    }

    setWorkflowState('analyzing');
    setError(null);

    try {
      const response = await apiService.analyzeLogs({
        dataset,
        logs: lines,
        options: {
          include_citations: true,
          include_raw_excerpts: true,
        },
      });

      setResult(response);
      setWorkflowState('completed');
    } catch (err) {
      if (err instanceof ApiError) {
        setError({
          code: err.code,
          message: err.message,
          requestId: err.requestId,
        });
      } else if (err instanceof Error) {
        setError({
          code: 'CONNECTION_ERROR',
          message: err.message,
        });
      } else {
        setError({
          code: 'UNEXPECTED_ERROR',
          message: 'An unexpected error occurred during incident analysis.',
        });
      }
      setWorkflowState('failed');
    }
  }, [dataset, rawText, workflowState]);

  const selectCitationById = useCallback(
    (citationId: string) => {
      if (!result) return;
      const found = result.citations.find((c) => c.citation_id === citationId);
      if (found) {
        setSelectedCitation(found);
      } else {
        // Fallback placeholder citation object if not in full array
        setSelectedCitation({
          citation_id: citationId,
          dataset: result.dataset,
          split: 'train',
          source_window_id: 'unknown',
        });
      }
    },
    [result]
  );

  const closeCitationDrawer = useCallback(() => {
    setSelectedCitation(null);
  }, []);

  return {
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
  };
}
