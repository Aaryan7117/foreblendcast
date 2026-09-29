import { create } from 'zustand';

export type PageId = 'live' | 'risk' | 'comparison' | 'evaluation' | 'wherewellose' | 'about' | 'replay';
export type LayerId = 'rainfall' | 'exceedance' | 'disagreement' | 'risk_tiers';
export type ModelId = 'blend' | 'hres' | 'ens' | 'graphcast' | 'baseline';
export type RegionId = 'all' | 'NW' | 'CENTRAL' | 'SOUTH' | 'EAST_NE';

interface AppState {
  /* Existing state — preserved */
  leadDay: number;
  focusedCity: string | null;
  tierFilter: string | null;
  setLeadDay: (day: number) => void;
  setFocusedCity: (city: string | null) => void;
  setTierFilter: (tier: string | null) => void;

  /* New state for redesign */
  activePage: PageId;
  activeLayer: LayerId;
  selectedModel: ModelId;
  selectedDistrict: string | null;
  region: RegionId;
  rasterOverride: string | null;
  mapMode: 'map' | 'satellite';
  isLiveBlenderEnabled: boolean;
  liveWeights: { hres: number; ens: number; graphcast: number };
  
  setActivePage: (page: PageId) => void;
  setActiveLayer: (layer: LayerId) => void;
  setSelectedModel: (model: ModelId) => void;
  setSelectedDistrict: (district: string | null) => void;
  setRegion: (region: RegionId) => void;
  setRasterOverride: (raster: string | null) => void;
  setMapMode: (mode: 'map' | 'satellite') => void;
  setIsLiveBlenderEnabled: (enabled: boolean) => void;
  setLiveWeights: (weights: { hres: number; ens: number; graphcast: number }) => void;
}

export const useAppStore = create<AppState>((set) => ({
  leadDay: 1,
  focusedCity: null,
  tierFilter: null,
  setLeadDay: (day) => set({ leadDay: day }),
  setFocusedCity: (city) => set({ focusedCity: city }),
  setTierFilter: (tier) => set({ tierFilter: tier }),

  activePage: 'live',
  activeLayer: 'rainfall',
  selectedModel: 'blend',
  selectedDistrict: null,
  region: 'all',
  rasterOverride: null,
  mapMode: 'map',
  isLiveBlenderEnabled: false,
  liveWeights: { hres: 0.33, ens: 0.33, graphcast: 0.34 },

  setActivePage: (page) => set({ activePage: page }),
  setActiveLayer: (layer) => set({ activeLayer: layer }),
  setSelectedModel: (model) => set({ selectedModel: model }),
  setSelectedDistrict: (district) => set({ selectedDistrict: district }),
  setRegion: (region) => set({ region, selectedDistrict: null }),
  setRasterOverride: (raster) => set({ rasterOverride: raster }),
  setMapMode: (mode) => set({ mapMode: mode }),
  setIsLiveBlenderEnabled: (enabled) => set({ isLiveBlenderEnabled: enabled }),
  setLiveWeights: (weights) => set({ liveWeights: weights }),
}));
