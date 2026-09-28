import React, { useState } from 'react';
import Plot from 'react-plotly.js';
import { useResults } from '../hooks/useResults';
import type { PointsResult } from '../types/results';
import { useAppStore } from '../store';

const CITIES = ['mumbai', 'chennai', 'kolkata', 'delhi', 'guwahati'];
const CITY_LABELS: Record<string, string> = {
  mumbai: 'Mumbai',
  chennai: 'Chennai',
  kolkata: 'Kolkata',
  delhi: 'Delhi',
  guwahati: 'Guwahati',
};

export const Spaghetti: React.FC = () => {
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
    fillcolor: 'rgba(23, 74, 53, 0.08)',
    line: { color: 'transparent' },
    name: '90% CI',
    showlegend: true,
    hoverinfo: 'none',
  });

  // Individual members
  Object.entries(points.members).forEach(([model, values]) => {
    data.push({
      x: xDays,
      y: values as number[],
      mode: 'lines',
      line: {
        width: 1.5,
        color: model === 'gfs' ? '#2878B5' : model === 'ecmwf' ? '#7B61FF' : model === 'graphcast' ? '#EF6C00' : '#94A3B8',
      },
      name: model.toUpperCase(),
      showlegend: true,
      hovertemplate: `${model.toUpperCase()}: %{y:.1f}mm<extra></extra>`,
    });
  });

  // Blend (thick line)
  data.push({
    x: xDays,
    y: points.blend as number[],
    mode: 'lines+markers',
    line: { color: '#174A35', width: 2.5 },
    marker: { size: 5, color: '#174A35' },
    name: 'Our Blend',
    hovertemplate: 'Blend: %{y:.1f}mm<extra></extra>',
  });

  return (
    <div className="bg-surface rounded-card border border-border p-5 shadow-card">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold text-textMain">
          Plume — {CITY_LABELS[citySlug] || citySlug}
        </h2>
        <select
          value={citySlug}
          onChange={e => setCitySlug(e.target.value)}
          className="bg-surfaceHighlight border border-border text-sm rounded-lg px-3 py-1.5 outline-none focus:border-brand-forest/50 text-textMain cursor-pointer"
        >
          {CITIES.map(c => (
            <option key={c} value={c}>{CITY_LABELS[c]}</option>
          ))}
        </select>
      </div>

      <div className="h-64 w-full">
        <Plot
          data={data}
          layout={{
            autosize: true,
            margin: { l: 45, r: 10, t: 10, b: 35 },
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            xaxis: {
              title: { text: 'Lead Day', font: { size: 11, color: '#536273' } },
              gridcolor: '#EDEBE4',
              zerolinecolor: '#EDEBE4',
              tickfont: { color: '#536273', size: 10 },
              linecolor: '#E2DFD5',
            },
            yaxis: {
              title: { text: 'Precip (mm)', font: { size: 11, color: '#536273' } },
              gridcolor: '#EDEBE4',
              zerolinecolor: '#EDEBE4',
              tickfont: { color: '#536273', size: 10 },
              linecolor: '#E2DFD5',
            },
            showlegend: true,
            legend: {
              orientation: 'h',
              yanchor: 'bottom',
              y: 1.02,
              xanchor: 'right',
              x: 1,
              font: { color: '#3D3D3D', size: 10 },
            },
            shapes: [
              {
                type: 'line',
                x0: leadDay,
                x1: leadDay,
                y0: 0,
                y1: 1,
                yref: 'paper',
                line: { color: '#C62828', width: 1.5, dash: 'dot' },
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
