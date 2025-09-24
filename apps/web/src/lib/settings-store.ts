import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { SaptivaKeyStatus } from './types';

interface SettingsState {
  saptivaApiKey: string | null;
  isModalOpen: boolean;
  status: SaptivaKeyStatus;
  saving: boolean;
  error: string | null;

  // Actions
  fetchStatus: () => Promise<void>;
  saveApiKey: (apiKey: string) => Promise<boolean>;
  clearApiKey: () => Promise<void>;
  openModal: () => void;
  closeModal: () => void;
  toggleModal: () => void;
  setError: (error: string | null) => void;
}

const initialStatus: SaptivaKeyStatus = {
  configured: false,
  mode: 'demo',
  source: 'unset',
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      saptivaApiKey: null,
      isModalOpen: false,
      error: null,
      status: initialStatus,
      saving: false,

      fetchStatus: async () => {
        const key = get().saptivaApiKey;
        set({
          status: {
            ...initialStatus,
            configured: !!key,
            mode: key ? 'live' : 'demo',
            source: key ? 'local' : 'unset',
          },
        });
      },

      saveApiKey: async ({ apiKey }: { apiKey: string; }) => {
        set({ saving: true, error: null });
        try {
          // Simulate API validation
          await new Promise(resolve => setTimeout(resolve, 1000));
          if (!apiKey || apiKey.trim() === '' || apiKey.includes('error')) {
            throw new Error('Invalid API Key format');
          }
          set({
            saptivaApiKey: apiKey,
            saving: false,
            status: { configured: true, mode: 'live', source: 'local' },
          });
          return true;
        } catch (e: any) {
          const error = e.message || 'Failed to save API key';
          set({ 
            saving: false, 
            status: { ...get().status, mode: 'demo' },
            error 
          });
          return false;
        }
      },

      clearApiKey: async () => {
        set({ 
          saptivaApiKey: null, 
          status: initialStatus, 
          error: null 
        });
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
