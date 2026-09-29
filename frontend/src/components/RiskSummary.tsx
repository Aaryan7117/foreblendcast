import React from 'react';
import { useResults } from '../hooks/useResults';
import type { DistrictsResult } from '../types/results';
import { useAppStore } from '../store';

export const RiskSummary: React.FC = () => {
  const { leadDay, region, setTierFilter, setActivePage } = useAppStore();
  const { data: districtsData } = useResults<DistrictsResult>(`districts_L${leadDay}.json`);

  if (!districtsData) return null;

  const districts = districtsData.districts.filter((d) => region === 'all' || d.region === region);
  const redCount = districts.filter((d) => d.tier === 'red').length;
  const orangeCount = districts.filter((d) => d.tier === 'orange').length;
  const yellowCount = districts.filter((d) => d.tier === 'yellow').length;
  const greenCount = districts.filter((d) => d.tier === 'green').length;

  const tiers = [
    { tierKey: 'red', label: 'Red Alert', sublabel: 'P(≥204.5 mm) high', count: redCount, color: 'text-tier-red', bg: 'bg-tier-redBg', borderColor: 'border-tier-red/25', hoverBorder: 'hover:border-tier-red/60', badgeBg: 'bg-tier-red' },
    { tierKey: 'orange', label: 'Orange Alert', sublabel: 'P(≥115.6 mm) high', count: orangeCount, color: 'text-tier-orange', bg: 'bg-tier-orangeBg', borderColor: 'border-tier-orange/25', hoverBorder: 'hover:border-tier-orange/60', badgeBg: 'bg-tier-orange' },
    { tierKey: 'yellow', label: 'Yellow Alert', sublabel: 'P(≥64.5 mm) high', count: yellowCount, color: 'text-tier-yellow', bg: 'bg-tier-yellowBg', borderColor: 'border-tier-yellow/25', hoverBorder: 'hover:border-tier-yellow/60', badgeBg: 'bg-tier-yellow' },
    { tierKey: 'green', label: 'Green Normal', sublabel: 'Below thresholds', count: greenCount, color: 'text-tier-green', bg: 'bg-tier-greenBg', borderColor: 'border-tier-green/25', hoverBorder: 'hover:border-tier-green/60', badgeBg: 'bg-tier-green' },
  ];

  const handleCardClick = (tierKey: string) => {
    setTierFilter(tierKey);
    setActivePage('risk');
  };

  return (
    <div className="bg-surface rounded-card border border-border p-4 shadow-card">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-bold text-textMain">{region === 'all' ? 'Nationwide' : 'Regional'} District Risk Summary</h3>
          <p className="text-[11px] text-textMuted">Disaster alert distribution for Lead Day {leadDay}</p>
        </div>
        <button
          className="text-xs text-brand-forest font-semibold hover:text-brand-darkGreen transition-colors flex items-center gap-1 group"
          onClick={() => setActivePage('risk')}
        >
          Detailed Risk Matrix
          <span className="transition-transform group-hover:translate-x-0.5">→</span>
        </button>
      </div>
      <div className="grid grid-cols-4 gap-2.5">
        {tiers.map((tier) => (
          <div
            key={tier.label}
            onClick={() => handleCardClick(tier.tierKey)}
            className={`${tier.bg} border ${tier.borderColor} ${tier.hoverBorder} rounded-lg p-2.5 text-center transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md cursor-pointer select-none`}
            title={`Filter by ${tier.label}`}
          >
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <span className={`w-2.5 h-2.5 rounded-full ${tier.badgeBg} shadow-xs`} />
              <span className="text-[11px] font-bold text-textMain">{tier.label}</span>
            </div>
            <div className={`text-2xl font-extrabold ${tier.color} tracking-tight`}>{tier.count}</div>
            <div className="text-[9.5px] text-textMuted font-medium mt-0.5 truncate">{tier.sublabel}</div>
          </div>
        ))}
      </div>
    </div>
  );
};
