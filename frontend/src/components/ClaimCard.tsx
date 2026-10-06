import React from 'react';
import { Claim } from '../types';
import { StatusBadge } from './StatusBadge';
import { CitationBadge } from './CitationBadge';

interface ClaimCardProps {
  claim: Claim;
  onCitationClick?: (citationId: string) => void;
  provenanceVerified?: boolean;
}

export const ClaimCard: React.FC<ClaimCardProps> = ({
  claim,
  onCitationClick,
  provenanceVerified = true,
}) => {
  return (
    <div className="claim-card" data-testid={`claim-card-${claim.claim_id.toLowerCase()}`}>
      <div className="claim-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="claim-id">{claim.claim_id}</span>
          <span className="badge badge-neutral" style={{ fontSize: 10 }}>
            {claim.claim_type}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <StatusBadge
            status={claim.supported ? 'VERIFIED' : 'UNSUPPORTED'}
            variant={claim.supported ? 'verified' : 'rejected'}
          />
        </div>
      </div>

      <div className="claim-body">{claim.text}</div>

      <div className="claim-citations">
        <span style={{ fontSize: 11, color: 'var(--color-text-muted)', fontWeight: 600 }}>
          SOURCES:
        </span>
        {claim.citation_ids.length > 0 ? (
          claim.citation_ids.map((citId) => (
            <CitationBadge
              key={citId}
              citationId={citId}
              onClick={onCitationClick}
              isVerified={provenanceVerified}
            />
          ))
        ) : (
          <span style={{ fontSize: 11, color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
            No citation mapped
          </span>
        )}
      </div>
    </div>
  );
};
