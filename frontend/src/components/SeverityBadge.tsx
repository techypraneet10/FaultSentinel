import React from 'react';
import { SeverityType } from '../types';

interface SeverityBadgeProps {
  severity: SeverityType | string;
  className?: string;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity, className = '' }) => {
  const norm = (severity || 'UNKNOWN').toUpperCase();

  let variantClass = 'badge-neutral';
  if (norm === 'HIGH') {
    variantClass = 'badge-incident';
  } else if (norm === 'MEDIUM') {
    variantClass = 'badge-suspicious';
  } else if (norm === 'LOW') {
    variantClass = 'badge-insufficient';
  }

  return (
    <span className={`badge ${variantClass} ${className}`} data-testid="severity-badge">
      Severity: {norm}
    </span>
  );
};
