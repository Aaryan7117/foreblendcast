import React, { useEffect, useRef } from 'react';
import { useAppStore } from '../store';
import { useResults } from '../hooks/useResults';
import type { MetaBlock } from '../types/results';
import { DistrictMap } from './DistrictMap';
import { AlertTriangle, Eye, Navigation } from 'lucide-react';

interface ReplayStepData {
  lead_day: number;
  init: string;
  valid: string;
  raster: string;
  blend_peak_mm: number | null;
  member_peak_mm: Record<string, number | null>;
  max_p_gt_64p5: number | null;
  max_p_gt_115p6: number | null;
  mean_disagreement: number | null;
  tiers: Record<string, number>;
  verification?: { hits: number; misses: number; false_alarms: number; rmse_mm: number | null };
}

interface ReplayResult {
  meta: MetaBlock;
  event: string;
  target_date: string;
  states: string[];
  steps: ReplayStepData[];
  verification: {
    raster: string;
    observed_peak_mm: number | null;
    districts_with_heavy_rain: number;
    districts_in_focus: number;
    definition: string;
  } | null;
  note: string;
}

interface ReplayStep {
  raster: string;
  date: string;
  title: string;
  content: string;
  metrics: { label: string; value: string }[];
}

const mm = (x: number | null | undefined) => (x === null || x === undefined ? '—' : `${x.toFixed(0)} mm`);
const pct = (x: number | null | undefined) => (x === null || x === undefined ? '—' : `${(x * 100).toFixed(0)}%`);

// Every number shown comes from results/replay.json, written by the pipeline.
function buildSteps(replay: ReplayResult): ReplayStep[] {
  const where = replay.states.join(' & ');
  const steps: ReplayStep[] = replay.steps.map((s) => {
    const flagged = s.tiers.red + s.tiers.orange + s.tiers.yellow;
    const v = s.verification;
    return {
      raster: s.raster,
      date: `Cycle ${s.init} 00 UTC`,
      title: `Lead day ${s.lead_day}: forecast for ${s.valid}`,
      content:
        `Forecast issued from the ${s.init} cycle with weights frozen on earlier years. ` +
        `${flagged} of the ${where} districts are at yellow or above ` +
        `(${s.tiers.red} red, ${s.tiers.orange} orange, ${s.tiers.yellow} yellow).` +
        (v ? ` Verified afterwards: ${v.hits} hits, ${v.misses} misses, ${v.false_alarms} false alarms.` : ''),
      metrics: [
        { label: 'Blend peak', value: mm(s.blend_peak_mm) },
        { label: 'Max P(≥64.5 mm)', value: pct(s.max_p_gt_64p5) },
        { label: 'Max P(≥115.6 mm)', value: pct(s.max_p_gt_115p6) },
        { label: 'RMSE vs ERA5', value: v ? `${v.rmse_mm?.toFixed(1) ?? '—'} mm` : '—' },
        ...Object.entries(s.member_peak_mm).map(([m, x]) => ({ label: `${m.toUpperCase()} peak`, value: mm(x) })),
      ],
    };
  });
  if (replay.verification) {
    const v = replay.verification;
    steps.push({
      raster: v.raster,
      date: `Verification ${replay.target_date}`,
      title: 'What ERA5 recorded',
      content:
        `${v.districts_with_heavy_rain} of ${v.districts_in_focus} districts in ${where} had heavy rain ` +
        `(${v.definition}). ${replay.note}`,
      metrics: [
        { label: 'ERA5 peak', value: mm(v.observed_peak_mm) },
        { label: 'Districts with heavy rain', value: String(v.districts_with_heavy_rain) },
      ],
    });
  }
  return steps;
}

