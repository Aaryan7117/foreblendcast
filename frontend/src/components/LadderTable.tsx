import React from 'react';
import { useResults } from '../hooks/useResults';
import type { LadderResult } from '../types/results';
import { useAppStore } from '../store';
import clsx from 'clsx';

const fmt = (x: number | null | undefined, digits = 2) =>
  x === null || x === undefined || !Number.isFinite(x) ? '—' : x.toFixed(digits);

export const LadderTable: React.FC = () => {
  const { data: ladder } = useResults<LadderResult>('ladder.json');
  const { leadDay } = useAppStore();

  if (!ladder) return null;

  // The metrics for the current lead day. Lead day keys are formatted like "L3"
  const leadKey = `L${leadDay}`;

  // Sort rows to enforce the hierarchy: Ceiling -> Blend -> Ablation -> Baseline -> Single -> Floor
  const hierarchy = {
    ceiling: 1,
    blend: 2,
    ablation: 3,
    baseline: 4,
    single: 5,
    floor: 6
  };

  const sortedRows = [...ladder.rows].sort((a, b) => {
    if (hierarchy[a.rung] !== hierarchy[b.rung]) {
      return hierarchy[a.rung] - hierarchy[b.rung];
    }
    // Within a rung, sort by RMSE ascending
    const rmseA = a.metrics[leadKey]?.rmse ?? 999;
    const rmseB = b.metrics[leadKey]?.rmse ?? 999;
    return rmseA - rmseB;
  });

  const head = ladder.headline;
  const vsEqual = head.rmse_change_vs_equal_weight_pct?.[leadKey];
  const vsBest = head.rmse_change_vs_best_single_pct?.[leadKey];
  const scale = ladder.fss_scale_km ?? 83;

  return (
    <div className="bg-surface rounded-card border border-border p-5 shadow-card">
      <div className="flex justify-between items-end mb-4">
        <div>
          <h2 className="text-lg font-bold text-textMain">Performance Ladder</h2>
          <p className="text-xs text-textMuted mt-1">
            Lead Day {leadDay} • held-out years {(head.test_years ?? []).join(', ')} • truth: {ladder.meta.ground_truth} reanalysis
          </p>
          <p className="text-xs text-textMuted mt-0.5">
            Adaptive blend RMSE: {fmt(vsEqual, 1)}% vs equal-weight mean, {fmt(vsBest, 1)}% vs best single model ({head.best_single.toUpperCase()}) •{' '}
            {fmt(head.pct_of_achievable_gain[leadKey], 1)}% of the gap to the oracle captured
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
              <th className="pb-3 font-semibold">Bias</th>
              <th className="pb-3 font-semibold">FSS 64.5 mm (~{scale} km)</th>
              <th className="pb-3 font-semibold">Freq. bias</th>
              <th className="pb-3 font-semibold">REV (C/L 0.1)</th>
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
                  <td className="py-3 font-mono text-sm">{fmt(m.rmse)}</td>
                  <td className="py-3 font-mono text-sm">{fmt(m.mae)}</td>
                  <td className="py-3 font-mono text-sm">{fmt(m.bias)}</td>
                  <td className="py-3 font-mono text-sm">{fmt(m.fss50)}</td>
                  <td className="py-3 font-mono text-sm">{fmt(m.freq_bias_64p5)}</td>
                  <td className="py-3 font-mono text-sm">{fmt(m.rev_cl0p1)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-textMuted mt-3 leading-relaxed">
        Weights are learned from earlier years and frozen before the test year is verified. BEST_SINGLE_TRAIN is
        chosen on training data; ORACLE picks the best model per cell in hindsight and is a ceiling, not a forecast.
        LGBM_BLEND is a LightGBM correction of the blend trained on the same years. ERA5 is the truth, which
        favours models trained on ERA5 (GraphCast).
      </p>
    </div>
  );
};
