---
name: meeting-orchestrator
description: MinuteFlow local-first meeting workflow using MCP servers.
---

# Meeting Orchestrator

Use this skill when the user wants to summarize a local meeting recording, combine it with meeting materials, or ask follow-up questions about the meeting.

## Preferred tools

Prefer these MCP servers:

- `minuteflow_pipeline`
- `minuteflow_transcription`
- `minuteflow_documents`
- `minuteflow_media`

## Default workflow

1. If the user wants an end-to-end result, call `run_meeting_workflow` first.
2. If the user wants debugging or stage-by-stage control, call:
   - `inspect_media`
   - `transcribe_media`
   - `parse_document` / `parse_documents`
   - `extract_frames`
3. Read the emitted packet and artifact paths before answering follow-up questions.

## Reasoning policy

- Use transcript-only mode when the user only needs speaker-aware notes or timestamps.
- Use visual analysis when the user asks about slides, demos, whiteboards, UI steps, or anything visible in the video.
- If the pipeline reports that no multimodal endpoint is configured, state that visual semantics were not fully analyzed.
- If the pipeline reports that no LLM endpoint is configured, answer from the packet artifacts with the host model.

## Output policy

- Lead with conclusions.
- Reference the artifact files produced by the workflow.
- Call out uncertainty explicitly when evidence is missing.

