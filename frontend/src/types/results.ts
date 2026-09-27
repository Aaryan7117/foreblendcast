export interface MetaBlock {
  cycle: string;
  generated_utc: string;
  git_commit: string;
  fixture: boolean;
  ground_truth: string;
  models_used: string[];
  availability_pattern: string;
  strategy: string;
  accumulation_window_utc: string;
  district_aggregation: string;
  status: string;
}

export interface MetricValues {
  rmse: number;
  mae: number;
  fss50: number;
  freq_bias_64p5: number;
  rev_cl0p1: number;
  ci_rmse_vs_best_single?: [number, number];
}

export interface LadderRow {
  rung: "floor" | "single" | "blend" | "ceiling";
  strategy: string;
  metrics: Record<string, MetricValues>; // keyed by lead e.g., "L1", "L3"
}

export interface LadderHeadline {
  best_single: string;
  ours: string;
  pct_of_achievable_gain: Record<string, number>;
}

export interface LadderResult {
  meta: MetaBlock;
  variable: string;
  lead_days: number[];
  rows: LadderRow[];
  headline: LadderHeadline;
}

export interface DistrictEntry {
  id: string;
  name: string;
  state: string;
  precip_p90_mm: number;
  tmax_c: number;
  wind_ms: number;
  p_gt_64p5: number;
  p_gt_115p6: number;
  p_gt_204p5: number;
  tier: "green" | "yellow" | "orange" | "red";
  heatwave: boolean;
  population: number;
  population_source: string;
  disagreement: number;
  weights: Record<string, number>;
  lomo_rmse_increase_pct: Record<string, number>;
  shrinkage: {
    level_used: string;
    n_eff: number;
    reason: string;
  };
}

export interface DistrictsResult {
  meta: MetaBlock;
  lead_day: number;
  districts: DistrictEntry[];
}

export interface PointsResult {
  meta: MetaBlock;
  city: string;
  lat: number;
  lon: number;
  variable: string;
  lead_days: number[];
  members: Record<string, (number | null)[]>;
  blend: (number | null)[];
  q05: (number | null)[];
  q95: (number | null)[];
  disagreement: number[];
  obs: (number | null)[];
}

export interface WhereWeLoseCell {
  district: string;
  lead_day: number;
  season: string;
  regime: string;
  blend_rmse: number;
  best_single: string;
  best_single_rmse: number;
  ci: [number, number];
  reason: string;
  override_available: boolean;
}

export interface WhereWeLoseResult {
  meta: MetaBlock;
  cells: WhereWeLoseCell[];
}

export interface RevResult {
  meta: MetaBlock;
  cost_loss: number[];
  curves: Record<string, number[]>;
  headline_cl: number;
}

export interface ReliabilityResult {
  meta: MetaBlock;
  threshold_mm: number;
  bins: number[];
  observed_freq: Record<string, number[]>;
  counts: Record<string, number[]>;
  brier?: Record<string, number>;
  auc?: Record<string, number>;
}

export interface FssCurveResult {
  meta: MetaBlock;
  threshold_mm: number;
  scales_km: number[];
  neighbourhoods?: number[];
  f0: number;
  fss_useful: number;
  curves: Record<string, number[]>;
}
