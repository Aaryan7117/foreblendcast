import React from 'react';

interface WatermarkProps {
  isFixture: boolean;
}

export const Watermark: React.FC<WatermarkProps> = ({ isFixture }) => {
  if (!isFixture) return null;
  return (
    <div className="pointer-events-none fixed inset-0 z-[9999] flex items-center justify-center overflow-hidden">
      <div className="transform -rotate-45 text-red-500/20 text-[10vw] font-black uppercase whitespace-nowrap">
        FIXTURE DATA — NOT RESULTS
      </div>
    </div>
  );
};
