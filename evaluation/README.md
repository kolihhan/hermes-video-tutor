# Evaluation

> [!IMPORTANT]
> `p3-live-paired-v2` is the current canonical product-oriented evaluation. `p3-live-paired-v1` is preserved as **historical evidence only** because its answer metric compared the complete cited response against a short-answer label and was construct-invalid for the intended question.

Evaluation labels are physically separate from runtime inputs.

- `inference_cases.json` contains only case IDs, neutral course references, and questions.
- `gold_labels.json` contains reference answers and grader-only modality/time-window labels.
- `evaluate.py` joins them only after inference.

The bundled three-case fixture is a deterministic product sanity check, not a research benchmark. A valid citation is not enough: strict short-answer correctness, cited modality, and evidence timing are scored separately.

## Frozen live paired evaluation v2

`live_inference_cases.json` and `live_gold_labels.json` are a frozen 12-case set over `fixture/`: six transcript-answerable cases and six visual-required cases. The fixture is self-authored, ffmpeg-generated, CC0-1.0, and contains no third-party source media. `fixture/provenance.json` records the generator, font, ffmpeg version, duration, and generated asset hashes.

The two conditions use the same Hermes/model setup, config, prompt, questions, transcript, and media. Only the `video_tutor` project toolset changes:

- `transcript_only`: transcript search/context tools only.
- `multimodal`: the same tools plus bounded frame/clip inspection.

The runner enforces frozen input hashes, project-local Hermes/config identities, Ollama model identity, tool surfaces, implementation hashes, alternating arm order, case timeout, a new output path, and atomic report creation. Hermes receives only runtime cases; gold is loaded by the evaluator after inference and is inaccessible through the restricted toolset.

### Scoring contract

V2 expects the runtime contract:

```text
FINAL: <short answer> [E#]
```

Answer correctness uses normalized equality against a canonical short answer or an explicit alias. This is intentionally a **strict protocol score**, not a human semantic-equivalence judge. A verbose but semantically correct answer can therefore fail `answer_correct`; the frozen metrics should not be described as human-rated answer accuracy.

Citation existence, required modality, and expected evidence timing are separate checks. The current evaluator also requires the evidence that satisfies the required modality to overlap the expected evidence window; a wrong-time frame cannot be rescued by a right-time transcript citation. This tightening does not alter the documented v2 headline passes: the frozen visual cases that passed already cited visual evidence in their expected windows.

The report also contains per-case evidence/activity, latency, tool calls, and native Hermes API-call/token/cost fields. `estimated_cost_usd: 0.0` is accompanied by `cost_status: unknown` / `cost_source: none`, so monetary cost is unavailable rather than verified as zero.

```powershell
.run\app-venv\Scripts\python.exe -m evaluation.run_live_paired --output runs\p3-live-paired-v2\report.json
```

The canonical report path is single-use; do not overwrite a valid frozen result.

## Canonical v2 result

Source of truth: `runs/p3-live-paired-v2/report.json`.

| Condition | Strict full pass | Visual-required strict full pass | Visual tool use on visual questions |
|---|---:|---:|---:|
| Transcript only | 16.7% | 0% | 0% |
| Multimodal tools enabled | **50.0%** | **66.7%** | **100%** |

Multimodal made no unnecessary visual-tool calls on the six transcript-answerable cases in this frozen run. The report verdict is **KEEP HERMES** for this small fixture.

These numbers are a narrow systems/product experiment, not a broad video-QA benchmark claim.

## Historical v1

`runs/p3-live-paired-v1/report.json` and its preserved evaluator-fix artifact remain provenance for the earlier experiment. V1's `0/12` answer result and `SIMPLIFY` verdict are **not the current canonical performance claim** and should not be mixed with v2.
