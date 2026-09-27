import { create } from 'zustand';

interface AppState {
  leadDay: number;
  focusedCity: string | null;
  tierFilter: string | null;
  setLeadDay: (day: number) => void;
  setFocusedCity: (city: string | null) => void;
  setTierFilter: (tier: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  leadDay: 3,
  focusedCity: null,
  tierFilter: null,
  setLeadDay: (day) => set({ leadDay: day }),
  setFocusedCity: (city) => set({ focusedCity: city }),
  setTierFilter: (tier) => set({ tierFilter: tier }),
}));
