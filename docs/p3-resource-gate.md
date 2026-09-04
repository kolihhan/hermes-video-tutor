# P3 Resource Gate

Resource-gate record for the metadata-only Video-MMLU audit. Official dataset: `Enxin/Video-MMLU`, pinned revision `f626a2e2fa6411ecc06be176c31501f1fc700d15`.

- Official metadata SHA256: `README.md` `DDDCF778327260B7BAEDCF2DC4F6DB55E918E4FE62A35B88223BBB05CD61299C`; `video_sources.jsonl` `7618F4BFEED64A682C625156D8252E642D7D25EB0346CF11BADE20B46BDFEC82`; `video_mmlu.jsonl` `45C311F5654CF9236AEB7C13D6CFFBF4DB7AEB31C58B5FB44D44442CDB96D528`; `Video_MMLU_CAP.tsv` `48B35811DDE50C674656CAFEE79C30C0D6A79CAAB40075890D59F162F1716B7F`; `Video_MMLU_QA.tsv` `094854E18F802C16DAD6EDB22CC662CD8A2B769E058417D12631B4FCF5D02B7E`.
- Exact audited totals: JSONL `J=1065`, reasoning `15853`, captions `15875`; CAP `IDs=1065`, questions `15940`; QA `IDs=1058`, rows `15848`; source IDs `1065`; shared QA mismatches `0`.
- Alias: `Maclaurin_Series_Visualization` vs `PE_0n9Ph_PQ`. Six shared CAP mismatches: JSONL `0` vs CAP `10`.
- Failed gates: authoritative mapping; archive filename/per-video integrity; third-party YouTube rights/per-video licenses.
- Official exposed leaderboard set was metadata-audited only; no DEV/FINAL result exists, and no gold reached any model. Preserve Hermes runtime and frozen external metadata provenance.

**Verdict:** `REVISE—blocked before media/inference; no metrics produced`

This verdict applies only to the attempted Video-MMLU resource. The bounded
audit is closed and no Video-MMLU inference will be run. The separate paired
Hermes evaluation uses the repository's self-authored CC0 fixture documented in
`evaluation/README.md`; it does not rehabilitate or substitute a Video-MMLU
claim.
