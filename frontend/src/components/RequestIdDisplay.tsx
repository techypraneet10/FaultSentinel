import React, { useState } from 'react';

interface RequestIdDisplayProps {
  requestId: string;
}

export const RequestIdDisplay: React.FC<RequestIdDisplayProps> = ({ requestId }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(requestId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <div className="request-id-container" data-testid="request-id-display">
      <span>REQ: {requestId}</span>
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        style={{ padding: '1px 6px', fontSize: 10 }}
        onClick={handleCopy}
        title="Copy Request ID"
        data-testid="copy-request-id-btn"
        aria-label="Copy Request ID"
      >
        {copied ? 'Copied!' : 'Copy'}
      </button>
    </div>
  );
};
