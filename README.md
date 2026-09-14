# Hermes Video Tutor

A video QA agent built on Hermes.

It can search a lecture transcript, expand nearby context, or look at a frame or short clip when the answer depends on something visual. The model decides which tool to use based on the question.

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

There are four project tools:

- `search_transcript(query, top_k=5)`
- `expand_context(segment_id)`
- `inspect_frame(timestamp_s)`
- `inspect_clip(start_s, end_s)`

The frame and clip tools return image content to the model, not just a file path. There is no fixed `search -> frame -> clip` sequence; Hermes chooses the next step after each result.

## Example

A transcript question may only need one search:

```text
Q: What are the three stages of the tutor pipeline?
-> search_transcript(...)
A: retrieve evidence, reason over it, and answer [E1]
```

A visual question can cause the agent to look at the video:

```text
Q: What color is the highlighted component around 4 seconds?
-> search_transcript(...)
-> inspect_frame(4.0)
A: blue [E2]
```

The UI shows tool activity and evidence. It does not expose hidden chain-of-thought.

## Run locally

On Windows, the easiest path is:

```cmd
run-demo.cmd
```

Prerequisites are Git, `uv`, ffmpeg, Ollama, and `qwen3.5:4b`.

CLI:

```powershell
video-tutor ask "What are the three stages of the tutor pipeline?"
```

To see tool activity and evidence summaries:

```powershell
.run\app-venv\Scripts\video-tutor.exe inspect --question "What color is the highlighted component around 4 seconds?"
```

The Streamlit UI and CLI both use the same `TutorService`.

## Evaluation

I use a small 12-question local fixture: six questions can be answered from the transcript and six need visual evidence. The transcript-only and multimodal runs use the same Hermes/model setup; the difference is whether frame and clip tools are available.

The first live run is kept in the repo, but I do **not** use its `0/12` score as a performance result. The evaluator compared the full cited response against a short-answer label, so the scoring contract was wrong for the format the agent produced.

Review-v2 changes the answer format to a short final answer plus citation and keeps answer correctness, citation, modality, and evidence timing as separate checks. That rerun is still pending, so there is no v2 performance claim yet.

The historical run and the reason it was rejected are documented in `docs/p3-decision.md`.

## A few implementation choices

- Hermes owns the agent loop; this repo only provides the project tools.
- The tool list stays small, so all four tools are exposed directly.
- Clip inspection samples a few frames from a short time range instead of sending arbitrary-length video.
- Reference answers and evaluator labels are kept out of the runtime inputs.
- If the agent does not have enough evidence, it can return an insufficient-evidence answer instead of guessing.

## Limits

- The 12-question fixture is self-authored and too small for general video-QA claims.
- Clip inspection uses sampled frames rather than native long-video input.
- Results depend heavily on the local model; the default is `qwen3.5:4b`.

More detail is in `docs/architecture.md`, `docs/hermes-integration.md`, and `docs/windows.md`.

## Development

```bash
python -m pytest -q
python -m compileall -q src evaluation tests
```
