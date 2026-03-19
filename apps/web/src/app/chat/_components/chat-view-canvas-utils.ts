export const getEffectiveCanvasChatId = (
  routeChatId: string | null,
  storeChatId: string | null,
): string | null => routeChatId ?? storeChatId ?? null;

export const isTempToRealChatReconciliation = (
  previousChatId: string | null,
  nextChatId: string | null,
): boolean =>
  Boolean(
    previousChatId &&
    previousChatId.startsWith("temp-") &&
    nextChatId &&
    !nextChatId.startsWith("temp-"),
  );

export const shouldResetCanvasForChatTransition = (
  previousChatId: string | null,
  nextChatId: string | null,
): boolean => {
  const hasChanged = previousChatId !== nextChatId;
  if (!hasChanged || previousChatId === null) {
    return false;
  }

  return !isTempToRealChatReconciliation(previousChatId, nextChatId);
};

export const shouldResetCanvasForNoActiveChat = (
  previousChatId: string | null,
  nextChatId: string | null,
): boolean => previousChatId !== null && nextChatId === null;
