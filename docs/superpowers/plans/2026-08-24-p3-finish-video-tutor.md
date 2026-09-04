# Hermes Video Tutor Finish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the portfolio-facing Hermes Video Tutor without changing the already-validated core agent/tool architecture.

**Architecture:** Keep `TutorService` as the product boundary and `HermesCliRuntime` as the only Hermes process boundary. CLI and Streamlit remain thin adapters. Evaluation labels remain physically separate from runtime inputs and join only after inference by case id.

**Tech Stack:** Python 3.11+, Hermes Agent project plugin, ffmpeg, Streamlit, pytest, PowerShell.

**Spec:** `/mnt/data/portfolio_redesign_specs/P3_HERMES_VIDEO_TUTOR_SPEC.md`

## Global Constraints

- Hermes owns the observe-act-observe loop; this repo must not implement a parallel agent framework.
- Runtime has zero access to benchmark reference answers, required modality labels, or benchmark captions/annotations.
- Tool Search stays disabled for the four-tool project surface.
- No fixed transcript -> frame -> clip workflow; Hermes chooses tools.
- Evidence exhaustion must produce an honest abstention.
- CLI and Streamlit call the same `TutorService`.
- Windows-specific setup may configure project-local runtime state but must not mutate global PowerShell execution policy or global Hermes configuration.

---

### Task 1: CLI and Streamlit adapters

**Files:**
- Create: `src/video_tutor/cli.py`
- Create: `app.py`
- Test: `tests/test_adapters.py`

**Interfaces:**
- Consumes: `TutorService.ask(question: str, course_manifest: str | Path) -> TutorAnswer`
- Produces: `video-tutor demo`, `video-tutor ask <question>`, and a Streamlit entry point using the same service factory.

- [ ] Write adapter tests proving both interfaces create/use the same `TutorService` boundary and do not call tools directly.
- [ ] Run the targeted tests and confirm RED because adapters do not exist.
- [ ] Implement the smallest CLI and Streamlit adapters.
- [ ] Run targeted tests and confirm GREEN.

### Task 2: Evaluation isolation and semantic scoring

**Files:**
- Create: `evaluation/inference_cases.json`
- Create: `evaluation/gold_labels.json`
- Create: `evaluation/evaluate.py`
- Create: `evaluation/README.md`
- Test: `tests/test_evaluation.py`

**Interfaces:**
- Inference file contains only `case_id`, `question`, and neutral course reference.
- Gold file contains `case_id`, `reference_answer`, `required_modality`, and optional expected evidence window.
- Evaluator joins predictions to gold only after runtime execution.

- [ ] Write tests proving the inference file contains no gold fields, wrong answer + valid citation fails semantic correctness, and visual-required cases require visual evidence.
- [ ] Run targeted tests and confirm RED because evaluator/files do not exist.
- [ ] Implement exact-match/normalized-answer scoring for the deterministic demo fixture plus modality/citation checks.
- [ ] Run targeted tests and confirm GREEN.

### Task 3: Transcript-only baseline and deterministic local evaluation

**Files:**
- Modify: `evaluation/evaluate.py`
- Create: `evaluation/run_demo_eval.py`
- Test: `tests/test_evaluation_runner.py`

**Interfaces:**
- Produces per-case records and aggregate metrics for transcript-only and multimodal modes.
- Offline deterministic mode is an evaluation fixture, not a substitute for live Hermes acceptance.

- [ ] Write tests proving the transcript-only baseline cannot use visual tools and that aggregate metrics distinguish answer correctness from citation validity.
- [ ] Run RED.
- [ ] Implement the deterministic runner using frozen fixture predictions/actions.
- [ ] Run GREEN.

### Task 4: Windows project-local setup and launch scripts

**Files:**
- Create: `scripts/setup-hermes.ps1`
- Create: `scripts/run-demo.ps1`
- Create: `run-demo.cmd`
- Create: `docs/windows.md`
- Test: `tests/test_windows_scripts.py`

**Interfaces:**
- `setup-hermes.ps1` creates `.run/` state, project-scoped Hermes home/config, and verifies `ffmpeg`, `ollama`, and the pinned Hermes checkout/executable without changing global settings.
- `run-demo.cmd` bypasses script execution policy only for the launched process.

- [ ] Write static contract tests for reserved `$PID` names, project-local paths, execution-policy behavior, and explicit dependency checks.
- [ ] Run RED.
- [ ] Implement PowerShell/CMD scripts and Windows doc.
- [ ] Run GREEN.

### Task 5: Portfolio README and full verification

**Files:**
- Create: `README.md`
- Create: `docs/architecture.md`
- Create: `docs/hermes-integration.md`

**Interfaces:**
- README must explain problem, architecture, quickstart, three traces, evaluation, design decisions, and limitations within the agreed 30-second story.

- [ ] Add static README contract test for required sections and no benchmark-overclaim wording.
- [ ] Run RED.
- [ ] Write concise docs using only verified claims.
- [ ] Run the complete P3 pytest suite, compileall, deterministic demo eval, runtime gold/reference grep, and package-cleanliness checks.
