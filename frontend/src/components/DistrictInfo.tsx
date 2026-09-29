import React from 'react';
import { useResults } from '../hooks/useResults';
import type { DistrictsResult } from '../types/results';
import { useAppStore } from '../store';
import { Users, CloudRain, Scale, AlertTriangle } from 'lucide-react';

const TIER_CONFIG = {
  red: { label: 'Red Alert', desc: 'Extreme risk of very heavy to extremely heavy rainfall', color: 'text-tier-red', bg: 'bg-tier-redBg', border: 'border-tier-red/40', badge: 'bg-tier-red' },
  orange: { label: 'Orange Alert', desc: 'High risk of isolated heavy to very heavy rainfall', color: 'text-tier-orange', bg: 'bg-tier-orangeBg', border: 'border-tier-orange/40', badge: 'bg-tier-orange' },
  yellow: { label: 'Yellow Alert', desc: 'Moderate rainfall expected; watch status', color: 'text-tier-yellow', bg: 'bg-tier-yellowBg', border: 'border-tier-yellow/40', badge: 'bg-tier-yellow' },
  green: { label: 'Green (Normal)', desc: 'No severe weather warning; standard conditions', color: 'text-tier-green', bg: 'bg-tier-greenBg', border: 'border-tier-green/40', badge: 'bg-tier-green' },
};

export const DistrictInfo: React.FC = () => {
  const { leadDay, region, selectedDistrict, setSelectedDistrict } = useAppStore();
  const { data: districtsData } = useResults<DistrictsResult>(`districts_L${leadDay}.json`);

  if (!districtsData) return null;

  const districts = districtsData.districts.filter((d) => region === 'all' || d.region === region);
  // default to the district with the highest heavy-rain probability
  const top = [...districts].sort((a, b) => b.p_gt_115p6 - a.p_gt_115p6 || b.p_gt_64p5 - a.p_gt_64p5)[0];
  const selected = (selectedDistrict && districts.find((d) => d.id === selectedDistrict)) || top;

  if (!selected) return null;

  const tierInfo = TIER_CONFIG[selected.tier];
  const totalPop = (selected.population / 1e6).toFixed(1);

  return (
    <div className="bg-surface rounded-card border border-border p-4 shadow-card hover:shadow-cardHover transition-shadow duration-200">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-bold text-textMain">District Alert & Vulnerability</h3>
          <p className="text-[11px] text-textMuted">Operational status for {selected.name}</p>
        </div>
        <select
          value={selected.id}
          onChange={(e) => setSelectedDistrict(e.target.value)}
          className="text-xs font-semibold bg-surfaceHighlight hover:bg-slate-100 border border-border rounded-lg px-2.5 py-1.5 text-textMain outline-none focus:ring-2 focus:ring-brand-forest/30 transition-all cursor-pointer max-w-[170px]"
          title="Select District"
        >
          {districts.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}, {d.state}
            </option>
          ))}
        </select>
      </div>

      {/* Alert banner with subtle hover */}
      <div className={`${tierInfo.bg} border ${tierInfo.border} rounded-lg p-3 mb-3.5 transition-all duration-200 hover:shadow-xs`}>
        <div className="flex items-center gap-2 mb-1">
          <span className={`w-2.5 h-2.5 rounded-full ${tierInfo.badge} shadow-xs`} />
          <span className={`text-sm font-bold ${tierInfo.color}`}>
            {tierInfo.label} — {selected.name}, {selected.state}
          </span>
        </div>
        <p className="text-xs text-textMuted leading-relaxed">{tierInfo.desc}</p>
        <div className="flex items-center gap-1.5 text-xs text-amber-800 font-medium mt-1.5 pt-1.5 border-t border-amber-200/50">
          <AlertTriangle size={13} className="text-tier-orange flex-shrink-0" />
          <span>
            P(≥64.5 mm) {(selected.p_gt_64p5 * 100).toFixed(0)}% · P(≥115.6 mm) {(selected.p_gt_115p6 * 100).toFixed(0)}% · P(≥204.5 mm) {(selected.p_gt_204p5 * 100).toFixed(0)}%
            {selected.tmax_c != null && ` · T(12 UTC) ${selected.tmax_c.toFixed(1)} °C${selected.heatwave ? ' (heatwave)' : ''}`}
            {selected.wind_ms != null && ` · wind ${selected.wind_ms.toFixed(1)} m/s${selected.high_wind ? ' (strong)' : ''}`}
          </span>
        </div>
      </div>

      {/* Info grid with interactive cards */}
      <div className="grid grid-cols-3 gap-2.5">
        {/* Population */}
        <div className="bg-surfaceHighlight/60 hover:bg-surfaceHighlight border border-border rounded-lg p-2.5 text-center transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xs">
          <div className="flex justify-center text-textMuted mb-1">
            <Users size={16} />
          </div>
          <div className="text-[10.5px] font-semibold text-textMuted uppercase tracking-wider">Population</div>
          <div className="text-base font-bold text-textMain mt-0.5">{totalPop}M</div>
          <div className="text-[9.5px] text-textLight">Residents (WorldPop 2020)</div>
        </div>

        {/* Expected Rainfall */}
        <div className="bg-surfaceHighlight/60 hover:bg-surfaceHighlight border border-border rounded-lg p-2.5 text-center transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xs">
          <div className="flex justify-center text-brand-forest mb-1">
            <CloudRain size={16} />
          </div>
          <div className="text-[10.5px] font-semibold text-textMuted uppercase tracking-wider">Expected Rain</div>
          <div className="text-base font-bold text-textMain mt-0.5">{selected.precip_p90_mm} mm</div>
          <div className="text-[9.5px] text-textLight">
            {selected.precip_q05_mm != null && selected.precip_q95_mm != null
              ? `90% interval ${selected.precip_q05_mm}–${selected.precip_q95_mm} mm`
              : 'district P90 cell'}
          </div>
        </div>

        {/* Model Weights */}
        <div className="bg-surfaceHighlight/60 hover:bg-surfaceHighlight border border-border rounded-lg p-2.5 text-center transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xs">
          <div className="flex justify-center text-brand-darkGreen mb-1">
            <Scale size={16} />
          </div>
          <div className="text-[10.5px] font-semibold text-textMuted uppercase tracking-wider mb-1">Blend Weights</div>
          <div className="space-y-1 text-left px-1">
            {Object.entries(selected.weights).map(([model, weight]) => (
              <div key={model} className="flex items-center justify-between text-[10px]">
                <span className="uppercase text-textMuted font-bold">{model}</span>
                <span className="font-mono font-semibold text-brand-forest">
                  {((weight as number) * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
