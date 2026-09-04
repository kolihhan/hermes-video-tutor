# Architecture

## Ownership

**Hermes owns**:

- observe → act → observe loop
- model/provider interaction
- conversation state
- tool dispatch
- continue/stop decisions

**This repository owns**:

- neutral course metadata
- transcript indexing
- safe ffmpeg frame/clip inspection
- session evidence and citations
- four video-specific tools
- `TutorService`
- CLI/Streamlit adapters
- evaluation

```text
CLI / Streamlit
      ↓
 TutorService
      ↓
HermesCliRuntime
      ↓
    Hermes
      ↓
video_tutor project plugin
  ├─ search_transcript
  ├─ expand_context
  ├─ inspect_frame
  └─ inspect_clip
      ↓
EvidenceStore + ActivityStore
```

`TutorService` never chooses a tool. If tool selection logic appears in the product service or UI, the architecture has regressed into a fixed workflow.

## Evidence boundary

Runtime evidence has only source facts produced during the session: ID, modality, timestamp/range, transcript text, and media references. Evaluation-only fields such as reference answers and required modality remain under `evaluation/` and are joined after inference by `case_id`.

For live paired evaluation, Hermes is restricted to the `video_tutor` toolset;
terminal and file tools are excluded, so evaluator-only gold cannot be read by
the model. The baseline registers the two transcript tools, while the treatment
adds only the two existing visual tools.

## Fail-safe behavior

A normal factual answer must cite evidence IDs created in the session. Unknown/missing citations fail closed. If Hermes returns `INSUFFICIENT_EVIDENCE`, or returns an uncited factual answer, `TutorService` exposes the explicit insufficient-evidence response.
