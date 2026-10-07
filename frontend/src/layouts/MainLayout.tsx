import React from 'react';
import { Sidebar } from '../components/Sidebar';
import { Header } from '../components/Header';
import { ConnectionState } from '../types';

interface MainLayoutProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  connectionState: ConnectionState;
  onRefreshHealth: () => void;
  dataset?: 'hdfs' | 'bgl';
  onDatasetChange?: (ds: 'hdfs' | 'bgl') => void;
  isDemo?: boolean;
  onToggleDemo?: (isDemo: boolean) => void;
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({
  activeTab,
  onTabChange,
  connectionState,
  onRefreshHealth,
  dataset = 'hdfs',
  onDatasetChange,
  isDemo = true,
  onToggleDemo,
  children,
}) => {
  return (
    <div className="app-container" data-testid="app-layout">
      {/* Desktop Sidebar (220-240px) */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={onTabChange}
        connectionState={connectionState}
        dataset={dataset}
        isDemoMode={isDemo}
      />

      {/* Main Workspace Area */}
      <div className="app-workspace">
        <Header
          activeTab={activeTab}
          connectionState={connectionState}
          onRefreshHealth={onRefreshHealth}
          dataset={dataset}
          onDatasetChange={onDatasetChange}
          isDemo={isDemo}
          onToggleDemo={onToggleDemo}
        />

        <main className="main-content">{children}</main>

        <footer className="app-footer">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontWeight: 600, color: 'var(--color-text-pure)' }}>FaultSentinel</span>
            <span>—</span>
            <span>AI-Assisted Incident Intelligence</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <span>Calibrated AI Incident Triage & Evidence-Grounded Root Cause Analysis</span>
            <span className="badge badge-neutral" style={{ fontSize: '10px' }}>RULE 1 PROTECTED</span>
          </div>
        </footer>
      </div>
    </div>
  );
};
