"use client";

import React, { useState, useRef, useEffect, useMemo } from "react";
import { CodeBracketIcon } from "@heroicons/react/24/outline";
import { cn } from "@/lib/utils";
import type { BankChartData } from "@/lib/types";
import dynamic from "next/dynamic";
import DOMPurify from "dompurify";
import { BankChartSkeleton } from "./BankChartSkeleton";
import { BankChartError } from "./BankChartError";
import { useTheme } from "next-themes";
import { ChartActionButtons } from "./ChartActionButtons";

const Plot = dynamic(() => import("react-plotly.js"), {
  ssr: false,
  loading: () => <BankChartSkeleton />,
});

interface BankChartCanvasViewProps {
  data: BankChartData;
  className?: string;
}

/**
 * BankChartCanvasView - Full visualization of bank chart in canvas sidebar
 *
 * Features:
 * - Full-size chart with complete Plotly controls
 * - Tabs: Chart | SQL Query | Interpretation
 * - Enriched metadata (banks, time range, source)
 * - Reuses Plotly rendering logic optimized for canvas
 *
 * Usage:
 *   <BankChartCanvasView data={bankChartData} />
 */
export function BankChartCanvasView({
  data,
  className,
}: BankChartCanvasViewProps) {
  const { resolvedTheme } = useTheme();
  const [activeTab, setActiveTab] = useState<"visualization" | "data">(
    "visualization",
  );
  const plotContainerRef = useRef<HTMLDivElement>(null);
  const [plotKey, setPlotKey] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  // Validate chart data immediately (not in useEffect)
  const validateData = (): string | null => {
    if (!data?.plotly_config?.data || !Array.isArray(data.plotly_config.data)) {
      return "Datos de gráfica inválidos o faltantes";
    }

    if (!data?.metric_name) {
      return "Nombre de métrica faltante";
    }

    if (!data?.bank_names || data.bank_names.length === 0) {
      return "No se especificaron bancos";
    }

    return null;
  };

  const validationError = validateData();

  // Force re-render of Plotly when container size changes or theme changes
  useEffect(() => {
    if (!plotContainerRef.current) return;

    const resizeObserver = new ResizeObserver(() => {
      // Force Plotly to recalculate layout
      setPlotKey((prev) => prev + 1);
    });

    resizeObserver.observe(plotContainerRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  // Force re-render when theme changes
  useEffect(() => {
    setPlotKey((prev) => prev + 1);
  }, [resolvedTheme]);

  // Extract enriched metadata
  const sqlQuery = data.metadata?.sql_generated;
  const metricInterpretation = data.metadata?.metric_interpretation;

  // 🔍 OBSERVABILITY: Debug logging for analytics data (ISSUE-6)
  useEffect(() => {
    const isDevelopment = process.env.NODE_ENV === "development";
    if (!isDevelopment) return;

    const plotlyData = data.plotly_config?.data || [];
    const firstPoint = plotlyData[0];
    const lastPoint = plotlyData[plotlyData.length - 1];

    // eslint-disable-next-line no-console
    console.log("[🔍 BankChartCanvasView] Analytics Debug:", {
      metric_name: data.metric_name,
      bank_names: data.bank_names,
      time_range: {
        start: data.time_range?.start,
        end: data.time_range?.end,
        is_valid_start: !isNaN(
          new Date(data.time_range?.start || "").getTime(),
        ),
        is_valid_end: !isNaN(new Date(data.time_range?.end || "").getTime()),
      },
      data_points: {
        total: plotlyData.length,
        first_x: firstPoint?.x?.[0],
        first_y: firstPoint?.y?.[0],
        last_x: lastPoint?.x?.[lastPoint.x.length - 1],
        last_y: lastPoint?.y?.[lastPoint.y.length - 1],
      },
      metadata: {
        has_sql: !!sqlQuery,
        sql_length: sqlQuery?.length,
        has_interpretation: !!metricInterpretation,
        keys: data.metadata ? Object.keys(data.metadata) : [],
      },
    });
  }, [data, sqlQuery, metricInterpretation]);

  // Sanitize user-generated content to prevent XSS attacks
  const sanitizedSQL = useMemo(() => {
    if (!sqlQuery) return null;
    // SQL queries should only contain plain text, no HTML tags
    return DOMPurify.sanitize(sqlQuery, {
      ALLOWED_TAGS: [],
      ALLOWED_ATTR: [],
    });
  }, [sqlQuery]);

  const sanitizedInterpretation = useMemo(() => {
    if (!metricInterpretation) return null;
    // Allow basic formatting tags for interpretation text
    return DOMPurify.sanitize(metricInterpretation, {
      ALLOWED_TAGS: ["p", "br", "strong", "em", "code", "ul", "ol", "li"],
      ALLOWED_ATTR: [],
    });
  }, [metricInterpretation]);

  // Retry handler
  const handleRetry = () => {
    setIsLoading(true);
    setPlotKey((prev) => prev + 1);
    setTimeout(() => setIsLoading(false), 1000);
  };

  // Download chart as PNG
  const handleDownloadPNG = async () => {
    if (typeof window === "undefined") return;

    try {
      const Plotly = await import("plotly.js-dist-min" as any);
      const plotElement = plotContainerRef.current?.querySelector(".plotly");

      if (plotElement) {
        await (Plotly as any).downloadImage(plotElement as any, {
          format: "png",
          width: 1200,
          height: 800,
          filename: `${data.metric_name}_${data.bank_names.join("_")}`,
        });
      }
    } catch (error) {
      // Silently handle error
    }
  };

  // Export data to CSV
  const handleExportCSV = () => {
    try {
      // Extract data from Plotly config
      const plotlyData = data.plotly_config?.data;
      if (!Array.isArray(plotlyData) || plotlyData.length === 0) return;

      // Create CSV header
      const headers = [
        "Banco",
        "Periodo",
        (data.metric_name || "Métrica").toUpperCase(),
      ];
      const rows: string[][] = [headers];

      // Extract rows from each trace
      plotlyData.forEach((trace: any) => {
        const bankName = trace.name || "Unknown";
        const xValues = trace.x || [];
        const yValues = trace.y || [];

        xValues.forEach((period: string, index: number) => {
          rows.push([bankName, period, String(yValues[index] || "")]);
        });
      });

      // Convert to CSV string
      const csvContent = rows.map((row) => row.join(",")).join("\n");

      // Download
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const link = document.createElement("a");
      const url = URL.createObjectURL(blob);

      link.setAttribute("href", url);
      link.setAttribute(
        "download",
        `${data.metric_name}_${data.bank_names.join("_")}.csv`,
      );
      link.style.visibility = "hidden";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      // Silently handle error
    }
  };

  // Saptiva Dual Theme: Chart configuration with dynamic colors
  // Plotly requires explicit colors, so we compute them based on theme
  const isDark = resolvedTheme === "dark";
  const textColor = isDark ? "#ffffff" : "#0a0a0a"; // White in dark, almost black in light
  const gridColor = isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)";
  const borderColor = isDark ? "rgba(255,255,255,0.2)" : "rgba(0,0,0,0.2)";

  // Safe access to plotly_config with fallback defaults
  const safeLayout = data.plotly_config?.layout || {};

  const plotlyLayout = {
    ...safeLayout,
    autosize: true,
    height: 500, // Increased from 320px
    margin: { l: 90, r: 15, t: 15, b: 50 }, // Increased left margin to prevent Y-axis tick clipping
    paper_bgcolor: "rgba(0,0,0,0)", // Transparent
    plot_bgcolor: "rgba(0,0,0,0)", // Transparent
    font: { color: textColor, size: 12 },
    hoverlabel: {
      bgcolor: isDark ? "#1a1a1a" : "#ffffff", // Dark background in dark mode
      bordercolor: isDark ? "#404040" : "#e5e5e5",
      font: { color: textColor, size: 13 },
    },
    xaxis: {
      ...(safeLayout.xaxis || {}),
      showgrid: false, // No vertical grid
      linecolor: borderColor,
      tickfont: { color: textColor },
    },
    yaxis: {
      ...(safeLayout.yaxis || {}),
      automargin: true, // Let Plotly automatically adjust margin for Y-axis labels
      gridcolor: gridColor,
      linecolor: borderColor,
      tickfont: { color: textColor },
    },
    legend: {
      ...(safeLayout.legend || {}),
      bgcolor: "rgba(0,0,0,0)",
      font: { color: textColor },
    },
  };

  // Early return for loading state
  if (isLoading) {
    return <BankChartSkeleton />;
  }

  // Early return for validation error
  if (validationError) {
    return <BankChartError message={validationError} onRetry={handleRetry} />;
  }

  return (
    <div className={cn("flex h-full flex-col", className)}>
      {/* Tabs with Action Buttons in same line */}
      <div className="flex items-center justify-between border-b border-border px-4">
        <div className="flex gap-4">
          <button
            onClick={() => setActiveTab("visualization")}
            className={cn(
              "pb-2 text-xs font-medium transition-colors border-b-2",
              activeTab === "visualization"
                ? "border-primary text-primary"
                : "border-transparent text-muted hover:text-foreground",
            )}
          >
            Gráfica
          </button>
          <button
            onClick={() => setActiveTab("data")}
            className={cn(
              "pb-2 text-xs font-medium transition-colors border-b-2",
              activeTab === "data"
                ? "border-primary text-primary"
                : "border-transparent text-muted hover:text-foreground",
            )}
          >
            Datos
          </button>
        </div>

        {/* Action Buttons - Right aligned on same line as tabs */}
        <ChartActionButtons
          onDownloadPNG={handleDownloadPNG}
          onExportCSV={handleExportCSV}
        />
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === "visualization" && (
          <div className="space-y-4 p-4">
            {/* Compact KPI Row */}
            <div className="flex items-center gap-4 text-xs mb-4 pb-3 border-b border-border/50">
              <div>
                <span className="text-muted">Bancos: </span>
                <span className="text-foreground font-medium">
                  {data.bank_names.join(", ")}
                </span>
              </div>
              <div className="text-muted">|</div>
              <div>
                <span className="text-muted">Actualizado: </span>
                <span className="text-foreground font-medium">
                  {(() => {
                    const asOfDate = new Date(data.data_as_of);
                    return isNaN(asOfDate.getTime())
                      ? "—"
                      : asOfDate.toLocaleDateString("es-MX", {
                          day: "numeric",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        });
                  })()}
                </span>
              </div>
            </div>

            {/* Chart - Larger */}
            <div ref={plotContainerRef} className="w-full h-[500px]">
              <Plot
                key={plotKey}
                data={(data.plotly_config?.data || []) as any}
                layout={plotlyLayout as any}
                config={{
                  responsive: true,
                  displayModeBar: false, // Hide toolbar
                  displaylogo: false,
                }}
                className="w-full"
                useResizeHandler
                style={{ width: "100%", height: "100%" }}
              />
            </div>

            {/* SQL Query Section - Below Chart (ALWAYS VISIBLE) */}
            <div className="space-y-3 pt-4 border-t border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm">
                  <CodeBracketIcon className="h-4 w-4 text-primary" />
                  <span className="font-medium text-foreground">
                    Consulta SQL
                  </span>
                </div>
                {sanitizedSQL && (
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(sanitizedSQL);
                    }}
                    className="px-3 py-1.5 text-xs font-medium text-muted hover:text-foreground bg-surface-2 hover:bg-surface rounded transition-colors"
                  >
                    Copiar
                  </button>
                )}
              </div>
              {sanitizedSQL ? (
                <pre className="overflow-x-auto bg-surface border border-border p-4 text-xs text-foreground dark:text-white font-mono rounded leading-relaxed">
                  {sanitizedSQL}
                </pre>
              ) : (
                <div className="p-4 bg-surface/50 border border-border/50 rounded text-xs text-muted italic">
                  No hay consulta SQL disponible para esta visualización
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "data" && (
          <div className="space-y-4 p-4">
            <div className="rounded-lg border border-border bg-transparent overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-surface-2 border-b border-border">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-primary uppercase tracking-wide text-xs">
                        Banco
                      </th>
                      <th className="px-4 py-3 text-left font-medium text-primary uppercase tracking-wide text-xs">
                        Periodo
                      </th>
                      <th className="px-4 py-3 text-right font-medium text-primary uppercase tracking-wide text-xs">
                        {data.metric_name}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {(data.plotly_config?.data || []).map(
                      (trace: any, traceIdx: number) => {
                        const bankName = trace.name || `Banco ${traceIdx + 1}`;
                        const xValues = trace.x || [];
                        const yValues = trace.y || [];

                        return xValues.map((period: string, idx: number) => (
                          <tr
                            key={`${traceIdx}-${idx}`}
                            className="hover:bg-surface-2/50 transition-colors"
                          >
                            <td className="px-4 py-2.5 text-foreground font-medium">
                              {bankName}
                            </td>
                            <td className="px-4 py-2.5 text-muted">{period}</td>
                            <td className="px-4 py-2.5 text-right text-foreground font-mono">
                              {typeof yValues[idx] === "number"
                                ? yValues[idx].toLocaleString("es-MX", {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                  })
                                : yValues[idx]}
                            </td>
                          </tr>
                        ));
                      },
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
