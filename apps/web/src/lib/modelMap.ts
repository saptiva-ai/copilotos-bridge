/**
 * Model Mapping - Fuzzy matching between backend model names and UI catalog
 *
 * This module handles the translation between backend model names (which may have
 * inconsistent casing, underscores, spaces) and the canonical UI model catalog.
 *
 * Key functions:
 * - findUiModelByBackendName: Map a backend name to a catalog entry
 * - resolveBackendId: Find the exact backend name to send to API
 * - buildModelList: Create the complete model list with availability status
 */

import { MODEL_CATALOG, type UiModel } from '../config/modelCatalog'

/**
 * Normalize a model name for fuzzy matching
 * - Lowercase
 * - Replace underscores and hyphens with spaces
 * - Collapse multiple spaces to single space
 * - Trim whitespace
 */
function normalizeModelName(name: string): string {
  return name
    .toLowerCase()
    .replace(/[_-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

/**
 * Find UI model by backend model name using fuzzy matching
 *
 * Matching strategy:
 * 1. Exact match in aliases (case-insensitive)
 * 2. Normalized match (handles underscores, hyphens, extra spaces)
 * 3. Contains match (for partial names like "turbo" → "Saptiva Turbo")
 *
 * @param backendName - Model name from backend API
 * @returns UI model entry or null if no match
 */
export function findUiModelByBackendName(backendName: string): UiModel | null {
  if (!backendName) return null

  const normalized = normalizeModelName(backendName)

  // Strategy 1: Exact alias match (case-insensitive)
  for (const model of MODEL_CATALOG) {
    const aliasMatch = model.aliases.find(
      (alias) => normalizeModelName(alias) === normalized
    )
    if (aliasMatch) return model
  }

  // Strategy 2: Partial match - check if normalized name contains model slug
  for (const model of MODEL_CATALOG) {
    if (normalized.includes(model.slug)) return model
  }

  // Strategy 3: Reverse partial - check if any alias contains the backend name
  for (const model of MODEL_CATALOG) {
    const containsMatch = model.aliases.find((alias) =>
      normalizeModelName(alias).includes(normalized)
    )
    if (containsMatch) return model
  }

  return null
}

/**
 * Resolve the exact backend model ID to use for API calls
 *
 * Given a UI model slug and list of available backend names, find the exact
 * backend name that should be sent to the API.
 *
 * @param backendAvailableNames - Array of model names from /api/models
 * @param slug - UI model slug (e.g., 'turbo', 'cortex')
 * @returns Exact backend name to send in API call, or null if not available
 */
export function resolveBackendId(
  backendAvailableNames: string[],
  slug: string
): string | null {
  const uiModel = MODEL_CATALOG.find((m) => m.slug === slug)
  if (!uiModel) return null

  // Find which backend name matches this UI model
  for (const backendName of backendAvailableNames) {
    const matchedModel = findUiModelByBackendName(backendName)
    if (matchedModel?.slug === slug) {
      return backendName // Return exact backend name for API
    }
  }

  return null
}

/**
 * Build complete model list with availability status
 *
 * Creates a list of all catalog models with:
 * - availability flag (is this model available in backend?)
 * - backendId (exact name to send to API, null if unavailable)
 *
 * @param backendAvailableNames - Array of model names from /api/models
 * @returns Array of models with availability and backend ID info
 */
export function buildModelList(backendAvailableNames: string[]): Array<{
  model: UiModel
  available: boolean
  backendId: string | null
}> {
  return MODEL_CATALOG.map((model) => {
    const backendId = resolveBackendId(backendAvailableNames, model.slug)
    return {
      model,
      available: backendId !== null,
      backendId,
    }
  })
}

/**
 * Get default model slug
 *
 * Given a backend default model name, find the corresponding UI slug.
 * Falls back to first catalog model if no match.
 *
 * @param backendDefaultName - Default model name from /api/models
 * @returns UI model slug
 */
export function getDefaultModelSlug(backendDefaultName: string | null): string {
  // Default to 'turbo' (Saptiva Turbo) if no backend default provided
  if (!backendDefaultName) return 'turbo'

  const matched = findUiModelByBackendName(backendDefaultName)
  return matched?.slug || 'turbo'
}

/**
 * Validate if a slug exists in catalog
 */
export function isValidSlug(slug: string): boolean {
  return MODEL_CATALOG.some((m) => m.slug === slug)
}