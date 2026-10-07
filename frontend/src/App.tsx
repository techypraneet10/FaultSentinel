import React, { useState } from 'react';
import { MainLayout } from './layouts/MainLayout';
import { AnalyzePage } from './pages/AnalyzePage';
import { ReviewPage } from './pages/ReviewPage';
import { ApiStatusPage } from './pages/ApiStatusPage';
import { OverviewPage } from './pages/OverviewPage';
import { IncidentsPage } from './pages/IncidentsPage';
import { AnomalyExplorerPage } from './pages/AnomalyExplorerPage';
import { EvaluationLabPage } from './pages/EvaluationLabPage';
import { CostIntelligencePage } from './pages/CostIntelligencePage';
import { ModelObservatoryPage } from './pages/ModelObservatoryPage';
import { ArchitecturePage } from './pages/ArchitecturePage';
import { useHealth } from './hooks/useHealth';
import { AnalyzeResponse, DatasetType } from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('analyze');
  const [currentAnalysis, setCurrentAnalysis] = useState<AnalyzeResponse | null>(null);
  const [dataset, setDataset] = useState<DatasetType>('hdfs');
  const [isDemo, setIsDemo] = useState<boolean>(true);
  const { connectionState, checkHealth } = useHealth();

  return (
    <MainLayout
      activeTab={activeTab}
      onTabChange={setActiveTab}
      connectionState={connectionState}
      onRefreshHealth={checkHealth}
      dataset={dataset}
      onDatasetChange={setDataset}
      isDemo={isDemo}
      onToggleDemo={setIsDemo}
    >
      {activeTab === 'analyze' && (
        <AnalyzePage onAnalysisComplete={setCurrentAnalysis} />
      )}
      {activeTab === 'overview' && (
        <OverviewPage onNavigateTab={setActiveTab} />
      )}
      {activeTab === 'incidents' && <IncidentsPage />}
      {activeTab === 'anomaly-explorer' && <AnomalyExplorerPage />}
      {activeTab === 'review' && (
        <ReviewPage
          currentAnalysis={currentAnalysis}
          onNavigateAnalyze={() => setActiveTab('analyze')}
        />
      )}
      {activeTab === 'evaluation' && <EvaluationLabPage />}
      {activeTab === 'cost' && <CostIntelligencePage />}
      {activeTab === 'observatory' && <ModelObservatoryPage />}
      {activeTab === 'architecture' && <ArchitecturePage />}
      {activeTab === 'status' && <ApiStatusPage />}
    </MainLayout>
  );
};

export default App;
