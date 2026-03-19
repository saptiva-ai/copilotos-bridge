---
id: "TASK-2026-01-06-1600__hu3-infra-fixes"
title: "HU3 NLP Fixes and Infrastructure Stabilization"
status: "DONE"
phase: "Complete"
date: "2026-01-06"
assignee: "Gemini"
---

# Summary
Resolved critical bugs in Bank Advisor (HU3) and Infrastructure setup to ensure stability of RAG and NLP pipelines.

## Changes
- **HU3 / Bank Advisor**:
  - Removed duplicate `BANK_KNOWLEDGE` handler in `hu3_nlp` (`c221d237`).
  - Corrected LLM client import in pipeline (`0348c3c1`).
  - Robustified clarification thresholds (`5f096032`).
  - Fixed NL2SQL empty results by anchoring time filters (`bf2df43b`).
- **Infrastructure**:
  - Added `WEAVIATE_API_KEY` to backend env (`57c4091e`).
  - Fixed critical `has_rag_context` bug in production (`f33c88e5`).
  - Updated registry images to v1.3.0 (`610599b3`).
  - Cleaned up local Weaviate configuration (`2038ba92`).

## Verification
- Tests passing.
- Production deployment scripts updated.
