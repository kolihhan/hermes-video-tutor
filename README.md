# Hermes Video Tutor

## Review-v2 evaluation status

The previous `p3-live-paired-v1` artifact is preserved as historical execution evidence, but its 0/12 answer score and `SIMPLIFY` verdict are **not a valid performance conclusion** because v1 exact-matched the full cited prose response against a short-answer gold label. Review-v2 fixes the contract before rerunning: successful model output must be `FINAL: <short answer> [E#]`, scoring deterministically extracts that short answer, citation/modality/window checks remain separate, and the custom Ollama treatment is deterministic (`temperature 0`). The pending canonical output is `runs/p3-live-paired-v2/report.json`.


**A video tutor agent built on Hermes.** It searches lecture transcripts, inspects frames or short clips when text is insufficient, and answers with evidence from the source.

```text
Student question
      ↓
  Hermes Agent
      ↓
 chooses the next action
  ↙       ↓       ↘
transcript frame   clip
  ↘       ↓       ↙
      evidence
         ↓
 grounded answer [E1]
```

## Why

A transcript is not the whole video. Slides, diagrams, colors, gestures, and on-screen state changes may require direct visual inspection. A transcript-only tutor can therefore sound confident while missing the evidence that actually answers the question.

This project keeps the agent loop in Hermes and adds a small video evidence environment around it.

## How it works

Hermes sees four project tools:

- `search_transcript(query, top_k=5)`
- `expand_context(segment_id)`
- `inspect_frame(timestamp_s)`
- `inspect_clip(start_s, end_s)`

There is **no fixed `search → frame → clip` workflow**. Hermes decides what to inspect after each observation. Frame/clip tools return Hermes multimodal tool results containing actual sampled images, not only file paths.

`Tool Search` is disabled for this four-tool surface so the model sees the tools directly instead of going through a progressive-disclosure meta-tool layer.

## Quickstart

### Windows demo

Prerequisites: Git, `uv`, ffmpeg, Ollama, and `qwen3.5:4b`.

```cmd
run-demo.cmd
```

The setup is project-local under `.run/`. It checks out the pinned Hermes
revision, creates `qwen3.5-hermes:4b` from `Modelfile.hermes`, and verifies the
custom tag. See [`docs/windows.md`](docs/windows.md).

### CLI

After setup, the CLI command is:

```powershell
video-tutor ask "What are the three stages of the tutor pipeline?"
```

On Windows the project-local executable is:

```powershell
.run\app-venv\Scripts\video-tutor.exe ask "What are the three stages of the tutor pipeline?"
```

Or print observable tool activity and evidence summaries:

```powershell
.run\app-venv\Scripts\video-tutor.exe inspect --question "What color is the highlighted component around 4 seconds?"
```

The Streamlit UI and CLI call the same `TutorService`.

## Example

Transcript-answerable question:

```text
Q: What are the three stages of the tutor pipeline?

Agent Activity
→ search_transcript(...)

A: retrieve evidence, reason over it, and answer [E1]
```

Visual-required question:

```text
Q: What color is the highlighted component around 4 seconds?

Agent Activity
→ search_transcript(...)
→ inspect_frame(4.0)

A: blue [E2]
```

Temporal question:

```text
Q: What color does the screen change to after Run is clicked?

Agent Activity
→ search_transcript(...)
→ inspect_frame(...)
→ inspect_clip(...)

A: green [E3]
```

The UI shows **Agent Activity**, not hidden chain-of-thought.

## Evaluation

Runtime inputs and grader labels are physically separated:

```text
evaluation/inference_cases.json  # case_id + neutral question/course only
evaluation/gold_labels.json      # grader-only answer/modality/time-window labels
```

A wrong answer with a valid citation does **not** pass. The evaluator scores answer correctness, citation validity, cited modality, and evidence timing separately.

The repository ships two frozen prediction fixtures to test the evaluator and product plumbing:

| Fixture | Answer accuracy | Full pass | Visual use when required |
|---|---:|---:|---:|
| Transcript-only fixture | 33.3% | 33.3% | 0% |
| Multimodal fixture | 100% | 100% | 100% |

