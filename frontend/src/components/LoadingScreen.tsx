import React, { useState, useEffect } from 'react';

interface LoadingScreenProps {
  onComplete: () => void;
}

const STEPS = [
  { label: 'Loading atmospheric forecast layers', delay: 1000 },
  { label: 'Aligning multi-model forecasts', delay: 2000 },
  { label: 'Blending rainfall signals', delay: 3000 },
];

export const LoadingScreen: React.FC<LoadingScreenProps> = ({ onComplete }) => {
  const [progress, setProgress] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [fading, setFading] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          return 100;
        }
        return prev + 1;
      });
    }, 38); // ~3800ms to reach 100

    STEPS.forEach((step, idx) => {
      setTimeout(() => {
        setCompletedSteps((prev) => [...prev, idx]);
      }, step.delay);
    });

    // Start fade at 3700ms, complete at 4000ms
    const fadeTimer = setTimeout(() => setFading(true), 3700);
    const completeTimer = setTimeout(() => onComplete(), 4000);

    return () => {
      clearInterval(interval);
      clearTimeout(fadeTimer);
      clearTimeout(completeTimer);
    };
  }, [onComplete]);

  return (
    <div
      className={`fixed inset-0 z-[10000] flex items-center justify-center transition-opacity duration-300 ${
        fading ? 'opacity-0' : 'opacity-100'
      }`}
      style={{ background: 'linear-gradient(180deg, #FAFAF7 0%, #F0EDE3 50%, #E8F0EB 100%)' }}
    >
      {/* Subtle mountain silhouette at bottom */}
      <div className="absolute bottom-0 left-0 right-0 h-48 opacity-[0.07]">
        <svg viewBox="0 0 1440 200" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full" preserveAspectRatio="none">
          <path d="M0 200L120 160L240 180L360 120L480 140L600 80L720 110L840 60L960 90L1080 40L1200 70L1320 30L1440 50V200H0Z" fill="#174A35"/>
          <path d="M0 200L180 170L360 150L540 130L720 145L900 100L1080 120L1260 90L1440 110V200H0Z" fill="#4F7D5C"/>
        </svg>
      </div>

      {/* Subtle rain effect */}
      <div className="absolute inset-0 overflow-hidden opacity-[0.04]">
        {Array.from({ length: 20 }).map((_, i) => (
          <div
            key={i}
            className="absolute w-px bg-brand-rain"
            style={{
              left: `${(i * 5) + 2}%`,
              top: `-${20 + (i % 3) * 10}%`,
              height: `${30 + (i % 4) * 15}%`,
              animationDuration: `${1.5 + (i % 3) * 0.5}s`,
              animationDelay: `${(i % 5) * 0.3}s`,
              animation: `rainFall ${1.5 + (i % 3) * 0.5}s linear ${(i % 5) * 0.3}s infinite`,
            }}
          />
        ))}
      </div>

      <div className="relative z-10 flex flex-col items-center gap-8 max-w-md px-6">
        {/* Brand */}
        <div className="text-center">
          <h1 className="text-4xl font-bold tracking-tight text-brand-navy">
            Fore<span className="text-brand-forest">Blend</span><span className="text-brand-leaf">Cast</span>
          </h1>
          <p className="text-sm text-textMuted mt-2 tracking-wide">
            Preparing forecast intelligence...
          </p>
        </div>

        {/* Steps */}
        <div className="w-full space-y-3">
          {STEPS.map((step, idx) => (
            <div
              key={idx}
              className={`flex items-center gap-3 text-sm transition-all duration-500 ${
                completedSteps.includes(idx) ? 'opacity-100' : 'opacity-30'
              }`}
            >
              <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-300 ${
                completedSteps.includes(idx)
                  ? 'bg-brand-forest text-white'
                  : 'border-2 border-border'
              }`}>
                {completedSteps.includes(idx) && (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20 6 9 17l-5-5"/>
                  </svg>
                )}
              </div>
              <span className={completedSteps.includes(idx) ? 'text-textMain' : 'text-textMuted'}>
                {step.label}
              </span>
            </div>
          ))}
        </div>

        {/* Progress bar */}
        <div className="w-full">
          <div className="w-full h-1.5 bg-border rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-100 ease-linear"
              style={{
                width: `${progress}%`,
                background: 'linear-gradient(90deg, #174A35, #4F7D5C)',
              }}
            />
          </div>
          <div className="flex justify-between mt-2 text-xs text-textLight">
            <span>Initializing</span>
            <span>{progress}%</span>
          </div>
        </div>

        {/* Subtitle */}
        <p className="text-xs text-textLight text-center leading-relaxed">
          Ministry of Earth Sciences • NCMRWF<br />
          Government of India
        </p>
      </div>

      <style>{`
        @keyframes rainFall {
          0% { transform: translateY(-100%); opacity: 0; }
          10% { opacity: 1; }
          90% { opacity: 1; }
          100% { transform: translateY(400%); opacity: 0; }
        }
      `}</style>
    </div>
  );
};
