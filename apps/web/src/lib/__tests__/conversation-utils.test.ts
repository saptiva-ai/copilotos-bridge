/**
 * Unit tests for conversation utilities
 */

import { deriveTitleLocal } from '../conversation-utils'

describe('deriveTitleLocal', () => {
  it('should capitalize first letter', () => {
    expect(deriveTitleLocal('cómo configurar el servidor')).toBe('Cómo configurar el servidor')
  })

  it('should remove final punctuation', () => {
    expect(deriveTitleLocal('Qué es machine learning?')).toBe('Qué es machine learning')
    expect(deriveTitleLocal('Explícame sobre APIs.')).toBe('Explícame sobre APIs')
    expect(deriveTitleLocal('¿Cómo funciona?!...')).toBe('¿Cómo funciona') // All trailing punctuation removed
  })

  it('should filter leading stopwords', () => {
    expect(deriveTitleLocal('hola cómo está el clima')).toBe('Cómo está el clima')
    expect(deriveTitleLocal('ayuda por favor con este error')).toBe('Por favor con este error') // "ayuda" is stopword
    expect(deriveTitleLocal('necesito ayuda urgente')).toBe('Ayuda urgente') // "necesito" is stopword
  })

  it('should handle markdown formatting', () => {
    expect(deriveTitleLocal('**¿Qué** es _Python_?')).toBe('¿Qué es Python') // Preserves original case
    expect(deriveTitleLocal('`código` en ##markdown')).toBe('Código en markdown')
  })

  it('should limit to 70 characters', () => {
    const longText = 'Este es un texto muy largo que definitivamente excede los setenta caracteres permitidos para el título'
    const result = deriveTitleLocal(longText)
    expect(result.length).toBeLessThanOrEqual(70)
    expect(result).toBe('Este es un texto muy largo que definitivamente excede los setenta cara')
  })

  it('should take only first line', () => {
    const multiline = 'Primera línea importante\nSegunda línea\nTercera línea'
    expect(deriveTitleLocal(multiline)).toBe('Primera línea importante')
  })

  it('should return fallback for empty or very short input', () => {
    expect(deriveTitleLocal('')).toBe('Nueva conversación')
    expect(deriveTitleLocal('   ')).toBe('Nueva conversación')
    expect(deriveTitleLocal('hola')).toBe('Nueva conversación') // stopword -> empty -> fallback
    expect(deriveTitleLocal('ok')).toBe('Nueva conversación') // too short
  })

  it('should handle mixed stopwords correctly', () => {
    expect(deriveTitleLocal('gracias por la ayuda')).toBe('Por la ayuda')
    expect(deriveTitleLocal('hey there how are you')).toBe('There how are you')
  })

  it('should normalize whitespace', () => {
    expect(deriveTitleLocal('texto   con    espacios    múltiples')).toBe('Texto con espacios múltiples')
  })

  it('should preserve non-stopword content', () => {
    expect(deriveTitleLocal('máquinas de aprendizaje profundo')).toBe('Máquinas de aprendizaje profundo')
    expect(deriveTitleLocal('API REST con autenticación')).toBe('API REST con autenticación')
  })

  it('should handle special characters in names', () => {
    expect(deriveTitleLocal('¿Quién es Ángel Cisneros?')).toBe('¿Quién es Ángel Cisneros')
    expect(deriveTitleLocal('José María Pérez')).toBe('José María Pérez')
  })

  it('should not produce false positives', () => {
    const normalText = 'El resumen del artículo es interesante'
    const result = deriveTitleLocal(normalText)
    expect(result).toBe('El resumen del artículo es interesante')
  })
})
