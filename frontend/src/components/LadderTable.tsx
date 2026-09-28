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
    <div className="bg-surface rounded-card border border-border p-5 shadow-card">
      <div className="flex justify-between items-end mb-4">
        <div>
          <h2 className="text-lg font-bold text-textMain">Performance Ladder</h2>
          <p className="text-xs text-textMuted mt-1">
            Lead Day {leadDay} • {ladder.headline.pct_of_achievable_gain[leadKey] ?? 0}% of achievable gain captured
          </p>
        </div>
        <div className="text-xs text-textMuted bg-surfaceHighlight border border-border px-2.5 py-1 rounded-md">
          Strategy: <span className="font-semibold text-textMain">{ladder.meta.strategy}</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="text-[11px] uppercase tracking-wider text-textMuted border-b border-border">
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
                    "border-b border-borderLight transition-colors hover:bg-surfaceHighlight/50",
                    isBlend && "bg-brand-leafPale/50 border-l-3 border-l-brand-forest",
                    isCeiling && "opacity-60",
                    isFloor && "opacity-45"
                  )}
                >
                  <td className="py-3 pl-3">
                    <div className="flex items-center gap-2">
                      <span className={clsx(
                        "font-semibold text-sm",
                        isBlend && "text-brand-forest font-bold",
                        isCeiling && "text-brand-rain",
                        isFloor && "text-textLight"
                      )}>
                        {row.strategy.toUpperCase()}
                      </span>
                      <span className={clsx(
                        "text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded font-medium",
                        isBlend ? "bg-brand-forest/10 text-brand-forest" :
                        isCeiling ? "bg-brand-rainPale text-brand-rain" :
                        isFloor ? "bg-surfaceHighlight text-textLight" :
                        "bg-surfaceHighlight text-textMuted"
                      )}>
                        {row.rung}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 font-mono text-sm">{m.rmse.toFixed(2)}</td>
                  <td className="py-3 font-mono text-sm">{m.mae.toFixed(2)}</td>
                  <td className="py-3 font-mono text-sm">{m.fss50.toFixed(2)}</td>
                  <td className="py-3 font-mono text-sm">{m.rev_cl0p1.toFixed(2)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
