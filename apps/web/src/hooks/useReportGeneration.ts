"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiClient } from "@/lib/api-client";

export type ReportStatus =
  | "idle"
  | "pending"
  | "generating"
  | "ready"
  | "error"
  | "downloading";

export interface ReportProgress {
  status: ReportStatus;
  progress: number; // 0–1
  completed: number;
  total: number;
  currentLabel: string;
  fileFormats: string[];
  errorMessage: string;
}

const POLL_INTERVAL_MS = 2000;

export function useReportGeneration() {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState<ReportProgress>({
    status: "idle",
    progress: 0,
    completed: 0,
    total: 0,
    currentLabel: "",
    fileFormats: [],
    errorMessage: "",
  });
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => stopPolling, [stopPolling]);

  const pollStatus = useCallback(
    async (id: string) => {
      try {
        const data = await apiClient.getBenchmarkReportStatus(id);

        setProgress({
          status: data.status as ReportStatus,
          progress: data.progress,
          completed: data.completed,
          total: data.total,
          currentLabel: data.current_label,
          fileFormats: data.file_formats,
          errorMessage: data.error_message,
        });

        if (data.status === "ready" || data.status === "error") {
          stopPolling();
        }
      } catch {
        setProgress((prev) => ({
          ...prev,
          status: "error",
          errorMessage: "Error al consultar estado del reporte",
        }));
        stopPolling();
      }
    },
    [stopPolling],
  );

  const generate = useCallback(
    async (
      presetIds: string[] | null = null,
      format: "pptx" | "pdf" | "both" = "both",
      targetPeriod?: string,
    ) => {
      stopPolling();

      setProgress({
        status: "pending",
        progress: 0,
        completed: 0,
        total: presetIds?.length ?? 32,
        currentLabel: "Iniciando generación...",
        fileFormats: [],
        errorMessage: "",
      });

      try {
        const response = await apiClient.generateBenchmarkReport(
          presetIds,
          format,
          targetPeriod,
        );
        const newTaskId = response.task_id;
        setTaskId(newTaskId);

        setProgress((prev) => ({
          ...prev,
          status: "generating",
          currentLabel: "Procesando gráficas...",
        }));

        // Start polling
        pollingRef.current = setInterval(() => {
          void pollStatus(newTaskId);
        }, POLL_INTERVAL_MS);
      } catch {
        setProgress((prev) => ({
          ...prev,
          status: "error",
          errorMessage: "Error al iniciar generación del reporte",
        }));
      }
    },
    [pollStatus, stopPolling],
  );

  const download = useCallback(
    async (format: "pptx" | "pdf") => {
      if (!taskId) return;

      setProgress((prev) => ({ ...prev, status: "downloading" }));

      try {
        const blob = await apiClient.downloadBenchmarkReport(taskId, format);

        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        const now = new Date();
        const pad = (n: number) => String(n).padStart(2, "0");
        const ts = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}`;
        link.download = `Reporte_Benchmark_${ts}.${format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        setProgress((prev) => ({ ...prev, status: "ready" }));
      } catch {
        setProgress((prev) => ({
          ...prev,
          status: "error",
          errorMessage: `Error al descargar archivo ${format.toUpperCase()}`,
        }));
      }
    },
    [taskId],
  );

  const reset = useCallback(() => {
    stopPolling();
    setTaskId(null);
    setProgress({
      status: "idle",
      progress: 0,
      completed: 0,
      total: 0,
      currentLabel: "",
      fileFormats: [],
      errorMessage: "",
    });
  }, [stopPolling]);

  return {
    progress,
    generate,
    download,
    reset,
    isGenerating:
      progress.status === "pending" || progress.status === "generating",
    isReady: progress.status === "ready",
    isError: progress.status === "error",
  };
}
