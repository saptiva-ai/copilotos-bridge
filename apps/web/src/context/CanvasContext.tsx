"use client";

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from "react";
import { useParams } from "next/navigation";
import type { AuditReportResponse } from "@/lib/types";
import { useCanvasStore } from "@/lib/stores/canvas-store";

interface CanvasState {
  isOpen: boolean;
  content: AuditReportResponse | null;
  activeTab?: string;
  sessionId: string | null;
  reportPdfUrl?: string | null;
}

interface CanvasContextType extends CanvasState {
  openCanvas: (
    data: AuditReportResponse,
    options?: { tab?: string; sessionId?: string; reportPdfUrl?: string },
  ) => void;
  closeCanvas: () => void;
  toggleCanvas: () => void;
  setActiveTab: (tab: string) => void;
}

const CanvasContext = createContext<CanvasContextType | undefined>(undefined);

export function CanvasProvider({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const currentSessionId = params?.chatId as string | undefined;

  const [state, setState] = useState<CanvasState>({
    isOpen: false,
    content: null,
    activeTab: undefined,
    sessionId: null,
    reportPdfUrl: null,
  });

  // Close canvas when switching to a different conversation
  useEffect(() => {
    if (
      state.sessionId &&
      currentSessionId &&
      state.sessionId !== currentSessionId
    ) {
      setState({
        isOpen: false,
        content: null,
        activeTab: undefined,
        sessionId: null,
        reportPdfUrl: null,
      });
      useCanvasStore.setState({
        isSidebarOpen: false,
        activeArtifactId: null,
        activeArtifactData: null,
        activeBankChart: null, // Clear bank chart when switching conversations
        activeMessageId: null,
        chartHistory: [],
      });
    }
  }, [currentSessionId, state.sessionId]);

  const openCanvas = useCallback(
    (
      data: AuditReportResponse,
      options?: { tab?: string; sessionId?: string; reportPdfUrl?: string },
    ) => {
      const resolvedSessionId = options?.sessionId ?? currentSessionId ?? null;

      // Block opening canvases for a different conversation to keep ownership per chat
      if (
        resolvedSessionId &&
        currentSessionId &&
        resolvedSessionId !== currentSessionId
      ) {
        return;
      }

      const extractReportUrl = (): string | null => {
        const meta: any = data?.metadata || {};
        const payload: any = (data as any)?.payload || {};

        return (
          options?.reportPdfUrl ||
          meta?.attachments?.full_report_pdf?.url ||
          meta?.attachments?.full_report_pdf?.presigned_url ||
          meta?.attachments?.report_pdf_url ||
          meta?.report_pdf_url ||
          meta?.report_url ||
          meta?.pdf_url ||
          payload?.attachments?.full_report_pdf?.url ||
          payload?.attachments?.full_report_pdf?.presigned_url ||
          payload?.attachments?.report_pdf_url ||
          payload?.report_pdf_url ||
          null
        );
      };

      setState({
        isOpen: true,
        content: data,
        activeTab: options?.tab,
        sessionId: resolvedSessionId,
        reportPdfUrl: extractReportUrl(),
      });
      useCanvasStore.setState({
        isSidebarOpen: true,
        activeArtifactId: null,
        activeArtifactData: data,
      });
    },
    [currentSessionId],
  );

  const closeCanvas = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isOpen: false,
    }));
    useCanvasStore.setState({
      isSidebarOpen: false,
      activeArtifactId: null,
      activeArtifactData: null,
      activeBankChart: null, // Clear bank chart when closing
      activeMessageId: null,
    });
  }, []);

  const toggleCanvas = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isOpen: !prev.isOpen,
    }));
    useCanvasStore.setState((prevState) => ({
      isSidebarOpen: !prevState.isSidebarOpen,
    }));
  }, []);

  const setActiveTab = useCallback((tab: string) => {
    setState((prev) => ({
      ...prev,
      activeTab: tab,
    }));
  }, []);

  return (
    <CanvasContext.Provider
      value={{
        ...state,
        openCanvas,
        closeCanvas,
        toggleCanvas,
        setActiveTab,
      }}
    >
      {children}
    </CanvasContext.Provider>
  );
}

export function useCanvas() {
  const context = useContext(CanvasContext);
  if (context === undefined) {
    throw new Error("useCanvas must be used within a CanvasProvider");
  }
  return context;
}
