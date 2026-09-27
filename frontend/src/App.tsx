
import { useAppStore } from './store';
import { useResults } from './hooks/useResults';
import type { LadderResult } from './types/results';
import { Watermark } from './components/Watermark';
import { DistrictMap } from './components/DistrictMap';
import { LadderTable } from './components/LadderTable';
import { Spaghetti } from './components/Spaghetti';
import { WhereWeLose } from './components/WhereWeLose';
import { DecisionCard } from './components/DecisionCard';

function App() {
  const { leadDay, setLeadDay } = useAppStore();
  const { data: ladder, loading } = useResults<LadderResult>('ladder.json');

  if (loading || !ladder) {
    return <div className="h-screen w-screen flex items-center justify-center text-white bg-background">Loading SIH26081...</div>;
  }

  return (
    <div className="h-screen w-screen flex flex-col bg-background text-textMain overflow-hidden">
      <Watermark isFixture={ladder.meta.fixture} />
      
      {/* Header */}
      <header className="h-16 flex items-center px-6 bg-surface border-b border-surfaceHighlight justify-between flex-shrink-0 z-10">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-black tracking-widest uppercase">SIH26081</h1>
          <span className="text-sm font-semibold text-textMuted uppercase tracking-widest px-3 py-1 bg-surfaceHighlight rounded-full">
            {ladder.meta.status}
          </span>
        </div>
        
        {/* Controls */}
        <div className="flex items-center gap-4">
          <span className="text-sm font-bold text-textMuted">LEAD DAY</span>
          <div className="flex bg-surfaceHighlight p-1 rounded-lg">
            {[1, 3, 5, 7, 10].map(day => (
              <button
                key={day}
                onClick={() => setLeadDay(day)}
                className={`px-4 py-1 text-sm font-bold rounded-md transition-colors ${
                  leadDay === day ? 'bg-blue-600 text-white shadow' : 'text-textMuted hover:text-textMain'
                }`}
              >
                L{day}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left Panel: Map */}
        <div className="w-1/2 h-full p-4 border-r border-surfaceHighlight flex flex-col gap-4">
          <DistrictMap />
        </div>

        {/* Right Panel: Data & Analytics */}
        <div className="w-1/2 h-full overflow-y-auto p-4 flex flex-col gap-4">
          <LadderTable />
          <Spaghetti />
          <div className="flex gap-4">
            <div className="flex-1">
              <WhereWeLose />
            </div>
            <div className="flex-1">
              <DecisionCard />
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="h-8 flex items-center px-4 bg-surface border-t border-surfaceHighlight text-xs text-textMuted justify-between flex-shrink-0">
        <div>
          Cycle: <span className="text-textMain">{ladder.meta.cycle}</span>
        </div>
        <div className="flex gap-4">
          <span>Generated: {ladder.meta.generated_utc}</span>
          <span>Commit: {ladder.meta.git_commit}</span>
          <span>Strategy: {ladder.meta.strategy}</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