These are a deterministic product sanity check, **not a live Hermes benchmark**. They intentionally encode expected fixture behavior so the evaluator can be tested without a model server. Live Hermes/Ollama results must be produced on the target runtime before making performance claims.

Run the sanity evaluator with:

```powershell
python -m evaluation.run_demo_eval --mode both
```

The separate frozen live evaluation uses a self-authored 60-second CC0 fixture
with 12 cases: six transcript-answerable and six visual-required. It compares
the same pinned Hermes/model/config/prompt twice, changing only the registered
project-tool surface:

- `transcript_only`: `search_transcript`, `expand_context`
- `multimodal`: those two plus `inspect_frame`, `inspect_clip`

Hermes is invoked with the explicit `video_tutor` toolset, so its broad default
terminal/file tools cannot reach evaluator gold. Condition order alternates by
case. Exact answer aliases, modality, evidence-window scoring, provenance
hashes, and the verdict rule are frozen before inference. Native Hermes usage
reports provide API-call and token accounting.

After running setup, the one canonical command is:

```powershell
.run\app-venv\Scripts\python.exe -m evaluation.run_live_paired --output runs\p3-live-paired-v2\report.json
```

The runner refuses to overwrite an existing report.

### Canonical live result

The frozen 12-case paired run completed all 24 invocations with no runtime
errors. Both arms scored `0/12` answer correctness and `0/12` full pass under
the precommitted normalized canonical/alias equality rule, so the frozen
verdict is **`SIMPLIFY`**. This poor result is retained without prompt or score
tuning.

| Condition | Answer / full pass | Visual-tool use on visual cases | Tool calls | Mean / p50 / p95 latency | API calls / tokens | Abstentions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Transcript only | 0/12 / 0/12 | 0/6 | 15 | 73.24s / 58.59s / 202.28s | 70 / 172,974 | 8 |
| Multimodal | 0/12 / 0/12 | 4/6 | 13 | 113.44s / 57.58s / 395.01s | 116 / 310,036 | 5 |

The canonical report is
[`runs/p3-live-paired-v1/report.json`](runs/p3-live-paired-v1/report.json),
SHA-256
`c4847605a65970e24ff67ac9b68565d32fbc876eba83d0b971e026624bbd9260`.
An independently detected `id`/`evidence_id` evaluator adapter defect was
corrected by deterministic offline rescoring of the unchanged predictions;
decision metrics and verdict did not change. The original scored report and
the earlier context-window infrastructure failure are preserved beside it.
See [`docs/p3-decision.md`](docs/p3-decision.md).

## Design decisions

- **Hermes owns the agent loop.** This repo does not fork or reimplement Hermes.
- **Four tools only.** The MVP is deliberately small.
- **Tool Search off.** Direct eager tool exposure is simpler for this small surface.
- **Visual tools return pixels.** Frames are delivered through Hermes' multimodal tool-result envelope.
- **Clips are bounded.** `inspect_clip` samples a small number of frames from a short interval instead of feeding arbitrary-length video.
- **Fail closed.** Missing citations or exhausted evidence produce an insufficient-evidence answer rather than a guess.
- **Gold stays evaluator-only.** Benchmark captions, annotations, reference answers, and modality labels never enter runtime metadata or prompts.

## Architecture

See [`docs/architecture.md`](docs/architecture.md) and [`docs/hermes-integration.md`](docs/hermes-integration.md).

## Limitations

- The completed 12-case result applies only to the self-authored fixture and the pinned local runtime; it is not evidence of general video-question-answering quality.
- The bundled lecture is a tiny deterministic product fixture, not a general video benchmark.
- Clip inspection currently uses bounded sampled frames plus overlapping transcript context rather than native long-video model input.
- The default model is a small local `qwen3.5:4b`; tool-selection and visual reasoning quality will depend on the installed model/runtime.
- Hermes v0.20.4 requires at least a 64K declared context; this runtime uses exactly 65,536 tokens for compatibility, not as a capacity claim.
