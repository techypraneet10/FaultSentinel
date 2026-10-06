import React from 'react';
import { Header } from '../components/Header';
import { ConnectionState } from '../types';

interface MainLayoutProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  connectionState: ConnectionState;
  onRefreshHealth: () => void;
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({
  activeTab,
  onTabChange,
  connectionState,
  onRefreshHealth,
  children,
}) => {
  return (
    <div className="app-container" data-testid="app-layout">
      <Header
        activeTab={activeTab}
        onTabChange={onTabChange}
        connectionState={connectionState}
        onRefreshHealth={onRefreshHealth}
      />
      <main className="main-content">{children}</main>
      <footer
        style={{
          padding: '16px 24px',
          borderTop: '1px solid var(--color-border-subtle)',
          backgroundColor: 'var(--color-bg-surface)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: 12,
          color: 'var(--color-text-muted)',
        }}
      >
        <div>SentinelLog Phase 11 — Operator Dashboard & Human Review Interface</div>
        <div>Calibrated Selective Prediction for LLM-Assisted Incident Triage</div>
      </footer>
    </div>
  );
};
