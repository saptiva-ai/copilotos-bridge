import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type ApiKeyStatus = 'idle' | 'saving' | 'success' | 'error';

interface SettingsState {
  saptivaApiKey: string | null;
  setSaptivaApiKey: (key: string | null) => void;
  isDemoMode: boolean;
  setIsDemoMode: (isDemo: boolean) => void;
  status: ApiKeyStatus;
  saving: boolean;
  error: string | null;
  saveApiKey: (key: string) => Promise<void>;
  clearApiKey: () => void;
  setError: (error: string | null) => void;
  isModalOpen: boolean;
  openModal: () => void;
  closeModal: () => void;
  toggleModal: () => void;
  fetchStatus: () => Promise<void>;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      saptivaApiKey: null,
      isDemoMode: true,
      status: 'idle',
      saving: false,
      error: null,
      isModalOpen: false,

      setSaptivaApiKey: (key) => {
        set({ saptivaApiKey: key, isDemoMode: !key, status: key ? 'success' : 'idle' });
      },
      setIsDemoMode: (isDemo) => set({ isDemoMode: isDemo }),
      setError: (error) => set({ error }),
      openModal: () => set({ isModalOpen: true }),
      closeModal: () => set({ isModalOpen: false }),
      toggleModal: () => set((state) => ({ isModalOpen: !state.isModalOpen })),

      saveApiKey: async (key: string) => {
        set({ saving: true, status: 'saving', error: null });
        try {
          // Simulate API call
          await new Promise(resolve => setTimeout(resolve, 1000));
          if (key.trim() === 'error') {
            throw new Error('Invalid API Key format');
          }
          get().setSaptivaApiKey(key);
          set({ saving: false, status: 'success' });
        } catch (e: any) {
          const error = e.message || 'Failed to save API key';
          set({ saving: false, status: 'error', error });
        }
      },

      clearApiKey: () => {
        get().setSaptivaApiKey(null);
      },

      fetchStatus: async () => {
        // Simulate fetching status
        if (get().saptivaApiKey) {
          set({ status: 'success' });
        } else {
          set({ status: 'idle' });
        }
      },
    }) as SettingsState,
    {
      name: 'saptiva-settings-storage',
    }
  )
);
