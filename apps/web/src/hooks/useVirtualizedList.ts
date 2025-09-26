import { useState, useEffect, useCallback, useMemo } from 'react'

interface UseVirtualizedListOptions {
  itemHeight: number
  containerHeight: number
  overscan?: number
  items: any[]
}

interface VirtualizedListResult {
  visibleStartIndex: number
  visibleEndIndex: number
  totalHeight: number
  offsetY: number
  visibleItems: any[]
}

/**
 * Hook para virtualizar listas largas y mejorar el rendimiento
 * Solo renderiza los elementos visibles en el viewport
 */
export function useVirtualizedList({
  itemHeight,
  containerHeight,
  overscan = 5,
  items
}: UseVirtualizedListOptions): VirtualizedListResult {
  const [scrollTop, setScrollTop] = useState(0)

  const visibleItemCount = Math.ceil(containerHeight / itemHeight)
  const startIndex = Math.floor(scrollTop / itemHeight)
  const endIndex = Math.min(startIndex + visibleItemCount + overscan, items.length - 1)

  const visibleStartIndex = Math.max(0, startIndex - overscan)
  const visibleEndIndex = endIndex

  const totalHeight = items.length * itemHeight
  const offsetY = visibleStartIndex * itemHeight

  const visibleItems = useMemo(() => {
    return items.slice(visibleStartIndex, visibleEndIndex + 1).map((item, index) => ({
      ...item,
      virtualIndex: visibleStartIndex + index
    }))
  }, [items, visibleStartIndex, visibleEndIndex])

  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(event.currentTarget.scrollTop)
  }, [])

  return {
    visibleStartIndex,
    visibleEndIndex,
    totalHeight,
    offsetY,
    visibleItems,
    handleScroll
  }
}