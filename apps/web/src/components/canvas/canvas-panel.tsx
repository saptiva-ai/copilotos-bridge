"use client";

import * as React from "react";
import { apiClient } from "@/lib/api-client";
import {
  clampCanvasWidthPercent,
  useCanvasStore,
} from "@/lib/stores/canvas-store";
import { cn } from "@/lib/utils";
import type { ArtifactRecord } from "@/lib/types";
import { MarkdownRenderer } from "./markdown-renderer";
import { MermaidGraph } from "./mermaid-graph";
import { graphToMermaid } from "@/lib/utils/graph-to-mermaid";
import { AuditDetailView } from "./views/AuditDetailView";
import { BankChartCanvasView } from "./BankChartCanvasView";
import { CanvasErrorBoundary } from "./CanvasErrorBoundary";

interface CanvasPanelProps {
  className?: string;
  reportPdfUrl?: string;
}

function ArtifactSkeleton() {
  return (
    <div className="space-y-3">
      <div className="h-4 w-1/3 rounded-md bg-surface-2 animate-pulse" />
      <div className="h-3 w-1/2 rounded-md bg-surface animate-pulse" />
      <div className="space-y-2">
        <div className="h-3 w-full rounded-md bg-surface animate-pulse" />
        <div className="h-3 w-5/6 rounded-md bg-surface animate-pulse" />
        <div className="h-3 w-4/6 rounded-md bg-surface animate-pulse" />
      </div>
    </div>
  );
}

