import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HelpOnboardingMenu } from "../HelpOnboardingMenu";
import { HELP_ONBOARDING_PROMPT_EVENT } from "@/lib/help-onboarding-events";
import {
  HELP_PRESET_SECTIONS,
  VISIBLE_SECTIONS_DEFAULT,
} from "../help-onboarding-content";

// Mock apiClient to provide latestPeriod
jest.mock("@/lib/api-client", () => ({
  apiClient: {
    getBenchmarkPresets: jest.fn().mockResolvedValue({
      latest_period: "2025-01",
      presets: [],
    }),
  },
}));

// Mock useReportGeneration since ReportGenerator is rendered inside
jest.mock("@/hooks/useReportGeneration", () => ({
  useReportGeneration: () => ({
    progress: {
      status: "idle",
      progress: 0,
      completed: 0,
      total: 0,
      currentLabel: "",
      fileFormats: [],
      errorMessage: "",
    },
    generate: jest.fn(),
    download: jest.fn(),
    reset: jest.fn(),
    isGenerating: false,
    isReady: false,
    isError: false,
  }),
}));

const TEST_PERIOD = "2025-01";

describe("HelpOnboardingMenu", () => {
  it("opens menu and updates aria-expanded state", async () => {
    render(<HelpOnboardingMenu />);
    const user = userEvent.setup();
    const trigger = screen.getByTestId("help-onboarding-trigger");

    expect(trigger).toHaveAttribute("aria-expanded", "false");
    await user.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByTestId("help-onboarding-menu")).toBeInTheDocument();
    expect(screen.getByTestId("help-onboarding-search")).toBeInTheDocument();
    expect(screen.getByText(HELP_PRESET_SECTIONS[0].title)).toBeInTheDocument();
  });

  it("filters prompts and dispatches exact prompt via getPrompt", async () => {
    const icapSection = HELP_PRESET_SECTIONS.find((s) => s.id === "icap")!;
    const targetPreset = icapSection.presets[1];
    const listener = jest.fn();
    window.addEventListener(
      HELP_ONBOARDING_PROMPT_EVENT,
      listener as EventListener,
    );

    render(<HelpOnboardingMenu />);
    const user = userEvent.setup();

    await user.click(screen.getByTestId("help-onboarding-trigger"));
    await user.type(screen.getByTestId("help-onboarding-search"), "icap");
    await user.click(screen.getByRole("button", { name: targetPreset.label }));

    await waitFor(() => {
      expect(listener).toHaveBeenCalledTimes(1);
    });

    const event = listener.mock.calls[0][0] as CustomEvent<{
      prompt: string;
    }>;
    // Prompt should be generated via getPrompt with the effective period
    expect(event.detail.prompt).toBe(targetPreset.getPrompt(TEST_PERIOD));
    await waitFor(() => {
      expect(
        screen.queryByTestId("help-onboarding-menu"),
      ).not.toBeInTheDocument();
    });
    expect(screen.getByTestId("help-onboarding-trigger")).toHaveAttribute(
      "aria-expanded",
      "false",
    );

    window.removeEventListener(
      HELP_ONBOARDING_PROMPT_EVENT,
      listener as EventListener,
    );
  });

  it("quebrantos-anio prompt matches Tableau V5 expectations", () => {
    const quebrantosSection = HELP_PRESET_SECTIONS.find(
      (s) => s.id === "quebrantos",
    )!;
    const preset = quebrantosSection.presets.find(
      (p) => p.id === "quebrantos-anio",
    )!;
    const prompt = preset.getPrompt(TEST_PERIOD);

    // Must contain core Tableau-parity keywords
    expect(prompt).toContain("barras VERTICALES");
    expect(prompt).toMatch(/primer trimestre.*T1|T1/);
    expect(prompt).toMatch(/TOTAL del trimestre|SUM/);
    expect(prompt).toContain("TOTAL del sistema");
    expect(prompt).toContain("INVEX (rojo)");
    expect(prompt).toContain("TOTAL (gris)");

    // Must NOT contain old V1/V4 prompt text (regression guard)
    expect(prompt).not.toContain(
      "De enero 2023 hasta el dato más reciente que tengas",
    );
    expect(prompt).not.toContain("promedio simple");
  });

  it("closes with Escape key and outside click", async () => {
    render(<HelpOnboardingMenu />);
    const user = userEvent.setup();
    const trigger = screen.getByTestId("help-onboarding-trigger");

    await user.click(trigger);
    expect(screen.getByTestId("help-onboarding-menu")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(
        screen.queryByTestId("help-onboarding-menu"),
      ).not.toBeInTheDocument();
    });
    expect(trigger).toHaveAttribute("aria-expanded", "false");

    await user.click(trigger);
    expect(screen.getByTestId("help-onboarding-menu")).toBeInTheDocument();

    await user.click(screen.getByTestId("help-onboarding-overlay"));
    await waitFor(() => {
      expect(
        screen.queryByTestId("help-onboarding-menu"),
      ).not.toBeInTheDocument();
    });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  it("shows only first N sections by default (collapsible grid)", async () => {
    render(<HelpOnboardingMenu />);
    const user = userEvent.setup();

    await user.click(screen.getByTestId("help-onboarding-trigger"));

    // Should show only VISIBLE_SECTIONS_DEFAULT sections
    const allTitles = HELP_PRESET_SECTIONS.map((s) => s.title);
    const visibleTitles = allTitles.slice(0, VISIBLE_SECTIONS_DEFAULT);
    const hiddenTitles = allTitles.slice(VISIBLE_SECTIONS_DEFAULT);

    for (const title of visibleTitles) {
      expect(screen.getByText(title)).toBeInTheDocument();
    }
    for (const title of hiddenTitles) {
      expect(screen.queryByText(title)).not.toBeInTheDocument();
    }

    // "Ver más" button should exist
    expect(
      screen.getByTestId("help-onboarding-expand-toggle"),
    ).toBeInTheDocument();
  });

  it("expands all sections when 'Ver más' is clicked", async () => {
    render(<HelpOnboardingMenu />);
    const user = userEvent.setup();

    await user.click(screen.getByTestId("help-onboarding-trigger"));
    await user.click(screen.getByTestId("help-onboarding-expand-toggle"));

    // All sections should be visible now
    for (const section of HELP_PRESET_SECTIONS) {
      expect(screen.getByText(section.title)).toBeInTheDocument();
    }
  });

  it("shows period label with effective period", async () => {
    render(<HelpOnboardingMenu />);
    const user = userEvent.setup();

    await user.click(screen.getByTestId("help-onboarding-trigger"));

    await waitFor(() => {
      expect(
        screen.getByTestId("help-onboarding-period-label"),
      ).toBeInTheDocument();
    });

    // "Enero 2025" appears in both PeriodSelector and period label
    expect(screen.getAllByText("Enero 2025").length).toBeGreaterThanOrEqual(1);
  });
});
