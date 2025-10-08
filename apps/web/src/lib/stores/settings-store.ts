/**
 * Settings State Store
 *
 * Manages application settings and feature flags:
 * - Model parameters (temperature, max tokens)
 * - Stream settings
 * - Feature flags from backend
 */

import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { FeatureFlagsResponse } from '../types'
import { apiClient } from '../api-client'
import { logError } from '../logger'

interface Settings {
  maxTokens: number
  temperature: number
  streamEnabled: boolean
}

interface SettingsState {
  // State
  settings: Settings
  featureFlags: FeatureFlagsResponse | null
  featureFlagsLoading: boolean

  // Actions
  updateSettings: (settings: Partial<Settings>) => void
  loadFeatureFlags: () => Promise<void>
  clearAllData: () => void
}

const defaultSettings: Settings = {
  maxTokens: 2000,
  temperature: 0.7,
  streamEnabled: true,
}

export const useSettingsStore = create<SettingsState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        settings: defaultSettings,
        featureFlags: null,
        featureFlagsLoading: false,

        // Actions
        updateSettings: (newSettings) =>
          set((state) => ({
            settings: { ...state.settings, ...newSettings },
          })),

        loadFeatureFlags: async () => {
          try {
            set({ featureFlagsLoading: true })
            const response = await apiClient.getFeatureFlags()
            set({ featureFlags: response, featureFlagsLoading: false })
          } catch (error) {
            logError('Failed to load feature flags:', error)
            set({ featureFlags: null, featureFlagsLoading: false })
          }
        },

        clearAllData: () => {
          set({
            settings: defaultSettings,
          })
        },
      }),
      {
        name: 'settings-store',
        partialize: (state) => ({
          settings: state.settings,
        }),
      }
    ),
    {
      name: 'settings-store',
    }
  )
)

// Backward compatibility export
export const useSettings = () => {
  const store = useSettingsStore()
  return {
    settings: store.settings,
    updateSettings: store.updateSettings,
  }
}
