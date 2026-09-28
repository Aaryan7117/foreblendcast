import React from 'react';
import { MapContainer, TileLayer, ZoomControl } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { RasterLayer } from './RasterLayer';
import { useResults } from '../hooks/useResults';
import type { DistrictsResult } from '../types/results';
import { useAppStore } from '../store';

const RAINFALL_LEGEND = [
  { value: '0', color: '#F7FCF0' },
  { value: '10', color: '#C7E9C0' },
  { value: '50', color: '#74C476' },
  { value: '100', color: '#FEB24C' },
  { value: '200', color: '#F03B20' },
  { value: '300+', color: '#BD0026' },
];

export const DistrictMap: React.FC = () => {
  const { leadDay, mapMode, setMapMode } = useAppStore();
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
            Rainfall Forecast (Calibrated Blend)
          </h3>
          <span className="block text-[11px] text-textMuted font-medium mt-0.5">
            24h Accumulation • Lead Day {leadDay} (L+{leadDay * 24}h)
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
          IMD Hazard Alert Tiers
        </h4>
        <div className="flex flex-col gap-1.5 text-[11px] font-medium">
          <div className="flex items-center gap-2 text-textMain">
            <div className="w-2.5 h-2.5 rounded-full bg-tier-red shadow-xs" /> Red (&gt;204.4 mm)
          </div>
          <div className="flex items-center gap-2 text-textMain">
            <div className="w-2.5 h-2.5 rounded-full bg-tier-orange shadow-xs" /> Orange (115.6–204.4 mm)
          </div>
          <div className="flex items-center gap-2 text-textMain">
            <div className="w-2.5 h-2.5 rounded-full bg-tier-yellow shadow-xs" /> Yellow (64.5–115.5 mm)
          </div>
          <div className="flex items-center gap-2 text-textMain">
            <div className="w-2.5 h-2.5 rounded-full bg-tier-green shadow-xs" /> Green (Normal)
          </div>
        </div>
      </div>
    </div>
  );
};
