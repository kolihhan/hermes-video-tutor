> **Review-v2 note:** `p3-live-paired-v1` is historical evidence only; its answer metric was construct-invalid. The next canonical run uses the frozen v2 `FINAL:` short-answer contract and writes `runs/p3-live-paired-v2/report.json`.

# Evaluation

Evaluation labels are physically separate from runtime inputs.

- `inference_cases.json` contains only case IDs, neutral course references, and questions.
- `gold_labels.json` contains reference answers and grader-only modality/time-window labels.
- `evaluate.py` joins them only after inference.

The bundled three-case fixture is a deterministic product sanity check, not a research benchmark. A valid citation is not enough: answer correctness, cited modality, and evidence timing are scored separately.

## Frozen live paired evaluation

`live_inference_cases.json` and `live_gold_labels.json` are a separate frozen
12-case set over `fixture/`: six transcript-answerable cases and six
visual-required cases. The fixture is self-authored, ffmpeg-generated, CC0-1.0,
and contains no third-party source media. `fixture/provenance.json` records the
generator, font, ffmpeg version, duration, and every generated asset hash.

The two conditions use the same Hermes v0.20.4 revision, custom
`qwen3.5-hermes:4b` model, config, prompt, questions, transcript, and media.
Only the `video_tutor` project toolset changes:

- `transcript_only`: transcript search/context tools only.
- `multimodal`: the same tools plus bounded frame/clip inspection.

The runner enforces the frozen input hashes, exact project-local Hermes
checkout/config, full Ollama model digests, 65,536-token custom context parameter,
tool surfaces, implementation hashes, alternating arm order, 600-second case
timeout, a new output path, and atomic report creation. Hermes receives only
runtime cases; gold is loaded by the evaluator and is inaccessible through the
restricted toolset.

Answers pass only by normalized equality to a canonical answer or explicit
alias. Citation existence, cited modality, and evidence-window overlap are
reported separately; they are not semantic-entailment claims. The report also
contains per-case evidence/activity, latency, tool calls, and native Hermes
API-call/token/cost usage.

```powershell
.run\app-venv\Scripts\python.exe -m evaluation.run_live_paired --output runs\p3-live-paired-v2\report.json
```

The canonical report path is single-use; do not rerun a valid result.

## Canonical result

`runs/p3-live-paired-v1/report.json` is complete (12 cases per arm) and freezes
`SIMPLIFY`. Transcript-only and Multimodal each scored `0/12` answer correctness
and `0/12` full pass. Multimodal used visual tools on `4/6` visual cases and
`0/6` transcript cases, but produced no scored answer gain. Native usage was 70
API calls / 172,974 tokens for Transcript-only and 116 / 310,036 for
Multimodal. The usage files contain `estimated_cost_usd: 0.0` but also
`cost_status: unknown` / `cost_source: none`, so monetary cost is unavailable,
not verified as zero.

Post-run validation found that the original evaluator adapter read `id` while
native `Evidence` serializes `evidence_id`. The original report is preserved at
`report.invalid-evaluator-evidence-key-20260829-b.json` (SHA-256
`f11aeacbf9d04348c7aecd8bc90aa51e98308015236721d5a1dcbba902442fdd`).
The canonical report deterministically rescores the exact unchanged predictions
with the native field name and records both evaluator hashes; no inference was
rerun, and no decision metric or verdict changed. Its SHA-256 is
`c4847605a65970e24ff67ac9b68565d32fbc876eba83d0b971e026624bbd9260`.
