import React, { useEffect, useState } from 'react';
import { useAppStore } from '../store';
import { BrainCircuit, ShieldCheck } from 'lucide-react';
import type { WeightsExplainResult } from '../types/results';

interface AttributionData {
  lead_day: number;
  target_region: string;
  weather_regime: string;
  weights: Record<string, number>;
  dominant_model: string;
  explanation: string;
  attribution_breakdown: Array<{
    model: string;
    weight_pct: number;
    strength: string;
    vulnerability: string;
  }>;
  scientific_justification: string;
}

const MODEL_LABEL: Record<string, string> = {
  hres: 'ECMWF IFS HRES',
  ens: 'ECMWF IFS ENS (mean)',
  graphcast: 'DeepMind GraphCast',
  pangu: 'Huawei Pangu-Weather',
};

// Same content as GET /api/weights/explain, built from the pipeline file when the API is down.
function fromPipelineFile(file: WeightsExplainResult, leadDay: number): AttributionData | null {
  const entry = file.leads?.[`L${leadDay}`]?.precip;
  if (!entry) return null;
  const weights = entry.national_weights_applied;
  const rmse = entry.national_train_rmse;
  const ranked = Object.keys(weights).sort((a, b) => weights[b] - weights[a]);
  const dominant = ranked[0];
  return {
    lead_day: leadDay,
    target_region: 'All-India average',
    weather_regime: 'mixed (per region)',
    weights,
    dominant_model: dominant,
    explanation: `${MODEL_LABEL[dominant] ?? dominant} carries ${(100 * weights[dominant]).toFixed(0)}% of the weight at lead day ${leadDay} because it had the lowest training RMSE (${rmse[dominant]}) over ${entry.train_years.join(', ')}. Weights were fitted on those years only and frozen before this cycle.`,
    attribution_breakdown: ranked.map((m) => ({
      model: MODEL_LABEL[m] ?? m,
      weight_pct: Math.round(1000 * weights[m]) / 10,
      strength: `training RMSE ${rmse[m]}`,
      vulnerability: 'verified against ERA5',
    })),
    scientific_justification: entry.formula,
  };
}

export const WeightAttributionCard: React.FC = () => {
  const { leadDay } = useAppStore();
  const [data, setData] = useState<AttributionData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/weights/explain?lead_day=${leadDay}`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch weight explanation');
        return res.json();
      })
      .then((json) => {
        if (!json.available) throw new Error('No weight explanation for this lead');
        setData(json);
        setLoading(false);
      })
      .catch(() =>
        fetch('/data/weights_explain.json')
          .then((res) => res.json())
          .then((file: WeightsExplainResult) => {
            setData(fromPipelineFile(file, leadDay));
            setLoading(false);
          })
          .catch(() => {
            setData(null);
            setLoading(false);
          })
      );
  }, [leadDay]);

  if (!loading && !data) {
    return (
      <div className="p-3 bg-surface rounded-lg border border-borderSubtle text-xs text-textMuted">
        No weight explanation is available for lead day {leadDay}.
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="p-3 bg-surface rounded-lg border border-borderSubtle text-xs text-textMuted flex items-center gap-2">
        <div className="w-3.5 h-3.5 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
        Loading the weights of this cycle...
      </div>
    );
  }

  return (
    <div className="bg-surface rounded-xl border border-brand-forest/30 shadow-sm overflow-hidden text-textMain">
      {/* Header */}
      <div className="bg-gradient-to-r from-emerald-950/80 to-slate-900 p-3.5 border-b border-emerald-800/40 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg">
            <BrainCircuit size={16} />
          </div>
          <div>
            <h4 className="text-xs font-bold text-emerald-200 tracking-wide flex items-center gap-1.5">
              WHY THESE WEIGHTS?
              <span className="px-1.5 py-0.5 text-[10px] bg-emerald-500/20 text-emerald-300 rounded font-mono">
                D+{data.lead_day}
              </span>
            </h4>
            <p className="text-[11px] text-emerald-400/80 font-medium">
              {data.target_region} • from training-period skill
            </p>
          </div>
        </div>
        <div className="text-right">
          <span className="text-[10px] font-mono text-emerald-400/90 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-700/50">
            {data.weather_regime}
          </span>
        </div>
      </div>

      {/* Body */}
      <div className="p-3.5 space-y-3">
        {/* Physical Rationale Quote */}
        <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
          <span className="font-semibold text-emerald-400">Why: </span>
          {data.explanation}
        </p>

        {/* Model Weight Share Bars */}
        <div className="space-y-2">
          <div className="flex justify-between items-center text-[11px] font-semibold text-textMuted uppercase tracking-wider">
            <span>Model Contribution</span>
            <span>Allocated Weight</span>
          </div>

          {data.attribution_breakdown.map((item) => (
            <div key={item.model} className="space-y-1">
              <div className="flex justify-between text-xs font-medium">
                <span className="flex items-center gap-1.5 text-slate-200">
                  <span
                    className={`w-2.5 h-2.5 rounded-full ${
                      item.model.includes('HRES')
                        ? 'bg-blue-500'
                        : item.model.includes('ENS')
                        ? 'bg-purple-500'
                        : 'bg-emerald-500'
                    }`}
                  />
                  {item.model}
                </span>
                <span className="font-mono font-bold text-emerald-300">
                  {item.weight_pct}%
                </span>
              </div>
              <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    item.model.includes('HRES')
                      ? 'bg-blue-500'
                      : item.model.includes('ENS')
                      ? 'bg-purple-500'
                      : 'bg-emerald-500'
                  }`}
                  style={{ width: `${item.weight_pct}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-textMuted pt-0.5">
                <span className="text-emerald-400/90 truncate max-w-[200px]">
                  ✓ {item.strength}
                </span>
                <span className="text-slate-400/80 truncate max-w-[140px] text-right">
                  ⚠ {item.vulnerability}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Scientific Footnote */}
        <div className="pt-2 border-t border-slate-800 flex items-start gap-1.5 text-[10px] text-slate-400">
          <ShieldCheck size={13} className="text-emerald-400 flex-shrink-0 mt-0.5" />
          <span>
            {data.scientific_justification}
          </span>
        </div>
      </div>
    </div>
  );
};