function GraphFallback({ data }: { data: any }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-3 text-xs text-muted">
      <p className="mb-2 font-semibold text-foreground">Vista de grafo</p>
      <pre className="overflow-auto text-[11px] leading-relaxed">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

export function CanvasPanel({ className, reportPdfUrl }: CanvasPanelProps) {
  const activeArtifactId = useCanvasStore((state) => state.activeArtifactId);
  const isSidebarOpen = useCanvasStore((state) => state.isSidebarOpen);
  const toggleSidebar = useCanvasStore((state) => state.toggleSidebar);
  const activeArtifactData = useCanvasStore(
    (state) => state.activeArtifactData,
  );
  // 🆕 Bank chart state for canvas visualization
  const activeBankChart = useCanvasStore((state) => state.activeBankChart);
  const canvasWidthPercent = useCanvasStore(
    (state) => state.canvasWidthPercent,
  );
  const setCanvasWidth = useCanvasStore((state) => state.setCanvasWidth);
  const cacheRef = React.useRef(new Map<string, ArtifactRecord>());
  const safeCanvasWidth = clampCanvasWidthPercent(canvasWidthPercent);

  const [artifact, setArtifact] = React.useState<ArtifactRecord | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const draggingRef = React.useRef(false);

  const handleMouseDown = React.useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    draggingRef.current = true;
  }, []);

  // Cleanup cache on unmount (when conversation changes due to key prop)
  React.useEffect(() => {
    return () => {
      // Clear cache to prevent memory leaks and stale data
      cacheRef.current.clear();
    };
  }, []);

  React.useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!draggingRef.current) return;
      const viewportWidth = window.innerWidth;
      // Calculate width as percentage of viewport (30-70%)
      const widthPercent = ((viewportWidth - e.clientX) / viewportWidth) * 100;
      setCanvasWidth(widthPercent); // Store will constrain to 30-70%
    };

    const onUp = () => {
      draggingRef.current = false;
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [setCanvasWidth]);

  React.useEffect(() => {
    let cancelled = false;

    // If showing PDF report, don't fetch artifact
    if (reportPdfUrl) {
      setArtifact(null);
      setError(null);
      setLoading(false);
      return;
    }

    // 🆕 If showing bank chart, don't fetch artifact (data already in activeBankChart)
    if (activeBankChart) {
      setArtifact(null);
      setError(null);
      setLoading(false);
      return;
    }

    if (!activeArtifactId) {
      setArtifact(null);
      setError(null);
      setLoading(false);
      return;
    }

    const cached = cacheRef.current.get(activeArtifactId);
    if (cached) {
      setArtifact(cached);
      return;
    }

    const fetchArtifact = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await apiClient.getArtifact(activeArtifactId);
        cacheRef.current.set(activeArtifactId, data);
        if (!cancelled) {
          setArtifact(data);
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(
            err?.response?.data?.detail ||
              "No se pudo cargar el artefacto. Intenta nuevamente.",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void fetchArtifact();

    return () => {
      cancelled = true;
    };
  }, [activeArtifactId, reportPdfUrl, activeBankChart]);

  const renderContent = () => {
    // 🆕 Priority 1: activeBankChart (bank chart visualizations)
    if (activeBankChart) {
      return <BankChartCanvasView data={activeBankChart} />;
    }

    // Priority 2: render audit detail directly if provided by store
    if (activeArtifactData) {
      // Accept plain payload or wrapped {type, payload}
      const payload = (activeArtifactData as any).payload || activeArtifactData;
      return <AuditDetailView report={payload} />;
    }

    if (reportPdfUrl) {
      return (
        <iframe
          src={reportPdfUrl}
          className="h-full w-full rounded-lg border-0 bg-white"
          title="Audit Report"
        />
      );
    }

    if (!activeArtifactId) {
      return (
        <div className="flex h-full items-center justify-center text-sm text-muted">
          Selecciona un artefacto desde el chat.
        </div>
      );
    }

    if (loading) {
      return <ArtifactSkeleton />;
    }

    if (error) {
      return (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
          {error}
        </div>
      );
    }

    if (!artifact) {
      return null;
    }

    const safeContent =
      typeof artifact.content === "string"
        ? artifact.content
        : JSON.stringify(artifact.content, null, 2);

    switch (artifact.type) {
      case "markdown":
      case "code":
        return <MarkdownRenderer content={safeContent} />;
      case "graph":
        try {
          let chart = safeContent;
          if (typeof artifact.content === "object") {
            chart = graphToMermaid(artifact.content as any);
          } else {
            try {
              const parsed = JSON.parse(artifact.content as string);
              chart = graphToMermaid(parsed);
            } catch {
              // Use raw content when parsing fails
            }
          }
          return <MermaidGraph chart={chart} />;
        } catch {
          return <GraphFallback data={artifact.content} />;
        }
      case "bank_chart": // 🆕 Case for persisted bank charts
        try {
          const chartData =
            typeof artifact.content === "string"
              ? JSON.parse(artifact.content)
              : artifact.content;
          return <BankChartCanvasView data={chartData} />;
        } catch {
          return (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
              Error al cargar gráfica. El formato de datos no es válido.
            </div>
          );
        }
      default:
        return (
          <div className="rounded-lg border border-border bg-surface p-3 text-sm text-muted">
            Tipo de artefacto no soportado.
          </div>
        );
    }
  };

  return (
    <>
      <div
        data-testid="canvas-panel"
        data-canvas-panel
        style={
          isSidebarOpen &&
          typeof window !== "undefined" &&
          window.innerWidth >= 768
            ? {
                width: `${safeCanvasWidth}vw`,
                position: "relative" as const,
                zIndex: 40,
                backfaceVisibility: "hidden" as const,
                WebkitBackfaceVisibility: "hidden" as const,
              }
            : {
                width: 0,
                position: "relative" as const,
                zIndex: 40,
              }
        }
        className={cn(
          "h-full bg-surface border-l border-border text-foreground relative flex flex-col overflow-hidden",
          // GPU-accelerated transitions (fix for Mac Chrome)
          "transition-[opacity,transform] duration-200 ease-out",
          "will-change-transform will-change-opacity",
          // Responsive width with safe constraints
          "flex-shrink-0",
          isSidebarOpen
            ? "opacity-100 translate-x-0 w-full md:w-auto" // Full width on mobile, use inline style on desktop
            : "opacity-0 translate-x-full pointer-events-none",
          className,
        )}
      >
        {/* Resize handle - only visible on desktop */}
        <div
          className="hidden md:block absolute left-0 top-0 bottom-0 w-1.5 cursor-col-resize bg-border/30 hover:bg-primary/50 active:bg-primary transition-colors z-50"
          onMouseDown={handleMouseDown}
          title="Arrastrar para ajustar el ancho"
        />
        <Header
          reportPdfUrl={reportPdfUrl}
          artifact={artifact}
          activeArtifactData={activeArtifactData}
          activeBankChart={activeBankChart}
          onToggle={toggleSidebar}
          isSidebarOpen={isSidebarOpen}
        />

        <div className="flex-1 px-4 md:px-6 py-4 overflow-y-auto">
          <CanvasErrorBoundary>{renderContent()}</CanvasErrorBoundary>
        </div>
      </div>
    </>
  );
}

function Header({
  reportPdfUrl,
  artifact,
  activeArtifactData,
  activeBankChart,
  onToggle,
  isSidebarOpen,
}: {
  reportPdfUrl?: string;
  artifact: ArtifactRecord | null;
  activeArtifactData: any;
  activeBankChart: any;
  onToggle: () => void;
  isSidebarOpen: boolean;
}) {
  const auditPayload = React.useMemo(() => {
    if (!activeArtifactData) return null;
    const payload = (activeArtifactData as any).payload || activeArtifactData;
    return payload && (payload as any).stats ? payload : null;
  }, [activeArtifactData]);

  const displayName = React.useMemo(() => {
    // Bank chart takes priority
    if (activeBankChart?.metric_name) {
      return activeBankChart.metric_name.toUpperCase();
    }
    if (auditPayload) {
      const meta = (auditPayload as any).metadata || {};
      const base =
        meta.display_name || meta.filename || (auditPayload as any).doc_name;
      if (base && /^[0-9a-fA-F-]{20,}$/.test(base)) return "Documento auditado";
      return base || "Reporte de Auditoría";
    }
    if (reportPdfUrl) return "Reporte de Auditoría";
    if (artifact?.title) return artifact.title;
    return "Sin selección";
  }, [auditPayload, reportPdfUrl, artifact, activeBankChart]);

  const headerLabel = React.useMemo(() => {
    if (activeBankChart) return "Gráfica";
    if (auditPayload) return "Auditoría";
    return "Canvas";
  }, [activeBankChart, auditPayload]);

  const stats = (auditPayload as any)?.stats;
  const policy =
    (auditPayload as any)?.metadata?.policy_used?.name ||
    (auditPayload as any)?.metadata?.policy_used?.id ||
    null;

  const badges = stats && [
    {
      label: "Crítico",
      value: stats.critical,
      color: "bg-red-500/20 text-red-300",
    },
    {
      label: "Alto",
      value: stats.high,
      color: "bg-orange-500/20 text-orange-300",
    },
    {
      label: "Medio",
      value: stats.medium,
      color: "bg-yellow-500/20 text-yellow-300",
    },
    { label: "Bajo", value: stats.low, color: "bg-sky-500/20 text-sky-300" },
  ];

  return (
    <div className="flex items-center justify-between border-b border-border px-4 py-2.5 shrink-0">
      <div className="min-w-0 flex-1 mr-3">
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider text-primary font-semibold">
            {headerLabel}
          </span>
          {auditPayload && stats && (
            <span className="text-[10px] text-muted">
              {stats.total} hallazgos
            </span>
          )}
        </div>
        <p className="text-sm font-medium truncate text-foreground mt-0.5">
          {displayName}
        </p>
        {auditPayload && (
          <div className="flex flex-wrap gap-1 mt-1.5">
            {badges?.map(
              (b: { label: string; value: number; color: string }) =>
                b.value > 0 && (
                  <span
                    key={b.label}
                    className={cn(
                      "rounded-full px-1.5 py-0.5 text-[10px] font-medium",
                      b.color,
                    )}
                  >
                    {b.value} {b.label}
                  </span>
                ),
            )}
          </div>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <button
          type="button"
          onClick={onToggle}
          className="rounded-md border border-border px-2.5 py-1 text-xs text-muted hover:border-primary/50 hover:text-foreground transition-colors"
        >
          Cerrar
        </button>
      </div>
    </div>
  );
}
