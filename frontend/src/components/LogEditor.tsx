import React, { useMemo, useState } from 'react';
import { DatasetType } from '../types';
import { formatBytes } from '../utils/formatters';
import { DEMO_HDFS_LOGS, DEMO_BGL_LOGS } from '../utils/sampleData';
import { Search, Copy, Check, Eye, Edit3 } from 'lucide-react';

interface LogEditorProps {
  dataset: DatasetType;
  onDatasetChange: (dataset: DatasetType) => void;
  rawText: string;
  onRawTextChange: (text: string) => void;
  disabled?: boolean;
  highlightedLineRange?: { start?: number | null; end?: number | null } | null;
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
  highlightedLineRange,
}) => {
  const [viewMode, setViewMode] = useState<'editor' | 'viewer'>('editor');
  const [searchQuery, setSearchQuery] = useState('');
  const [copied, setCopied] = useState(false);

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

  const handleCopy = () => {
    navigator.clipboard.writeText(rawText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getSeverityStyle = (line: string) => {
    if (line.includes('FATAL') || line.includes('ERROR') || line.includes('Exception')) {
      return { color: 'var(--color-critical)', tag: 'ERROR' };
    }
    if (line.includes('WARN')) {
      return { color: 'var(--color-warning)', tag: 'WARN' };
    }
    if (line.includes('INFO')) {
      return { color: 'var(--color-text-primary)', tag: 'INFO' };
    }
    return { color: 'var(--color-text-secondary)', tag: 'DEBUG' };
  };

  return (
    <div className="panel" data-testid="log-editor-panel" style={{ backgroundColor: 'var(--color-bg-surface)' }}>
      <div className="panel-header" style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="panel-title">Incident Log Ingestion Workspace</span>
          <span
            className="badge badge-neutral"
            style={{ fontSize: 10, fontFamily: 'var(--font-mono)' }}
          >
            BOUNDED INGESTION
          </span>
        </div>

        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => handleLoadSample('hdfs')}
            disabled={disabled}
            data-testid="load-hdfs-sample-btn"
          >
            HDFS (Demo)
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => handleLoadSample('bgl')}
            disabled={disabled}
            data-testid="load-bgl-sample-btn"
          >
            BGL (Demo)
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
          {rawText && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleCopy}
              title="Copy raw logs"
            >
              {copied ? <Check size={12} color="var(--color-success)" /> : <Copy size={12} />}
            </button>
          )}
          {lines.length > 0 && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setViewMode(viewMode === 'editor' ? 'viewer' : 'editor')}
              title={viewMode === 'editor' ? 'Switch to Terminal Viewer' : 'Switch to Text Editor'}
            >
              {viewMode === 'editor' ? <Eye size={12} /> : <Edit3 size={12} />}
              <span>{viewMode === 'editor' ? 'Line View' : 'Raw Edit'}</span>
            </button>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 16, marginBottom: 12 }}>
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

        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'flex-end', gap: 20 }}>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: 11, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
              Records
            </span>
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 13,
                fontWeight: 600,
                color: lines.length > MAX_RECORDS ? 'var(--color-rejected-text)' : 'var(--color-text-pure)',
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
                fontWeight: 600,
                color: byteSize > MAX_PAYLOAD_BYTES ? 'var(--color-rejected-text)' : 'var(--color-text-pure)',
              }}
              data-testid="payload-size"
            >
              {formatBytes(byteSize)} / 1.0 MB
            </div>
          </div>
        </div>
      </div>

      {viewMode === 'editor' ? (
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
      ) : (
        <div style={{ marginBottom: 12 }}>
          {/* Viewer search bar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                backgroundColor: 'var(--color-bg-base)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 4,
                padding: '4px 8px',
                width: '100%',
              }}
            >
              <Search size={13} color="var(--color-text-muted)" />
              <input
                type="text"
                placeholder="Search log records..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
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
          </div>

          {/* Line-numbered terminal viewer */}
          <div
            style={{
              backgroundColor: 'var(--color-bg-base)',
              border: '1px solid var(--color-border-default)',
              borderRadius: 4,
              maxHeight: '260px',
              overflowY: 'auto',
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
            }}
          >
            {lines.map((line, idx) => {
              const lineNum = idx + 1;
              const matchesSearch = !searchQuery || line.toLowerCase().includes(searchQuery.toLowerCase());
              if (!matchesSearch) return null;

              const isHighlighted =
                highlightedLineRange &&
                highlightedLineRange.start !== null &&
                highlightedLineRange.start !== undefined &&
                lineNum >= (highlightedLineRange.start || 0) &&
                lineNum <= (highlightedLineRange.end || highlightedLineRange.start || 0);

              const { color } = getSeverityStyle(line);

              return (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'baseline',
                    padding: '2px 8px',
                    backgroundColor: isHighlighted ? 'rgba(245, 158, 11, 0.15)' : 'transparent',
                    borderLeft: isHighlighted ? '3px solid var(--color-warning)' : '3px solid transparent',
                    borderBottom: '1px solid var(--color-border-subtle)',
                    transition: 'background-color 0.15s ease',
                  }}
                >
                  <span
                    style={{
                      width: '32px',
                      color: isHighlighted ? 'var(--color-warning)' : 'var(--color-text-muted)',
                      userSelect: 'none',
                      fontWeight: isHighlighted ? 700 : 400,
                    }}
                  >
                    {String(lineNum).padStart(2, '0')}
                  </span>
                  <span style={{ color, wordBreak: 'break-all' }}>{line}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

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
