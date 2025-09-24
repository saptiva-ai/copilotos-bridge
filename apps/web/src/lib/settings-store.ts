import { create } from 'zustand';

// A minimal store to satisfy the type checker.

export const useSettingsStore = create<any>(() => ({
  saptivaApiKey: null,
  isModalOpen: false,
  isDemoMode: true,
  error: null,
  status: { configured: false, mode: 'demo' },
  saving: false,
  fetchStatus: async () => {},
  saveApiKey: async () => true,
  clearApiKey: async () => true,
  openModal: () => {},
  closeModal: () => {},
  toggleModal: () => {},
  setError: () => {},
}));
