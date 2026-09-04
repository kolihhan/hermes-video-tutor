> **Historical v1 decision only.** The v1 inference artifact remains preserved, but the 0/12 answer metric and resulting `SIMPLIFY` verdict are not accepted as a current performance conclusion because the scorer compared full cited prose with short-answer gold. Review-v2 reruns the same fixture/tool treatment under a frozen `FINAL:` short-answer contract.

# P3 decision — frozen 2026-08-29

## Facts

- Experiment: the same pinned native Hermes agent on 12 frozen cases, with
  `transcript_only` exposing two transcript tools and `multimodal` adding only
  `inspect_frame` and `inspect_clip`; condition order alternated by case.
- Runtime: Hermes v0.20.4 revision
  `8911e2e0edf750b104edbdc106d63d6cdac88524`; local
  `qwen3.5-hermes:4b` digest
  `df725e7109960f60ee9244232a4da4ed7f19a9692965fa005b83355638265dc7`;
  65,536-token context.
- Transcript-only: answer correctness `0/12`; full pass `0/12`; visual-tool
  use `0/6` visual and `0/6` transcript cases; 15 tool calls; 70 API calls;
  172,974 tokens; mean/p50/p95 latency 73.24/58.59/202.28 seconds; 8
  abstentions.
- Multimodal: answer correctness `0/12`; full pass `0/12`; visual-tool use
  `4/6` visual and `0/6` transcript cases; 13 tool calls; 116 API calls;
  310,036 tokens; mean/p50/p95 latency 113.44/57.58/395.01 seconds; 5
  abstentions.
- Total wall time: 2,240.26 seconds. Native usage files recorded
  `estimated_cost_usd: 0.0` but also `cost_status: unknown` and
  `cost_source: none`; monetary cost is therefore unavailable rather than
  verified as zero.
- Canonical report: `runs/p3-live-paired-v1/report.json`, 127,005 bytes,
  SHA-256
  `c4847605a65970e24ff67ac9b68565d32fbc876eba83d0b971e026624bbd9260`.

The first attempt was infrastructure-invalid before inference because the
declared context was 32,768; it is preserved as
`report.failed-context-window-32768-20260829-a.json`, SHA-256
`afbaabeae0389a1790b45f2a6c82f9264ba80470fca54ba65c74ff348223e418`.
The next run completed inference, but independent validation found that its
scorer adapter read `id` instead of native `evidence_id`. That original report
is preserved as `report.invalid-evaluator-evidence-key-20260829-b.json`,
SHA-256
`f11aeacbf9d04348c7aecd8bc90aa51e98308015236721d5a1dcbba902442fdd`.
The canonical report deterministically rescores its unchanged predictions and
records both evaluator hashes. No inference was repeated; decision metrics and
verdict were unchanged.

## Interpretation

Frozen verdict: **`SIMPLIFY`**. The visual treatment demonstrated tool use but
no gain under the precommitted exact normalized canonical/alias scorer, while
using more API calls and tokens and higher mean latency. The result supports
removing the visual treatment from the claimed default for this narrow
self-authored fixture. It does not establish general Hermes or video-model
quality, and the verbose answers show the strict short-answer protocol is a
material limitation rather than a basis for post-result tuning.
