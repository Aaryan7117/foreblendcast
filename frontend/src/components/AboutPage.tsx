import React from 'react';

export const AboutPage: React.FC = () => {
  return (
    <div className="h-full overflow-y-auto custom-scrollbar p-6 bg-background">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Hero */}
        <div className="bg-surface rounded-card border border-border p-8 shadow-card hover:shadow-cardHover transition-shadow duration-200">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="text-xs bg-emerald-100 text-brand-forest px-2.5 py-1 rounded-md font-bold tracking-wide">
              SIH26081
            </span>
            <span className="text-xs bg-slate-100 text-slate-700 px-2.5 py-1 rounded-md font-medium">
              Theme: Disaster Management
            </span>
            <span className="text-xs bg-emerald-50 text-emerald-800 border border-emerald-200 px-2.5 py-1 rounded-md font-semibold">
              MoES & NCMRWF
            </span>
          </div>
          <h1 className="text-3xl font-extrabold text-textMain tracking-tight">
            Fore<span className="text-brand-forest">Blend</span><span className="text-brand-leaf">Cast</span>
          </h1>
          <p className="text-base sm:text-lg text-textMuted max-w-2xl leading-relaxed mt-2">
            Hybrid AI–NWP Multi-Model Forecast Blending & Calibrated Disaster Risk Early Warning System
          </p>
        </div>

        {/* What is ForeBlendCast */}
        <div className="bg-surface rounded-card border border-border p-6 shadow-card hover:shadow-cardHover transition-shadow duration-200">
          <h2 className="text-lg font-bold text-textMain mb-3">System Architecture & Capabilities</h2>
          <p className="text-sm text-textMuted leading-relaxed mb-4">
            ForeBlendCast is a prototype multi-model forecast blending system designed for the Ministry of Earth Sciences (MoES) and NCMRWF. It synthesizes numerical weather prediction (NWP) models (ECMWF IFS HRES, ECMWF IFS ENS) with state-of-the-art AI-driven atmospheric models (Google DeepMind GraphCast) to produce calibrated, probabilistic rainfall, temperature and wind forecasts and district-level risk tiers across India. It runs retrospectively on the WeatherBench2 archive (2018, 2020, 2022).
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-surfaceHighlight rounded-lg p-4 border border-border hover:border-slate-300 hover:shadow-xs transition-all duration-150">
              <h3 className="text-sm font-bold text-textMain mb-1.5 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-brand-forest" />
                Adaptive Spatial-Temporal Weighting
              </h3>
              <p className="text-xs text-textMuted leading-relaxed">
                Weights are calculated dynamically per district, per lead day, and per weather regime using empirical Bayes shrinkage to prevent overfitting while adapting to local topographic effects.
              </p>
            </div>
            <div className="bg-surfaceHighlight rounded-lg p-4 border border-border hover:border-slate-300 hover:shadow-xs transition-all duration-150">
              <h3 className="text-sm font-bold text-textMain mb-1.5 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-brand-forest" />
                Probability-Matched Blending (PM)
              </h3>
              <p className="text-xs text-textMuted leading-relaxed">
                Retains sharp, localized extreme rainfall gradients that traditional arithmetic averaging smoothes out, matching the blended CDF to the combined ensemble distribution.
              </p>
            </div>
            <div className="bg-surfaceHighlight rounded-lg p-4 border border-border hover:border-slate-300 hover:shadow-xs transition-all duration-150">
              <h3 className="text-sm font-bold text-textMain mb-1.5 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-tier-orange" />
                Calibrated IMD Risk Classification
              </h3>
              <p className="text-xs text-textMuted leading-relaxed">
                All 700+ districts are categorized into Green, Yellow, Orange, and Red alert tiers from calibrated probabilities of exceeding the IMD rainfall categories (64.5 mm, 115.6 mm, 204.5 mm). Probability thresholds are tuned on training years; population exposure is reported alongside.
              </p>
            </div>
            <div className="bg-surfaceHighlight rounded-lg p-4 border border-border hover:border-slate-300 hover:shadow-xs transition-all duration-150">
              <h3 className="text-sm font-bold text-textMain mb-1.5 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-brand-navy" />
                Leave-One-Model-Out (LOMO) Sensitivity
              </h3>
              <p className="text-xs text-textMuted leading-relaxed">
                Evaluates warning tier robustness if any single model drops out or disagrees, providing actionable confidence bounds for disaster response planners.
              </p>
            </div>
          </div>
        </div>

        {/* Institutional Stakeholders */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-surface rounded-card border border-border p-6 shadow-card hover:shadow-cardHover transition-shadow duration-200">
            <div className="flex items-center gap-3 mb-3">
              <div className="bg-white p-1.5 rounded-lg border border-slate-200 shadow-xs flex-shrink-0">
                <img
                  src="/logos/moes-logo.png"
                  alt="Ministry of Earth Sciences"
                  className="h-10 w-auto object-contain"
                  style={{ aspectRatio: '425 / 136' }}
                />
              </div>
              <div>
                <h2 className="text-base font-bold text-textMain leading-tight">Ministry of Earth Sciences</h2>
                <span className="text-[11px] text-textMuted font-medium">Government of India</span>
              </div>
            </div>
            <p className="text-sm text-textMuted leading-relaxed">
              The Ministry of Earth Sciences (MoES), Government of India, is mandated to provide services for weather, climate, ocean and coastal state, hydrology, seismology, and natural hazards. It oversees nodal bodies including IMD, NCMRWF, and IITM.
            </p>
          </div>

          <div className="bg-surface rounded-card border border-border p-6 shadow-card hover:shadow-cardHover transition-shadow duration-200">
            <div className="flex items-center gap-3 mb-3">
              <div className="bg-white p-1.5 rounded-lg border border-slate-200 shadow-xs flex-shrink-0">
                <img
                  src="/logos/ncmrwf-logo.png"
                  alt="NCMRWF"
                  className="h-10 w-auto object-contain"
                  style={{ aspectRatio: '370 / 383' }}
                />
              </div>
              <div>
                <h2 className="text-base font-bold text-textMain leading-tight">NCMRWF</h2>
                <span className="text-[11px] text-textMuted font-medium">National Centre for Medium Range Weather Forecasting</span>
              </div>
            </div>
            <p className="text-sm text-textMuted leading-relaxed">
              NCMRWF is a premier scientific research institution under MoES focused on continuously improving numerical weather prediction (NWP) systems for medium-range horizons (3–10 days) across the Indian monsoon domain.
            </p>
          </div>
        </div>

        {/* Tech stack */}
        <div className="bg-surface rounded-card border border-border p-6 shadow-card hover:shadow-cardHover transition-shadow duration-200">
          <h2 className="text-lg font-bold text-textMain mb-3">Technology Stack</h2>
          <div className="flex flex-wrap gap-2">
            {[
              'React 19', 'TypeScript', 'Leaflet', 'Plotly.js', 'Tailwind CSS', 'Vite',
              'Python (Backend Read-Only)', 'xarray', 'NumPy', 'scikit-learn', 'LightGBM', 'WeatherBench 2'
            ].map(t => (
              <span key={t} className="text-xs bg-surfaceHighlight text-textMuted px-3 py-1.5 rounded-md border border-border font-medium hover:border-slate-300 transition-colors">
                {t}
              </span>
            ))}
          </div>
        </div>

        {/* Disclaimer */}
        <div className="bg-tier-yellowBg border border-tier-yellow/30 rounded-card p-4">
          <p className="text-xs text-textMuted leading-relaxed">
            <strong className="text-textMain">Official Notice:</strong> Prototype system developed for Smart India Hackathon 2026 (SIH26081). Verified against ECMWF ERA5 reanalysis on the 0.25° grid; no IMD gridded observations are used. ERA5 favours models trained on it (GraphCast, Pangu-Weather) and under-represents extreme rainfall. Temperature is the 12 UTC value, a proxy for the daily maximum.
          </p>
        </div>
      </div>
    </div>
  );
};
