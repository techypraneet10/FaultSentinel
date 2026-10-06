import React from 'react';

interface CitationBadgeProps {
  citationId: string;
  onClick?: (citationId: string) => void;
  isVerified?: boolean;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({
  citationId,
  onClick,
  isVerified = true,
}) => {
  return (
    <button
      type="button"
      className="citation-btn"
      onClick={() => onClick && onClick(citationId)}
      title={`Inspect evidence for ${citationId} (${isVerified ? 'Verified' : 'Unverified'})`}
      data-testid={`citation-btn-${citationId.toLowerCase()}`}
      style={{
        borderColor: isVerified ? 'var(--color-border-default)' : 'var(--color-rejected-border)',
        color: isVerified ? 'var(--color-text-code)' : 'var(--color-rejected-text)',
      }}
    >
      [{citationId}]
    </button>
  );
};
