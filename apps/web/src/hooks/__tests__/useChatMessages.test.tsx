/**
 * Tests for useChatMessages - React Query integration
 */

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useChatMessages } from "../useChatMessages";
import { apiClient } from "../../lib/api-client";
import { useChatStore } from "../../lib/stores/chat-store";

// Mock dependencies
jest.mock("../../lib/api-client");
jest.mock("../../lib/logger", () => ({
  logDebug: jest.fn(),
  logError: jest.fn(),
}));

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe("useChatMessages", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    jest.clearAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it("should not fetch for draft chat", async () => {
    const { result } = renderHook(() => useChatMessages("draft"), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockApiClient.getUnifiedChatHistory).not.toHaveBeenCalled();
    expect(result.current.messages).toEqual([]);
  });

  it("should not fetch for temp chats", async () => {
    const { result } = renderHook(() => useChatMessages("temp-123"), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockApiClient.getUnifiedChatHistory).not.toHaveBeenCalled();
  });

  it("should fetch messages for real chat", async () => {
    const chatId = "real-chat-id";
    const mockMessages = [
      {
        id: "msg-1",
        content: "Hello",
        role: "user",
        timestamp: "2024-01-01T00:00:00Z",
      },
    ];

    mockApiClient.getUnifiedChatHistory.mockResolvedValueOnce({
      events: [
        {
          event_type: "chat_message",
          created_at: "2024-01-01T00:00:00Z",
          chat_data: mockMessages[0],
        },
      ],
    } as any);

    const { result } = renderHook(() => useChatMessages(chatId), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockApiClient.getUnifiedChatHistory).toHaveBeenCalledWith(
      chatId,
      50,
      0,
      true,
      false,
    );
    expect(result.current.messages).toHaveLength(1);
  });

  it("should sync messages to Zustand store", async () => {
    const chatId = "sync-test";
    const mockMessages = [
      {
        id: "msg-1",
        content: "Test",
        role: "user",
        timestamp: "2024-01-01T00:00:00Z",
      },
    ];

    mockApiClient.getUnifiedChatHistory.mockResolvedValueOnce({
      events: [
        {
          event_type: "chat_message",
          created_at: "2024-01-01T00:00:00Z",
          chat_data: mockMessages[0],
        },
      ],
    } as any);

    renderHook(() => useChatMessages(chatId), { wrapper });

    await waitFor(() => {
      const messages = useChatStore.getState().messages;
      expect(messages).toHaveLength(1);
      const hydratedStatus = useChatStore.getState().hydratedByChatId[chatId];
      expect(hydratedStatus).toBe(true);
    });
  });

  it("should handle API errors gracefully", async () => {
    const chatId = "error-chat";
    mockApiClient.getUnifiedChatHistory.mockRejectedValueOnce(
      new Error("API Error"),
    );

    const { result } = renderHook(() => useChatMessages(chatId), { wrapper });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeTruthy();
  });
});
