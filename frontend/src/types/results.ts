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
  ground_truth_detail?: string;
  train_years?: number[];
  regimes?: Record<string, string>;
  season?: string;
  tier_probability_thresholds?: Record<string, number>;
  hazard_definitions?: Record<string, string>;
  temperature_definition?: string;
}

export interface MetricValues {
  rmse: number | null;
  mae: number | null;
  bias?: number | null;
  fss50?: number | null;
  freq_bias_64p5?: number | null;
  rev_cl0p1: number | null;
  brier?: number | null;
  n_days?: number;
  ci_rmse_vs_best_single?: [number | null, number | null];
  ci_rmse_vs_equal_weight?: [number | null, number | null];
}

export interface LadderRow {
  rung: "floor" | "baseline" | "single" | "ablation" | "blend" | "ceiling";
  strategy: string;
  metrics: Record<string, MetricValues>; // keyed by lead e.g., "L1", "L3"
}

export interface LadderHeadline {
  best_single: string;
  ours: string;
  pct_of_achievable_gain: Record<string, number>;
  rmse_strategy?: string;
  rmse_change_vs_equal_weight_pct?: Record<string, number>;
  rmse_change_vs_best_single_pct?: Record<string, number>;
  test_years?: number[];
}

export interface LadderResult {
  meta: MetaBlock;
  variable: string;
  lead_days: number[];
  rows: LadderRow[];
  headline: LadderHeadline;
  fss_scale_km?: number;
  units?: string;
}

export interface DistrictEntry {
  id: string;
  name: string;
  state: string;
  precip_p90_mm: number;
  region?: string;
  tmax_c: number | null;
  wind_ms: number | null;
  high_wind?: boolean;
  p_heatwave?: number;
  p_hot_40?: number;
  p_wind_8?: number;
  t2m_anomaly_c?: number;
  precip_q05_mm?: number;
  precip_q95_mm?: number;
  regime?: string;
  season?: string;
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
    lambda?: number;
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
  significant?: boolean;
  loss_pct?: number;
  n_days?: number;
  reason: string;
  override_available: boolean;
}

export interface WhereWeLoseResult {
  meta: MetaBlock;
  summary?: {
    contexts_tested: number;
    contexts_lost: number;
    contexts_lost_significantly: number;
  };
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

export interface AblationLead {
  deterministic: { step: string; strategy: string; rmse: number; mae: number; rmse_change_vs_previous_pct: number | null }[];
  probabilistic: {
    event: string;
    brier: Record<string, number>;
    crps: Record<string, number>;
    crps_change_vs_equal_weight_pct: number;
    crps_change_vs_raw_ensemble_pct: number;
    interval_90_coverage: number;
    selected_interval_90_coverage?: number;
    quantile_methods?: {
      selected: string;
      test_crps_7_levels: Record<string, number>;
      test_crps_change_lightgbm_vs_table_pct: number;
    };
  };
}

export interface SummaryResult {
  meta: MetaBlock;
  test_years: number[];
  variables: Record<string, {
    units: string;
    headline: LadderHeadline;
    ablation: Record<string, AblationLead>;
    where_we_lose: { contexts_tested: number; contexts_lost: number; contexts_lost_significantly: number };
  }>;
}

export interface WeightsExplainEntry {
  national_weights_applied: Record<string, number>;
  national_train_rmse: Record<string, number>;
  tau: number;
  shrink_k: number;
  train_years: number[];
  formula: string;
  model_status: Record<string, string>;
  regions: Record<string, {
    label: string;
    season: string;
    regime: string;
    weights_applied: Record<string, number>;
    train_rmse: Record<string, number>;
    train_days: number;
  }>;
}

export interface WeightsExplainResult {
  meta: MetaBlock;
  leads: Record<string, Record<string, WeightsExplainEntry>>;
}
