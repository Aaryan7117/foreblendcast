import React from 'react';
import { useAppStore } from '../store';
import type { PageId } from '../store';
import type { LadderResult } from '../types/results';

interface HeaderProps {
  meta?: LadderResult['meta'];
}

const NAV_ITEMS: { id: PageId; label: string }[] = [
  { id: 'live', label: 'Live Forecast' },
  { id: 'risk', label: 'Risk Dashboard' },
  { id: 'comparison', label: 'Model Comparison' },
  { id: 'evaluation', label: 'Evaluation' },
  { id: 'wherewellose', label: 'Where We Lose' },
  { id: 'about', label: 'About' },
];

/**
 * Robust date formatter that safely handles non-standard ISO strings like "2022-07-15T00Z"
 * entirely on the frontend without modifying backend data fixtures.
 */
function formatCycleDate(cycleStr?: string): { short: string; full: string } {
  if (!cycleStr) {
    return { short: '15 Jul 2022', full: '15 July 2022, 00:00 UTC' };
  }

  // Normalize "2022-07-15T00Z" -> "2022-07-15T00:00:00Z"
  let normalized = cycleStr.trim();
  if (/T\d{2}Z$/i.test(normalized)) {
    normalized = normalized.replace(/T(\d{2})Z$/i, 'T$1:00:00Z');
  }

  let date = new Date(normalized);

  // Fallback regex parser for YYYY-MM-DD
  if (isNaN(date.getTime())) {
    const match = cycleStr.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (match) {
      date = new Date(Date.UTC(parseInt(match[1], 10), parseInt(match[2], 10) - 1, parseInt(match[3], 10)));
    }
  }

  if (isNaN(date.getTime())) {
    return { short: '15 Jul 2022', full: cycleStr };
  }

  const short = date.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  });

  const full = `${date.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  })}, 00:00 UTC`;

  return { short, full };
}

