import { useEffect, useState } from 'react';
import { useAppStore } from '../store';

// A simple Blues colormap mapping (0 to 200 mm)
function getRainfallColor(value: number) {
  if (value < 0.5) return [255, 255, 255, 0]; // Transparent

  if (value < 10) {
    // 0 to 10: #F7FCF0 to #C7E9C0
    const f = value / 10;
    return [247 + f * (199 - 247), 252 + f * (233 - 252), 240 + f * (192 - 240), 255];
  } else if (value < 50) {
    // 10 to 50: #C7E9C0 to #74C476
    const f = (value - 10) / 40;
    return [199 + f * (116 - 199), 233 + f * (196 - 233), 192 + f * (118 - 192), 255];
  } else if (value < 100) {
    // 50 to 100: #74C476 to #FEB24C
    const f = (value - 50) / 50;
    return [116 + f * (254 - 116), 196 + f * (178 - 196), 118 + f * (76 - 118), 255];
  } else if (value < 200) {
    // 100 to 200: #FEB24C to #F03B20
    const f = (value - 100) / 100;
    return [254 + f * (240 - 254), 178 + f * (59 - 178), 76 + f * (32 - 76), 255];
  } else {
    // 200+: #BD0026
    return [189, 0, 38, 255];
  }
}

export function useLiveRaster(leadDay: number) {
  const { isLiveBlenderEnabled, liveWeights } = useAppStore();
  const [dataUri, setDataUri] = useState<string | null>(null);
  const [rmse, setRmse] = useState<number | null>(null);
  const [grids, setGrids] = useState<any>(null);

  useEffect(() => {
    if (!isLiveBlenderEnabled) {
      setDataUri(null);
      setRmse(null);
      return;
    }

    // Fetch the raw grids
    fetch(`/data/rasters/raw_grids_L${leadDay}.json`)
      .then(res => res.json())
      .then(data => {
        setGrids(data);
      })
      .catch(console.error);
  }, [isLiveBlenderEnabled, leadDay]);

  useEffect(() => {
    if (!isLiveBlenderEnabled || !grids) return;

    const { shape, land_mask, obs, models } = grids;
    const [rows, cols] = shape;
    
    // Normalize weights
    const totalW = liveWeights.hres + liveWeights.ens + liveWeights.graphcast;
    const w1 = totalW > 0 ? liveWeights.hres / totalW : 0;
    const w2 = totalW > 0 ? liveWeights.ens / totalW : 0;
    const w3 = totalW > 0 ? liveWeights.graphcast / totalW : 0;

    // Create canvas
    const canvas = document.createElement('canvas');
    canvas.width = cols;
    canvas.height = rows;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const imgData = ctx.createImageData(cols, rows);

    let mseSum = 0;
    let mseCount = 0;

    const hres = models.hres;
    const ens = models.ens;
    const graphcast = models.graphcast;

    for (let i = 0; i < hres.length; i++) {
      // Calculate blend
      let h = hres[i] !== null ? hres[i] : 0;
      let e = ens[i] !== null ? ens[i] : 0;
      let g = graphcast[i] !== null ? graphcast[i] : 0;
      let blend = w1 * h + w2 * e + w3 * g;

      // RMSE
      if (land_mask[i] === 1 && obs && obs[i] !== null) {
        mseSum += Math.pow(blend - obs[i], 2);
        mseCount++;
      }

      // Draw (note: frontend canvas Y goes down, but lat/lon grids usually have Y go up)
      // If the backend exported [::-1] then we don't need to flip.
      // We will flip Y to match matplotlib behaviour if needed. Let's flip it by default:
      const row = rows - 1 - Math.floor(i / cols);
      const col = i % cols;
      const idx = (row * cols + col) * 4;

      const [r, g_col, b, a] = getRainfallColor(blend);
      imgData.data[idx] = r;
      imgData.data[idx + 1] = g_col;
      imgData.data[idx + 2] = b;
      imgData.data[idx + 3] = a;
    }

    ctx.putImageData(imgData, 0, 0);
    setDataUri(canvas.toDataURL('image/png'));
    
    if (mseCount > 0) {
      setRmse(Math.sqrt(mseSum / mseCount));
    }
  }, [grids, isLiveBlenderEnabled, liveWeights]);

  return { dataUri, rmse };
}
