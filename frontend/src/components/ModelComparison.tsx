import React from 'react';
import { useResults } from '../hooks/useResults';
import type { LadderResult } from '../types/results';
import { useAppStore } from '../store';
import type { ModelId } from '../store';
import { Check, ArrowRight } from 'lucide-react';

// strategy = the ladder row that holds the held-out metrics of each view
const MODELS: { id: ModelId; strategy: string; name: string; sublabel: string; badge: string }[] = [
  { id: 'blend', strategy: 'context_shrink_pm', name: 'ForeBlendCast', sublabel: 'Adaptive Blend', badge: 'Blend' },
  { id: 'hres', strategy: 'hres', name: 'ECMWF IFS HRES', sublabel: 'Deterministic NWP', badge: 'NWP' },
  { id: 'ens', strategy: 'ens', name: 'ECMWF IFS ENS', sublabel: 'Ensemble Mean', badge: 'Ensemble' },
  { id: 'graphcast', strategy: 'graphcast', name: 'Google GraphCast', sublabel: 'AI Weather Model', badge: 'AI' },
  { id: 'baseline', strategy: 'equal_weight', name: 'Arithmetic Mean', sublabel: 'Equal-Weight Baseline', badge: 'Baseline' },
];

const fmt = (x: number | null | undefined, digits = 2) =>
  x === null || x === undefined || !Number.isFinite(x) ? '—' : x.toFixed(digits);

export const ModelComparison: React.FC = () => {
  const { leadDay, selectedModel, setSelectedModel, setActivePage } = useAppStore();
  const { data: ladder } = useResults<LadderResult>('ladder.json');

  if (!ladder) return null;

  const leadKey = `L${leadDay}`;
  const metricsOf = (strategy: string) =>
    ladder.rows.find((r) => r.strategy === strategy)?.metrics[leadKey];
  const best = Math.min(
    ...MODELS.map((m) => metricsOf(m.strategy)?.rmse ?? Number.POSITIVE_INFINITY)
  );

  return (
    <div className="bg-surface rounded-card border border-border p-4 shadow-card hover:shadow-cardHover transition-shadow duration-200">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-bold text-textMain">
            Multi-Model Comparison (Lead Day {leadDay} • L+{leadDay * 24}h)
          </h3>
          <p className="text-[11px] text-textMuted">
            Held-out rainfall skill vs ERA5, {(ladder.headline.test_years ?? []).join(' & ')} • select a card to map that field
          </p>
        </div>
        <button
          className="text-xs text-brand-forest font-semibold hover:text-brand-darkGreen transition-colors flex items-center gap-1 group"
          onClick={() => setActivePage('comparison')}
        >
          Detailed Comparison
          <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5" />
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2.5">
        {MODELS.map((model) => {
          const isSelected = selectedModel === model.id;
          const isBlend = model.id === 'blend';
          const m = metricsOf(model.strategy);
          const isBest = m?.rmse !== undefined && m?.rmse !== null && m.rmse === best;

          return (
            <div
              key={model.id}
              onClick={() => setSelectedModel(model.id)}
              className={`rounded-xl border p-3 transition-all duration-200 hover:-translate-y-1 hover:shadow-md cursor-pointer select-none flex flex-col justify-between ${
                isSelected
                  ? 'border-brand-forest bg-emerald-50/70 shadow-sm ring-2 ring-brand-forest/20'
                  : isBlend
                  ? 'border-emerald-300/60 bg-emerald-50/30 hover:border-brand-forest/50'
                  : 'border-border bg-surfaceHighlight/50 hover:bg-surfaceHighlight hover:border-slate-300'
              }`}
            >
              <div className="flex items-start justify-between gap-1">
                <div className="min-w-0">
                  <div className={`text-xs font-bold truncate leading-tight ${isBlend ? 'text-brand-forest' : 'text-textMain'}`}>
                    {model.name}
                  </div>
                  <div className="text-[10px] text-textMuted leading-tight mt-0.5 truncate">
                    {model.sublabel}
                  </div>
                </div>
                <span className={`px-1.5 py-0.5 rounded text-[8.5px] font-bold uppercase tracking-wider flex items-center gap-0.5 flex-shrink-0 ${
                  isBest ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-700'
                }`}>
                  {isBest && <Check size={9} strokeWidth={3} />}
                  {isBest ? 'Lowest RMSE' : model.badge}
                </span>
              </div>

              {/* Held-out metrics of this model, from results/ladder.json */}
              <div className="mt-2.5 pt-2 border-t border-slate-200/60 grid grid-cols-3 gap-1 text-[10.5px]">
                <div>
                  <div className="text-textLight font-medium">RMSE</div>
                  <div className="font-mono font-bold text-textMain">{fmt(m?.rmse)}</div>
                </div>
                <div>
                  <div className="text-textLight font-medium">MAE</div>
                  <div className="font-mono font-bold text-textMain">{fmt(m?.mae)}</div>
                </div>
                <div>
                  <div className="text-textLight font-medium">FSS</div>
                  <div className="font-mono font-bold text-textMain">{fmt(m?.fss50)}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
