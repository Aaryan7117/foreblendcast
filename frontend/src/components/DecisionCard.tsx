import React from 'react';
import { useResults } from '../hooks/useResults';
import type { DistrictsResult } from '../types/results';
import { useAppStore } from '../store';
import { ShieldAlert, ShieldCheck } from 'lucide-react';

export const DecisionCard: React.FC = () => {
  const { leadDay } = useAppStore();
  const { data: districtsData } = useResults<DistrictsResult>(`districts_L${leadDay}.json`);

  if (!districtsData) return null;

  const districts = districtsData.districts;
  
  const redCount = districts.filter(d => d.tier === 'red').length;
  const orangeCount = districts.filter(d => d.tier === 'orange').length;
  
  // Find top districts by maximum LOMO increase
  const sortedByLomo = [...districts].sort((a, b) => {
    const maxA = Math.max(...Object.values(a.lomo_rmse_increase_pct));
    const maxB = Math.max(...Object.values(b.lomo_rmse_increase_pct));
    return maxB - maxA;
  }).slice(0, 3);

  return (
    <div className="bg-surfaceHighlight p-4 rounded-xl border border-surfaceHighlight h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4 text-blue-400">
        <ShieldCheck size={20} />
        <h2 className="text-lg font-bold tracking-wide">Decision Support</h2>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-tier-red/10 border border-tier-red/30 p-3 rounded-lg text-center">
          <div className="text-3xl font-black text-tier-red">{redCount}</div>
          <div className="text-xs uppercase text-textMuted tracking-wider mt-1">Red Districts</div>
        </div>
        <div className="bg-tier-orange/10 border border-tier-orange/30 p-3 rounded-lg text-center">
          <div className="text-3xl font-black text-tier-orange">{orangeCount}</div>
          <div className="text-xs uppercase text-textMuted tracking-wider mt-1">Orange Districts</div>
        </div>
      </div>

      <div className="flex-1">
        <h3 className="text-sm font-bold uppercase text-textMuted mb-3 flex items-center gap-2">
          <ShieldAlert size={14} /> Highest Model Sensitivity
        </h3>
        <div className="space-y-3">
          {sortedByLomo.map(d => {
            // Find which model is most critical
            const maxLomoEntry = Object.entries(d.lomo_rmse_increase_pct).reduce((a, b) => a[1] > b[1] ? a : b);
            
            return (
              <div key={d.id} className="bg-surface p-3 rounded-lg border border-surfaceHighlight text-sm">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-bold">{d.name}, {d.state}</span>
                  <span className={`w-3 h-3 rounded-full bg-tier-${d.tier}`}></span>
                </div>
                <div className="text-xs text-textMuted">
                  Without <span className="font-bold text-textMain">{maxLomoEntry[0].toUpperCase()}</span>, 
                  RMSE increases by <span className="text-red-400 font-mono">+{maxLomoEntry[1]}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
