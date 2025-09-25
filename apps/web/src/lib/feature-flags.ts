import * as React from 'react'

const FLAG_STORAGE_PREFIX = 'flag.'
const LAYOUT_GRID_FLAG_KEY = 'layout.grid.v1'

function parseBoolean(value: string | null | undefined): boolean | null {
  if (value === undefined || value === null) return null
  const normalized = value.trim().toLowerCase()
  if (normalized === 'true' || normalized === '1') return true
  if (normalized === 'false' || normalized === '0') return false
  return null
}

const envLayoutFlag = parseBoolean(process.env.NEXT_PUBLIC_FLAG_LAYOUT_GRID_V1)
const DEFAULT_LAYOUT_GRID_FLAG = envLayoutFlag ?? true

function readFlagFromStorage(key: string): boolean | null {
  if (typeof window === 'undefined') return null
  const stored = window.localStorage.getItem(`${FLAG_STORAGE_PREFIX}${key}`)
  return parseBoolean(stored)
}

function writeFlagToStorage(key: string, value: boolean) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(`${FLAG_STORAGE_PREFIX}${key}`, value ? 'true' : 'false')
}

export function isLayoutGridV1Enabled(): boolean {
  const stored = readFlagFromStorage(LAYOUT_GRID_FLAG_KEY)
  if (stored !== null) return stored
  return DEFAULT_LAYOUT_GRID_FLAG
}

export function setLayoutGridV1Enabled(enabled: boolean) {
  writeFlagToStorage(LAYOUT_GRID_FLAG_KEY, enabled)
}

export function useLayoutGridV1(): boolean {
  const [enabled, setEnabled] = React.useState<boolean>(DEFAULT_LAYOUT_GRID_FLAG)

  React.useEffect(() => {
    setEnabled(isLayoutGridV1Enabled())
  }, [])

  return enabled
}
