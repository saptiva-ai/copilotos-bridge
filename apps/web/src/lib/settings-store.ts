import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsState {
  saptivaApiKey: string | null;
  setSaptivaApiKey: (key: string | null) => void;
  isDemoMode: boolean;
  setIsDemoMode: (isDemo: boolean) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      saptivaApiKey: null,
      isDemoMode: true,
      setSaptivaApiKey: (key) => {
        set({ saptivaApiKey: key, isDemoMode: !key });
      },
      setIsDemoMode: (isDemo) => set({ isDemoMode: isDemo }),
    }),
    {
      name: 'saptiva-settings-storage',
    }
  )
);