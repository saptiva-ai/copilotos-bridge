"use client";

import * as React from "react";
import {
  ArrowDownTrayIcon,
  ArrowPathIcon,
  CalendarDaysIcon,
  CheckCircleIcon,
  ChevronDownIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  DocumentArrowDownIcon,
  ExclamationTriangleIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { cn } from "@/lib/utils";
import {
  HELP_PRESET_SECTIONS,
  MESES_LARGO,
  getAllPresetIds,
} from "./help-onboarding-content";
import { useReportGeneration } from "@/hooks/useReportGeneration";

/**
 * ReportGenerator — Benchmark report generation UI.
 *
 * Shows inside the HelpOnboardingMenu with:
 * - All presets selected by default
 * - Hidden checkboxes (expandable on demand)
 * - Download buttons for PPTX and PDF
 * - Progress bar during generation
 */
const MESES = [
  "Ene",
  "Feb",
  "Mar",
  "Abr",
  "May",
  "Jun",
  "Jul",
  "Ago",
  "Sep",
  "Oct",
  "Nov",
  "Dic",
] as const;

export function PeriodSelector({
  value,
  onChange,
  latestPeriod,
}: {
  value: string;
  onChange: (v: string) => void;
  latestPeriod: string | null;
}) {
  const [isOpen, setIsOpen] = React.useState(false);

  // Parse latestPeriod from DB — no fallback to current date to avoid future months
  const maxYear = latestPeriod
    ? parseInt(latestPeriod.split("-")[0], 10)
    : null;
  const maxMonth = latestPeriod
    ? parseInt(latestPeriod.split("-")[1], 10)
    : null;

  const [viewYear, setViewYear] = React.useState(
    maxYear ?? new Date().getFullYear(),
  );
  const ref = React.useRef<HTMLDivElement>(null);

  // Parse current value
  const selectedYear = value ? parseInt(value.split("-")[0], 10) : null;
  const selectedMonth = value ? parseInt(value.split("-")[1], 10) : null;

  // Close on click outside
  React.useEffect(() => {
    if (!isOpen) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [isOpen]);

  const handleSelect = (month: number) => {
    const mm = String(month).padStart(2, "0");
    onChange(`${viewYear}-${mm}`);
    setIsOpen(false);
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange("");
    setIsOpen(false);
  };

  const displayText =
    selectedYear && selectedMonth
      ? `${MESES_LARGO[selectedMonth - 1]} ${selectedYear}`
      : null;

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => {
          if (!maxYear) return; // Don't open until latestPeriod loads
          if (!isOpen && selectedYear) setViewYear(selectedYear);
          else if (!isOpen) setViewYear(maxYear);
          setIsOpen((o) => !o);
        }}
        className={cn(
          "inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium shadow-sm transition-all",
          value
            ? "border-primary/40 bg-primary/10 text-primary dark:border-primary/50 dark:bg-primary/20 dark:text-primary"
            : "border-border bg-white text-foreground hover:border-primary/40 hover:bg-primary/5 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:border-primary/50 dark:hover:bg-primary/10",
        )}
      >
        <CalendarDaysIcon className="h-4 w-4" />
        {displayText ??
          (maxMonth && maxYear
            ? `${MESES_LARGO[maxMonth - 1]} ${maxYear}`
            : "Último disponible")}
        {value && (
          <XMarkIcon
            className="h-3 w-3 text-muted hover:text-foreground"
            onClick={handleClear}
          />
        )}
      </button>

      {isOpen && (
        <div className="absolute left-0 top-full z-50 mt-1 w-[220px] rounded-lg border border-border bg-background p-2 shadow-lg">
          {/* Year navigation */}
          <div className="mb-2 flex items-center justify-between">
            <button
              type="button"
              onClick={() => setViewYear((y) => y - 1)}
              className="rounded p-1 text-muted transition-colors hover:bg-primary/10 hover:text-foreground"
            >
              <ChevronLeftIcon className="h-4 w-4" />
            </button>
            <span className="text-sm font-semibold text-foreground">
              {viewYear}
            </span>
            <button
              type="button"
              onClick={() => setViewYear((y) => y + 1)}
              disabled={maxYear != null && viewYear >= maxYear}
              className="rounded p-1 text-muted transition-colors hover:bg-primary/10 hover:text-foreground disabled:opacity-30"
            >
              <ChevronRightIcon className="h-4 w-4" />
            </button>
          </div>

          {/* Month grid 4×3 */}
          <div className="grid grid-cols-4 gap-1">
            {MESES.map((mes, i) => {
              const monthNum = i + 1;
              const isSelected =
                selectedYear === viewYear && selectedMonth === monthNum;
              const isFuture =
                maxYear != null &&
                maxMonth != null &&
                (viewYear > maxYear ||
                  (viewYear === maxYear && monthNum > maxMonth));

              return (
                <button
                  key={mes}
                  type="button"
                  disabled={isFuture}
                  onClick={() => handleSelect(monthNum)}
                  className={cn(
                    "rounded-md px-1 py-1.5 text-[11px] font-medium transition-all",
                    isSelected
                      ? "bg-primary text-white shadow-sm"
                      : "text-foreground hover:bg-primary/10",
                    isFuture && "cursor-not-allowed text-muted/40 opacity-40",
                  )}
                >
                  {mes}
                </button>
              );
            })}
          </div>

          {/* Quick clear */}
          {value && (
            <button
              type="button"
              onClick={handleClear}
              className="mt-2 w-full rounded-md border border-border py-1 text-[10px] text-muted transition-colors hover:bg-muted/10 hover:text-foreground"
            >
              Usar último (
              {maxMonth && maxYear
                ? `${MESES[maxMonth - 1]} ${maxYear}`
                : "auto"}
              )
            </button>
          )}
        </div>
      )}
    </div>
  );
}

