import React, { useState } from 'react';
import Plot from 'react-plotly.js';
import { useResults } from '../hooks/useResults';
import type { PointsResult } from '../types/results';
import { useAppStore } from '../store';

const CITIES = ['mumbai', 'chennai', 'kolkata', 'delhi', 'guwahati'];

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
    y: [...points.q95, ...[...points.q05].reverse()],
    fill: 'toself',
    fillcolor: 'rgba(59, 130, 246, 0.2)', // blue-500 at 20%
    line: { color: 'transparent' },
    name: '90% CI',
    showlegend: true,
    hoverinfo: 'none'
  });

  // Individual members
  Object.entries(points.members).forEach(([model, values]) => {
    data.push({
      x: xDays,
      y: values,
      mode: 'lines',
      line: { 
        width: 1, 
        color: 'rgba(148, 163, 184, 0.4)' // textMuted
      },
      name: model,
      showlegend: false,
      hoverinfo: 'none'
    });
  });

  // Blend (thick line)
  data.push({
    x: xDays,
    y: points.blend,
    mode: 'lines+markers',
    line: { color: '#3B82F6', width: 3 }, // blue-500
    marker: { size: 6, color: '#3B82F6' },
    name: 'Our Blend',
    hovertemplate: 'Day %{x}: %{y:.1f}mm<extra></extra>'
  });

  return (
    <div className="bg-surfaceHighlight p-4 rounded-xl border border-surfaceHighlight">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold tracking-wide">Plume (City Focus)</h2>
        <select 
          value={citySlug}
          onChange={e => setCitySlug(e.target.value)}
          className="bg-surface border border-surfaceHighlight text-sm rounded px-3 py-1 outline-none focus:border-blue-500"
        >
          {CITIES.map(c => (
            <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
          ))}
        </select>
      </div>

      <div className="h-64 w-full">
        <Plot
          data={data}
          layout={{
            autosize: true,
            margin: { l: 40, r: 10, t: 10, b: 30 },
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            xaxis: { 
              title: 'Lead Day',
              gridcolor: '#2A344F',
              zerolinecolor: '#2A344F',
              tickfont: { color: '#94A3B8' },
              titlefont: { color: '#94A3B8' }
            },
            yaxis: { 
              title: 'Precip (mm)',
              gridcolor: '#2A344F',
              zerolinecolor: '#2A344F',
              tickfont: { color: '#94A3B8' },
              titlefont: { color: '#94A3B8' }
            },
            showlegend: true,
            legend: {
              orientation: 'h',
              yanchor: 'bottom',
              y: 1.02,
              xanchor: 'right',
              x: 1,
              font: { color: '#E2E8F0' }
            },
            shapes: [
              {
                type: 'line',
                x0: leadDay,
                x1: leadDay,
                y0: 0,
                y1: 1,
                yref: 'paper',
                line: { color: '#EF4444', width: 2, dash: 'dot' } // Red line for current lead day
              }
            ]
          }}
          useResizeHandler={true}
          style={{ width: '100%', height: '100%' }}
          config={{ displayModeBar: false }}
        />
      </div>
    </div>
  );
};
