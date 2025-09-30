/**
 * Tests for model mapping logic
 *
 * These tests verify the fuzzy matching between backend model names
 * and the UI catalog, ensuring robust handling of inconsistent casing
 * and naming variations from the backend.
 */

// Note: These tests are designed for Jest/Vitest. Run with: pnpm test
// If using TypeScript without test runner, comment out the imports below
import {
  findUiModelByBackendName,
  resolveBackendId,
  buildModelList,
  getDefaultModelSlug,
  isValidSlug,
} from '../src/lib/modelMap'
import { MODEL_CATALOG } from '../src/config/modelCatalog'

describe('modelMap - findUiModelByBackendName', () => {
  describe('Exact alias matching (case-insensitive)', () => {
    it('should match "Saptiva Turbo" to turbo', () => {
      const result = findUiModelByBackendName('Saptiva Turbo')
      expect(result?.slug).toBe('turbo')
    })

    it('should match "saptiva turbo" (lowercase) to turbo', () => {
      const result = findUiModelByBackendName('saptiva turbo')
      expect(result?.slug).toBe('turbo')
    })

    it('should match "SAPTIVA TURBO" (uppercase) to turbo', () => {
      const result = findUiModelByBackendName('SAPTIVA TURBO')
      expect(result?.slug).toBe('turbo')
    })

    it('should match "Saptiva Cortex" to cortex', () => {
      const result = findUiModelByBackendName('Saptiva Cortex')
      expect(result?.slug).toBe('cortex')
    })

    it('should match "Saptiva Ops" to ops', () => {
      const result = findUiModelByBackendName('Saptiva Ops')
      expect(result?.slug).toBe('ops')
    })
  })

  describe('Normalized matching (underscores, hyphens)', () => {
    it('should match "saptiva-turbo" (hyphen) to turbo', () => {
      const result = findUiModelByBackendName('saptiva-turbo')
      expect(result?.slug).toBe('turbo')
    })

    it('should match "saptiva_turbo" (underscore) to turbo', () => {
      const result = findUiModelByBackendName('saptiva_turbo')
      expect(result?.slug).toBe('turbo')
    })

    it('should match "sap_turbo" (shortened underscore) to turbo', () => {
      const result = findUiModelByBackendName('sap_turbo')
      expect(result?.slug).toBe('turbo')
    })

    it('should match "SAPTIVA_CORTEX" (uppercase underscore) to cortex', () => {
      const result = findUiModelByBackendName('SAPTIVA_CORTEX')
      expect(result?.slug).toBe('cortex')
    })

    it('should match "saptiva-ops" (hyphen) to ops', () => {
      const result = findUiModelByBackendName('saptiva-ops')
      expect(result?.slug).toBe('ops')
    })
  })

  describe('Partial matching (contains slug)', () => {
    it('should match "turbo" (short name) to turbo', () => {
      const result = findUiModelByBackendName('turbo')
      expect(result?.slug).toBe('turbo')
    })

    it('should match "cortex" (short name) to cortex', () => {
      const result = findUiModelByBackendName('cortex')
      expect(result?.slug).toBe('cortex')
    })

    it('should match "ops" (short name) to ops', () => {
      const result = findUiModelByBackendName('ops')
      expect(result?.slug).toBe('ops')
    })

    it('should match "Saptiva  Turbo" (extra spaces) to turbo', () => {
      const result = findUiModelByBackendName('Saptiva  Turbo')
      expect(result?.slug).toBe('turbo')
    })
  })

  describe('Unknown models', () => {
    it('should return null for unknown model name', () => {
      const result = findUiModelByBackendName('Unknown Model')
      expect(result).toBeNull()
    })

    it('should return null for empty string', () => {
      const result = findUiModelByBackendName('')
      expect(result).toBeNull()
    })

    it('should return null for completely unrelated name', () => {
      const result = findUiModelByBackendName('GPT-4')
      expect(result).toBeNull()
    })
  })

  describe('Edge cases', () => {
    it('should handle mixed case with special characters', () => {
      const result = findUiModelByBackendName('SaPtIvA_TuRbO')
      expect(result?.slug).toBe('turbo')
    })

    it('should handle trailing/leading whitespace', () => {
      const result = findUiModelByBackendName('  Saptiva Turbo  ')
      expect(result?.slug).toBe('turbo')
    })
  })
})

