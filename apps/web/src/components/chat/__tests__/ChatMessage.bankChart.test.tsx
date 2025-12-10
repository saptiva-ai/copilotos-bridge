/**
 * Tests for Bank Chart Canvas Integration
 *
 * Tests the bank chart button in chat messages that opens the canvas sidebar.
 */

import { render, screen, fireEvent } from "@testing-library/react";
import { ChatMessage } from "../ChatMessage";
import { useCanvasStore } from "@/lib/stores/canvas-store";
import type { BankChartData } from "@/lib/types";

// Mock dependencies
jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }: { children: string }) => <div>{children}</div>,
}));

jest.mock("../StreamingMessage", () => ({
  StreamingMessage: () => <div>Streaming...</div>,
}));

jest.mock("../BankChartMessage", () => ({
  BankChartMessage: () => <div>Bank Chart</div>,
}));

jest.mock("../PreviewAttachment", () => ({
  PreviewAttachment: () => <div>Attachment</div>,
}));

// Mock canvas store
jest.mock("@/lib/stores/canvas-store", () => ({
  useCanvasStore: jest.fn(),
}));

const mockBankChartData: BankChartData = {
  type: "bank_chart",
  metric_name: "imor",
  bank_names: ["BBVA", "Santander"],
  time_range: {
    start: "2024-01-01",
    end: "2024-12-31",
  },
  data_as_of: "2024-12-01T00:00:00Z",
  source: "CNBV",
  plotly_config: {
    data: [
      {
        x: ["2024-01", "2024-02"],
        y: [2.5, 2.3],
        type: "bar",
        name: "BBVA",
      },
    ],
    layout: {
      title: "IMOR - Índice de Morosidad",
      xaxis: { title: "Periodo" },
      yaxis: { title: "Porcentaje" },
    },
  },
  metadata: {
    sql_generated: "SELECT * FROM metrics WHERE metric = 'imor'",
    metric_interpretation: "El IMOR representa el índice de morosidad...",
  },
};

describe("ChatMessage - Bank Chart Button", () => {
  const mockOpenBankChart = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();

    // Mock both the hook and getState
    (useCanvasStore as unknown as jest.Mock).mockImplementation((selector) => {
      if (typeof selector === "function") {
        return selector({
          openBankChart: mockOpenBankChart,
          activeMessageId: null,
        });
      }
      return {
        openBankChart: mockOpenBankChart,
        activeMessageId: null,
      };
    });

    // Mock getState method
    (useCanvasStore as any).getState = jest.fn(() => ({
      openBankChart: mockOpenBankChart,
      activeMessageId: null,
    }));
  });

  it("should render bank chart button when bankChartData is present", () => {
    render(
      <ChatMessage
        role="assistant"
        content="Aquí está la gráfica del IMOR:"
        metadata={{ bank_chart_data: mockBankChartData }}
      />,
    );

    const button = screen.getByRole("button", { name: /Abrir gráfica/i });
    expect(button).toBeInTheDocument();
  });

  it("should NOT render bank chart button for user messages", () => {
    render(
      <ChatMessage
        role="user"
        content="Muéstrame el IMOR"
        metadata={{ bank_chart_data: mockBankChartData }}
      />,
    );

    const button = screen.queryByRole("button", { name: /ver gráfica/i });
    expect(button).not.toBeInTheDocument();
  });

  it("should open canvas when button is clicked", () => {
    const messageId = "msg_123";
    const artifactId = "artifact_456";

    render(
      <ChatMessage
        id={messageId}
        role="assistant"
        content="Aquí está la gráfica:"
        metadata={{
          bank_chart_data: mockBankChartData,
          artifact_id: artifactId,
        }}
      />,
    );

    const button = screen.getByRole("button", { name: /Abrir gráfica/i });
    fireEvent.click(button);

    expect(mockOpenBankChart).toHaveBeenCalledWith(
      mockBankChartData,
      artifactId,
      messageId,
      false,
    );
  });

  it("should use 'temp' artifact ID when artifact_id is not available", () => {
    const messageId = "msg_789";

    render(
      <ChatMessage
        id={messageId}
        role="assistant"
        content="Aquí está la gráfica:"
        metadata={{ bank_chart_data: mockBankChartData }}
      />,
    );

    const button = screen.getByRole("button", { name: /Abrir gráfica/i });
    fireEvent.click(button);

    expect(mockOpenBankChart).toHaveBeenCalledWith(
      mockBankChartData,
      "temp",
      messageId,
      false,
    );
  });

  it("should display metric name in uppercase", () => {
    render(
      <ChatMessage
        role="assistant"
        content="Aquí está la gráfica:"
        metadata={{ bank_chart_data: mockBankChartData }}
      />,
    );

    expect(screen.getByText(/IMOR/)).toBeInTheDocument();
  });

  it("should show chart icon in button", () => {
    render(
      <ChatMessage
        role="assistant"
        content="Aquí está la gráfica:"
        metadata={{ bank_chart_data: mockBankChartData }}
      />,
    );

    const button = screen.getByRole("button", { name: /Abrir gráfica/i });
    // Check for SVG icon (ChartBarIcon)
    const svg = button.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });
});
