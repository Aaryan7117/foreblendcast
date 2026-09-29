import React from 'react';
import { useAppStore } from '../store';
import { useResults } from '../hooks/useResults';
import type { DistrictsResult } from '../types/results';
import { Wheat, Anchor, ShieldCheck, HeartPulse } from 'lucide-react';

export const ImpactCards: React.FC = () => {
  const { leadDay, selectedDistrict } = useAppStore();
  const { data: districtsData } = useResults<DistrictsResult>(`districts_L${leadDay}.json`);

  if (!districtsData) return null;

  const districts = districtsData.districts;
  const selected = selectedDistrict
    ? districts.find((d) => d.id === selectedDistrict)
    : districts[0];

  if (!selected) return null;

  const getImpacts = (tier: string) => {
    switch (tier.toLowerCase()) {
      case 'red':
        return [
          {
            persona: 'Farmer',
            icon: <Wheat size={18} />,
            action: 'Do not spray pesticides. Delay all sowing activities immediately. Harvest mature crops if possible.',
            color: 'text-amber-700',
            bg: 'bg-amber-50'
          },
          {
            persona: 'Fisher',
            icon: <Anchor size={18} />,
            action: 'Do not venture into the sea. Secure boats in safe harbors.',
            color: 'text-blue-700',
            bg: 'bg-blue-50'
          },
          {
            persona: 'District Magistrate',
            icon: <ShieldCheck size={18} />,
            action: `Pre-position NDRF teams. Mobilize evacuation for low-lying areas. Approx. ${(selected.population / 1e6).toFixed(1)}M exposed.`,
            color: 'text-purple-700',
            bg: 'bg-purple-50'
          },
          {
            persona: 'Citizen',
            icon: <HeartPulse size={18} />,
            action: 'Avoid rivers and low-lying areas. Stay indoors during heavy downpours.',
            color: 'text-rose-700',
            bg: 'bg-rose-50'
          }
        ];
      case 'orange':
        return [
          {
            persona: 'Farmer',
            icon: <Wheat size={18} />,
            action: 'Postpone irrigation and fertilizer application. Check drainage in fields.',
            color: 'text-amber-700',
            bg: 'bg-amber-50'
          },
          {
            persona: 'Fisher',
            icon: <Anchor size={18} />,
            action: 'Avoid deep-sea fishing. Return to coast if weather deteriorates.',
            color: 'text-blue-700',
            bg: 'bg-blue-50'
          },
          {
            persona: 'District Magistrate',
            icon: <ShieldCheck size={18} />,
            action: 'Keep SDRF on standby. Alert block development officers in flood-prone zones.',
            color: 'text-purple-700',
            bg: 'bg-purple-50'
          },
          {
            persona: 'Citizen',
            icon: <HeartPulse size={18} />,
            action: 'Avoid unnecessary travel during rain. Keep emergency kits ready.',
            color: 'text-rose-700',
            bg: 'bg-rose-50'
          }
        ];
      default: // yellow or green
        return [
          {
            persona: 'Farmer',
            icon: <Wheat size={18} />,
            action: 'Normal farming activities can continue. Monitor upcoming forecasts.',
            color: 'text-slate-600',
            bg: 'bg-slate-50'
          },
          {
            persona: 'Fisher',
            icon: <Anchor size={18} />,
            action: 'Normal fishing activities allowed. Carry safety equipment.',
            color: 'text-slate-600',
            bg: 'bg-slate-50'
          },
          {
            persona: 'District Magistrate',
            icon: <ShieldCheck size={18} />,
            action: 'Standard operational readiness. Review district disaster management plans.',
            color: 'text-slate-600',
            bg: 'bg-slate-50'
          },
          {
            persona: 'Citizen',
            icon: <HeartPulse size={18} />,
            action: 'Normal routine. Follow standard weather advisories.',
            color: 'text-slate-600',
            bg: 'bg-slate-50'
          }
        ];
    }
  };

  const impacts = getImpacts(selected.tier);

  return (
    <div className="bg-surface rounded-card border border-border p-4 shadow-card hover:shadow-cardHover transition-shadow duration-200">
      <div className="mb-3">
        <h3 className="text-sm font-bold text-textMain">Impact-Based Advisories (WMO)</h3>
        <p className="text-[11px] text-textMuted">Actionable insights for {selected.name}</p>
      </div>
      
      <div className="space-y-2.5">
        {impacts.map((impact) => (
          <div key={impact.persona} className={`flex items-start gap-3 p-2.5 rounded-lg border border-border/50 ${impact.bg} transition-colors`}>
            <div className={`mt-0.5 flex-shrink-0 ${impact.color}`}>
              {impact.icon}
            </div>
            <div>
              <h4 className={`text-xs font-bold ${impact.color} mb-0.5`}>{impact.persona}</h4>
              <p className="text-[11px] text-textMain leading-snug">{impact.action}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
