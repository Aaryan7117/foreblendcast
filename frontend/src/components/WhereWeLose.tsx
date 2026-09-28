import React from 'react';
import { useResults } from '../hooks/useResults';
import type { WhereWeLoseResult } from '../types/results';
import { useAppStore } from '../store';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';

export const WhereWeLose: React.FC = () => {
  const { leadDay } = useAppStore();
  const { data: whereLose } = useResults<WhereWeLoseResult>('where_we_lose.json');

  if (!whereLose) return null;

  // Filter for current lead day
  const cells = whereLose.cells.filter(c => c.lead_day === leadDay);

  return (
    <div className="bg-surface rounded-card border border-border p-5 shadow-card hover:shadow-cardHover transition-shadow duration-200 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-3 text-tier-orange">
        <AlertTriangle size={18} />
        <h2 className="text-base font-bold text-textMain">Where We Lose (Failure Mode Analysis)</h2>
      </div>

      <p className="text-xs text-textMuted mb-4 leading-relaxed">
        Meteorological conditions and geographic sub-regions where individual models outperform the blend. Scientific transparency is maintained — no model failure is concealed.
      </p>

      {cells.length === 0 ? (
        <div className="text-textMuted text-xs py-8 text-center bg-surfaceHighlight/60 rounded-xl border border-border flex flex-col items-center justify-center">
          <CheckCircle2 size={24} className="text-brand-forest mb-2" />
          <span className="font-semibold text-textMain">No Systematic Blend Losses</span>
          <span className="text-textLight mt-0.5">The multi-model blend captured optimal performance across all evaluated districts for Lead Day {leadDay}.</span>
        </div>
      ) : (
        <div className="space-y-2.5 overflow-y-auto custom-scrollbar flex-1 pr-1">
          {cells.map((cell, idx) => (
            <div
              key={idx}
              className="bg-surfaceHighlight/70 hover:bg-surfaceHighlight p-3 rounded-lg border border-amber-200/50 hover:border-amber-300 transition-all duration-150 hover:-translate-y-0.5 hover:shadow-xs"
            >
              <div className="flex justify-between items-start mb-2">
                <div className="font-bold text-xs text-textMain">{cell.district}</div>
                <div className="text-[9.5px] uppercase font-bold tracking-wider bg-tier-orangeBg text-tier-orange border border-tier-orange/30 px-2 py-0.5 rounded">
                  Loss vs {cell.best_single.toUpperCase()}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs mb-2">
                <div className="bg-white/70 p-1.5 rounded border border-slate-200/60">
                  <div className="text-textMuted text-[9.5px] uppercase font-semibold">Blend RMSE</div>
                  <div className="font-mono text-tier-red font-bold text-sm">{cell.blend_rmse.toFixed(2)} mm</div>
                </div>
                <div className="bg-white/70 p-1.5 rounded border border-slate-200/60">
                  <div className="text-textMuted text-[9.5px] uppercase font-semibold">Best Single ({cell.best_single})</div>
                  <div className="font-mono text-tier-green font-bold text-sm">{cell.best_single_rmse.toFixed(2)} mm</div>
                </div>
              </div>

              <div className="text-[11px] text-textMuted pt-1.5 border-t border-border/80">
                <span className="font-semibold text-textMain">Root Cause:</span> {cell.reason}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
