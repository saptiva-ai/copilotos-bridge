import { expect, type TestInfo } from "@playwright/test";
import { CanvasPage } from "../pages/CanvasPage";
import { ChatPage } from "../pages/ChatPage";
import {
  buildChartPayload,
  buildChartSSEEvents,
  type BuildChartPayloadParams,
  type ChartPayload,
} from "./bank-chart-fixtures";
import type { ChatStreamScenario } from "./mock-api";

/**
 * Reusable helpers for conversational chart E2E tests.
 *
 * Usage:
 * 1. Build semantic stream scenarios with `createChartStreamScenarios`.
 * 2. Register them using `mockApi.mockChatStreamByQuery(page, scenarios)`.
 * 3. Execute each conversational turn with `runChartTurn`.
 *
 * `runChartTurn` centralizes:
 * - chat send + response wait
 * - chart button count growth
 * - optional canvas open + chart render wait
 * - optional period/value grounding validation from Data tab
 * - optional JSON evidence attachment for PDF reports
 */

export interface ChartStreamTurnDefinition {
  name: string;
  matcher: ChatStreamScenario["matcher"];
  payload: BuildChartPayloadParams;
}

export interface GroundingExpectation {
  bankName: string;
  period: string;
  valuePattern: RegExp | string;
}

export interface ChartTurnAssertions {
  assistantMustContain?: Array<string | RegExp>;
  chartButtonMustContain?: string | RegExp;
  openCanvas?: boolean;
  waitForChartRendered?: boolean;
  grounding?: GroundingExpectation;
}

export interface RunChartTurnOptions {
  query: string;
  expectedChartButtons: number;
  chatPage: ChatPage;
  canvasPage: CanvasPage;
  assertions?: ChartTurnAssertions;
  testInfo?: TestInfo;
  evidenceName?: string;
}

export interface ChartTurnResult {
  lastAssistantMessage: string;
  dataRows: Array<{ bank: string; period: string; value: string; raw: string[] }>;
  matchedGroundingRow: {
    bank: string;
    period: string;
    value: string;
    raw: string[];
  } | null;
}

function matchesValuePattern(value: string, pattern: RegExp | string): boolean {
  if (pattern instanceof RegExp) {
    // Avoid stateful failures when callers pass global regexes.
    const flags = pattern.flags.replace(/g/g, "");
    return new RegExp(pattern.source, flags).test(value);
  }
  return value.includes(pattern);
}

export function createChartStreamScenarios(
  turns: ChartStreamTurnDefinition[],
): { scenarios: ChatStreamScenario[]; payloads: ChartPayload[] } {
  const payloads = turns.map((turn) => buildChartPayload(turn.payload));
  const scenarios: ChatStreamScenario[] = turns.map((turn, index) => ({
    name: turn.name,
    matcher: turn.matcher,
    events: buildChartSSEEvents(payloads[index]),
  }));

  return { scenarios, payloads };
}

export async function runChartTurn(
  options: RunChartTurnOptions,
): Promise<ChartTurnResult> {
  const { chatPage, canvasPage, query, expectedChartButtons, assertions } =
    options;

  await chatPage.sendMessage(query);
  await chatPage.waitForResponse();
  await chatPage.waitForChartButtonsCount(expectedChartButtons);

  if (assertions?.chartButtonMustContain) {
    await expect(chatPage.chartButtons.last()).toContainText(
      assertions.chartButtonMustContain,
    );
  }

  const lastAssistantMessage = await chatPage.getLastMessage();
  if (assertions?.assistantMustContain) {
    for (const expected of assertions.assistantMustContain) {
      if (typeof expected === "string") {
        expect(lastAssistantMessage).toContain(expected);
      } else {
        expect(lastAssistantMessage).toMatch(expected);
      }
    }
  }

  const shouldOpenCanvas =
    assertions?.openCanvas ?? Boolean(assertions?.grounding);
  if (shouldOpenCanvas) {
    await chatPage.openLastChartButton();
    await canvasPage.waitForPanel();
    await canvasPage.waitForChartSelection();

    const waitForChartRendered = assertions?.waitForChartRendered ?? true;
    if (waitForChartRendered) {
      await canvasPage.waitForChartRendered();
    }
  }

  let dataRows: ChartTurnResult["dataRows"] = [];
  let matchedGroundingRow: ChartTurnResult["matchedGroundingRow"] = null;

  if (assertions?.grounding) {
    const { bankName, period, valuePattern } = assertions.grounding;

    await canvasPage.openDataTab();
    await canvasPage.expectDataRow({ bankName, period, valuePattern });

    dataRows = await canvasPage.getDataRows();
    matchedGroundingRow =
      dataRows.find(
        (row) =>
          row.bank.toUpperCase().includes(bankName.toUpperCase()) &&
          row.period === period,
      ) ?? null;

    const matchesValue = matchedGroundingRow
      ? matchesValuePattern(matchedGroundingRow.value, valuePattern)
      : false;

    expect(matchedGroundingRow).not.toBeNull();
    expect(matchesValue).toBe(true);

    if (options.testInfo) {
      await attachGroundingEvidence(options.testInfo, {
        filename:
          options.evidenceName ??
          `grounding-${bankName.toLowerCase().replace(/\s+/g, "-")}.json`,
        label: `${bankName} chart period/value grounding`,
        query,
        expected: { bankName, period, valuePattern },
        matchedRow: matchedGroundingRow,
        rows: dataRows,
      });
    }
  }

  return {
    lastAssistantMessage,
    dataRows,
    matchedGroundingRow,
  };
}

interface AttachGroundingEvidenceOptions {
  filename: string;
  label: string;
  query: string;
  expected: GroundingExpectation;
  matchedRow: ChartTurnResult["matchedGroundingRow"];
  rows: ChartTurnResult["dataRows"];
}

export async function attachGroundingEvidence(
  testInfo: TestInfo,
  options: AttachGroundingEvidenceOptions,
): Promise<void> {
  const expectedValue =
    options.expected.valuePattern instanceof RegExp
      ? options.expected.valuePattern.source
      : options.expected.valuePattern;

  const actualValue = options.matchedRow?.value ?? "";
  const matchesValue = matchesValuePattern(
    actualValue,
    options.expected.valuePattern,
  );

  await testInfo.attach(options.filename, {
    body: Buffer.from(
      JSON.stringify(
        {
          label: options.label,
          bankName: options.expected.bankName,
          query: options.query,
          expected: {
            period: options.expected.period,
            valuePattern: expectedValue,
          },
          actual: options.matchedRow
            ? {
                period: options.matchedRow.period,
                value: options.matchedRow.value,
              }
            : null,
          matched: Boolean(options.matchedRow) && matchesValue,
          rows: options.rows,
        },
        null,
        2,
      ),
      "utf-8",
    ),
    contentType: "application/json",
  });
}
