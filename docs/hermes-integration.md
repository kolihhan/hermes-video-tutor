# Hermes integration

This project uses Hermes as an upstream agent runtime through its **project plugin** surface. It is not a Hermes fork.

## Pinning

`hermes.lock` records the full intended upstream release/revision.
`scripts/setup-hermes.ps1` performs a depth-1/blobless fetch of that exact
revision under `.run/hermes-agent`, verifies the clean checkout, and installs it
into a project-local Hermes environment. The user's global Hermes
checkout/config is not modified.

## Project plugin

The plugin lives under:

```text
.hermes/plugins/video_tutor/
```

`HermesCliRuntime` launches Hermes from the repository root and sets `HERMES_ENABLE_PROJECT_PLUGINS=1`, allowing Hermes to discover this project plugin.

The product plugin registers exactly four tools and forwards execution to
`video_tutor.plugin_bridge`. For the frozen paired evaluation,
`VIDEO_TUTOR_TOOL_MODE=transcript_only` registers only the two transcript tools;
`multimodal` registers all four. Business logic stays in `src/video_tutor/`;
the plugin itself remains a thin registration adapter.

`HermesCliRuntime` passes `--toolsets video_tutor` explicitly. This is the gold
isolation boundary: Hermes's broad default CLI toolset (including terminal and
file access) is not available in either evaluation condition. The same command
also asks Hermes to write its native per-invocation usage report for API-call,
token, model/provider, and estimated-cost accounting.

## Tool Search

`config/hermes-project.yaml` sets:

```yaml
tools:
  tool_search:
    enabled: "off"
```

Tool Search is useful when many plugin/MCP schemas would consume substantial context. This project has only four video tools, so direct eager exposure avoids an unnecessary discovery/bridge round trip.

## Multimodal results

`inspect_frame` and `inspect_clip` return Hermes multimodal tool-result envelopes with text plus base64 image URLs. `inspect_clip` deliberately sends a bounded set of sampled frames rather than arbitrary-length native video.

## Live-runtime boundary

Unit tests can verify plugin registration, tool envelopes, media bounds, evidence/citation behavior, and CLI invocation shape. They cannot prove that a particular Windows Ollama/Hermes transport session remains stable or that a small local model chooses the right tools. That is a separate live acceptance step documented in `docs/windows.md`.
