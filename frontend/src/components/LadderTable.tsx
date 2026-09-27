import React from 'react';
import { useResults } from '../hooks/useResults';
import type { LadderResult } from '../types/results';
import { useAppStore } from '../store';
import clsx from 'clsx';

export const LadderTable: React.FC = () => {
  const { data: ladder } = useResults<LadderResult>('ladder.json');
  const { leadDay } = useAppStore();

  if (!ladder) return null;

  // The metrics for the current lead day. Lead day keys are formatted like "L3"
  const leadKey = `L${leadDay}`;

  // Sort rows to enforce the hierarchy: Ceiling -> Blend -> Single -> Floor
  const hierarchy = {
    ceiling: 1,
    blend: 2,
    single: 3,
    floor: 4
  };

  const sortedRows = [...ladder.rows].sort((a, b) => {
    if (hierarchy[a.rung] !== hierarchy[b.rung]) {
      return hierarchy[a.rung] - hierarchy[b.rung];
    }
    // If both are singles, sort by RMSE ascending
    const rmseA = a.metrics[leadKey]?.rmse ?? 999;
    const rmseB = b.metrics[leadKey]?.rmse ?? 999;
    return rmseA - rmseB;
  });

  return (
    <div className="bg-surfaceHighlight p-4 rounded-xl border border-surfaceHighlight">
      <div className="flex justify-between items-end mb-4">
        <div>
          <h2 className="text-xl font-bold tracking-wide">Performance Ladder</h2>
          <p className="text-sm text-textMuted uppercase mt-1">
            Validating Lead Day {leadDay} • {ladder.headline.pct_of_achievable_gain[leadKey] ?? 0}% of achievable gain captured
          </p>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="text-xs uppercase tracking-wider text-textMuted border-b border-surface/50">
              <th className="pb-3 pl-3 font-semibold">Model / Strategy</th>
              <th className="pb-3 font-semibold">RMSE</th>
              <th className="pb-3 font-semibold">MAE</th>
              <th className="pb-3 font-semibold">FSS (50km)</th>
              <th className="pb-3 font-semibold">REV (0.1)</th>
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row, i) => {
              const m = row.metrics[leadKey];
              if (!m) return null;
              
              const isBlend = row.rung === 'blend';
              const isCeiling = row.rung === 'ceiling';
              const isFloor = row.rung === 'floor';
              
              return (
                <tr 
                  key={row.strategy + i}
                  className={clsx(
                    "border-b border-surface/30 transition-colors hover:bg-surface/50",
                    isBlend && "bg-blue-900/20 border-l-4 border-l-blue-500",
                    isCeiling && "opacity-70",
                    isFloor && "opacity-50"
                  )}
                >
                  <td className="py-3 pl-3">
                    <div className="flex items-center gap-2">
                      <span className={clsx(
                        "font-semibold",
                        isBlend && "text-blue-400 font-bold",
                        isCeiling && "text-purple-400",
                        isFloor && "text-gray-500"
                      )}>
                        {row.strategy.toUpperCase()}
                      </span>
                      <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-surface text-textMuted">
                        {row.rung}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 font-mono">{m.rmse.toFixed(2)}</td>
                  <td className="py-3 font-mono">{m.mae.toFixed(2)}</td>
                  <td className="py-3 font-mono">{m.fss50.toFixed(2)}</td>
                  <td className="py-3 font-mono">{m.rev_cl0p1.toFixed(2)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