describe('modelMap - resolveBackendId', () => {
  describe('Backend ID resolution', () => {
    it('should return exact backend name for "Saptiva Turbo"', () => {
      const backendModels = ['Saptiva Turbo', 'Saptiva Cortex', 'Saptiva Ops']
      const result = resolveBackendId(backendModels, 'turbo')
      expect(result).toBe('Saptiva Turbo')
    })

    it('should return exact backend name for "saptiva turbo" (lowercase)', () => {
      const backendModels = ['saptiva turbo', 'saptiva cortex']
      const result = resolveBackendId(backendModels, 'turbo')
      expect(result).toBe('saptiva turbo')
    })

    it('should return exact backend name for "saptiva-turbo" (hyphenated)', () => {
      const backendModels = ['saptiva-turbo', 'saptiva-cortex']
      const result = resolveBackendId(backendModels, 'turbo')
      expect(result).toBe('saptiva-turbo')
    })

    it('should return exact backend name for "SAPTIVA_TURBO" (uppercase underscore)', () => {
      const backendModels = ['SAPTIVA_TURBO', 'SAPTIVA_CORTEX']
      const result = resolveBackendId(backendModels, 'turbo')
      expect(result).toBe('SAPTIVA_TURBO')
    })

    it('should prefer first match when multiple variants exist', () => {
      const backendModels = ['Saptiva Turbo', 'saptiva_turbo', 'turbo']
      const result = resolveBackendId(backendModels, 'turbo')
      expect(result).toBe('Saptiva Turbo')
    })
  })

  describe('Unavailable models', () => {
    it('should return null when model slug not available in backend', () => {
      const backendModels = ['Saptiva Cortex', 'Saptiva Ops']
      const result = resolveBackendId(backendModels, 'turbo')
      expect(result).toBeNull()
    })

    it('should return null for invalid slug', () => {
      const backendModels = ['Saptiva Turbo']
      const result = resolveBackendId(backendModels, 'nonexistent')
      expect(result).toBeNull()
    })

    it('should return null for empty backend list', () => {
      const result = resolveBackendId([], 'turbo')
      expect(result).toBeNull()
    })
  })
})

describe('modelMap - buildModelList', () => {
  it('should build complete list with all models available', () => {
    const backendModels = ['Saptiva Turbo', 'Saptiva Cortex', 'Saptiva Ops']
    const result = buildModelList(backendModels)

    expect(result).toHaveLength(MODEL_CATALOG.length)
    expect(result.every((item) => item.available)).toBe(true)
    expect(result.every((item) => item.backendId !== null)).toBe(true)
  })

  it('should mark unavailable models correctly', () => {
    const backendModels = ['Saptiva Turbo'] // Only turbo available
    const result = buildModelList(backendModels)

    const turbo = result.find((m) => m.model.slug === 'turbo')
    const cortex = result.find((m) => m.model.slug === 'cortex')
    const ops = result.find((m) => m.model.slug === 'ops')

    expect(turbo?.available).toBe(true)
    expect(turbo?.backendId).toBe('Saptiva Turbo')

    expect(cortex?.available).toBe(false)
    expect(cortex?.backendId).toBeNull()

    expect(ops?.available).toBe(false)
    expect(ops?.backendId).toBeNull()
  })

  it('should handle case-insensitive backend names', () => {
    const backendModels = ['saptiva turbo', 'SAPTIVA_CORTEX']
    const result = buildModelList(backendModels)

    const turbo = result.find((m) => m.model.slug === 'turbo')
    const cortex = result.find((m) => m.model.slug === 'cortex')

    expect(turbo?.available).toBe(true)
    expect(turbo?.backendId).toBe('saptiva turbo')

    expect(cortex?.available).toBe(true)
    expect(cortex?.backendId).toBe('SAPTIVA_CORTEX')
  })

  it('should handle empty backend list', () => {
    const result = buildModelList([])

    expect(result).toHaveLength(MODEL_CATALOG.length)
    expect(result.every((item) => !item.available)).toBe(true)
    expect(result.every((item) => item.backendId === null)).toBe(true)
  })
})

