import React from 'react';
import { useAppStore } from '../store';
import type { LayerId, ModelId, RegionId } from '../store';
import { Cloud, TrendingUp, GitBranch, MapPin, ShieldCheck } from 'lucide-react';
import { LiveBlender } from './LiveBlender';

const LAYERS: { id: LayerId; label: string; icon: React.ReactNode; desc: string }[] = [
  { id: 'rainfall', label: 'Rainfall (mm)', icon: <Cloud size={15} />, desc: '24h blended precipitation' },
  { id: 'exceedance', label: 'Exceedance Probability', icon: <TrendingUp size={15} />, desc: 'Calibrated P(rain ≥ 64.5 mm)' },
  { id: 'disagreement', label: 'Model Disagreement', icon: <GitBranch size={15} />, desc: 'Spread ÷ training-period spread' },
  { id: 'risk_tiers', label: 'Risk Tiers (District)', icon: <MapPin size={15} />, desc: 'Disaster warning levels' },
];

// Lead days the pipeline produces (canonical/accumulation.py)
const LEAD_DAYS = [1, 3, 5, 7, 9];

// IMD homogeneous regions, the same ones the weights are conditioned on
const REGIONS: { id: RegionId; label: string }[] = [
  { id: 'all', label: 'Pan-India (all districts)' },
  { id: 'NW', label: 'Northwest India' },
  { id: 'CENTRAL', label: 'Central India' },
  { id: 'SOUTH', label: 'South Peninsula' },
  { id: 'EAST_NE', label: 'East & Northeast India' },
];

const MODELS: { id: ModelId; label: string; sublabel: string; badge: string }[] = [
  { id: 'blend', label: 'Blended Forecast', sublabel: 'ForeBlendCast', badge: 'Active' },
  { id: 'hres', label: 'ECMWF IFS HRES', sublabel: 'High-Res NWP', badge: '0.25°' },
  { id: 'ens', label: 'ECMWF IFS ENS', sublabel: 'Ensemble Mean', badge: '0.25°' },
  { id: 'graphcast', label: 'DeepMind GraphCast', sublabel: 'AI-NWP Model', badge: 'ML' },
  { id: 'baseline', label: 'Arithmetic Mean', sublabel: 'Equal Weights', badge: 'Base' },
];

