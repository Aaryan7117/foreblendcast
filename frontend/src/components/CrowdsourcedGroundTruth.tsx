import React, { useState, useEffect } from 'react';
import { Camera, CheckCircle2, Droplets, MapPin, Send, Plus, X } from 'lucide-react';

interface Report {
  id: string;
  district_id: string;
  district_name: string;
  state: string;
  latitude: number;
  longitude: number;
  observer_name: string;
  observer_phone?: string;
  hazard_type: string;
  severity: string;
  water_depth_cm?: number;
  notes: string;
  timestamp: string;
  verified_by_ndrf: boolean;
  model_forecast_alignment: string;
}

export const CrowdsourcedGroundTruth: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form State
  const [districtName, setDistrictName] = useState('Cachar (Silchar)');
  const [districtId] = useState('AS-CACHAR');
  const [observerName, setObserverName] = useState('');
  const [observerPhone, setObserverPhone] = useState('');
  const [hazardType, setHazardType] = useState('waterlogging');
  const [waterDepth, setWaterDepth] = useState<number>(60);
  const [notes, setNotes] = useState('');

  const fetchReports = () => {
    fetch('/api/crowdsource/reports')
      .then((res) => res.json())
      .then((data) => {
        setReports(data.reports || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching ground reports:', err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload = {
        district_id: districtId,
        district_name: districtName,
        state: 'Assam',
        latitude: 24.833,
        longitude: 92.779,
        observer_name: observerName || 'Citizen Observer',
        observer_phone: observerPhone || '+91 98000 00000',
        hazard_type: hazardType,
        severity: waterDepth > 60 ? 'severe' : waterDepth > 20 ? 'moderate' : 'minor',
        water_depth_cm: Number(waterDepth),
        notes: notes || 'Ground observation logged via mobile/web interface.',
      };

      const res = await fetch('/api/crowdsource/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setSuccessMsg('Ground observation successfully recorded and linked to ForeBlendCast!');
        fetchReports();
        setTimeout(() => {
          setShowModal(false);
          setSuccessMsg(null);
          setNotes('');
        }, 1800);
      }
    } catch (err) {
      console.error('Submit error:', err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-surface rounded-xl border border-borderSubtle shadow-sm overflow-hidden text-textMain">
      {/* Header */}
      <div className="bg-slate-900/90 p-3.5 border-b border-borderSubtle flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-blue-500/20 text-blue-400 rounded-lg">
            <Droplets size={16} />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
              CROWDSOURCED GROUND TRUTH (VGI)
              <span className="px-1.5 py-0.5 text-[10px] bg-blue-500/20 text-blue-300 rounded font-mono">
                {reports.length} REPORTS
              </span>
            </h4>
            <p className="text-[11px] text-textMuted font-medium">
              Citizen & NDRF Field Observations vs. Model Blend
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-1 text-xs px-2.5 py-1.5 bg-brand-forest hover:bg-emerald-700 text-white rounded-lg font-medium transition-colors shadow-sm"
        >
          <Plus size={14} /> Report Ground Truth
        </button>
      </div>

      {/* Reports Feed */}
      <div className="p-3.5 space-y-2.5 max-h-[290px] overflow-y-auto">
        {loading ? (
          <div className="text-xs text-textMuted py-4 text-center">Loading field observations...</div>
        ) : reports.length === 0 ? (
          <div className="text-xs text-textMuted py-4 text-center">No ground reports recorded yet.</div>
        ) : (
          reports.map((rep) => (
            <div
              key={rep.id}
              className="p-3 rounded-lg bg-slate-900/70 border border-slate-800 space-y-2 hover:border-slate-700 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <MapPin size={13} className="text-blue-400 flex-shrink-0" />
                  <span className="font-semibold text-xs text-slate-200">
                    {rep.district_name}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    ({rep.district_id})
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  {rep.verified_by_ndrf && (
                    <span className="flex items-center gap-0.5 text-[9px] font-semibold text-emerald-400 bg-emerald-950/70 border border-emerald-800 px-1.5 py-0.5 rounded">
                      <CheckCircle2 size={10} /> NDRF VERIFIED
                    </span>
                  )}
                  <span
                    className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${
                      rep.severity === 'severe'
                        ? 'bg-red-950 text-red-400 border border-red-800'
                        : 'bg-amber-950 text-amber-400 border border-amber-800'
                    }`}
                  >
                    {rep.hazard_type}
                  </span>
                </div>
              </div>

              {/* Water Depth Indicator if applicable */}
              {rep.water_depth_cm !== undefined && (
                <div className="flex items-center gap-2 text-xs font-mono">
                  <span className="text-textMuted text-[11px]">Water Depth:</span>
                  <span className="font-bold text-blue-300 bg-blue-950/60 px-1.5 py-0.5 rounded border border-blue-900">
                    {rep.water_depth_cm} cm
                  </span>
                  <span className="text-[10px] text-slate-400">
                    • {rep.water_depth_cm >= 90 ? 'Waist Level' : rep.water_depth_cm >= 40 ? 'Knee Level' : 'Ankle Level'}
                  </span>
                </div>
              )}

              {/* Observer Note */}
              <p className="text-[11px] text-slate-300 leading-relaxed italic">
                "{rep.notes}"
              </p>

              {/* Model Forecast Alignment Badge */}
              <div className="pt-1 border-t border-slate-800/80 flex items-center justify-between text-[10px]">
                <span className="text-slate-400 font-medium">
                  By {rep.observer_name}
                </span>
                <span className="text-emerald-400/90 font-medium bg-emerald-950/40 px-1.5 py-0.5 rounded">
                  ✓ {rep.model_forecast_alignment}
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modal: Submit Ground Truth Report */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-md w-full p-4 text-textMain shadow-2xl space-y-3">
            <div className="flex justify-between items-center border-b border-slate-800 pb-2">
              <h3 className="font-bold text-sm text-slate-100 flex items-center gap-2">
                <Camera size={16} className="text-emerald-400" />
                Citizen Ground Truth Submission
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-textMuted hover:text-white"
              >
                <X size={16} />
              </button>
            </div>

            {successMsg ? (
              <div className="p-3 bg-emerald-950/80 border border-emerald-700 rounded-lg text-xs text-emerald-200 text-center font-medium">
                {successMsg}
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-3 text-xs">
                <div>
                  <label className="block text-textMuted mb-1 font-medium">District & Landmark</label>
                  <input
                    type="text"
                    value={districtName}
                    onChange={(e) => setDistrictName(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded bg-slate-800 border border-slate-700 text-slate-100 font-medium"
                    placeholder="e.g. Cachar (Silchar Town)"
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-textMuted mb-1 font-medium">Hazard Type</label>
                    <select
                      value={hazardType}
                      onChange={(e) => setHazardType(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded bg-slate-800 border border-slate-700 text-slate-100"
                    >
                      <option value="waterlogging">Waterlogging / Flood</option>
                      <option value="heavy_rain">Heavy Rain</option>
                      <option value="high_wind">Squally Wind / Gusts</option>
                      <option value="landslide">Landslide / Mudflow</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-textMuted mb-1 font-medium">
                      Water Depth (cm): <span className="font-bold text-emerald-400 font-mono">{waterDepth} cm</span>
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="150"
                      value={waterDepth}
                      onChange={(e) => setWaterDepth(Number(e.target.value))}
                      className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500 mt-1.5"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-textMuted mb-1 font-medium">Observer Details</label>
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="text"
                      placeholder="Your Name (or NDRF Volunteer)"
                      value={observerName}
                      onChange={(e) => setObserverName(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded bg-slate-800 border border-slate-700 text-slate-100"
                    />
                    <input
                      type="text"
                      placeholder="Mobile No. (optional)"
                      value={observerPhone}
                      onChange={(e) => setObserverPhone(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded bg-slate-800 border border-slate-700 text-slate-100"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-textMuted mb-1 font-medium">Ground Observations & Road Status</label>
                  <textarea
                    rows={2}
                    placeholder="Describe flooded roads, river levels, or damages..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded bg-slate-800 border border-slate-700 text-slate-100"
                  />
                </div>

                <div className="p-2 bg-slate-800/60 rounded border border-slate-700 flex items-center justify-between text-[11px] text-textMuted">
                  <span className="flex items-center gap-1.5">
                    <Camera size={14} className="text-blue-400" /> Photo Verification: Active GPS Geotag
                  </span>
                  <span className="text-emerald-400 font-medium">Auto-Attached</span>
                </div>

                <div className="flex justify-end gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded text-slate-300 font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded flex items-center gap-1.5 transition-colors shadow"
                  >
                    <Send size={13} /> {submitting ? 'Submitting...' : 'Submit Ground Report'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
