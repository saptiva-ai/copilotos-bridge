import { render, screen, fireEvent, waitFor } from '@testing-library/react'

import type { SaptivaKeyStatus } from '../../../lib/types'
import { SaptivaKeyForm } from '../SaptivaKeyForm'

const baseStatus: SaptivaKeyStatus = {
  configured: false,
  mode: 'demo',
  source: 'unset',
  hint: null,
  statusMessage: null,
  lastValidatedAt: null,
  updatedAt: null,
  updatedBy: null,
}

describe('SaptivaKeyForm', () => {
  it('submits trimmed API key and resets the field on success', async () => {
    const handleSubmit = jest.fn().mockResolvedValue(true)
    const handleClear = jest.fn().mockResolvedValue(true)
    const setError = jest.fn()

    render(
      <SaptivaKeyForm
        status={baseStatus}
        saving={false}
        error={null}
        isOpen
        onSubmit={handleSubmit}
        onClear={handleClear}
        setError={setError}
      />
    )

    const input = screen.getByLabelText(/SAPTIVA API Key/i) as HTMLInputElement
    fireEvent.change(input, { target: { value: '  test-demo-key  ' } })

    fireEvent.submit(input.form!)

    await waitFor(() => expect(handleSubmit).toHaveBeenCalledWith('test-demo-key'))
    await waitFor(() => expect(input.value).toBe(''))
  })

  it('shows validation error when field is empty', async () => {
    const handleSubmit = jest.fn()
    const handleClear = jest.fn().mockResolvedValue(true)
    const setError = jest.fn()

    render(
      <SaptivaKeyForm
        status={baseStatus}
        saving={false}
        error={null}
        isOpen
        onSubmit={handleSubmit}
        onClear={handleClear}
        setError={setError}
      />
    )

    const submitButton = screen.getByRole('button', { name: /guardar api key/i })
    fireEvent.click(submitButton)

    expect(handleSubmit).not.toHaveBeenCalled()
    expect(setError).toHaveBeenCalledWith('Ingresa una API key válida')
  })

  it('allows removing stored key when it comes from database', async () => {
    const status: SaptivaKeyStatus = {
      ...baseStatus,
      configured: true,
      mode: 'live',
      source: 'database',
      hint: '•••• demo',
      statusMessage: 'Key válida',
      updatedAt: '2025-09-23T22:11:00.000Z',
    }

    const handleSubmit = jest.fn().mockResolvedValue(true)
    const handleClear = jest.fn().mockResolvedValue(true)
    const setError = jest.fn()

    render(
      <SaptivaKeyForm
        status={status}
        saving={false}
        error={null}
        isOpen
        onSubmit={handleSubmit}
        onClear={handleClear}
        setError={setError}
      />
    )

    const input = screen.getByLabelText(/SAPTIVA API Key/i)
    fireEvent.change(input, { target: { value: 'new-key' } })

    const clearButton = screen.getByRole('button', { name: /eliminar key/i })
    fireEvent.click(clearButton)

    await waitFor(() => expect(handleClear).toHaveBeenCalledTimes(1))
    await waitFor(() => expect((input as HTMLInputElement).value).toBe(''))
  })
})
