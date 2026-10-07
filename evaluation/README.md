# Evaluation

Evaluation labels are physically separate from runtime inputs.

- `inference_cases.json` contains only case IDs, neutral course references, and questions.
- `gold_labels.json` contains reference answers and grader-only modality/time-window labels.
- `evaluate.py` joins them only after inference.

The bundled three-case fixture is a deterministic product sanity check, not a research benchmark. A valid citation is not enough: answer correctness, cited modality, and evidence timing are scored separately.

## Frozen live paired evaluation

`live_inference_cases.json` and `live_gold_labels.json` define the current frozen 12-case fixture: six transcript-answerable cases and six visual-required cases. The fixture is self-authored, ffmpeg-generated, CC0-1.0, and contains no third-party source media. `fixture/provenance.json` records generated-asset provenance and hashes.

The two conditions use the same Hermes v0.20.4 revision, custom `qwen3.5-hermes:4b` model, config, prompt, questions, transcript, and media. Only the project tool surface changes:

- `transcript_only`: transcript search/context tools only.
- `multimodal`: the same tools plus bounded frame/clip inspection.

Hermes receives only runtime cases; gold is loaded by the evaluator after inference and is inaccessible through the restricted toolset.

### Scoring contract

V2 requires the model to emit `FINAL: <short answer> [E#]`. `answer_correct` is intentionally a **strict protocol score**: after parsing the `FINAL:` answer, normalized text must equal the canonical answer or an explicit alias. It is not a human semantic-accuracy judge. A semantically reasonable but overlong response can therefore score false.

Citation existence, required modality, and evidence-window overlap are separate checks. For a timed visual case, the evidence that satisfies the visual requirement must itself overlap the expected window; a transcript citation at the right time cannot rescue a visual citation from the wrong time. These checks establish protocol consistency, not semantic entailment between evidence and answer.

## Current canonical result: v2

Source of truth: `runs/p3-live-paired-v2/report.json`.

| Condition | Full pass | Visual-required full pass | Visual tool use on visual questions |
|---|---:|---:|---:|
| Transcript only | 16.7% | 0% | 0% |
| Multimodal tools enabled | **50.0%** | **66.7%** | **100%** |

Multimodal mode made no unnecessary visual-tool calls on the six transcript-answerable cases in this frozen run.

This is a small self-authored product-oriented paired evaluation, not a broad video-QA benchmark claim. The frozen v2 report is not silently rescored when evaluator contracts change; code fixes that strengthen future evaluator invariants are regression-tested separately.

```powershell
.run\app-venv\Scripts\python.exe -m evaluation.run_live_paired --output runs\p3-live-paired-v2\report.json
```

The canonical report path is single-use; do not overwrite a valid frozen result.

## Historical v1

`p3-live-paired-v1` is historical evidence only. Its original answer/evidence adapter was construct-invalid for the current claim, including an `id` versus native `evidence_id` mismatch. The original artifact and deterministic rescore are preserved for auditability, but v1 is not the portfolio performance claim and does not override the v2 result above.