export const Sidebar: React.FC = () => {
  const {
    activeLayer, setActiveLayer,
    leadDay, setLeadDay,
    selectedModel, setSelectedModel,
    region, setRegion,
  } = useAppStore();

  return (
    <aside className="w-[260px] flex-shrink-0 bg-surface border-r border-border flex flex-col h-full overflow-y-auto custom-scrollbar select-none">
      <div className="p-4 flex flex-col gap-5">
        {/* Forecast Layers */}
        <section>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-textMuted">
              Forecast Layers
            </h3>
            <span className="text-[10px] text-textLight font-medium">Select one</span>
          </div>
          <div className="space-y-1.5">
            {LAYERS.map((layer) => {
              const isSelected = activeLayer === layer.id;
              return (
                <button
                  key={layer.id}
                  onClick={() => setActiveLayer(layer.id)}
                  className={`w-full flex items-start gap-2.5 px-3 py-2 rounded-lg text-left transition-all duration-150 group border ${
                    isSelected
                      ? 'bg-emerald-50/80 text-brand-forest border-brand-forest/30 shadow-xs ring-1 ring-brand-forest/10'
                      : 'text-textMuted hover:text-textMain hover:bg-surfaceHighlight border-transparent hover:border-slate-200'
                  }`}
                >
                  <span className={`mt-0.5 transition-colors ${isSelected ? 'text-brand-forest' : 'text-textLight group-hover:text-textMuted'}`}>
                    {layer.icon}
                  </span>
                  <div>
                    <div className="text-[12.5px] font-medium leading-snug">
                      {layer.label}
                    </div>
                    <div className="text-[10px] text-textLight leading-tight mt-0.5">
                      {layer.desc}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        {/* Divider */}
        <div className="h-px bg-border/80" />

        {/* Lead Day Selector */}
        <section>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-textMuted">
              Lead Time Horizon
            </h3>
            <span className="text-[10px] font-semibold text-brand-forest bg-emerald-50 px-1.5 py-0.5 rounded">
              +{leadDay * 24} Hours
            </span>
          </div>
          <div className="grid grid-cols-5 gap-1.5">
            {LEAD_DAYS.map((day) => {
              const isSelected = leadDay === day;
              return (
                <button
                  key={day}
                  onClick={() => setLeadDay(day)}
                  className={`py-2 px-1 text-center text-xs font-semibold rounded-md transition-all duration-150 flex flex-col items-center justify-center ${
                    isSelected
                      ? 'bg-brand-forest text-white shadow-sm ring-2 ring-brand-forest/20 scale-[1.02]'
                      : 'bg-surfaceHighlight text-textMuted hover:bg-slate-100 hover:text-textMain hover:border-slate-300 border border-border hover:-translate-y-0.5'
                  }`}
                  title={`Lead Day ${day} (${day * 24} hours ahead)`}
                >
                  <span>D{day}</span>
                  <span className={`text-[9px] font-normal mt-0.5 ${isSelected ? 'text-emerald-100' : 'text-textLight'}`}>
                    {day}d
                  </span>
                </button>
              );
            })}
          </div>
        </section>

        {/* Divider */}
        <div className="h-px bg-border/80" />

        {/* Model View */}
        <section>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-textMuted">
              Model View
            </h3>
            <span className="text-[10px] text-textLight font-medium">Comparison</span>
          </div>
          <div className="space-y-1">
            {MODELS.map((model) => {
              const isSelected = selectedModel === model.id;
              return (
                <button
                  key={model.id}
                  onClick={() => setSelectedModel(model.id)}
                  className={`w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-left transition-all duration-150 border ${
                    isSelected
                      ? 'bg-emerald-50/70 border-brand-forest/25 text-brand-forest shadow-xs font-medium'
                      : 'border-transparent text-textMuted hover:bg-surfaceHighlight hover:text-textMain hover:border-slate-200'
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <div className={`w-3.5 h-3.5 rounded-full border flex items-center justify-center flex-shrink-0 transition-colors ${
                      isSelected
                        ? 'border-brand-forest bg-brand-forest'
                        : 'border-slate-300 bg-white'
                    }`}>
                      {isSelected && (
                        <div className="w-1.5 h-1.5 rounded-full bg-white" />
                      )}
                    </div>
                    <div className="truncate">
                      <div className="text-[12px] truncate leading-tight">
                        {model.label}
                      </div>
                      <div className="text-[10px] text-textLight leading-tight">
                        {model.sublabel}
                      </div>
                    </div>
                  </div>
                  <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded flex-shrink-0 ml-1.5 ${
                    isSelected
                      ? 'bg-emerald-200/50 text-brand-forest'
                      : 'bg-slate-100 text-slate-500'
                  }`}>
                    {model.badge}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Live Blender Component */}
          <LiveBlender />
        </section>

        {/* Divider */}
        <div className="h-px bg-border/80" />

        {/* Region Focus */}
        <section>
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-textMuted mb-2">
            Region / Sub-Division
          </h3>
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value as RegionId)}
            className="w-full bg-surfaceHighlight hover:bg-slate-100 border border-border hover:border-slate-300 text-xs font-medium rounded-lg px-3 py-2 text-textMain outline-none focus:ring-2 focus:ring-brand-forest/30 transition-all cursor-pointer"
          >
            {REGIONS.map((r) => (
              <option key={r.id} value={r.id}>{r.label}</option>
            ))}
          </select>
        </section>
      </div>

      {/* Bottom tagline */}
      <div className="mt-auto p-3.5 border-t border-border bg-surfaceHighlight/50">
        <div className="flex items-center gap-2.5 text-textMuted">
          <div className="p-1 rounded-md bg-emerald-100/60 text-brand-forest">
            <ShieldCheck size={18} />
          </div>
          <div className="text-[11px] leading-tight">
            <span className="font-semibold text-textMain block">ForeBlendCast</span>
            <span className="text-[10px] text-textMuted">Prototype — not an official warning</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
