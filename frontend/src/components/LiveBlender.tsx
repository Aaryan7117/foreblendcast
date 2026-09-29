import React from 'react';
import { useAppStore } from '../store';
import { useLiveRaster } from '../hooks/useLiveRaster';
import { Settings2, Zap } from 'lucide-react';

export const LiveBlender: React.FC = () => {
  const { 
    isLiveBlenderEnabled, 
    setIsLiveBlenderEnabled, 
    liveWeights, 
    setLiveWeights,
    leadDay
  } = useAppStore();
  
  const { rmse } = useLiveRaster(leadDay);

  const handleWeightChange = (model: keyof typeof liveWeights, value: number) => {
    setLiveWeights({ ...liveWeights, [model]: value / 100 });
  };

  return (
    <div className="mt-6 border border-brand-primary/20 rounded-lg bg-surface Highlight p-3">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-textMain flex items-center gap-1.5">
          <Settings2 size={16} className="text-brand-primary" />
          Live Forecaster Override
        </h3>
        <label className="relative inline-flex items-center cursor-pointer">
          <input 
            type="checkbox" 
            className="sr-only peer" 
            checked={isLiveBlenderEnabled}
            onChange={(e) => setIsLiveBlenderEnabled(e.target.checked)}
          />
          <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-brand-primary"></div>
        </label>
      </div>
      
      {isLiveBlenderEnabled ? (
        <div className="space-y-4">
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs font-medium text-textMain mb-1">
                <span>HRES</span>
                <span>{Math.round(liveWeights.hres * 100)}%</span>
              </div>
              <input 
                type="range" min="0" max="100" 
                value={Math.round(liveWeights.hres * 100)} 
                onChange={(e) => handleWeightChange('hres', parseInt(e.target.value))}
                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
            </div>
            <div>
              <div className="flex justify-between text-xs font-medium text-textMain mb-1">
                <span>ENS</span>
                <span>{Math.round(liveWeights.ens * 100)}%</span>
              </div>
              <input 
                type="range" min="0" max="100" 
                value={Math.round(liveWeights.ens * 100)} 
                onChange={(e) => handleWeightChange('ens', parseInt(e.target.value))}
                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
              />
            </div>
            <div>
              <div className="flex justify-between text-xs font-medium text-textMain mb-1">
                <span>GraphCast</span>
                <span>{Math.round(liveWeights.graphcast * 100)}%</span>
              </div>
              <input 
                type="range" min="0" max="100" 
                value={Math.round(liveWeights.graphcast * 100)} 
                onChange={(e) => handleWeightChange('graphcast', parseInt(e.target.value))}
                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-green-500"
              />
            </div>
          </div>
          
          <div className="bg-brand-primary/10 rounded-md p-2 flex items-center justify-between border border-brand-primary/20">
            <span className="text-xs font-semibold text-brand-primary flex items-center gap-1">
              <Zap size={14} /> Live RMSE
            </span>
            <span className="text-sm font-bold text-brand-primary">
              {rmse !== null ? rmse.toFixed(2) : '--'} mm
            </span>
          </div>

          {/* Quick Actions & Official Sign-Off */}
          <div className="pt-2 border-t border-borderSubtle space-y-2">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setLiveWeights({ hres: 0.45, ens: 0.35, graphcast: 0.20 })}
                className="flex-1 text-[11px] py-1 px-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-medium transition-colors"
              >
                Reset Pipeline Weights
              </button>
            </div>

            <button
              type="button"
              onClick={async () => {
                try {
                  const res = await fetch('/api/bulletin/signoff', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      forecaster_name: 'Chief Forecaster (Operational Duty)',
                      forecaster_role: 'Lead Meteorologist, NWP Blending',
                      lead_day: leadDay,
                      custom_weights: liveWeights,
                      remarks: `Forecaster approved hybrid multi-model blend with Live RMSE ${rmse?.toFixed(2) ?? 'n/a'} mm.`,
                    }),
                  });
                  if (res.ok) {
                    const data = await res.json();
                    alert(`✅ OFFICIAL BULLETIN ISSUED:\n\nBulletin ID: ${data.bulletin.bulletin_id}\nLead Day: D+${data.bulletin.lead_day}\nCAP Feed: ${data.bulletin.cap_feed_endpoint}\nDispatched to NDMA SACHET Gateway.`);
                  }
                } catch (e) {
                  alert('Error signing bulletin: ' + e);
                }
              }}
              className="w-full py-2 px-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-lg text-xs font-bold shadow-md flex items-center justify-center gap-1.5 transition-all"
            >
              Sign-Off & Issue IMD-SACHET Bulletin
            </button>
          </div>
        </div>
      ) : (
        <p className="text-xs text-textMuted leading-snug">
          Enable to manually adjust model weights and see the rainfall forecast and RMSE update in real time.
        </p>
      )}
    </div>
  );
};