describe('modelMap - getDefaultModelSlug', () => {
  it('should return correct slug for "Saptiva Turbo"', () => {
    const result = getDefaultModelSlug('Saptiva Turbo')
    expect(result).toBe('turbo')
  })

  it('should return correct slug for "saptiva cortex"', () => {
    const result = getDefaultModelSlug('saptiva cortex')
    expect(result).toBe('cortex')
  })

  it('should return correct slug for "SAPTIVA_OPS"', () => {
    const result = getDefaultModelSlug('SAPTIVA_OPS')
    expect(result).toBe('ops')
  })

  it('should fallback to first catalog model for unknown name', () => {
    const result = getDefaultModelSlug('Unknown Model')
    expect(result).toBe(MODEL_CATALOG[0]?.slug || 'turbo')
  })

  it('should fallback to first catalog model for null', () => {
    const result = getDefaultModelSlug(null)
    expect(result).toBe(MODEL_CATALOG[0]?.slug || 'turbo')
  })

  it('should fallback to first catalog model for empty string', () => {
    const result = getDefaultModelSlug('')
    expect(result).toBe(MODEL_CATALOG[0]?.slug || 'turbo')
  })
})

describe('modelMap - isValidSlug', () => {
  it('should return true for valid slugs', () => {
    expect(isValidSlug('turbo')).toBe(true)
    expect(isValidSlug('cortex')).toBe(true)
    expect(isValidSlug('ops')).toBe(true)
  })

  it('should return false for invalid slugs', () => {
    expect(isValidSlug('invalid')).toBe(false)
    expect(isValidSlug('gpt-4')).toBe(false)
    expect(isValidSlug('')).toBe(false)
  })
})

describe('Integration tests - Full workflow', () => {
  it('should correctly map backend models to UI and resolve IDs', () => {
    // Simulate backend response with various naming conventions
    const backendModels = ['Saptiva Turbo', 'saptiva_cortex', 'SAPTIVA-OPS']

    // Build model list (what store.loadModels does)
    const modelList = buildModelList(backendModels)

    // All should be available
    expect(modelList.every((m) => m.available)).toBe(true)

    // Verify each model has correct mapping
    const turbo = modelList.find((m) => m.model.slug === 'turbo')
    expect(turbo?.backendId).toBe('Saptiva Turbo')

    const cortex = modelList.find((m) => m.model.slug === 'cortex')
    expect(cortex?.backendId).toBe('saptiva_cortex')

    const ops = modelList.find((m) => m.model.slug === 'ops')
    expect(ops?.backendId).toBe('SAPTIVA-OPS')

    // Verify resolving slug back to backend ID
    expect(resolveBackendId(backendModels, 'turbo')).toBe('Saptiva Turbo')
    expect(resolveBackendId(backendModels, 'cortex')).toBe('saptiva_cortex')
    expect(resolveBackendId(backendModels, 'ops')).toBe('SAPTIVA-OPS')
  })

  it('should handle partial availability gracefully', () => {
    const backendModels = ['Saptiva Turbo'] // Only one model available

    const modelList = buildModelList(backendModels)

    // Turbo should be available
    const turbo = modelList.find((m) => m.model.slug === 'turbo')
    expect(turbo?.available).toBe(true)
    expect(turbo?.backendId).toBe('Saptiva Turbo')

    // Others should be unavailable but still in catalog
    const cortex = modelList.find((m) => m.model.slug === 'cortex')
    expect(cortex?.available).toBe(false)
    expect(cortex?.backendId).toBeNull()
    expect(cortex?.model.displayName).toBe('Saptiva Cortex')
    expect(cortex?.model.description).toBeTruthy()
  })
})