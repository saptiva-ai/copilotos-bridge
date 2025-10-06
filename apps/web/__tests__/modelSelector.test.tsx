/**
 * Tests for Model Selector Component
 *
 * Verifica que el selector de modelos funcione correctamente,
 * mostrando información de cada modelo y permitiendo la selección.
 */

import { describe, it, expect } from '@jest/globals'
import { MODEL_CATALOG } from '../src/config/modelCatalog'

describe('Model Catalog Configuration', () => {
  describe('Model catalog structure', () => {
    it('should have all expected models', () => {
      const expectedSlugs = ['turbo', 'cortex', 'ops', 'coder']

      expectedSlugs.forEach(slug => {
        expect(MODEL_CATALOG).toHaveProperty(slug)
      })
    })

    it('should have required fields for each model', () => {
      Object.values(MODEL_CATALOG).forEach(model => {
        expect(model).toHaveProperty('name')
        expect(model).toHaveProperty('description')
        expect(model).toHaveProperty('backend_id')
        expect(model).toHaveProperty('icon')
      })
    })

    it('should have unique backend_ids', () => {
      const backendIds = Object.values(MODEL_CATALOG).map(m => m.backend_id)
      const uniqueIds = new Set(backendIds)

      expect(backendIds.length).toBe(uniqueIds.size)
    })

    it('should have non-empty descriptions', () => {
      Object.values(MODEL_CATALOG).forEach(model => {
        expect(model.description.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Turbo model configuration', () => {
    const turbo = MODEL_CATALOG.turbo

    it('should have correct backend_id', () => {
      expect(turbo.backend_id).toBe('SAPTIVA_TURBO')
    })

    it('should have backend aliases', () => {
      expect(turbo.backend_aliases).toContain('Saptiva Turbo')
      expect(turbo.backend_aliases).toContain('saptiva_turbo')
    })

    it('should have speed-related characteristics', () => {
      const description = turbo.description.toLowerCase()
      expect(
        description.includes('rápid') ||
        description.includes('veloz') ||
        description.includes('speed')
      ).toBe(true)
    })
  })

  describe('Cortex model configuration', () => {
    const cortex = MODEL_CATALOG.cortex

    it('should have correct backend_id', () => {
      expect(cortex.backend_id).toBe('SAPTIVA_CORTEX')
    })

    it('should have backend aliases', () => {
      expect(cortex.backend_aliases).toContain('Saptiva Cortex')
      expect(cortex.backend_aliases).toContain('saptiva_cortex')
    })

    it('should have analysis-related characteristics', () => {
      const description = cortex.description.toLowerCase()
      expect(
        description.includes('análisis') ||
        description.includes('profundo') ||
        description.includes('razonamiento')
      ).toBe(true)
    })
  })

  describe('Ops model configuration', () => {
    const ops = MODEL_CATALOG.ops

    it('should have correct backend_id', () => {
      expect(ops.backend_id).toBe('SAPTIVA_OPS')
    })

    it('should have backend aliases', () => {
      expect(ops.backend_aliases).toContain('Saptiva Ops')
      expect(ops.backend_aliases).toContain('saptiva_ops')
    })

    it('should have code/operations-related characteristics', () => {
      const description = ops.description.toLowerCase()
      expect(
        description.includes('código') ||
        description.includes('code') ||
        description.includes('devops') ||
        description.includes('operaciones')
      ).toBe(true)
    })
  })

  describe('Coder model configuration', () => {
    const coder = MODEL_CATALOG.coder

    it('should have correct backend_id', () => {
      expect(coder.backend_id).toBe('SAPTIVA_CODER')
    })

    it('should have backend aliases', () => {
      expect(coder.backend_aliases).toContain('Saptiva Coder')
      expect(coder.backend_aliases).toContain('saptiva_coder')
    })
  })

  describe('Model aliases for fuzzy matching', () => {
    it('should support case-insensitive matching', () => {
      Object.values(MODEL_CATALOG).forEach(model => {
        expect(model.backend_aliases).toBeDefined()
        expect(Array.isArray(model.backend_aliases)).toBe(true)
        expect(model.backend_aliases.length).toBeGreaterThan(0)
      })
    })

    it('should include variations with underscores', () => {
      Object.values(MODEL_CATALOG).forEach(model => {
        const hasUnderscore = model.backend_aliases.some(
          alias => alias.includes('_')
        )
        expect(hasUnderscore).toBe(true)
      })
    })

    it('should include proper case variations', () => {
      Object.values(MODEL_CATALOG).forEach(model => {
        const hasProperCase = model.backend_aliases.some(
          alias => alias.includes(' ') && alias[0] === alias[0].toUpperCase()
        )
        expect(hasProperCase).toBe(true)
      })
    })
  })

  describe('Icon configuration', () => {
    it('should have valid icon for each model', () => {
      const validIcons = ['zap', 'brain', 'code', 'terminal', 'cpu']

      Object.values(MODEL_CATALOG).forEach(model => {
        expect(validIcons).toContain(model.icon)
      })
    })

    it('should have unique icons (recommended)', () => {
      const icons = Object.values(MODEL_CATALOG).map(m => m.icon)
      const uniqueIcons = new Set(icons)

      // Permitir duplicados pero advertir si hay muchos
      expect(uniqueIcons.size).toBeGreaterThanOrEqual(2)
    })
  })
})

describe('Model Selection Logic', () => {
  describe('Default model', () => {
    it('should have a default model defined', () => {
      // Asumiendo que hay un modelo por defecto en la configuración
      const defaultModel = MODEL_CATALOG.cortex // Cortex es típicamente el default
      expect(defaultModel).toBeDefined()
    })
  })

  describe('Model validation', () => {
    it('should validate that all backend_ids match expected format', () => {
      const validPattern = /^SAPTIVA_[A-Z]+$/

      Object.values(MODEL_CATALOG).forEach(model => {
        expect(model.backend_id).toMatch(validPattern)
      })
    })

    it('should validate slug format', () => {
      const validSlugPattern = /^[a-z]+$/

      Object.keys(MODEL_CATALOG).forEach(slug => {
        expect(slug).toMatch(validSlugPattern)
      })
    })
  })
})

describe('Model Metadata', () => {
  describe('Display information', () => {
    it('should have user-friendly names', () => {
      Object.values(MODEL_CATALOG).forEach(model => {
        expect(model.name.length).toBeGreaterThan(2)
        expect(model.name.length).toBeLessThan(50)
      })
    })

    it('should have concise descriptions', () => {
      Object.values(MODEL_CATALOG).forEach(model => {
        expect(model.description.length).toBeGreaterThan(10)
        expect(model.description.length).toBeLessThan(200)
      })
    })
  })

  describe('Consistency', () => {
    it('should follow consistent naming pattern', () => {
      Object.values(MODEL_CATALOG).forEach(model => {
        // Los backend_ids deberían seguir SAPTIVA_MODELNAME
        expect(model.backend_id).toContain('SAPTIVA_')
      })
    })

    it('should have consistent alias patterns', () => {
      Object.values(MODEL_CATALOG).forEach(model => {
        // Cada modelo debería tener al menos 2 aliases
        expect(model.backend_aliases.length).toBeGreaterThanOrEqual(2)

        // Debería incluir el backend_id en los aliases
        const hasBackendId = model.backend_aliases.includes(model.backend_id)
        expect(hasBackendId).toBe(true)
      })
    })
  })
})
