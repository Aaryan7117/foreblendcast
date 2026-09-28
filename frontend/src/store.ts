import { create } from 'zustand';

export type PageId = 'live' | 'risk' | 'comparison' | 'evaluation' | 'wherewellose' | 'about';
export type LayerId = 'rainfall' | 'exceedance' | 'disagreement' | 'risk_tiers';
export type ModelId = 'blend' | 'hres' | 'ens' | 'graphcast' | 'baseline';

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
  mapMode: 'map' | 'satellite';
  setActivePage: (page: PageId) => void;
  setActiveLayer: (layer: LayerId) => void;
  setSelectedModel: (model: ModelId) => void;
  setSelectedDistrict: (district: string | null) => void;
  setMapMode: (mode: 'map' | 'satellite') => void;
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
  mapMode: 'map',
  setActivePage: (page) => set({ activePage: page }),
  setActiveLayer: (layer) => set({ activeLayer: layer }),
  setSelectedModel: (model) => set({ selectedModel: model }),
  setSelectedDistrict: (district) => set({ selectedDistrict: district }),
  setMapMode: (mode) => set({ mapMode: mode }),
}));
