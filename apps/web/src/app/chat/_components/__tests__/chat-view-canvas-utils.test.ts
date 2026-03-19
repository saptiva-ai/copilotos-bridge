import {
  getEffectiveCanvasChatId,
  isTempToRealChatReconciliation,
  shouldResetCanvasForChatTransition,
  shouldResetCanvasForNoActiveChat,
} from "../chat-view-canvas-utils";

describe("chat-view-canvas-utils", () => {
  describe("getEffectiveCanvasChatId", () => {
    it("prefers route chat id when available", () => {
      expect(getEffectiveCanvasChatId("route-1", "store-1")).toBe("route-1");
    });

    it("falls back to store chat id when route id is null", () => {
      expect(getEffectiveCanvasChatId(null, "store-1")).toBe("store-1");
    });

    it("returns null when both ids are missing", () => {
      expect(getEffectiveCanvasChatId(null, null)).toBeNull();
    });
  });

  describe("isTempToRealChatReconciliation", () => {
    it("detects temp to real transition", () => {
      expect(
        isTempToRealChatReconciliation("temp-abc", "123e4567-e89b-12d3-a456"),
      ).toBe(true);
    });

    it("returns false for real to real transition", () => {
      expect(isTempToRealChatReconciliation("chat-a", "chat-b")).toBe(false);
    });
  });

  describe("shouldResetCanvasForChatTransition", () => {
    it("does not reset on initial mount from null to real chat", () => {
      expect(shouldResetCanvasForChatTransition(null, "chat-1")).toBe(false);
    });

    it("resets on real chat change", () => {
      expect(shouldResetCanvasForChatTransition("chat-1", "chat-2")).toBe(true);
    });

    it("does not reset on temp to real reconciliation", () => {
      expect(
        shouldResetCanvasForChatTransition(
          "temp-abc",
          "123e4567-e89b-12d3-a456",
        ),
      ).toBe(false);
    });
  });

  describe("shouldResetCanvasForNoActiveChat", () => {
    it("resets when chat becomes null after having an active chat", () => {
      expect(shouldResetCanvasForNoActiveChat("chat-1", null)).toBe(true);
    });

    it("does not reset when there was no active chat before", () => {
      expect(shouldResetCanvasForNoActiveChat(null, null)).toBe(false);
    });
  });
});