export const AssamReplay: React.FC = () => {
  const { setActiveLayer, setRasterOverride } = useAppStore();
  const { data: replay, error } = useResults<ReplayResult>('replay.json');
  const observerRef = useRef<IntersectionObserver | null>(null);
  const steps = replay ? buildSteps(replay) : [];

  // Default to rainfall layer when entering replay
  useEffect(() => {
    setActiveLayer('rainfall');
    return () => {
      setRasterOverride(null);
    };
  }, [setActiveLayer, setRasterOverride]);

  useEffect(() => {
    if (!replay) return;
    setRasterOverride(replay.steps[0]?.raster ?? null);
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-active');
            const raster = entry.target.getAttribute('data-raster');
            if (raster) {
              setRasterOverride(raster);
            }
          } else {
            entry.target.classList.remove('is-active');
          }
        });
      },
      {
        root: null,
        rootMargin: '-40% 0px -40% 0px', // Trigger when near the center of the viewport
        threshold: 0
      }
    );

    const stepElements = document.querySelectorAll('.replay-step');
    stepElements.forEach((el) => observerRef.current?.observe(el));

    return () => {
      observerRef.current?.disconnect();
    };
  }, [replay, setRasterOverride]);

  return (
    <div className="flex-1 flex overflow-hidden bg-background relative">
      {/* Left Sidebar: Narrative Text */}
      <div className="w-[450px] overflow-y-auto custom-scrollbar relative z-10 border-r border-border bg-surface/95 backdrop-blur-md shadow-xl flex flex-col">
        <div className="p-8 pb-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-brand-forest/10 text-brand-forest rounded-full text-xs font-bold uppercase tracking-wider mb-4 border border-brand-forest/20">
            <Eye size={14} />
            Out-of-Sample Replay
          </div>
          <h1 className="text-3xl font-black text-textMain tracking-tight mb-3">
            Assam–Meghalaya Floods
          </h1>
          <p className="text-sm text-textMuted leading-relaxed">
            {replay
              ? `Three successive forecast cycles for ${replay.target_date}. 2022 is a held-out test year: the weights were fitted on earlier years only. Scroll to move from the earliest cycle to the verification.`
              : error
              ? 'The replay has not been generated. Run the pipeline to create results/replay.json.'
              : 'Loading replay…'}
          </p>
        </div>

        <div className="flex-1 px-8 py-12 pb-96 space-y-48">
          {steps.map((step, idx) => (
            <div
              key={idx}
              className="replay-step relative opacity-40 transition-opacity duration-500 hover:opacity-100"
              data-raster={step.raster}
              style={{ minHeight: '300px' }}
            >
              <div className="absolute -left-10 top-0 h-full w-px bg-border">
                <div className="absolute top-4 -left-1.5 w-3 h-3 rounded-full bg-brand-forest border-2 border-surface" />
              </div>

              <div className="bg-surfaceHighlight border border-border p-6 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
                <div className="text-xs font-bold text-brand-forest tracking-wider uppercase mb-2">
                  {step.date}
                </div>
                <h3 className="text-xl font-bold text-textMain mb-4">
                  {step.title}
                </h3>
                <p className="text-textMuted text-sm leading-relaxed mb-6">
                  {step.content}
                </p>

                <div className="grid grid-cols-2 gap-3">
                  {step.metrics.map((m, i) => (
                    <div key={i} className="bg-background rounded-lg p-3 border border-border">
                      <div className="text-[10px] text-textLight uppercase tracking-wider font-semibold mb-1">
                        {m.label}
                      </div>
                      <div className="text-sm font-bold text-textMain">
                        {m.value}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right Map Area */}
      <div className="flex-1 relative bg-slate-900">
        <DistrictMap />

        {/* Helper overlay */}
        <div className="absolute bottom-6 right-6 z-[400] bg-surface/90 backdrop-blur px-4 py-3 rounded-xl border border-border shadow-lg flex items-center gap-3 animate-bounce">
          <Navigation size={18} className="text-brand-forest" />
          <span className="text-sm font-semibold text-textMain">
            Scroll narrative to advance time
          </span>
        </div>

        {/* Prototype Disclaimer */}
        <div className="absolute bottom-6 left-6 z-[400] max-w-sm">
           <div className="flex items-start gap-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-700 dark:text-red-400">
             <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" />
             <div className="text-xs font-medium leading-relaxed">
               [EXERCISE] — This is a prototype output for SIH26081. Not an official IMD warning. Do not use for real-life decisions.
             </div>
           </div>
        </div>
      </div>

      {/* Intersection Observer CSS effect */}
      <style>{`
        .replay-step.is-active {
          opacity: 1 !important;
          transform: scale(1.02);
        }
      `}</style>
    </div>
  );
};
