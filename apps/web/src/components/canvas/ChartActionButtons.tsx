"use client";

import { ArrowDownTrayIcon, TableCellsIcon } from "@heroicons/react/24/outline";

interface ChartActionButtonsProps {
  onDownloadPNG: () => void;
  onExportCSV: () => void;
}

/**
 * ChartActionButtons - Reusable action buttons for chart operations
 *
 * Features:
 * - Download chart as PNG
 * - Export data as CSV
 * - Compact horizontal layout aligned to the right
 *
 * Usage:
 *   <ChartActionButtons
 *     onDownloadPNG={handleDownloadPNG}
 *     onExportCSV={handleExportCSV}
 *   />
 */
export function ChartActionButtons({
  onDownloadPNG,
  onExportCSV,
}: ChartActionButtonsProps) {
  return (
    <div className="flex items-center justify-end gap-1">
      <button
        onClick={onDownloadPNG}
        className="p-1.5 text-muted hover:text-foreground hover:bg-surface-2 rounded transition-colors"
        title="Descargar PNG"
      >
        <ArrowDownTrayIcon className="h-4 w-4" />
      </button>
      <button
        onClick={onExportCSV}
        className="p-1.5 text-muted hover:text-foreground hover:bg-surface-2 rounded transition-colors"
        title="Exportar CSV"
      >
        <TableCellsIcon className="h-4 w-4" />
      </button>
    </div>
  );
}
