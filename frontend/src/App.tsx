import React, { useState } from 'react';
import { MainLayout } from './layouts/MainLayout';
import { AnalyzePage } from './pages/AnalyzePage';
import { ReviewPage } from './pages/ReviewPage';
import { ApiStatusPage } from './pages/ApiStatusPage';
import { OverviewPage } from './pages/OverviewPage';
import { useHealth } from './hooks/useHealth';
import { AnalyzeResponse } from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('analyze');
  const [currentAnalysis, setCurrentAnalysis] = useState<AnalyzeResponse | null>(null);
  const { connectionState, checkHealth } = useHealth();

  return (
    <MainLayout
      activeTab={activeTab}
      onTabChange={setActiveTab}
      connectionState={connectionState}
      onRefreshHealth={checkHealth}
    >
      {activeTab === 'analyze' && (
        <AnalyzePage onAnalysisComplete={setCurrentAnalysis} />
      )}
      {activeTab === 'review' && (
        <ReviewPage
          currentAnalysis={currentAnalysis}
          onNavigateAnalyze={() => setActiveTab('analyze')}
        />
      )}
      {activeTab === 'status' && <ApiStatusPage />}
      {activeTab === 'overview' && <OverviewPage />}
    </MainLayout>
  );
};

export default App;
