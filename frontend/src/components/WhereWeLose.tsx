import React from 'react';
import { useResults } from '../hooks/useResults';
import type { WhereWeLoseResult } from '../types/results';
import { useAppStore } from '../store';
import { AlertTriangle } from 'lucide-react';

export const WhereWeLose: React.FC = () => {
  const { leadDay } = useAppStore();
  const { data: whereLose } = useResults<WhereWeLoseResult>('where_we_lose.json');

  if (!whereLose) return null;

  // Filter for current lead day
  const cells = whereLose.cells.filter(c => c.lead_day === leadDay);

  return (
    <div className="bg-surfaceHighlight p-4 rounded-xl border border-surfaceHighlight h-full">
      <div className="flex items-center gap-2 mb-4 text-orange-400">
        <AlertTriangle size={20} />
        <h2 className="text-lg font-bold tracking-wide">Where We Lose</h2>
      </div>

      {cells.length === 0 ? (
        <div className="text-textMuted text-sm py-4 text-center">
          No systematic losses detected at Lead Day {leadDay}.
        </div>
      ) : (
        <div className="space-y-3">
          {cells.map((cell, idx) => (
            <div key={idx} className="bg-surface p-3 rounded-lg border border-orange-500/30">
              <div className="flex justify-between items-start mb-2">
                <div className="font-bold">{cell.district}</div>
                <div className="text-xs uppercase bg-orange-500/20 text-orange-400 px-2 py-0.5 rounded">
                  Overrides {cell.best_single.toUpperCase()}
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-2 text-sm mb-2">
                <div>
                  <div className="text-textMuted text-xs uppercase">Blend RMSE</div>
                  <div className="font-mono text-red-400">{cell.blend_rmse.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-textMuted text-xs uppercase">Best Single ({cell.best_single})</div>
                  <div className="font-mono text-green-400">{cell.best_single_rmse.toFixed(2)}</div>
                </div>
              </div>

              <div className="text-xs text-textMuted mt-2 pt-2 border-t border-surfaceHighlight">
                Reason: <span className="text-textMain">{cell.reason}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
