import React from 'react';
import { MapContainer, TileLayer, ZoomControl } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { RasterLayer } from './RasterLayer';
import { useResults } from '../hooks/useResults';
import type { DistrictsResult } from '../types/results';
import { useAppStore } from '../store';

const LAYER_TITLE = {
  rainfall: 'Rainfall Forecast',
  exceedance: 'Calibrated P(rain ≥ 64.5 mm)',
  disagreement: 'Model Disagreement Index',
  risk_tiers: 'District Risk Tiers',
};
const MODEL_TITLE = {
  blend: 'Adaptive Blend',
  hres: 'ECMWF HRES',
  ens: 'ECMWF ENS mean',
  graphcast: 'GraphCast',
  baseline: 'Equal-Weight Mean',
};

// matplotlib "Blues" over 0–200 mm, the colormap outputs/render_png.py uses
const RAINFALL_LEGEND = [
  { value: '0', color: '#F7FBFF' },
  { value: '40', color: '#D0E1F2' },
  { value: '80', color: '#94C4DF' },
  { value: '120', color: '#4A98C9' },
  { value: '160', color: '#1764AB' },
  { value: '200+', color: '#08306B' },
];

export const DistrictMap: React.FC = () => {
  const { leadDay, mapMode, setMapMode, activeLayer, selectedModel, rasterOverride } = useAppStore();
  const { data: _districts } = useResults<DistrictsResult>(`districts_L${leadDay}.json`);

  // Public, keyless basemaps (Zero CARTO dependencies, zero red watermarks)
  const tileUrl = mapMode === 'satellite'
    ? 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
    : 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';

  const attribution = mapMode === 'satellite'
    ? 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP'
    : '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors';

  return (
    <div className="h-full w-full bg-surfaceHighlight rounded-card border border-border overflow-hidden relative shadow-card">
      {/* Map title overlay with subtle hover */}
      <div className="absolute top-3 left-3 z-[400] transition-all duration-200">
        <div className="bg-surface/95 backdrop-blur-md px-3.5 py-2 rounded-lg border border-border shadow-sm hover:shadow-md transition-shadow">
          <h3 className="text-sm font-semibold text-textMain flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-brand-forest" />
            {LAYER_TITLE[activeLayer]}{activeLayer === 'rainfall' ? ` (${MODEL_TITLE[selectedModel]})` : ''}
          </h3>
          <span className="block text-[11px] text-textMuted font-medium mt-0.5">
            {rasterOverride ? 'Event replay' : `24h Accumulation • Lead Day ${leadDay} (L+${leadDay * 24}h)`}
          </span>
        </div>
      </div>

      {/* Map/Satellite toggle with polished interactive hover */}
      <div className="absolute top-3 right-3 z-[400] flex bg-surface/95 backdrop-blur-md border border-border rounded-lg p-0.5 shadow-sm">
        <button
          onClick={() => setMapMode('map')}
          className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all duration-150 ${
            mapMode === 'map'
              ? 'bg-brand-forest text-white shadow-xs'
              : 'text-textMuted hover:text-textMain hover:bg-slate-100'
          }`}
          title="Switch to Standard OpenStreetMap"
        >
          Map (OSM)
        </button>
        <button
          onClick={() => setMapMode('satellite')}
          className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all duration-150 ${
            mapMode === 'satellite'
              ? 'bg-brand-forest text-white shadow-xs'
              : 'text-textMuted hover:text-textMain hover:bg-slate-100'
          }`}
          title="Switch to Esri Satellite Imagery"
        >
          Satellite
        </button>
      </div>

      {/* Leaflet MapContainer with pure OpenStreetMap/Esri basemap (NO CARTO) */}
      <MapContainer
        center={[22.0, 79.0]}
        zoom={5}
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
      >
        <ZoomControl position="topleft" />
        <TileLayer
          key={mapMode}
          url={tileUrl}
          attribution={attribution}
          maxZoom={mapMode === 'satellite' ? 18 : 19}
        />
        <RasterLayer />
      </MapContainer>

      {/* Rainfall intensity legend */}
      <div className="absolute bottom-4 left-4 z-[400] bg-surface/95 backdrop-blur-md p-3 rounded-lg border border-border shadow-sm hover:shadow-md transition-shadow">
        <h4 className="text-[10px] font-bold uppercase tracking-wider text-textMuted mb-2">
          Rainfall Intensity (mm/day)
        </h4>
        <div className="flex items-center gap-0">
          {RAINFALL_LEGEND.map((item, idx) => (
            <div key={idx} className="flex flex-col items-center">
              <div
                className="w-7 sm:w-8 h-3.5 first:rounded-l-sm last:rounded-r-sm border-y border-slate-300"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-[9px] font-medium text-textMuted mt-1">{item.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* IMD Hazard Tier legend */}
      <div className="absolute bottom-4 right-4 z-[400] bg-surface/95 backdrop-blur-md p-3 rounded-lg border border-border shadow-sm hover:shadow-md transition-shadow">
        <h4 className="text-[10px] font-bold uppercase tracking-wider text-textMuted mb-2">
          Alert Tiers (probability of)
        </h4>
        <div className="flex flex-col gap-1.5 text-[11px] font-medium">
          <div className="flex items-center gap-2 text-textMain">
            <div className="w-2.5 h-2.5 rounded-full bg-tier-red shadow-xs" /> Red (≥204.5 mm)
          </div>
          <div className="flex items-center gap-2 text-textMain">
            <div className="w-2.5 h-2.5 rounded-full bg-tier-orange shadow-xs" /> Orange (≥115.6 mm)
          </div>
          <div className="flex items-center gap-2 text-textMain">
            <div className="w-2.5 h-2.5 rounded-full bg-tier-yellow shadow-xs" /> Yellow (≥64.5 mm)
          </div>
          <div className="flex items-center gap-2 text-textMain">
            <div className="w-2.5 h-2.5 rounded-full bg-tier-green shadow-xs" /> Green (Normal)
          </div>
        </div>
      </div>
    </div>
  );
};
