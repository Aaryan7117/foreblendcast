import React from 'react';
import { useResults } from '../hooks/useResults';
import type { DistrictsResult, WhereWeLoseResult, SummaryResult } from '../types/results';
import { useAppStore } from '../store';
import { CloudRain, AlertTriangle, TrendingUp, GitBranch, ArrowRight } from 'lucide-react';

interface Insight {
  icon: React.ReactNode;
  iconBg: string;
  title: string;
  description: string;
}

export const KeyInsights: React.FC = () => {
  const { leadDay, setActivePage } = useAppStore();
  const { data: districtsData } = useResults<DistrictsResult>(`districts_L${leadDay}.json`);
  const { data: whereLose } = useResults<WhereWeLoseResult>('where_we_lose.json');
  const { data: summary } = useResults<SummaryResult>('summary.json');

  if (!districtsData) return null;

  const districts = districtsData.districts;
  const insights: Insight[] = [];

  // Insight 1: Heavy rainfall districts
  const heavyRainfallDistricts = districts.filter((d) => d.precip_p90_mm > 100);
  if (heavyRainfallDistricts.length > 0) {
    const names = heavyRainfallDistricts.slice(0, 2).map((d) => d.name).join(' & ');
    insights.push({
      icon: <CloudRain size={16} />,
      iconBg: 'bg-emerald-100 text-brand-forest',
      title: `Intense Rainfall Cluster in ${names}`,
      description: `${heavyRainfallDistricts.length} districts with a blended P90 above 100 mm; highest ${Math.max(...heavyRainfallDistricts.map((d) => d.precip_p90_mm))} mm.`,
    });
  }

  // Insight 2: Flood risk from district tiers
  const atRiskDistricts = districts.filter((d) => d.tier === 'red' || d.tier === 'orange');
  if (atRiskDistricts.length > 0) {
    const totalPop = atRiskDistricts.reduce((sum, d) => sum + d.population, 0);
    insights.push({
      icon: <AlertTriangle size={16} />,
      iconBg: 'bg-amber-100 text-tier-orange',
      title: `${atRiskDistricts.length} Districts at Orange or Red`,
      description: `${(totalPop / 1e6).toFixed(1)}M residents live in these districts (WorldPop 2020). Exercise output, no alert has been issued.`,
    });
  }

  // Insight 3: Blend performance
  const rain = summary?.variables?.precip;
  const prob = rain?.ablation?.[`L${leadDay}`]?.probabilistic;
  const rmseVsEqual = rain?.headline?.rmse_change_vs_equal_weight_pct?.[`L${leadDay}`];
  if (summary && prob && rmseVsEqual !== undefined) {
    insights.push({
      icon: <TrendingUp size={16} />,
      iconBg: 'bg-emerald-50 text-brand-forest',
      title: 'Adaptive Blend vs Equal-Weight Mean',
      description: `Held-out ${summary.test_years.join(' & ')}, lead day ${leadDay}: RMSE ${rmseVsEqual.toFixed(1)}%, CRPS ${prob.crps_change_vs_equal_weight_pct.toFixed(1)}% (negative is better). The 90% interval (${prob.quantile_methods?.selected === 'lgbm' ? 'LightGBM' : 'quantile table'}) covered ${((prob.selected_interval_90_coverage ?? prob.interval_90_coverage) * 100).toFixed(0)}% of observations.`,
    });
  }

  // Insight 4: Model disagreement
  const highDisagreement = districts.filter((d) => d.disagreement > 2.0);
  if (whereLose?.summary) {
    const s = whereLose.summary;
    insights.push({
      icon: <GitBranch size={16} />,
      iconBg: 'bg-slate-100 text-slate-700',
      title: `Blend Loses in ${s.contexts_lost_significantly} of ${s.contexts_tested} Contexts`,
      description: `Region × season × regime contexts where a single model beat the blend beyond bootstrap noise. ${highDisagreement.length} districts show model spread above twice the training norm today.`,
    });
  } else if (highDisagreement.length > 0) {
    insights.push({
      icon: <GitBranch size={16} />,
      iconBg: 'bg-slate-100 text-slate-700',
      title: `Model Disagreement in ${highDisagreement.length} Districts`,
      description: 'Model spread is more than twice its training-period norm in these districts.',
    });
  }

  return (
    <div className="bg-surface rounded-card border border-border p-4 shadow-card hover:shadow-cardHover transition-shadow duration-200">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-bold text-textMain">Key Meteorological Insights</h3>
          <p className="text-[11px] text-textMuted">Computed from the pipeline outputs of this cycle</p>
        </div>
        <button
          className="text-xs text-brand-forest font-semibold hover:text-brand-darkGreen transition-colors flex items-center gap-1 group"
          onClick={() => setActivePage('evaluation')}
        >
          Verification Metrics
          <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5" />
        </button>
      </div>

      <div className="space-y-2">
        {insights.map((insight, idx) => (
          <div
            key={idx}
            className="flex items-start gap-3 p-2.5 rounded-lg border border-transparent hover:border-border hover:bg-surfaceHighlight/50 hover:shadow-xs transition-all duration-150 cursor-default"
          >
            <div className={`w-8 h-8 rounded-lg ${insight.iconBg} flex items-center justify-center flex-shrink-0 mt-0.5 shadow-xs`}>
              {insight.icon}
            </div>
            <div>
              <div className="text-xs font-bold text-textMain leading-snug">{insight.title}</div>
              <div className="text-[11px] text-textMuted leading-relaxed mt-0.5">{insight.description}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
