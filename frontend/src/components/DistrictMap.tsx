import React from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { RasterLayer } from './RasterLayer';
import { useResults } from '../hooks/useResults';
import type { DistrictsResult } from '../types/results';
import { useAppStore } from '../store';

export const DistrictMap: React.FC = () => {
  const { leadDay } = useAppStore();
  const { data: _districts } = useResults<DistrictsResult>(`districts_L${leadDay}.json`);

  return (
    <div className="h-full w-full bg-surfaceHighlight rounded-xl border border-surfaceHighlight overflow-hidden relative shadow-lg">
      <MapContainer 
        center={[22.0, 79.0]} 
        zoom={5} 
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png"
          attribution='&copy; OpenStreetMap contributors &copy; CARTO'
        />
        <RasterLayer />
        
        {/* We would render GeoJSON districts here if we had the static shapes */}
      </MapContainer>
      
      {/* Legend overlay */}
      <div className="absolute bottom-4 right-4 z-[400] bg-surface/90 p-3 rounded-lg border border-surfaceHighlight backdrop-blur-md">
        <h4 className="text-xs font-bold uppercase tracking-wider text-textMuted mb-2">Tiers</h4>
        <div className="flex flex-col gap-1.5 text-xs">
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-tier-red"></div> Red (Extreme)</div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-tier-orange"></div> Orange (Very Heavy)</div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-tier-yellow"></div> Yellow (Heavy)</div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-tier-green"></div> Green (Normal)</div>
        </div>
      </div>
    </div>
  );
};
