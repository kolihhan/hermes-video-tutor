<h1 align="center">Hermes Video Tutor</h1>

<p align="center">
  <strong>A local multimodal video QA agent that decides when transcript evidence is enough — and when it needs to inspect the video.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-111827?style=flat-square&logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/Streamlit-111827?style=flat-square&logo=streamlit" alt="Streamlit" />
  <img src="https://img.shields.io/badge/Hermes_Agent-111827?style=flat-square" alt="Hermes agent" />
  <img src="https://img.shields.io/badge/Multimodal-111827?style=flat-square" alt="Multimodal" />
  <img src="https://img.shields.io/badge/Evidence_Grounded-111827?style=flat-square" alt="Evidence grounded" />
</p>

<p align="center">
  <a href="#demo">Demo</a> ·
  <a href="#key-result">Key result</a> ·
  <a href="#how-it-works">Architecture</a> ·
  <a href="#quickstart">Quickstart</a>
</p>

## At a glance

| | |
|---|---|
| **Problem** | Transcript-only QA fails when the answer is visible in a frame or clip rather than spoken. Sending every question to a vision model is wasteful. |
| **What I built** | A local agent with four video tools that can stop after transcript search or escalate to frame / clip inspection only when needed. |
| **Evidence** | On a frozen 12-question fixture, multimodal mode reached **66.7% full pass on visual-required questions** and used a visual tool on **100% of those questions**. |
| **Design focus** | Adaptive modality, visible tool activity, and evidence-grounded answers. |

> [!NOTE]
> The interesting part is not “LLM + video.” It is the **modality decision**: when should the agent trust text, and when should it inspect the video?

## Demo

```cmd
run-demo.cmd
```

The Streamlit UI keeps the lecture, question, answer, **Agent Activity**, and **Evidence** together on one screen.

A typical visual-required question looks like this:

```text
Q: What color is the highlighted component around 4 seconds?

Hermes
  → search_transcript(...)
  → inspect_frame(4.0)

A: blue [E2]
```

A transcript-answerable question can stop after search. There is no fixed `search → frame → clip` pipeline.

## Key result

Frozen paired evaluation on **12 local fixture questions** — 6 transcript-answerable and 6 visual-required — using the same Hermes/model setup:

| Condition | Full pass | Visual-required full pass | Visual tool use on visual questions |
|---|---:|---:|---:|
| Transcript only | 16.7% | 0% | 0% |
| **Multimodal tools enabled** | **50.0%** | **66.7%** | **100%** |

On transcript-answerable cases, multimodal mode made **no unnecessary visual-tool calls** in this frozen run.

Source of truth: [`runs/p3-live-paired-v2/report.json`](runs/p3-live-paired-v2/report.json).

> [!IMPORTANT]
> This is a small, **self-authored** product-oriented paired evaluation, **not a broad video-QA benchmark claim**. V2 full-pass uses a strict `FINAL: <short answer> [E#]` protocol with normalized equality to the canonical answer or an explicit alias; it should not be read as human semantic-accuracy scoring.

## How it works

```mermaid
flowchart TD
    Q[Question] --> H[Hermes agent]
    H --> T[Search transcript]
    H --> C[Expand nearby context]
    H --> F[Inspect frame]
    H --> V[Inspect short clip]
    T --> H
    C --> H
    F --> H
    V --> H
    H --> A[Grounded answer + evidence]
```

The project exposes only four domain tools:

| Tool | Purpose |
|---|---|
| `search_transcript(query, top_k=5)` | Find spoken evidence and return both evidence IDs and transcript segment IDs. |
| `expand_context(segment_id)` | Pull nearby transcript context around a search hit. |
| `inspect_frame(timestamp_s)` | Inspect a single visual moment. |
| `inspect_clip(start_s, end_s)` | Inspect a short range when one frame is insufficient. |

Hermes owns the agent loop; this repository supplies the domain tools, evidence contract, product UI, and evaluation harness.

### Why this project

Video QA is often presented as “send the video to a multimodal model.” This project asks a narrower systems question: **can a local agent choose the cheapest useful modality while keeping the evidence visible?** The loop starts with transcript search, escalates only when visual evidence is needed, returns evidence IDs with the answer, and allows abstention when evidence is insufficient.

## What the UI shows

- lecture video + user question
- final answer with evidence IDs
- which domain tools the agent called
- short activity summaries
- transcript or visual evidence used for the answer
- failure / abstention behavior when evidence is insufficient

The UI exposes tool activity and evidence without exposing hidden chain-of-thought.

## Quickstart

Prerequisites: Git, `uv`, ffmpeg, Ollama, and `qwen3.5:4b`.

### Windows demo

```cmd
run-demo.cmd
```

### CLI

```powershell
video-tutor ask "What are the three stages of the tutor pipeline?"
```

### Inspect activity + evidence

```powershell
.run\app-venv\Scripts\video-tutor.exe inspect --question "What color is the highlighted component around 4 seconds?"
```

## Engineering choices

- **Adaptive modality** instead of sending every question through visual inspection.
- **Small tool surface**: four domain tools cover the useful behavior without extra orchestration layers.
- **Bounded clip inspection** using sampled frames from a short range.
- **Evidence-first tool outputs** so visual inspection returns model-usable evidence, not only file paths.
- **Abstention allowed** when evidence is insufficient.
- **One `TutorService`** behind Streamlit and CLI.
- **Evaluation labels kept out of runtime inputs**.

## Evaluation notes

The historical v1 scorer is not used as a performance claim. V2 separates strict short-answer correctness from citation validity, modality choice, and evidence-window correctness. A timed modality check is bound to evidence of the required modality, so a right-time transcript cannot make a wrong-time visual citation pass.

The frozen report also records tool calls, latency, evidence, failure / abstention state, and per-case activity.

## Limitations

- The 12-question fixture is **self-authored** and intentionally small.
- V2 answer correctness is a strict protocol metric, not a semantic entailment or human-judged QA score.
- Clip inspection uses sampled frames rather than native long-video input.
- Results depend on the frozen local-model configuration.
- The demo targets lecture-style video rather than arbitrary long-form media.

More detail: [`docs/architecture.md`](docs/architecture.md) · [`docs/hermes-integration.md`](docs/hermes-integration.md) · [`docs/windows.md`](docs/windows.md)
