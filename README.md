# Hermes Video Tutor

A local video QA agent built on Hermes. It can search a lecture transcript, expand nearby context, or inspect a frame or short clip when the answer depends on visual evidence.

## How it works

```text
question
   |
Hermes agent
   |
   +--> search transcript
   +--> expand context
   +--> inspect frame
   +--> inspect clip
   |
 answer + source evidence
```

The project exposes four tools:

- `search_transcript(query, top_k=5)`
- `expand_context(segment_id)`
- `inspect_frame(timestamp_s)`
- `inspect_clip(start_s, end_s)`

There is no fixed `search -> frame -> clip` sequence. Hermes decides which tool to call next from the question and previous tool output.

The UI shows tool activity and evidence summaries without exposing hidden chain-of-thought.

## Evaluation

The current frozen v2 evaluation is **complete**.

It uses a small paired local fixture with **12 questions**:

- 6 transcript-answerable cases
- 6 visual-required cases

Each question is evaluated under two conditions using the same Hermes/model setup:

1. **transcript-only** — visual tools are unavailable
2. **multimodal** — frame and clip tools are available

The evaluator keeps these checks separate:

- answer correctness
- citation validity
- modality choice
- evidence-window correctness

The v2 run also records tool calls, latency, evidence, failure/abstention state, and per-case activity. The frozen report's project-level verdict is **`KEEP HERMES`**.

Source of truth: [`runs/p3-live-paired-v2/report.json`](runs/p3-live-paired-v2/report.json).

### Why v2 matters

The historical v1 evaluation is intentionally not used as a performance claim because its scorer compared the full cited response against a short-answer label. That scoring contract did not match the output format.

V2 fixes the evaluation contract by separating the short final answer from citation/evidence checks. The README now points to that completed run instead of saying the rerun is still pending.

## Example

A transcript question may only need one search:

```text
Q: What are the three stages of the tutor pipeline?
-> search_transcript(...)
A: retrieve evidence, reason over it, and answer [E1]
```

A visual question can cause the agent to inspect video evidence:

```text
Q: What color is the highlighted component around 4 seconds?
-> search_transcript(...)
-> inspect_frame(4.0)
A: blue [E2]
```

## Run locally

On Windows:

```cmd
run-demo.cmd
```

Prerequisites are Git, `uv`, ffmpeg, Ollama, and `qwen3.5:4b`.

CLI:

```powershell
video-tutor ask "What are the three stages of the tutor pipeline?"
```

To inspect tool activity and evidence summaries:

```powershell
.run\app-venv\Scripts\video-tutor.exe inspect --question "What color is the highlighted component around 4 seconds?"
```

The Streamlit UI and CLI use the same `TutorService`.

## Implementation choices

- Hermes owns the agent loop; the project supplies the domain tools.
- The tool list stays intentionally small.
- Frame/clip tools return visual content to the model, not only file paths.
- Clip inspection samples frames from a short range rather than sending arbitrary-length video.
- Reference answers and evaluator labels are kept out of runtime inputs.
- The agent can abstain when evidence is insufficient.

## Limits

- The 12-question fixture is self-authored and too small for broad video-QA claims.
- Clip inspection uses sampled frames rather than native long-video input.
- Results depend on the frozen local-model configuration.

More detail is in `docs/architecture.md`, `docs/hermes-integration.md`, and `docs/windows.md`.

## Development

```bash
python -m pytest -q
python -m compileall -q src evaluation tests
```
