import { useState, useCallback } from 'react';
import { useAppStore } from './store';
import { useResults } from './hooks/useResults';
import './App.css';
import type { LadderResult } from './types/results';

import { LoadingScreen } from './components/LoadingScreen';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { DistrictMap } from './components/DistrictMap';
import { RiskSummary } from './components/RiskSummary';
import { DistrictInfo } from './components/DistrictInfo';
import { ForecastChart } from './components/ForecastChart';
import { ModelComparison } from './components/ModelComparison';
import { KeyInsights } from './components/KeyInsights';
import { LadderTable } from './components/LadderTable';
import { Spaghetti } from './components/Spaghetti';
import { WhereWeLose } from './components/WhereWeLose';
import { DecisionCard } from './components/DecisionCard';
import { AboutPage } from './components/AboutPage';

function App() {
  const { activePage } = useAppStore();
  const { data: ladder, loading } = useResults<LadderResult>('ladder.json');
  const [showLoading, setShowLoading] = useState(true);

  const handleLoadingComplete = useCallback(() => {
    setShowLoading(false);
  }, []);

  if (loading || !ladder) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="w-9 h-9 border-3 border-brand-forest border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm font-medium text-textMuted">Loading ForeBlendCast operational data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex flex-col bg-background text-textMain overflow-hidden font-sans">
      {/* 4-Second Staged Atmospheric Loading Screen */}
      {showLoading && <LoadingScreen onComplete={handleLoadingComplete} />}

      {/* Government Header with Official MoES & NCMRWF Logos */}
      <Header meta={ladder.meta} />

      {/* Main Operational Dashboard Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar (Active on primary operational forecasting views) */}
        {(activePage === 'live' || activePage === 'risk' || activePage === 'comparison') && (
          <Sidebar />
        )}

        {/* Tab-driven Page Routing */}
        <main className="flex-1 flex overflow-hidden">
          {activePage === 'live' && <LiveForecastPage />}
          {activePage === 'risk' && <RiskDashboardPage />}
          {activePage === 'comparison' && <ModelComparisonPage />}
          {activePage === 'evaluation' && <EvaluationPage />}
          {activePage === 'wherewellose' && <WhereWeLosePage />}
          {activePage === 'about' && <AboutPage />}
        </main>
      </div>
    </div>
  );
}

/* ─── Page: Live Forecast (Primary Operational View) ─ */
function LiveForecastPage() {
  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Center: Map + Bottom Multi-Model Comparison Strip */}
      <div className="flex-1 flex flex-col h-full p-3 min-w-0 gap-3 overflow-hidden">
        <div className="flex-1 min-h-[340px] relative overflow-hidden">
          <DistrictMap />
        </div>
        <div className="flex-shrink-0">
          <ModelComparison />
        </div>
      </div>

      {/* Right Panel: Risk Summary, District Details, Plume Chart, Key Insights */}
      <div className="w-[390px] xl:w-[430px] flex-shrink-0 h-full overflow-y-auto custom-scrollbar border-l border-border bg-background p-3 space-y-3">
        <RiskSummary />
        <DistrictInfo />
        <ForecastChart />
        <KeyInsights />
      </div>
    </div>
  );
}

/* ─── Page: Risk Dashboard ─────────────────────────── */
function RiskDashboardPage() {
  return (
    <div className="flex-1 flex overflow-hidden">
      <div className="flex-1 h-full p-3 min-w-0">
        <DistrictMap />
      </div>
      <div className="w-[410px] xl:w-[450px] flex-shrink-0 h-full overflow-y-auto custom-scrollbar border-l border-border bg-background p-3 space-y-3">
        <RiskSummary />
        <DistrictInfo />
        <DecisionCard />
        <KeyInsights />
      </div>
    </div>
  );
}

/* ─── Page: Model Comparison ───────────────────────── */
function ModelComparisonPage() {
  return (
    <div className="flex-1 h-full overflow-y-auto custom-scrollbar p-4 space-y-4">
      <ModelComparison />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ForecastChart />
        <KeyInsights />
      </div>
    </div>
  );
}

/* ─── Page: Evaluation ─────────────────────────────── */
function EvaluationPage() {
  return (
    <div className="flex-1 h-full overflow-y-auto custom-scrollbar p-4 space-y-4">
      <LadderTable />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Spaghetti />
        <DecisionCard />
      </div>
    </div>
  );
}

/* ─── Page: Where We Lose (Scientific Transparency) ── */
function WhereWeLosePage() {
  return (
    <div className="flex-1 h-full overflow-y-auto custom-scrollbar p-4">
      <div className="max-w-5xl mx-auto space-y-4">
        <WhereWeLose />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Spaghetti />
          <DecisionCard />
        </div>
      </div>
    </div>
  );
}

export default App;
