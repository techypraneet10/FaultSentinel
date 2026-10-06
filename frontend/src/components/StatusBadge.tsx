import React from 'react';

interface StatusBadgeProps {
  status: string;
  variant?: 'verified' | 'rejected' | 'neutral' | 'incident' | 'suspicious' | 'insufficient';
  label?: string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  variant,
  label,
  className = '',
}) => {
  const norm = status.toUpperCase();

  let resolvedVariant = variant;
  if (!resolvedVariant) {
    if (norm === 'VERIFIED' || norm === 'SUFFICIENT' || norm === 'SUCCESS' || norm === 'OPERATIONAL') {
      resolvedVariant = 'verified';
    } else if (norm === 'REJECTED' || norm === 'FAILED' || norm === 'UNFAITHFUL' || norm === 'ERROR') {
      resolvedVariant = 'rejected';
    } else if (norm === 'INCIDENT') {
      resolvedVariant = 'incident';
    } else if (norm === 'SUSPICIOUS') {
      resolvedVariant = 'suspicious';
    } else if (norm === 'INSUFFICIENT_EVIDENCE' || norm === 'INSUFFICIENT') {
      resolvedVariant = 'insufficient';
    } else {
      resolvedVariant = 'neutral';
    }
  }

  const badgeClass = `badge badge-${resolvedVariant} ${className}`;

  return (
    <span className={badgeClass} data-testid={`badge-${status.toLowerCase()}`}>
      {label || status}
    </span>
  );
};
