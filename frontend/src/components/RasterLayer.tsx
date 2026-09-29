import React, { useEffect, useState } from 'react';
import { ImageOverlay } from 'react-leaflet';
import type { LatLngBoundsExpression } from 'leaflet';
import { useAppStore } from '../store';
import type { LayerId, ModelId } from '../store';
import { useLiveRaster } from '../hooks/useLiveRaster';

// Raster the pipeline writes for every layer / model combination.
export function rasterName(layer: LayerId, model: ModelId, leadDay: number): string {
  if (layer === 'exceedance') return `p_gt_64p5_L${leadDay}.png`;
  if (layer === 'disagreement') return `disagreement_L${leadDay}.png`;
  if (layer === 'risk_tiers') return `tier_L${leadDay}.png`;
  if (model === 'blend') return `precip_pm_L${leadDay}.png`;
  return `precip_${model}_L${leadDay}.png`;
}

export const RasterLayer: React.FC = () => {
  const { leadDay, isLiveBlenderEnabled, activeLayer, selectedModel, rasterOverride } = useAppStore();
  const [bounds, setBounds] = useState<LatLngBoundsExpression | null>(null);
  const { dataUri } = useLiveRaster(leadDay);

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

  const live = isLiveBlenderEnabled && dataUri && activeLayer === 'rainfall';
  const url = rasterOverride
    ? `/data/rasters/${rasterOverride}`
    : leadDay === 0
    ? '/data/rasters/truth.png'
    : (live ? dataUri : `/data/rasters/${rasterName(activeLayer, selectedModel, leadDay)}`);

  return (
    <ImageOverlay
      key={url}
      url={url}
      bounds={bounds}
      opacity={0.7}
      zIndex={10}
    />
  );
};
