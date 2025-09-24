import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type ApiKeyStatus = 'idle' | 'validating' | 'valid' | 'invalid' | 'demo';

interface SettingsState {
  saptivaApiKey: string | null;
  isModalOpen: boolean;
  isDemoMode: boolean;
  error: string | null;
  status: {
    configured: boolean;
    mode: ApiKeyStatus;
  };
  saving: boolean;

  // Actions
  fetchStatus: () => Promise<void>;
  saveApiKey: (args: { apiKey: string; validate: boolean; }) => Promise<boolean>;
  clearApiKey: () => Promise<boolean>;
  openModal: () => void;
  closeModal: () => void;
  toggleModal: () => void;
  setError: (error: string | null) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      saptivaApiKey: null,
      isModalOpen: false,
      isDemoMode: true,
      error: null,
      status: { configured: false, mode: 'demo' },
      saving: false,

      fetchStatus: async () => {
        const key = get().saptivaApiKey;
        set({ 
          status: { 
            configured: !!key, 
            mode: key ? 'valid' : 'demo' 
          },
          isDemoMode: !key
        });
      },

      saveApiKey: async ({ apiKey, validate }) => {
        set({ saving: true, status: { ...get().status, mode: 'validating' }, error: null });
        try {
          if (validate) {
            // Simulate API validation
            await new Promise(resolve => setTimeout(resolve, 1000));
            if (!apiKey || apiKey.trim() === '' || apiKey.includes('error')) {
              throw new Error('Invalid API Key format');
            }
          }
          set({ 
            saptivaApiKey: apiKey, 
            isDemoMode: false,
            saving: false, 
            status: { configured: true, mode: 'valid' } 
          });
          return true;
        } catch (e: any) {
          const error = e.message || 'Failed to save API key';
          set({ 
            saving: false, 
            status: { ...get().status, mode: 'invalid' }, 
            error 
          });
          return false;
        }
      },

      clearApiKey: async () => {
        set({ 
          saptivaApiKey: null, 
          isDemoMode: true,
          status: { configured: false, mode: 'demo' },
          error: null
        });
        return true;
      },

      openModal: () => set({ isModalOpen: true }),
      closeModal: () => set({ isModalOpen: false }),
      toggleModal: () => set((state) => ({ isModalOpen: !state.isModalOpen })),
      setError: (error) => set({ error }),
    }),
    {
      name: 'saptiva-settings-storage',
    }
  )
);
