# TASK: Disable Model Selector by Default

**ID**: TASK-2026-01-30__disable-model-selector-by-default
**Status**: DONE
**Priority**: Medium
**Created**: 2026-01-30
**Completed**: 2026-01-30

## Summary

Disable the model selector dropdown by default and make it controllable via environment variable. When disabled, the default model should be "Saptiva Turbo".

## Acceptance Criteria

- [x] Add `NEXT_PUBLIC_MODEL_SELECTOR_ENABLED` feature flag (default: `false`)
- [x] ModelSelector only renders when feature flag is `true`
- [x] When disabled, default model is "turbo" (Saptiva Turbo) - already the default in chat-store
- [x] Document the env variable in `.env.example`

## Technical Notes

- Feature flag pattern already exists in `apps/web/src/lib/feature-flags.ts`
- ModelSelector is rendered in 3 places in `ChatShell.tsx`:
  - `GridChatShell` (desktop header)
  - `LegacyMobileLayout` (mobile header)
  - `LegacyChatShell` (legacy layout header)
- Default model is already "turbo" in `chat-store.ts`

## Files Modified

1. `apps/web/src/lib/feature-flags.ts` - Added `modelSelector` flag (default: `false`)
2. `apps/web/src/components/chat/ChatShell.tsx` - Added `featureFlags.modelSelector` check in 3 places
3. `envs/.env.example` - Added `NEXT_PUBLIC_MODEL_SELECTOR_ENABLED=false`

## Usage

To enable the model selector, set in your `envs/.env`:
```
NEXT_PUBLIC_MODEL_SELECTOR_ENABLED=true
```
