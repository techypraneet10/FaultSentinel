import React from 'react';
import {
  LayoutDashboard,
  Zap,
  AlertOctagon,
  LineChart,
  FileSearch,
  FlaskConical,
  Scale,
  Cpu,
  Network,
  Sliders,
  Shield,
  Compass,
  PlayCircle,
  Flame,
  Activity,
  GitFork,
  FileKey,
} from 'lucide-react';
import { ConnectionState } from '../types';

export interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  badge?: string;
  testId?: string;
}

interface SidebarProps {
  activeTab: string;
  onTabChange: (tabId: string) => void;
  connectionState: ConnectionState;
  dataset: string;
  isDemoMode?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onTabChange,
  connectionState,
  dataset,
  isDemoMode = true,
}) => {
  const navItems: NavItem[] = [
    {
      id: 'walkthrough',
      label: 'Recruiter Tour',
      icon: <Compass size={15} />,
      testId: 'nav-walkthrough',
      badge: 'Start Here',
    },
    {
      id: 'overview',
      label: 'Overview',
      icon: <LayoutDashboard size={15} />,
      testId: 'nav-overview',
    },
    {
      id: 'analyze',
      label: 'Live Triage',
      icon: <Zap size={15} />,
      testId: 'nav-analyze',
      badge: 'Interactive',
    },
    {
      id: 'replay',
      label: 'Incident Replay',
      icon: <PlayCircle size={15} />,
      testId: 'nav-replay',
      badge: 'v1.1',
    },
    {
      id: 'fault-lab',
      label: 'Fault Injection',
      icon: <Flame size={15} />,
      testId: 'nav-fault-lab',
      badge: 'Chaos',
    },
    {
      id: 'calibration-health',
      label: 'Calibration Health',
      icon: <Activity size={15} />,
      testId: 'nav-calibration-health',
      badge: 'Drift',
    },
    {
      id: 'evidence-graph',
      label: 'Evidence Graph',
      icon: <GitFork size={15} />,
      testId: 'nav-evidence-graph',
      badge: 'DAG',
    },
    {
      id: 'passport',
      label: 'Decision Passport',
      icon: <FileKey size={15} />,
      testId: 'nav-passport',
      badge: 'Audit',
    },
    {
      id: 'incidents',
      label: 'Incidents',
      icon: <AlertOctagon size={15} />,
      testId: 'nav-incidents',
    },
    {
      id: 'anomaly-explorer',
      label: 'Anomaly Explorer',
      icon: <LineChart size={15} />,
      testId: 'nav-explorer',
    },
    {
      id: 'review',
      label: 'Explanations',
      icon: <FileSearch size={15} />,
      testId: 'nav-review',
    },
    {
      id: 'evaluation',
      label: 'Evaluation Lab',
      icon: <FlaskConical size={15} />,
      testId: 'nav-evaluation',
      badge: 'Phase 12',
    },
    {
      id: 'cost',
      label: 'Cost Intelligence',
      icon: <Scale size={15} />,
      testId: 'nav-cost',
    },
    {
      id: 'observatory',
      label: 'Model Observatory',
      icon: <Cpu size={15} />,
      testId: 'nav-observatory',
    },
    {
      id: 'architecture',
      label: 'Architecture',
      icon: <Network size={15} />,
      testId: 'nav-architecture',
    },
    {
      id: 'status',
      label: 'Configuration',
      icon: <Sliders size={15} />,
      testId: 'nav-status',
    },
  ];

  return (
    <aside className="app-sidebar" data-testid="app-sidebar">
      {/* Brand Header */}
      <div className="sidebar-brand-container">
        <div className="sidebar-brand-header">
          <div className="sidebar-brand-icon">
            <Shield size={16} strokeWidth={2.5} color="#ffffff" />
          </div>
          <div>
            <div className="sidebar-brand-title">FAULTSENTINEL</div>
            <div className="sidebar-brand-desc">AI Incident Intelligence</div>
          </div>
        </div>
      </div>

      {/* Nav List */}
      <nav className="sidebar-nav" aria-label="Incident Command Center Navigation">
        <div className="sidebar-nav-section-title">COMMAND & INVESTIGATION</div>
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
              onClick={() => onTabChange(item.id)}
              data-testid={item.testId}
              aria-current={isActive ? 'page' : undefined}
            >
              <span className="sidebar-nav-icon">{item.icon}</span>
              <span className="sidebar-nav-label">{item.label}</span>
              {item.badge && (
                <span className="sidebar-nav-badge">{item.badge}</span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Footer Status */}
      <div className="sidebar-footer">
        <div className="sidebar-status-pill">
          <div
            className={`status-indicator-dot ${
              connectionState === 'connected' ? 'connected' : connectionState === 'offline' ? 'offline' : 'degraded'
            }`}
          />
          <span className="sidebar-status-text">
            {connectionState === 'connected' ? 'System Operational' : connectionState === 'checking' ? 'Connecting...' : 'API Offline'}
          </span>
        </div>

        <div className="sidebar-env-row">
          <span className="sidebar-env-tag">{dataset.toUpperCase()}</span>
          <span className="sidebar-env-mode">{isDemoMode ? 'DEMO MODE' : 'PROD'}</span>
          <span className="sidebar-version-tag">v1.0.0</span>
        </div>
      </div>
    </aside>
  );
};
