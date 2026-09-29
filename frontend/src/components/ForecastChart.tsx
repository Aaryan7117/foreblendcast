import React, { useState } from 'react';
import Plot from 'react-plotly.js';
import { useResults } from '../hooks/useResults';
import type { PointsResult } from '../types/results';
import { useAppStore } from '../store';
import { LineChart, MapPin } from 'lucide-react';

const CITIES = ['mumbai', 'chennai', 'kolkata', 'delhi', 'guwahati'];
const CITY_LABELS: Record<string, string> = {
  mumbai: 'Mumbai (Coastal West)',
  chennai: 'Chennai (Coastal South)',
  kolkata: 'Kolkata (Gangetic Delta)',
  delhi: 'Delhi (North Plains)',
  guwahati: 'Guwahati (North East)',
};

const MODEL_COLORS: Record<string, string> = {
  blend: '#0e3825',
  hres: '#1d4ed8',
  ens: '#7c3aed',
  graphcast: '#d97706',
};

export const ForecastChart: React.FC = () => {
  const [citySlug, setCitySlug] = useState<string>('mumbai');
  const { data: points } = useResults<PointsResult>(`points/${citySlug}.json`);
  const { leadDay } = useAppStore();

  if (!points) return null;

  const xDays = points.lead_days;

  const data: any[] = [];

  // q05-q95 shaded region
  data.push({
    x: [...xDays, ...[...xDays].reverse()],
    y: [...(points.q95 as number[]), ...([...(points.q05 as number[])].reverse())],
    fill: 'toself',
    fillcolor: 'rgba(16, 185, 129, 0.12)',
    line: { color: 'transparent' },
    name: '90% predictive interval (q05–q95)',
    showlegend: true,
    hoverinfo: 'none',
  });

  // Individual model members
  Object.entries(points.members).forEach(([model, values]) => {
    const color = MODEL_COLORS[model] || '#64748B';
    data.push({
      x: xDays,
      y: values as number[],
      mode: 'lines',
      line: { width: 1.5, color, dash: model === 'ens' ? 'dash' : 'solid' },
      name: model === 'hres' ? 'ECMWF HRES' : model === 'ens' ? 'ECMWF ENS mean' : model === 'graphcast' ? 'GraphCast (AI)' : model.toUpperCase(),
      hovertemplate: `${model.toUpperCase()}: %{y:.1f} mm<extra></extra>`,
    });
  });

  // Blend (thick line with markers)
  data.push({
    x: xDays,
    y: points.blend as number[],
    mode: 'lines+markers',
    line: { color: MODEL_COLORS.blend, width: 2.75 },
    marker: { size: 6, color: MODEL_COLORS.blend },
    name: 'ForeBlendCast (Blended)',
    hovertemplate: 'Blend: %{y:.1f} mm<extra></extra>',
  });

  return (
    <div className="bg-surface rounded-card border border-border p-4 shadow-card hover:shadow-cardHover transition-shadow duration-200">
      <div className="flex justify-between items-center mb-3">
        <div>
          <h3 className="text-sm font-bold text-textMain flex items-center gap-1.5">
            <LineChart size={16} className="text-brand-forest" />
            Rainfall Plume & Ensemble Meteogram
          </h3>
          <p className="text-[11px] text-textMuted">Members, blend and the interval learned from past errors</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 text-xs text-textMuted font-medium bg-surfaceHighlight hover:bg-slate-100 border border-border rounded-lg px-2.5 py-1 transition-colors">
            <MapPin size={12} className="text-brand-forest" />
            <select
              value={citySlug}
              onChange={(e) => setCitySlug(e.target.value)}
              className="bg-transparent text-xs font-semibold text-textMain outline-none cursor-pointer"
              title="Select City Location"
            >
              {CITIES.map((c) => (
                <option key={c} value={c}>{CITY_LABELS[c]}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="h-56 w-full">
        <Plot
          data={data}
          layout={{
            autosize: true,
            margin: { l: 45, r: 12, t: 10, b: 35 },
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            xaxis: {
              title: { text: 'Lead Horizon (Days)', font: { size: 10.5, color: '#536273' } },
              gridcolor: '#F1F5F9',
              zerolinecolor: '#E2E8F0',
              tickfont: { color: '#536273', size: 10 },
              linecolor: '#CBD5E1',
            },
            yaxis: {
              title: { text: 'Precipitation (mm/24h)', font: { size: 10.5, color: '#536273' } },
              gridcolor: '#F1F5F9',
              zerolinecolor: '#E2E8F0',
              tickfont: { color: '#536273', size: 10 },
              linecolor: '#CBD5E1',
            },
            showlegend: true,
            legend: {
              orientation: 'h',
              yanchor: 'bottom',
              y: 1.02,
              xanchor: 'left',
              x: 0,
              font: { color: '#334155', size: 9 },
              tracegroupgap: 4,
            },
            shapes: [
              {
                type: 'line',
                x0: leadDay,
                x1: leadDay,
                y0: 0,
                y1: 1,
                yref: 'paper',
                line: { color: '#DC2626', width: 1.5, dash: 'dot' },
              },
            ],
          }}
          useResizeHandler={true}
          style={{ width: '100%', height: '100%' }}
          config={{ displayModeBar: false }}
        />
      </div>
    </div>
  );
};
