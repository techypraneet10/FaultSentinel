import React, { useMemo } from 'react';
import { DatasetType } from '../types';
import { formatBytes } from '../utils/formatters';
import { DEMO_HDFS_LOGS, DEMO_BGL_LOGS } from '../utils/sampleData';

interface LogEditorProps {
  dataset: DatasetType;
  onDatasetChange: (dataset: DatasetType) => void;
  rawText: string;
  onRawTextChange: (text: string) => void;
  disabled?: boolean;
}

const MAX_RECORDS = 200;
const MAX_LINE_LENGTH = 2000;
const MAX_PAYLOAD_BYTES = 1024 * 1024; // 1MB

export const LogEditor: React.FC<LogEditorProps> = ({
  dataset,
  onDatasetChange,
  rawText,
  onRawTextChange,
  disabled = false,
}) => {
  const lines = useMemo(() => {
    return rawText
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => l.length > 0);
  }, [rawText]);

  const byteSize = useMemo(() => {
    return new Blob([rawText]).size;
  }, [rawText]);

  const validationErrors = useMemo(() => {
    const errs: string[] = [];
    if (lines.length > MAX_RECORDS) {
      errs.push(`Record count (${lines.length}) exceeds maximum allowed (${MAX_RECORDS}).`);
    }
    const longLines = lines.filter((l) => l.length > MAX_LINE_LENGTH);
    if (longLines.length > 0) {
      errs.push(`${longLines.length} line(s) exceed maximum length of ${MAX_LINE_LENGTH} characters.`);
    }
    if (byteSize > MAX_PAYLOAD_BYTES) {
      errs.push(`Payload size (${formatBytes(byteSize)}) exceeds maximum allowed (1.0 MB).`);
    }
    return errs;
  }, [lines, byteSize]);

  const handleLoadSample = (ds: DatasetType) => {
    onDatasetChange(ds);
    const sample = ds === 'hdfs' ? DEMO_HDFS_LOGS : DEMO_BGL_LOGS;
    onRawTextChange(sample.join('\n'));
  };

  return (
    <div className="panel" data-testid="log-editor-panel">
      <div className="panel-header">
        <span className="panel-title">Incident Log Ingestion Workspace</span>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => handleLoadSample('hdfs')}
            disabled={disabled}
            data-testid="load-hdfs-sample-btn"
          >
            Load HDFS (Demo)
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => handleLoadSample('bgl')}
            disabled={disabled}
            data-testid="load-bgl-sample-btn"
          >
            Load BGL (Demo)
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onRawTextChange('')}
            disabled={disabled || !rawText}
            data-testid="clear-logs-btn"
          >
            Clear
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 16, marginBottom: 12 }}>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label" htmlFor="dataset-select">
            Target Dataset
          </label>
          <select
            id="dataset-select"
            className="form-select"
            value={dataset}
            onChange={(e) => onDatasetChange(e.target.value as DatasetType)}
            disabled={disabled}
            data-testid="dataset-select"
          >
            <option value="hdfs">HDFS (Hadoop Filesystem)</option>
            <option value="bgl">BGL (BlueGene/L)</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'flex-end', gap: 16 }}>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: 11, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
              Records
            </span>
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 13,
                color: lines.length > MAX_RECORDS ? 'var(--color-rejected-text)' : 'var(--color-text-primary)',
              }}
              data-testid="record-count"
            >
              {lines.length} / {MAX_RECORDS}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: 11, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
              Payload Size
            </span>
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 13,
                color: byteSize > MAX_PAYLOAD_BYTES ? 'var(--color-rejected-text)' : 'var(--color-text-primary)',
              }}
              data-testid="payload-size"
            >
              {formatBytes(byteSize)} / 1.0 MB
            </div>
          </div>
        </div>
      </div>

      <div className="form-group">
        <label className="form-label" htmlFor="logs-textarea">
          <span>Raw Log Sequence (One record per line)</span>
          <span style={{ color: 'var(--color-text-muted)', fontSize: 11 }}>
            Max 2,000 chars/line • Path references forbidden
          </span>
        </label>
        <textarea
          id="logs-textarea"
          className="form-textarea"
          value={rawText}
          onChange={(e) => onRawTextChange(e.target.value)}
          placeholder="Paste system log messages here (one event per line)..."
          disabled={disabled}
          data-testid="logs-textarea"
          rows={8}
        />
      </div>

      {validationErrors.length > 0 && (
        <div
          style={{
            padding: '8px 12px',
            backgroundColor: 'var(--color-rejected-bg)',
            border: '1px solid var(--color-rejected-border)',
            borderRadius: 4,
            fontSize: 12,
            color: 'var(--color-rejected-text)',
            marginBottom: 8,
          }}
          data-testid="validation-errors"
        >
          {validationErrors.map((err, i) => (
            <div key={i}>• {err}</div>
          ))}
        </div>
      )}
    </div>
  );
};
