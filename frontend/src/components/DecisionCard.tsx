import React from 'react';
import { useResults } from '../hooks/useResults';
import type { DistrictsResult } from '../types/results';
import { useAppStore } from '../store';
import { ShieldAlert, ShieldCheck } from 'lucide-react';

export const DecisionCard: React.FC = () => {
  const { leadDay, setSelectedDistrict, setActivePage } = useAppStore();
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
    <div className="bg-surface rounded-card border border-border p-5 shadow-card hover:shadow-cardHover transition-shadow duration-200 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-3 text-brand-forest">
        <ShieldCheck size={18} />
        <h2 className="text-base font-bold text-textMain">Disaster Early Warning Decision Support</h2>
      </div>

      <p className="text-xs text-textMuted mb-4 leading-relaxed">
        Operational decision metrics for National Disaster Management Authority (NDMA) & State Disaster Management Authorities (SDMAs).
      </p>

      <div className="grid grid-cols-2 gap-2.5 mb-4">
        <div className="bg-tier-redBg border border-tier-red/30 p-3 rounded-lg text-center transition-all duration-150 hover:-translate-y-0.5 hover:shadow-xs">
          <div className="text-2xl font-extrabold text-tier-red">{redCount}</div>
          <div className="text-[10px] uppercase text-textMuted tracking-wider mt-0.5 font-bold">Red Alert Districts</div>
        </div>
        <div className="bg-tier-orangeBg border border-tier-orange/30 p-3 rounded-lg text-center transition-all duration-150 hover:-translate-y-0.5 hover:shadow-xs">
          <div className="text-2xl font-extrabold text-tier-orange">{orangeCount}</div>
          <div className="text-[10px] uppercase text-textMuted tracking-wider mt-0.5 font-bold">Orange Alert Districts</div>
        </div>
      </div>

      <div className="flex-1">
        <h3 className="text-xs font-bold uppercase tracking-wider text-textMuted mb-2.5 flex items-center gap-1.5">
          <ShieldAlert size={14} className="text-brand-forest" />
          Leave-One-Model-Out (LOMO) Sensitivity
        </h3>
        <div className="space-y-2">
          {sortedByLomo.map(d => {
            const maxLomoEntry = Object.entries(d.lomo_rmse_increase_pct).reduce((a, b) => a[1] > b[1] ? a : b);

            return (
              <div 
                key={d.id} 
                onClick={() => {
                  setSelectedDistrict(d.id);
                  setActivePage('live');
                }}
                className="bg-surfaceHighlight/70 hover:bg-surfaceHighlight p-2.5 rounded-lg border border-border hover:border-slate-300 text-xs transition-all duration-150 hover:-translate-y-0.5 hover:shadow-xs cursor-pointer select-none"
                title="Click to view district forecast"
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="font-bold text-textMain">{d.name}, {d.state}</span>
                  <span className={`w-2.5 h-2.5 rounded-full bg-tier-${d.tier} shadow-xs`} />
                </div>
                <div className="text-[11px] text-textMuted">
                  Critical reliance on <span className="font-bold text-textMain">{maxLomoEntry[0].toUpperCase()}</span>: Dropout degrades RMSE by{' '}
                  <span className="text-tier-red font-mono font-bold">+{maxLomoEntry[1]}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
