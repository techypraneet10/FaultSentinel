import React from 'react';
import { ConnectionState } from '../types';
import { HealthIndicator } from './HealthIndicator';

interface HeaderProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  connectionState: ConnectionState;
  onRefreshHealth: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onTabChange,
  connectionState,
  onRefreshHealth,
}) => {
  return (
    <header className="app-header" data-testid="app-header">
      <div className="brand-section">
        <div className="brand-logo">
          <span style={{ fontSize: 18 }}>🛡️</span>
          <span>SentinelLog</span>
          <span className="brand-badge">SRE Console</span>
        </div>
        <span style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>
          Calibrated Incident Intelligence
        </span>
      </div>

      <nav className="app-nav" aria-label="Main Navigation">
        <button
          type="button"
          className={`nav-link ${activeTab === 'analyze' ? 'active' : ''}`}
          onClick={() => onTabChange('analyze')}
          data-testid="nav-analyze"
        >
          Incident Analysis
        </button>
        <button
          type="button"
          className={`nav-link ${activeTab === 'review' ? 'active' : ''}`}
          onClick={() => onTabChange('review')}
          data-testid="nav-review"
        >
          Evidence Review
        </button>
        <button
          type="button"
          className={`nav-link ${activeTab === 'status' ? 'active' : ''}`}
          onClick={() => onTabChange('status')}
          data-testid="nav-status"
        >
          API Status
        </button>
        <button
          type="button"
          className={`nav-link ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => onTabChange('overview')}
          data-testid="nav-overview"
        >
          Architecture
        </button>
      </nav>

      <div className="header-meta">
        <HealthIndicator connectionState={connectionState} onRefresh={onRefreshHealth} />
      </div>
    </header>
  );
};
