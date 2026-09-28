import React from 'react';
import { useResults } from '../hooks/useResults';
import type { DistrictsResult } from '../types/results';
import { useAppStore } from '../store';
import type { ModelId } from '../store';
import { Check, ArrowRight } from 'lucide-react';

const MODEL_LABELS: Record<string, { id: ModelId; name: string; sublabel: string; badge: string }> = {
  blend: { id: 'blend', name: 'ForeBlendCast', sublabel: 'Adaptive Calibrated Blend', badge: 'Recommended' },
  hres: { id: 'hres', name: 'ECMWF IFS HRES', sublabel: '0.1° Deterministic NWP', badge: 'High-Res' },
  ens: { id: 'ens', name: 'ECMWF IFS ENS', sublabel: '50-Member Ensemble Mean', badge: 'Probabilistic' },
  graphcast: { id: 'graphcast', name: 'Google GraphCast', sublabel: 'AI-NWP Weather Model', badge: 'Deep Learning' },
  baseline: { id: 'baseline', name: 'Arithmetic Mean', sublabel: 'Unweighted Baseline', badge: 'Standard' },
};

const MODEL_KEYS = ['blend', 'hres', 'ens', 'graphcast', 'baseline'];

export const ModelComparison: React.FC = () => {
  const { leadDay, selectedModel, setSelectedModel, setActivePage } = useAppStore();
  const { data: districtsData } = useResults<DistrictsResult>(`districts_L${leadDay}.json`);

  if (!districtsData) return null;

  const districts = districtsData.districts;
  const avgPrecip = districts.length > 0
    ? (districts.reduce((sum, d) => sum + d.precip_p90_mm, 0) / districts.length).toFixed(0)
    : '—';

  return (
    <div className="bg-surface rounded-card border border-border p-4 shadow-card hover:shadow-cardHover transition-shadow duration-200">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-bold text-textMain">
            Multi-Model Comparison (Lead Day {leadDay} • L+{leadDay * 24}h)
          </h3>
          <p className="text-[11px] text-textMuted">Comparing NWP, AI, and Blended rainfall fields</p>
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
        {MODEL_KEYS.map((key) => {
          const model = MODEL_LABELS[key];
          const isSelected = selectedModel === model.id;
          const isBlend = key === 'blend';

          return (
            <div
              key={key}
              onClick={() => setSelectedModel(model.id)}
              className={`rounded-xl border p-3 text-center transition-all duration-200 hover:-translate-y-1 hover:shadow-md cursor-pointer select-none flex flex-col justify-between ${
                isSelected
                  ? 'border-brand-forest bg-emerald-50/70 shadow-sm ring-2 ring-brand-forest/20'
                  : isBlend
                  ? 'border-emerald-300/60 bg-emerald-50/30 hover:border-brand-forest/50'
                  : 'border-border bg-surfaceHighlight/50 hover:bg-surfaceHighlight hover:border-slate-300'
              }`}
            >
              <div>
                {/* Mini card visual badge */}
                <div className="relative w-full aspect-[16/11] bg-gradient-to-b from-slate-50 to-slate-100 rounded-lg mb-2 overflow-hidden flex items-center justify-center border border-slate-200/70 shadow-xs">
                  <svg viewBox="0 0 80 100" className="w-10 h-12 opacity-25" fill="none" stroke="#2D6A4F" strokeWidth="1">
                    <path d="M40 5 L55 15 L60 30 L65 45 L55 55 L60 70 L50 85 L45 95 L40 90 L35 80 L25 85 L20 75 L15 60 L20 45 L25 35 L30 20 L35 10 Z" />
                  </svg>
                  {isBlend && (
                    <div className="absolute top-1.5 right-1.5">
                      <div className="w-4 h-4 rounded-full bg-brand-forest text-white flex items-center justify-center shadow-xs">
                        <Check size={10} strokeWidth={3} />
                      </div>
                    </div>
                  )}
                  <span className={`absolute bottom-1 px-1.5 py-0.5 rounded text-[8.5px] font-bold uppercase tracking-wider ${
                    isBlend ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-700'
                  }`}>
                    {model.badge}
                  </span>
                </div>

                <div className={`text-xs font-bold truncate leading-tight ${isBlend ? 'text-brand-forest' : 'text-textMain'}`}>
                  {model.name}
                </div>
                <div className="text-[10px] text-textMuted leading-tight mt-0.5 truncate">
                  {model.sublabel}
                </div>
              </div>

              {/* Average precipitation metric */}
              <div className="mt-2.5 pt-2 border-t border-slate-200/60 flex items-center justify-between text-[10.5px]">
                <span className="text-textLight font-medium">Avg P90:</span>
                <span className="font-mono font-bold text-textMain">{avgPrecip} mm</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