interface ReportGeneratorProps {
  targetPeriod: string;
  onPeriodChange: (v: string) => void;
  latestPeriod: string | null;
}

export function ReportGenerator({
  targetPeriod,
  onPeriodChange,
  latestPeriod,
}: ReportGeneratorProps) {
  const allIds = React.useMemo(() => getAllPresetIds(), []);
  const [selectedIds, setSelectedIds] = React.useState<Set<string>>(
    () => new Set(allIds),
  );
  const [isCustomizing, setIsCustomizing] = React.useState(false);

  const {
    progress,
    generate,
    download,
    reset,
    isGenerating,
    isReady,
    isError,
  } = useReportGeneration();

  const handleToggleSection = React.useCallback(
    (sectionId: string) => {
      const section = HELP_PRESET_SECTIONS.find((s) => s.id === sectionId);
      if (!section) return;

      const sectionPresetIds = section.presets.map((p) => p.id);
      const allSelected = sectionPresetIds.every((id) => selectedIds.has(id));

      setSelectedIds((prev) => {
        const next = new Set(prev);
        for (const id of sectionPresetIds) {
          if (allSelected) {
            next.delete(id);
          } else {
            next.add(id);
          }
        }
        return next;
      });
    },
    [selectedIds],
  );

  const handleGenerate = React.useCallback(
    (format: "pptx" | "pdf" | "both") => {
      const ids =
        selectedIds.size === allIds.length ? null : Array.from(selectedIds);
      void generate(ids, format, targetPeriod || undefined);
    },
    [selectedIds, allIds.length, generate, targetPeriod],
  );

  const handleDownload = React.useCallback(
    (format: "pptx" | "pdf") => {
      void download(format);
    },
    [download],
  );

  const selectedCount = selectedIds.size;
  const progressPct = Math.round(progress.progress * 100);

  return (
    <div className="mt-5 rounded-lg border border-primary/20 bg-primary/5 p-3">
      {/* Header — contextual based on state */}
      <div className="flex items-center justify-between gap-2">
        <div
          className={cn(
            "flex items-center gap-1.5 text-xs font-semibold",
            isReady ? "text-emerald-600" : "text-foreground",
          )}
        >
          {isReady ? (
            <CheckCircleIcon className="h-4 w-4 text-emerald-500" />
          ) : (
            <DocumentArrowDownIcon className="h-4 w-4 text-primary" />
          )}
          {isReady ? "Reporte Benchmark" : "Generar Reporte Benchmark"}
          {(() => {
            const p = targetPeriod || latestPeriod;
            if (!p) return null;
            const y = parseInt(p.split("-")[0], 10);
            const m = parseInt(p.split("-")[1], 10);
            return (
              <span className="ml-1 font-normal text-muted">
                — {MESES_LARGO[m - 1]} {y}
              </span>
            );
          })()}
        </div>

        {/* Customize toggle — inline with header in idle state */}
        {progress.status === "idle" && (
          <button
            type="button"
            onClick={() => setIsCustomizing((c) => !c)}
            className="inline-flex items-center gap-1 text-[10px] text-muted transition-colors hover:text-foreground"
          >
            Personalizar secciones ({selectedCount}/{allIds.length})
            <ChevronDownIcon
              className={cn(
                "h-2.5 w-2.5 transition-transform",
                isCustomizing ? "rotate-180" : "rotate-0",
              )}
            />
          </button>
        )}
      </div>

      {/* Idle state: show generate buttons */}
      {progress.status === "idle" && (
        <>
          {/* Section checkboxes — 2-column grid (hidden by default) */}
          {isCustomizing && (
            <div className="mt-2">
              <div className="grid grid-cols-2 gap-x-2 gap-y-0.5">
                {HELP_PRESET_SECTIONS.map((section) => {
                  const sectionPresetIds = section.presets.map((p) => p.id);
                  const checkedCount = sectionPresetIds.filter((id) =>
                    selectedIds.has(id),
                  ).length;
                  const allChecked = checkedCount === sectionPresetIds.length;
                  const someChecked = checkedCount > 0 && !allChecked;

                  return (
                    <label
                      key={section.id}
                      className="flex cursor-pointer items-center gap-1.5 rounded px-1.5 py-1 text-[11px] text-foreground transition-colors hover:bg-primary/10"
                    >
                      <input
                        type="checkbox"
                        checked={allChecked}
                        ref={(el) => {
                          if (el) el.indeterminate = someChecked;
                        }}
                        onChange={() => handleToggleSection(section.id)}
                        className="h-3 w-3 rounded border-border text-primary accent-primary focus:ring-primary/50"
                      />
                      <span className="truncate">
                        {section.title}{" "}
                        <span className="text-muted">
                          ({sectionPresetIds.length})
                        </span>
                      </span>
                    </label>
                  );
                })}
              </div>

              {/* Select all / deselect all */}
              <div className="mt-1 flex gap-2 pl-1.5">
                <button
                  type="button"
                  onClick={() => setSelectedIds(new Set(allIds))}
                  className="text-[10px] font-medium text-primary hover:underline"
                >
                  Seleccionar todo
                </button>
                <span className="text-[10px] text-muted">|</span>
                <button
                  type="button"
                  onClick={() => setSelectedIds(new Set())}
                  className="text-[10px] font-medium text-primary hover:underline"
                >
                  Deseleccionar todo
                </button>
              </div>
            </div>
          )}

          {/* Generate buttons — compact row */}
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              onClick={() => handleGenerate("pptx")}
              disabled={selectedCount === 0}
              className="inline-flex items-center gap-1 rounded-md border border-primary/25 bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-primary transition-all hover:bg-primary/20 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ArrowDownTrayIcon className="h-3 w-3" />
              Descargar PPTX
            </button>
            <button
              type="button"
              onClick={() => handleGenerate("pdf")}
              disabled={selectedCount === 0}
              className="inline-flex items-center gap-1 rounded-md border border-primary/25 bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-primary transition-all hover:bg-primary/20 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ArrowDownTrayIcon className="h-3 w-3" />
              Descargar PDF
            </button>
            <button
              type="button"
              onClick={() => handleGenerate("both")}
              disabled={selectedCount === 0}
              className="inline-flex items-center gap-1 rounded-md border border-primary/25 bg-primary/20 px-2.5 py-1 text-[11px] font-semibold text-primary transition-all hover:bg-primary/30 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ArrowDownTrayIcon className="h-3 w-3" />
              Ambos
            </button>
          </div>
        </>
      )}

      {/* Generating state: compact progress bar */}
      {isGenerating && (
        <div className="mt-2">
          <div className="mb-1 flex items-center justify-between text-[11px]">
            <span className="text-muted">
              {progress.completed}/{progress.total} gráficas
            </span>
            <span className="font-medium text-primary">{progressPct}%</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-border">
            <div
              className="h-full rounded-full bg-primary transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          {progress.currentLabel && (
            <p className="mt-1 truncate text-[10px] text-muted">
              Procesando: {progress.currentLabel}
            </p>
          )}
        </div>
      )}

      {/* Ready state: compact success + download row */}
      {isReady && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <span className="mr-auto text-[11px] text-emerald-600">
            Reporte generado con {progress.completed} gráficas.
          </span>
          {progress.fileFormats.includes("pptx") && (
            <button
              type="button"
              onClick={() => handleDownload("pptx")}
              className="inline-flex items-center gap-1 rounded-md border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-700 transition-all hover:bg-emerald-500/20"
            >
              <ArrowDownTrayIcon className="h-3 w-3" />
              Descargar PPTX
            </button>
          )}
          {progress.fileFormats.includes("pdf") && (
            <button
              type="button"
              onClick={() => handleDownload("pdf")}
              className="inline-flex items-center gap-1 rounded-md border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-700 transition-all hover:bg-emerald-500/20"
            >
              <ArrowDownTrayIcon className="h-3 w-3" />
              Descargar PDF
            </button>
          )}
          <button
            type="button"
            onClick={reset}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-muted transition-colors hover:bg-muted/10 hover:text-foreground"
          >
            <ArrowPathIcon className="h-3 w-3" />
            Generar otro
          </button>
        </div>
      )}

      {/* Downloading state */}
      {progress.status === "downloading" && (
        <p className="mt-2 text-[11px] text-muted">Descargando archivo...</p>
      )}

      {/* Error state */}
      {isError && (
        <div className="mt-2">
          <div className="flex items-start gap-1.5 rounded-md border border-rose-500/20 bg-rose-500/10 px-2.5 py-2">
            <ExclamationTriangleIcon className="mt-px h-3.5 w-3.5 flex-shrink-0 text-rose-500" />
            <div>
              <p className="text-[11px] font-medium text-rose-600">
                Error al generar reporte
              </p>
              {progress.errorMessage && (
                <p className="mt-0.5 text-[10px] text-rose-500/80">
                  {progress.errorMessage}
                </p>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={reset}
            className="mt-1.5 text-[11px] text-primary hover:underline"
          >
            Intentar de nuevo
          </button>
        </div>
      )}
    </div>
  );
}

export default ReportGenerator;
