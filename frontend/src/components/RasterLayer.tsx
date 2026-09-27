import React, { useEffect, useState } from 'react';
import { ImageOverlay } from 'react-leaflet';
import type { LatLngBoundsExpression } from 'leaflet';
import { useAppStore } from '../store';

export const RasterLayer: React.FC = () => {
  // const map = useMap();
  const { leadDay } = useAppStore();
  const [bounds, setBounds] = useState<LatLngBoundsExpression | null>(null);

  useEffect(() => {
    fetch('/data/rasters/bounds.json')
      .then(res => res.json())
      .then(data => {
        setBounds([
          [data.south, data.west],
          [data.north, data.east]
        ]);
      })
      .catch(console.error);
  }, []);

  if (!bounds) return null;

  return (
    <ImageOverlay
      url={`/data/rasters/precip_pm_L${leadDay}.png`}
      bounds={bounds}
      opacity={0.7}
      zIndex={10}
    />
  );
};
