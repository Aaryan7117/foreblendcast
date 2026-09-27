const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '..', 'public', 'data');

const meta = {
  cycle: "2022-07-15T00Z",
  generated_utc: new Date().toISOString(),
  git_commit: "fixture",
  fixture: true,
  ground_truth: "IMD_0p25_rain|ERA5",
  models_used: ["gfs", "ecmwf", "graphcast"],
  availability_pattern: "full",
  strategy: "context_shrink_pm",
  accumulation_window_utc: "03:00-03:00",
  district_aggregation: "area_weighted_p90",
  status: "EXERCISE - NOT AN OFFICIAL IMD WARNING"
};

function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}
ensureDir(DATA_DIR);
ensureDir(path.join(DATA_DIR, 'points'));
ensureDir(path.join(DATA_DIR, 'rasters'));

// ladder.json
const ladder = {
  meta,
  variable: "precip",
  lead_days: [1, 3, 5, 7, 10],
  rows: [
    {
      rung: "floor", strategy: "climatology", metrics: {
        L1: { rmse: 1.0, mae: 1.0, fss50: 0.5, freq_bias_64p5: 1.0, rev_cl0p1: 0.0, ci_rmse_vs_best_single: [0, 0] },
        L3: { rmse: 1.0, mae: 1.0, fss50: 0.5, freq_bias_64p5: 1.0, rev_cl0p1: 0.0, ci_rmse_vs_best_single: [0, 0] }
      }
    },
    {
      rung: "single", strategy: "gfs", metrics: {
        L1: { rmse: 0.8, mae: 0.8, fss50: 0.6, freq_bias_64p5: 1.0, rev_cl0p1: 0.2, ci_rmse_vs_best_single: [0, 0] },
        L3: { rmse: 0.8, mae: 0.8, fss50: 0.6, freq_bias_64p5: 1.0, rev_cl0p1: 0.2, ci_rmse_vs_best_single: [0, 0] }
      }
    },
    {
      rung: "blend", strategy: "context_shrink_pm", metrics: {
        L1: { rmse: 0.5, mae: 0.5, fss50: 0.8, freq_bias_64p5: 1.0, rev_cl0p1: 0.6, ci_rmse_vs_best_single: [0.1, 0.2] },
        L3: { rmse: 0.5, mae: 0.5, fss50: 0.8, freq_bias_64p5: 1.0, rev_cl0p1: 0.6, ci_rmse_vs_best_single: [0.1, 0.2] }
      }
    },
    {
      rung: "ceiling", strategy: "oracle", metrics: {
        L1: { rmse: 0.2, mae: 0.2, fss50: 0.9, freq_bias_64p5: 1.0, rev_cl0p1: 0.9, ci_rmse_vs_best_single: [0, 0] },
        L3: { rmse: 0.2, mae: 0.2, fss50: 0.9, freq_bias_64p5: 1.0, rev_cl0p1: 0.9, ci_rmse_vs_best_single: [0, 0] }
      }
    }
  ],
  headline: {
    best_single: "gfs",
    ours: "context_shrink_pm",
    pct_of_achievable_gain: { L1: 75.0, L3: 70.0 }
  }
};
fs.writeFileSync(path.join(DATA_DIR, 'ladder.json'), JSON.stringify(ladder, null, 2));

// districts_L{lead}.json
const districtNames = ["MH-RATNAGIRI", "TN-CHENNAI", "DL-DELHI", "AS-KAMRUP", "WB-KOLKATA"];
[1, 3, 5, 7, 10].forEach(lead => {
  const districts = districtNames.map((id, i) => ({
    id,
    name: id.split('-')[1],
    state: id.split('-')[0],
    precip_p90_mm: 50 + i * 20,
    tmax_c: 30,
    wind_ms: 5,
    p_gt_64p5: 0.5,
    p_gt_115p6: 0.3,
    p_gt_204p5: 0.1,
    tier: ["green", "yellow", "orange", "red", "orange"][i],
    heatwave: false,
    population: 1000000 * (i + 1),
    population_source: "WorldPop 2020",
    disagreement: 1.2,
    weights: { gfs: 0.4, ecmwf: 0.4, graphcast: 0.2 },
    lomo_rmse_increase_pct: { gfs: 5, ecmwf: 6, graphcast: 2 },
    shrinkage: { level_used: "district", n_eff: 50, reason: "ok" }
  }));
  fs.writeFileSync(path.join(DATA_DIR, `districts_L${lead}.json`), JSON.stringify({ meta, lead_day: lead, districts }, null, 2));
});

// points/{city}.json
const cities = [
  { slug: "mumbai", name: "Mumbai", lat: 19.07, lon: 72.88 },
  { slug: "chennai", name: "Chennai", lat: 13.08, lon: 80.27 },
  { slug: "kolkata", name: "Kolkata", lat: 22.57, lon: 88.36 },
  { slug: "delhi", name: "Delhi", lat: 28.61, lon: 77.21 },
  { slug: "guwahati", name: "Guwahati", lat: 26.14, lon: 91.74 }
];
cities.forEach(c => {
  const arr = Array(10).fill(0).map(() => 50);
  const data = {
    meta, city: c.name, lat: c.lat, lon: c.lon, variable: "precip", lead_days: [1,2,3,4,5,6,7,8,9,10],
    members: { gfs: arr, ecmwf: arr, graphcast: arr },
    blend: arr, q05: arr.map(v => v * 0.5), q95: arr.map(v => v * 1.5),
    disagreement: Array(10).fill(1.5), obs: Array(10).fill(40)
  };
  fs.writeFileSync(path.join(DATA_DIR, 'points', `${c.slug}.json`), JSON.stringify(data, null, 2));
});

// where_we_lose.json
fs.writeFileSync(path.join(DATA_DIR, 'where_we_lose.json'), JSON.stringify({
  meta,
  cells: [{ district: "MH-RATNAGIRI", lead_day: 3, season: "JJAS", regime: "active", blend_rmse: 10, best_single: "ecmwf", best_single_rmse: 8, ci: [1, 3], reason: "shrinkage_to_national", override_available: true }]
}, null, 2));

// curves
fs.writeFileSync(path.join(DATA_DIR, 'rev.json'), JSON.stringify({ meta, cost_loss: [0.1], curves: { blend: [0.5], ecmwf: [0.4], gfs: [0.3] }, headline_cl: 0.1 }, null, 2));
fs.writeFileSync(path.join(DATA_DIR, 'reliability.json'), JSON.stringify({ meta, threshold_mm: 64.5, bins: [0.5], observed_freq: { blend: [0.5] }, counts: { blend: [100] } }, null, 2));
fs.writeFileSync(path.join(DATA_DIR, 'fss_curve.json'), JSON.stringify({ meta, threshold_mm: 64.5, scales_km: [5, 25, 50, 100, 150], f0: 0.1, fss_useful: 0.55, curves: { blend: [0.6, 0.7, 0.8, 0.85, 0.9] } }, null, 2));

// bounds.json
fs.writeFileSync(path.join(DATA_DIR, 'rasters', 'bounds.json'), JSON.stringify({ north: 38.5, south: 6.5, east: 100, west: 66.5 }, null, 2));

console.log("Fixtures generated in public/data/");
