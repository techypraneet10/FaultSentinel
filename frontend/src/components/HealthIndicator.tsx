import React from 'react';
import { ConnectionState } from '../types';

interface HealthIndicatorProps {
  connectionState: ConnectionState;
  onRefresh?: () => void;
}

export const HealthIndicator: React.FC<HealthIndicatorProps> = ({
  connectionState,
  onRefresh,
}) => {
  let label = 'Offline';
  let dotColor = '#f85149';

  if (connectionState === 'connected') {
    label = 'API Connected';
    dotColor = '#3fb950';
  } else if (connectionState === 'degraded') {
    label = 'Degraded';
    dotColor = '#e3b341';
  } else if (connectionState === 'checking') {
    label = 'Checking...';
    dotColor = '#8b949e';
  }

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '3px 8px',
        backgroundColor: 'var(--color-bg-surface-raised)',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--color-border-subtle)',
        fontSize: 12,
        fontFamily: 'var(--font-mono)',
        cursor: onRefresh ? 'pointer' : 'default',
      }}
      onClick={onRefresh}
      title="Click to recheck API health"
      data-testid="health-indicator"
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          backgroundColor: dotColor,
          display: 'inline-block',
        }}
        data-testid={`health-dot-${connectionState}`}
      />
      <span style={{ color: 'var(--color-text-secondary)' }}>{label}</span>
    </div>
  );
};
