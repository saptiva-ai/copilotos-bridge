/**
 * files-store.ts - Persistent file attachments store with Zustand
 *
 * MVP-LOCK: Persists file attachments by chat_id to survive page refreshes
 *
 * Features:
 * - Stores attachments by conversation ID
 * - Persists to localStorage
 * - Survives page refreshes
 * - Supports draft mode (no chat_id yet)
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { FileAttachment } from "../../types/files";

type AttachmentsByChat = Record<string, FileAttachment[]>;

interface FilesStoreState {
  byChat: AttachmentsByChat;
  setForChat: (chatId: string, files: FileAttachment[]) => void;
  getForChat: (chatId: string) => FileAttachment[];
  addToChat: (chatId: string, file: FileAttachment) => void;
  removeFromChat: (chatId: string, fileId: string) => void;
  clearForChat: (chatId: string) => void;
  clearAll: () => void;
}

export const useFilesStore = create<FilesStoreState>()(
  persist(
    (set, get) => ({
      byChat: {},

      setForChat: (chatId, files) =>
        set((state) => ({
          byChat: {
            ...state.byChat,
            [chatId]: files,
          },
        })),

      getForChat: (chatId) => get().byChat[chatId] ?? [],

      addToChat: (chatId, file) =>
        set((state) => {
          const existing = state.byChat[chatId] ?? [];
          // Prevent duplicates
          if (existing.some((f) => f.file_id === file.file_id)) {
            return state;
          }
          return {
            byChat: {
              ...state.byChat,
              [chatId]: [...existing, file],
            },
          };
        }),

      removeFromChat: (chatId, fileId) =>
        set((state) => ({
          byChat: {
            ...state.byChat,
            [chatId]: (state.byChat[chatId] ?? []).filter(
              (f) => f.file_id !== fileId,
            ),
          },
        })),

      clearForChat: (chatId) =>
        set((state) => {
          const newByChat = { ...state.byChat };
          delete newByChat[chatId];
          return { byChat: newByChat };
        }),

      clearAll: () => set({ byChat: {} }),
    }),
    {
      name: "files-by-chat", // localStorage key
      // Only persist necessary data (file_ids, status, metadata)
      partialize: (state) => ({ byChat: state.byChat }),
    },
  ),
);
