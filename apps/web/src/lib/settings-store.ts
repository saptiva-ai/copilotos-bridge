import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type ApiKeyStatus = 'idle' | 'validating' | 'valid' | 'invalid' | 'demo';

// Based on error: Property 'source' is missing...
interface SaptivaKeyStatus {
  mode: ApiKeyStatus;
  configured: boolean;
  source: 'local' | 'remote' | null;
}

interface SettingsState {
  saptivaApiKey: string | null;
  apiKeyStatus: SaptivaKeyStatus;
  isModalOpen: boolean;
  isDemoMode: boolean;
  error: string | null;
  saving: boolean;

  // Actions
  setSaptivaApiKey: (key: string | null) => void;
  saveApiKey: (args: { apiKey: string; validate: boolean; }) => Promise<boolean>;
  clearApiKey: () => Promise<boolean>;
  openModal: () => void;
  closeModal: () => void;
  setError: (error: string | null) => void;
  fetchStatus: () => Promise<void>;
  toggleModal: () => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      saptivaApiKey: null,
      apiKeyStatus: { mode: 'idle', configured: false, source: null },
      isModalOpen: false,
      isDemoMode: true,
      error: null,
      saving: false,

      setSaptivaApiKey: (key) => {
        const isDemo = !key;
        set({
          saptivaApiKey: key,
          isDemoMode: isDemo,
          apiKeyStatus: { 
            mode: isDemo ? 'demo' : 'valid', 
            configured: !isDemo, 
            source: 'local' 
          },
        });
      },

      saveApiKey: async ({ apiKey, validate }) => {
        set({ saving: true, apiKeyStatus: { ...get().apiKeyStatus, mode: 'validating' }, error: null });
        try {
          if (validate) {
            // Simulate API validation
            await new Promise(resolve => setTimeout(resolve, 1000));
            if (!apiKey || apiKey.trim() === '' || apiKey.includes('error')) {
              throw new Error('Invalid API Key');
            }
          }
          get().setSaptivaApiKey(apiKey);
          set({ saving: false });
          return true;
        } catch (e: any) {
          const error = e.message || 'Failed to save API key';
          set({ saving: false, apiKeyStatus: { ...get().apiKeyStatus, mode: 'invalid' }, error });
          return false;
        }
      },

      clearApiKey: async () => {
        set({ saptivaApiKey: null, apiKeyStatus: { mode: 'idle', configured: false, source: null }, isDemoMode: true });
        return true;
      },

      openModal: () => set({ isModalOpen: true }),
      closeModal: () => set({ isModalOpen: false }),
      setError: (error) => set({ error }),

      fetchStatus: async () => {
        const { saptivaApiKey } = get();
        if (saptivaApiKey) {
          set({ apiKeyStatus: { mode: 'valid', configured: true, source: 'local' } });
        } else {
          set({ apiKeyStatus: { mode: 'demo', configured: false, source: null } });
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