export const Header: React.FC<HeaderProps> = ({ meta }) => {
  const { activePage, setActivePage } = useAppStore();
  const dateInfo = formatCycleDate(meta?.cycle);

  return (
    <header className="flex-shrink-0 z-50 select-none">
      {/* 
        Full-width Deep Forest-Green Header with Realistic Layered Mountain Panorama
        Matches the visual reference exactly:
        - Natural panoramic mountain landscape across the background
        - Distant mountains through soft mist with morning light
        - Deep forest green foreground canopy
        - Official MoES and NCMRWF branding
        - ForeBlendCast title, SIH26081 badge, and subtitle
        - National Weather Forecasting System & Cycle Date badge
      */}
      <div 
        className="relative overflow-hidden shadow-md"
        style={{
          background: '#0a2618',
        }}
      >
        {/* Layer 1: High-Resolution Realistic Mountain Landscape Panorama */}
        <div 
          className="absolute inset-0 bg-cover bg-center pointer-events-none"
          style={{
            backgroundImage: "url('/assets/foreblend-mountains-bg.jpg')",
            backgroundPosition: 'center 38%',
            filter: 'saturate(1.1) brightness(0.92)',
          }}
          aria-hidden="true"
        />

        {/* Layer 2: Subtle Atmospheric Vignette for Perfect Contrast & Legibility */}
        <div 
          className="absolute inset-0 pointer-events-none"
          style={{
            background: 'linear-gradient(to right, rgba(5, 24, 15, 0.72) 0%, rgba(8, 36, 23, 0.35) 25%, rgba(8, 36, 23, 0.35) 75%, rgba(5, 24, 15, 0.75) 100%), linear-gradient(to bottom, rgba(5, 24, 15, 0.25) 0%, rgba(5, 24, 15, 0.55) 100%)',
          }}
          aria-hidden="true"
        />

        {/* Layer 3: Header Content */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-2.5 sm:py-3 relative z-20 gap-3">
          {/* LEFT: Official MoES & NCMRWF institutional branding */}
          <div className="flex items-center gap-3 sm:gap-4 flex-shrink-0">
            {/* MoES Official Branding - Merged seamlessly with header background */}
            <div 
              className="flex items-center cursor-default transition-opacity hover:opacity-95"
              title="Ministry of Earth Sciences, Government of India"
            >
              <img
                src="/logos/moes-logo-white.png"
                alt="Ministry of Earth Sciences, Government of India"
                className="h-8 sm:h-9 w-auto object-contain flex-shrink-0 drop-shadow-[0_1px_3px_rgba(0,0,0,0.5)]"
                style={{ aspectRatio: '425 / 136' }}
              />
            </div>

            {/* Subtle institutional divider */}
            <div className="w-px h-8 bg-white/25 hidden sm:block" aria-hidden="true" />

            {/* NCMRWF Official Emblem & Institutional Label */}
            <div 
              className="flex items-center gap-2.5 cursor-default group"
              title="National Centre for Medium Range Weather Forecasting"
            >
              <div className="w-8 sm:w-9 h-8 sm:h-9 rounded-full bg-white p-0.5 shadow-sm border border-white/30 flex items-center justify-center flex-shrink-0">
                <img
                  src="/logos/ncmrwf-logo.png"
                  alt="NCMRWF"
                  className="w-full h-full object-contain rounded-full"
                  style={{ aspectRatio: '370 / 383' }}
                />
              </div>
              <div className="text-left hidden lg:block leading-tight">
                <div className="text-[11.5px] font-bold text-white tracking-tight drop-shadow-sm">
                  NCMRWF
                </div>
                <div className="text-[9.5px] text-white/90 font-medium max-w-[155px] leading-tight drop-shadow-sm">
                  National Centre for Medium Range Weather Forecasting
                </div>
              </div>
            </div>
          </div>

          {/* CENTER: ForeBlendCast Identity matching reference */}
          <div className="flex-1 flex justify-center px-2">
            <div className="text-center">
              <div className="flex items-center justify-center gap-2.5">
                <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight drop-shadow-md">
                  Fore<span className="text-emerald-300">Blend</span>Cast
                </h1>
                <span className="text-[9.5px] font-bold bg-[#104C33]/85 border border-[#34D399]/40 text-[#A7F3D0] px-2.5 py-0.5 rounded-full uppercase tracking-wider shadow-xs backdrop-blur-sm">
                  SIH26081
                </span>
              </div>
              <p className="text-[11px] text-white/90 font-normal mt-0.5 tracking-wide hidden md:block max-w-[500px] truncate drop-shadow-sm">
                Hybrid AI–NWP Multi-Model Forecast Blending & Calibrated Disaster Risk System
              </p>
            </div>
          </div>

          {/* RIGHT: Operational status + Cycle Date card matching reference (NO OVERLAP) */}
          <div className="flex items-center gap-3.5 flex-shrink-0 z-20">
            <div className="hidden xl:flex flex-col text-right justify-center">
              <span className="text-white text-[11.5px] font-bold tracking-wide leading-tight drop-shadow-sm">
                National Weather Forecasting System
              </span>
              <span className="text-emerald-300 text-[10px] font-medium leading-tight mt-0.5 drop-shadow-sm">
                Calibrated Disaster Early Warning
              </span>
            </div>

            <div className="w-px h-8 bg-white/20 hidden xl:block" aria-hidden="true" />

            {/* Cycle Date Card */}
            <div 
              className="flex items-center gap-2.5 bg-[#092B1C]/85 hover:bg-[#092B1C]/95 border border-emerald-400/40 rounded-xl px-3.5 py-1.5 shadow-sm backdrop-blur-md transition-all duration-150 cursor-default"
              title={`Operational Forecast Cycle: ${dateInfo.full}`}
            >
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-xs" />
              <div className="text-left">
                <div className="text-[9px] uppercase tracking-wider text-emerald-300 font-bold leading-none">
                  Cycle Date
                </div>
                <div className="text-xs font-bold text-white leading-tight mt-0.5 whitespace-nowrap">
                  {dateInfo.short}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation bar with polished hover and active states */}
      <nav className="bg-surface border-b border-border shadow-xs px-4 sm:px-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1 overflow-x-auto custom-scrollbar py-1">
            {NAV_ITEMS.map((item) => {
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActivePage(item.id)}
                  className={`px-3.5 py-2 text-[13px] font-medium transition-all duration-150 rounded-md relative select-none whitespace-nowrap ${
                    isActive
                      ? 'text-brand-forest font-semibold bg-emerald-50/80 shadow-xs'
                      : 'text-textMuted hover:text-textMain hover:bg-slate-100/80 hover:shadow-xs'
                  }`}
                >
                  {item.label}
                  {isActive && (
                    <span 
                      className="absolute bottom-0 left-3 right-3 h-[2.5px] bg-brand-forest rounded-full transition-all duration-200" 
                      aria-hidden="true"
                    />
                  )}
                </button>
              );
            })}
          </div>

          {/* Institutional subtext on right of nav */}
          <div className="hidden lg:flex items-center gap-3 text-xs text-textMuted border-l border-border pl-4 py-1">
            <span className="flex items-center gap-1.5 font-medium text-[11px]">
              <span className="w-1.5 h-1.5 rounded-full bg-tier-green" />
              NWP: ECMWF IFS
            </span>
            <span className="flex items-center gap-1.5 font-medium text-[11px]">
              <span className="w-1.5 h-1.5 rounded-full bg-tier-green" />
              AI: GraphCast
            </span>
          </div>
        </div>
      </nav>
    </header>
  );
};
