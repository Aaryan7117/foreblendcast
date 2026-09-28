import React from 'react';

interface WatermarkProps {
  isFixture?: boolean;
}

/**
 * Watermark component - disabled to remove giant red diagonal overlay from the UI.
 * Data contracts and fixture status remain untouched in the underlying data.
 */
export const Watermark: React.FC<WatermarkProps> = () => {
  return null;
};
