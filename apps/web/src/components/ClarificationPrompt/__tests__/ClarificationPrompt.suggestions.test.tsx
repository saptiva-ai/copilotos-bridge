import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { ClarificationPrompt } from "..";

describe("ClarificationPrompt suggestions", () => {
  const basePayload = {
    type: "clarification" as const,
    message: "Elige una opción",
    clarifications: [
      {
        field: "metric",
        reason: "Falta métrica",
        question: "¿Qué métrica te interesa?",
        options: [
          { label: "IMOR", value: "IMOR" },
          { label: "ICAP", value: "ICAP" },
        ],
      },
    ],
    suggested_metrics: ["IMOR", "ICOR"],
    related_queries: [
      "¿Cómo ha evolucionado IMOR de SISTEMA en los últimos 3 meses?",
    ],
  };

  it("renders suggested metrics", () => {
    render(<ClarificationPrompt payload={basePayload} onResolve={jest.fn()} />);

    expect(screen.getByText("Métricas sugeridas")).toBeInTheDocument();
    expect(screen.getAllByText("IMOR").length).toBeGreaterThan(0);
  });

  it("fires onResolve with quick_query when clicking related query", () => {
    const onResolve = jest.fn();
    render(<ClarificationPrompt payload={basePayload} onResolve={onResolve} />);

    fireEvent.click(
      screen.getByText(
        "¿Cómo ha evolucionado IMOR de SISTEMA en los últimos 3 meses?",
      ),
    );

    expect(onResolve).toHaveBeenCalledWith({
      quick_query:
        "¿Cómo ha evolucionado IMOR de SISTEMA en los últimos 3 meses?",
    });
  });
});
