import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type ApiKeyStatus = 'idle' | 'validating' | 'valid' | 'invalid';

interface SettingsState {
  saptivaApiKey: string | null;
  apiKeyStatus: ApiKeyStatus;
  isModalOpen: boolean;
  isDemoMode: boolean;
  error: string | null;

  // Actions
  setSaptivaApiKey: (key: string | null) => void;
  validateApiKey: (key: string) => Promise<boolean>;
  clearApiKey: () => void;
  openModal: () => void;
  closeModal: () => void;
  setError: (error: string | null) => void;
  // The following are derived or composite state/actions based on previous errors
  status: { configured: boolean; mode: ApiKeyStatus };
  saving: boolean;
  fetchStatus: () => Promise<void>;
  toggleModal: () => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      saptivaApiKey: null,
      apiKeyStatus: 'idle',
      isModalOpen: false,
      isDemoMode: true,
      error: null,

      get status() {
        const key = get().saptivaApiKey;
        const status = get().apiKeyStatus;
        return { configured: !!key, mode: status };
      },

      get saving() {
        return get().apiKeyStatus === 'validating';
      },

      setSaptivaApiKey: (key) => {
        set({
          saptivaApiKey: key,
          isDemoMode: !key,
          apiKeyStatus: key ? 'valid' : 'idle',
        });
      },

      validateApiKey: async (apiKey: string) => {
        set({ apiKeyStatus: 'validating', error: null });
        try {
          // Simulate API validation
          await new Promise(resolve => setTimeout(resolve, 1000));
          if (!apiKey || apiKey.trim() === '' || apiKey.includes('error')) {
            throw new Error('Invalid API Key');
          }
          set({ saptivaApiKey: apiKey, apiKeyStatus: 'valid', isDemoMode: false });
          return true;
        } catch (e: any) {
          set({ apiKeyStatus: 'invalid', error: e.message });
          return false;
        }
      },

      clearApiKey: () => {
        set({ saptivaApiKey: null, apiKeyStatus: 'idle', isDemoMode: true });
      },

      openModal: () => set({ isModalOpen: true }),
      closeModal: () => set({ isModalOpen: false }),
      setError: (error) => set({ error }),

      fetchStatus: async () => {
        const { saptivaApiKey } = get();
        if (saptivaApiKey) {
          set({ apiKeyStatus: 'valid' });
        } else {
          set({ apiKeyStatus: 'idle' });
        }
      },

      toggleModal: () => {
        set((state) => ({ isModalOpen: !state.isModalOpen }));
      },
    }),
    {
      name: 'saptiva-settings-storage',
    }
  )
);
