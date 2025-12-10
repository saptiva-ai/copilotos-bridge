/**
 * Tests for BankChartCanvasView Component
 *
 * Tests the full bank chart visualization in the canvas sidebar.
 */

import { render, screen, fireEvent } from "@testing-library/react";
import { BankChartCanvasView } from "../BankChartCanvasView";
import type { BankChartData } from "@/lib/types";

// Mock react-plotly.js to avoid rendering issues in tests
jest.mock("react-plotly.js", () => ({
  __esModule: true,
  default: ({ data, layout }: any) => (
    <div data-testid="plotly-chart">
      <div data-testid="plotly-data">{JSON.stringify(data)}</div>
      <div data-testid="plotly-layout">{JSON.stringify(layout)}</div>
    </div>
  ),
}));

const mockChartData: BankChartData = {
  type: "bank_chart",
  metric_name: "imor",
  bank_names: ["BBVA", "Santander", "HSBC"],
  time_range: {
    start: "2024-01-01",
    end: "2024-12-31",
  },
  data_as_of: "2024-12-01T10:30:00Z",
  source: "CNBV",
  plotly_config: {
    data: [
      {
        x: ["2024-01", "2024-02", "2024-03"],
        y: [2.5, 2.3, 2.1],
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
    sql_generated:
      "SELECT metric_value FROM banking_metrics WHERE metric_name = 'imor'",
    metric_interpretation:
      "El Índice de Morosidad (IMOR) representa el porcentaje de créditos vencidos.",
  },
};

describe("BankChartCanvasView", () => {
  it("should render metric name in header", async () => {
    render(<BankChartCanvasView data={mockChartData} />);
    expect(await screen.findByText("IMOR")).toBeInTheDocument();
  });

  it("should render bank names", async () => {
    render(<BankChartCanvasView data={mockChartData} />);
    expect(
      await screen.findByText(/BBVA, Santander, HSBC/),
    ).toBeInTheDocument();
  });

  it("should render time range", async () => {
    render(<BankChartCanvasView data={mockChartData} />);
    // Dates will be formatted based on locale - check for any date from 2024
    const dates = await screen.findAllByText(/2024/);
    expect(dates.length).toBeGreaterThan(0);
  });

  it("should render component without crashing", () => {
    const { container } = render(<BankChartCanvasView data={mockChartData} />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("should render chart tab by default", async () => {
    render(<BankChartCanvasView data={mockChartData} />);
    const plotlyChart = await screen.findByTestId("plotly-chart");
    expect(plotlyChart).toBeInTheDocument();
  });

  it("should render SQL tab when clicked", async () => {
    render(<BankChartCanvasView data={mockChartData} />);

    const sqlTab = await screen.findByText(/SQL Query/i);
    fireEvent.click(sqlTab);

    expect(await screen.findByText(/SELECT metric_value/)).toBeInTheDocument();
  });

  it("should render interpretation tab when clicked", async () => {
    render(<BankChartCanvasView data={mockChartData} />);

    const interpretationTab = await screen.findByText(/Interpretación/i);
    fireEvent.click(interpretationTab);

    expect(
      await screen.findByText(/porcentaje de créditos vencidos/i),
    ).toBeInTheDocument();
  });

  it("should switch between tabs correctly", async () => {
    render(<BankChartCanvasView data={mockChartData} />);

    // Initially on chart tab
    expect(await screen.findByTestId("plotly-chart")).toBeInTheDocument();

    // Switch to SQL tab
    const sqlTab = await screen.findByText(/SQL Query/i);
    fireEvent.click(sqlTab);
    expect(await screen.findByText(/SELECT metric_value/)).toBeInTheDocument();

    // Switch back to chart tab
    const chartTab = await screen.findByText(/Gráfica/i);
    fireEvent.click(chartTab);
    expect(await screen.findByTestId("plotly-chart")).toBeInTheDocument();
  });

  it("should render chart even if SQL query is missing", async () => {
    const dataWithoutSQL = {
      ...mockChartData,
      metadata: {
        metric_interpretation: "Some interpretation",
      },
    };

    render(<BankChartCanvasView data={dataWithoutSQL} />);

    // Chart should still render
    const plotlyChart = await screen.findByTestId("plotly-chart");
    expect(plotlyChart).toBeInTheDocument();
  });

  it("should render chart even if interpretation is missing", async () => {
    const dataWithoutInterpretation = {
      ...mockChartData,
      metadata: {
        sql_generated: "SELECT * FROM table",
      },
    };

    render(<BankChartCanvasView data={dataWithoutInterpretation} />);

    // Chart should still render
    const plotlyChart = await screen.findByTestId("plotly-chart");
    expect(plotlyChart).toBeInTheDocument();
  });

  it("should render Plotly chart with correct data", async () => {
    render(<BankChartCanvasView data={mockChartData} />);

    const plotlyData = await screen.findByTestId("plotly-data");
    const dataContent = plotlyData.textContent;

    expect(dataContent).toContain("2024-01");
    expect(dataContent).toContain("BBVA");
  });

  it("should render Plotly chart with correct layout", async () => {
    render(<BankChartCanvasView data={mockChartData} />);

    const plotlyLayout = await screen.findByTestId("plotly-layout");
    const layoutContent = plotlyLayout.textContent;

    expect(layoutContent).toContain("IMOR");
    expect(layoutContent).toContain("Periodo");
  });

  it("should show error when plotly_config.data is missing", async () => {
    const invalidData = {
      ...mockChartData,
      plotly_config: {
        ...mockChartData.plotly_config,
        data: undefined as any,
      },
    };

    render(<BankChartCanvasView data={invalidData} />);

    expect(
      await screen.findByText("Datos de gráfica inválidos o faltantes"),
    ).toBeInTheDocument();
  });

  it("should show error when metric_name is missing", async () => {
    const invalidData = {
      ...mockChartData,
      metric_name: undefined as any,
    };

    render(<BankChartCanvasView data={invalidData} />);

    expect(
      await screen.findByText("Nombre de métrica faltante"),
    ).toBeInTheDocument();
  });

  it("should show error when bank_names is empty", async () => {
    const invalidData = {
      ...mockChartData,
      bank_names: [],
    };

    render(<BankChartCanvasView data={invalidData} />);

    expect(
      await screen.findByText("No se especificaron bancos"),
    ).toBeInTheDocument();
  });

  it("should show retry button on error", async () => {
    const invalidData = {
      ...mockChartData,
      plotly_config: {
        ...mockChartData.plotly_config,
        data: undefined as any,
      },
    };

    render(<BankChartCanvasView data={invalidData} />);

    const retryButton = await screen.findByRole("button", {
      name: /reintentar/i,
    });
    expect(retryButton).toBeInTheDocument();
  });
});
