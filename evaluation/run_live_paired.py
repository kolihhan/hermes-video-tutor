from __future__ import annotations

from dataclasses import asdict
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from typing import Any, Callable
from urllib.request import urlopen

from video_tutor.contracts import TutorAnswer
from video_tutor.hermes_runtime import HermesCliRuntime
from video_tutor.tutor import TutorService
from .evaluate import evaluate_predictions

MODES = ("transcript_only", "multimodal")
ROOT = Path(__file__).resolve().parents[1]
MODEL = "qwen3.5-hermes:4b"
BASE_MODEL = "qwen3.5:4b"
TIMEOUT_S = 600
FROZEN_SHA256 = {
    "evaluation/live_inference_cases.json": "8a67946bf34ff93d52255fde38dc66a8f4e3ad187924011dea0cb2091ec314c7",
    "evaluation/live_gold_labels.json": "f01a3bb27463121099c2dacd47a8252211e5a2382d7468a8f1a0f2e0ec09d7ac",
    "evaluation/fixture/provenance.json": "b4d8189ac5289e4827ff34d9a3ec61cef4031b8cc18643d312e34d58cff539b9",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> list[dict[str, Any]]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"expected a JSON list of objects: {path}")
    return rows


def _atomic_write(path: Path, payload: object) -> None:
    if path.exists():
        raise FileExistsError(f"paired output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
            temp_name = handle.name
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp_name, path)
    finally:
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)


def _run(command: list[str]) -> str:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"preflight command failed: {command[0]}") from exc
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"preflight command failed: {command[0]}")
    return completed.stdout.strip()


def _tool_surface(repo_root: Path, mode: str) -> list[str]:
    plugin = repo_root / ".hermes" / "plugins" / "video_tutor" / "__init__.py"
    spec = importlib.util.spec_from_file_location(f"p3_preflight_{mode}", plugin)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the video_tutor project plugin")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Context:
        def __init__(self) -> None:
            self.tools: list[str] = []

        def register_tool(self, **kwargs: Any) -> None:
            self.tools.append(str(kwargs["name"]))

    previous = os.environ.get("VIDEO_TUTOR_TOOL_MODE")
    try:
        os.environ["VIDEO_TUTOR_TOOL_MODE"] = mode
        context = Context()
        module.register(context)
    finally:
        if previous is None:
            os.environ.pop("VIDEO_TUTOR_TOOL_MODE", None)
        else:
            os.environ["VIDEO_TUTOR_TOOL_MODE"] = previous
    return sorted(context.tools)


def _preflight(*, repo_root: Path, hermes_home: Path, cases_path: Path, gold_path: Path) -> dict[str, Any]:
    repo_root = Path(repo_root).resolve()
    hermes_home = Path(hermes_home).resolve()
    cases_path = Path(cases_path).resolve()
    gold_path = Path(gold_path).resolve()
    if cases_path != repo_root / "evaluation" / "live_inference_cases.json" or gold_path != repo_root / "evaluation" / "live_gold_labels.json":
        raise ValueError("live run requires the frozen runtime cases and evaluator-only gold files")
    actual_hashes = {
        name: _sha256(repo_root / name) for name in FROZEN_SHA256
    }
    if actual_hashes != FROZEN_SHA256:
        raise ValueError("frozen input hash mismatch")
    cases, gold = _load(cases_path), _load(gold_path)
    if len(cases) != 12 or len(gold) != 12:
        raise ValueError("frozen paired run requires exactly 12 cases and gold rows")
    case_ids = [str(row.get("case_id", "")) for row in cases]
    if case_ids != [str(row.get("case_id", "")) for row in gold] or len(set(case_ids)) != 12:
        raise ValueError("case and gold IDs must match exactly once")
    _validate_inputs(cases, gold, repo_root, True)

    fixture_root = repo_root / "evaluation" / "fixture"
    fixture = json.loads((fixture_root / "provenance.json").read_text(encoding="utf-8"))
    ffmpeg_version = _run(["ffmpeg", "-version"]).splitlines()[0]
    if ffmpeg_version != fixture.get("ffmpeg_version"):
        raise ValueError("fixture ffmpeg provenance mismatch")
    duration = float(_run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(fixture_root / "media" / "lecture.mp4"),
    ]))
    if abs(duration - 60.0) > 0.01:
        raise ValueError(f"fixture duration mismatch: {duration:g}s")

    lock = dict(
        line.split("=", 1) for line in (repo_root / "hermes.lock").read_text(encoding="utf-8").splitlines()
        if line and "=" in line
    )
    lock = {key.strip(): value.strip() for key, value in lock.items()}
    if lock.get("release") != "v0.20.4" or lock.get("commit") != "8911e2e0edf750b104edbdc106d63d6cdac88524":
        raise ValueError("Hermes lock mismatch")
    checkout = repo_root / ".run" / "hermes-agent"
    revision = _run(["git", "-C", str(checkout), "rev-parse", "HEAD"])
    if not re.fullmatch(r"[0-9a-fA-F]{40}", revision) or revision.lower() != lock["commit"].lower():
        raise ValueError(f"Hermes checkout mismatch: {revision}")
    sparse_checkout = _run(["git", "-C", str(checkout), "sparse-checkout", "list"]).splitlines()
    if sparse_checkout != ["/*", "!/contributors/"]:
        raise ValueError(f"Hermes sparse checkout mismatch: {sparse_checkout}")
    if _run(["git", "-C", str(checkout), "status", "--porcelain"]):
        raise ValueError("Hermes checkout is dirty")
    if hermes_home != repo_root / ".run" / "hermes-home":
        raise ValueError("Hermes home must be the project-local frozen profile")
    source_config = repo_root / "config" / "hermes-project.yaml"
    installed_config = hermes_home / "config.yaml"
    config_text = source_config.read_text(encoding="utf-8")
    if f'default: "{MODEL}"' not in config_text or source_config.read_bytes() != installed_config.read_bytes():
        raise ValueError("project Hermes config mismatch")
    executable = repo_root / ".run" / "hermes-venv" / "Scripts" / "hermes.exe"
    if not executable.is_file():
        raise ValueError("project-local Hermes executable is missing")

    try:
        with urlopen("http://localhost:11434/api/tags", timeout=10) as response:
            models = json.loads(response.read()).get("models", [])
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("Ollama model preflight failed") from exc
    by_name = {str(row.get("name")): row for row in models if isinstance(row, dict)}
    base, model = by_name.get(BASE_MODEL), by_name.get(MODEL)
    if base is None or model is None:
        raise ValueError(f"required Ollama models are missing: {BASE_MODEL}, {MODEL}")
    for row in (base, model):
        if not re.fullmatch(r"[0-9a-f]{64}", str(row.get("digest", ""))):
            raise ValueError("Ollama returned an invalid model digest")
    details = model.get("details", {})
    if details.get("parent_model") != BASE_MODEL or not {"vision", "tools"}.issubset(model.get("capabilities", [])):
        raise ValueError("custom Ollama model does not match the frozen base/capabilities")
    parameter_lines = _run(["ollama", "show", "--parameters", MODEL]).splitlines()
    parameters = dict(parts for line in parameter_lines if len(parts := line.split(maxsplit=1)) == 2)
    if parameters.get("num_ctx") != "65536":
        raise ValueError("custom Ollama model num_ctx mismatch")
    if parameters.get("temperature") not in {"0", "0.0"}:
        raise ValueError("custom Ollama model temperature must be deterministic (0)")

    expected_surfaces = {
        "transcript_only": ["expand_context", "search_transcript"],
        "multimodal": ["expand_context", "inspect_clip", "inspect_frame", "search_transcript"],
    }
    surfaces = {mode: _tool_surface(repo_root, mode) for mode in MODES}
    if surfaces != expected_surfaces:
        raise ValueError(f"plugin tool surface mismatch: {surfaces}")

    implementation_paths = sorted((repo_root / "src" / "video_tutor").glob("*.py")) + [
        repo_root / ".hermes" / "plugins" / "video_tutor" / "__init__.py",
        repo_root / ".hermes" / "plugins" / "video_tutor" / "plugin.yaml",
        repo_root / "evaluation" / "evaluate.py",
        repo_root / "evaluation" / "run_live_paired.py",
        repo_root / "scripts" / "generate_fixture.py",
        repo_root / "scripts" / "setup-hermes.ps1",
        source_config,
        repo_root / "Modelfile.hermes",
        repo_root / "hermes.lock",
        repo_root / "pyproject.toml",
        repo_root / "uv.lock",
    ]
    if any(not path.is_file() for path in implementation_paths):
        raise ValueError("frozen implementation file is missing")
    implementation_sha256 = {
        path.relative_to(repo_root).as_posix(): _sha256(path) for path in implementation_paths
    }
    return {
        "cases_sha256": _sha256(cases_path),
        "gold_sha256": _sha256(gold_path),
        "fixture": dict(fixture, provenance_sha256=_sha256(fixture_root / "provenance.json"), measured_duration_s=duration),
        "model": {
            "tag": MODEL,
            "digest": model["digest"],
            "base_tag": BASE_MODEL,
            "base_digest": base["digest"],
            "size_bytes": model.get("size"),
            "details": details,
            "capabilities": model.get("capabilities", []),
            "parameters": parameters,
        },
        "hermes": {
            "release": lock["release"],
            "revision": revision,
            "sparse_checkout": sparse_checkout,
            "executable_sha256": _sha256(executable),
            "config_sha256": _sha256(source_config),
        },
        "tool_surfaces": surfaces,
        "implementation_sha256": implementation_sha256,
        "timeout_s": TIMEOUT_S,
    }


def _default_factory(repo_root: Path, hermes_home: Path, session_root: Path, mode: str) -> TutorService:
    executable = repo_root / ".run" / "hermes-venv" / "Scripts" / "hermes.exe"
    return TutorService(runtime=HermesCliRuntime(repo_root=repo_root, hermes_home=hermes_home, executable=str(executable), timeout_s=TIMEOUT_S, tool_mode=mode), session_root=session_root / mode)


def _validate_inputs(cases: list[dict[str, Any]], gold: list[dict[str, Any]], repo_root: Path, validate_fixture: bool) -> None:
    if any(set(row) != {"case_id", "question", "course"} or not row["question"].strip() for row in cases):
        raise ValueError("runtime cases must contain only case_id, question, and course")
    required_gold = {"case_id", "reference_answer", "accepted_aliases", "required_modality", "expected_evidence_window"}
    if any(not required_gold.issubset(row) or not isinstance(row["accepted_aliases"], list) for row in gold):
        raise ValueError("gold rows do not match the frozen schema")
    if validate_fixture:
        provenance = json.loads((repo_root / "evaluation" / "fixture" / "provenance.json").read_text(encoding="utf-8"))
        video = repo_root / "evaluation" / "fixture" / "media" / "lecture.mp4"
        assets = {
            "course.json": repo_root / "evaluation" / "fixture" / "course.json",
            "transcript.json": repo_root / "evaluation" / "fixture" / "transcript.json",
            "media/lecture.mp4": video,
        }
        expected_hashes = {name: _sha256(path) for name, path in assets.items()}
        generator = repo_root / Path(str(provenance.get("generator", "")).replace("\\", "/"))
        if (provenance.get("license") != "CC0-1.0" or provenance.get("duration_s") != 60
                or provenance.get("asset_sha256") != expected_hashes
                or not generator.is_file() or provenance.get("generator_sha256") != _sha256(generator)):
            raise ValueError("fixture provenance mismatch")
        expected_modelfile = "FROM qwen3.5:4b\nPARAMETER num_ctx 65536\nPARAMETER temperature 0"
        if (repo_root / "Modelfile.hermes").read_text(encoding="utf-8").strip() != expected_modelfile:
            raise ValueError("Hermes Modelfile base mismatch")
        if "release = v0.20.4" not in (repo_root / "hermes.lock").read_text(encoding="utf-8"):
            raise ValueError("Hermes lock mismatch")


def _verdict(aggregates: dict[str, dict[str, Any]], complete: bool) -> str:
    if not complete:
        return "INSUFFICIENT"
    transcript_gain = aggregates["multimodal"]["answer_correct"]["transcript_only"] - aggregates["transcript_only"]["answer_correct"]["transcript_only"]
    transcript_full_gain = aggregates["multimodal"]["full_pass"]["transcript_only"] - aggregates["transcript_only"]["full_pass"]["transcript_only"]
    visual_answer_gain = aggregates["multimodal"]["answer_correct"]["visual_required"] - aggregates["transcript_only"]["answer_correct"]["visual_required"]
    visual_full_gain = aggregates["multimodal"]["full_pass"]["visual_required"] - aggregates["transcript_only"]["full_pass"]["visual_required"]
    if visual_answer_gain >= 2 / 6 and visual_full_gain >= 2 / 6 and transcript_gain >= 0 and transcript_full_gain >= 0 and aggregates["multimodal"]["visual_tool_use_on_visual_required"] >= 4 / 6 and aggregates["multimodal"]["unnecessary_visual_use_on_transcript"] <= 1 / 6:
        return "KEEP HERMES"
    if (visual_answer_gain <= 0 and visual_full_gain <= 0
            and aggregates["transcript_only"]["answer_correct"]["overall"] >= aggregates["multimodal"]["answer_correct"]["overall"]
            and aggregates["transcript_only"]["full_pass"]["overall"] >= aggregates["multimodal"]["full_pass"]["overall"]):
        return "SIMPLIFY"
    return "REVISE"


def run_paired(*, cases_path: Path, gold_path: Path, output_path: Path,
               service_factory: Callable[[str], Any] | None = None,
               repo_root: Path = ROOT, hermes_home: Path = ROOT / ".run" / "hermes-home",
               session_root: Path = ROOT / ".run" / "paired-sessions") -> Path:
    output_path = Path(output_path)
    if output_path.exists():
        raise FileExistsError(f"paired output already exists: {output_path}")
    cases, gold = _load(cases_path), _load(gold_path)
    if len(cases) != 12 or len(gold) != 12:
        raise ValueError("frozen paired run requires exactly 12 cases and gold rows")
    case_ids = [str(row.get("case_id", "")) for row in cases]
    gold_ids = [str(row.get("case_id", "")) for row in gold]
    if case_ids != gold_ids or len(set(case_ids)) != 12:
        raise ValueError("case and gold IDs must match exactly once")
    live_runtime = service_factory is None
    if live_runtime:
        provenance = _preflight(
            repo_root=repo_root,
            hermes_home=hermes_home,
            cases_path=cases_path,
            gold_path=gold_path,
        )
    else:
        _validate_inputs(cases, gold, repo_root, False)
        provenance = {
            "cases_sha256": _sha256(Path(cases_path)),
            "gold_sha256": _sha256(Path(gold_path)),
            "validation": "injected service; live runtime preflight not applicable",
        }
    if service_factory is None:
        service_factory = lambda mode: _default_factory(repo_root, hermes_home, session_root, mode)
    services = {mode: service_factory(mode) for mode in MODES}
    predictions: dict[str, list[dict[str, Any]]] = {mode: [] for mode in MODES}
    complete = True
    condition_order: list[dict[str, Any]] = []
    run_started = datetime.now(timezone.utc)
    wall_started = time.perf_counter()
    for index, case in enumerate(cases):
        order = MODES[index % 2:] + MODES[:index % 2]
        condition_order.append({"case_id": case["case_id"], "order": list(order)})
        for mode in order:
            started = time.perf_counter()
            try:
                answer: TutorAnswer = services[mode].ask(question=str(case["question"]), course_manifest=repo_root / case["course"] if not Path(case["course"]).is_absolute() else Path(case["course"]))
                if live_runtime and not isinstance(answer.usage.get("api_calls"), int):
                    raise RuntimeError("Hermes usage accounting is missing")
                prediction = {
                    "case_id": case["case_id"],
                    "answer": answer.text,
                    "final_product_answer": answer.text,
                    "raw_model_answer": answer.raw_model_answer,
                    "rejection_reason": answer.rejection_reason,
                    "status": answer.status,
                    "evidence": [asdict(item) for item in answer.evidence],
                    "activity": [asdict(item) for item in answer.activity],
                    "tool_calls": [event.tool for event in answer.activity],
                    "usage": answer.usage,
                    "latency_ms": (time.perf_counter() - started) * 1000,
                }
            except Exception as exc:
                complete = False
                prediction = {"case_id": case["case_id"], "answer": "", "status": "runtime_error",
                    "evidence": [], "activity": [], "tool_calls": [], "latency_ms": (time.perf_counter() - started) * 1000,
                    "error": {"type": type(exc).__name__, "message": str(exc)}}
            predictions[mode].append(prediction)
    aggregates = {mode: evaluate_predictions(rows, gold) for mode, rows in predictions.items()}
    for mode in MODES:
        aggregates[mode]["hermes_process_invocations"] = len(predictions[mode])
    payload = {"schema_version": "video-tutor-live-paired/v2", "complete": complete, "verdict": _verdict(aggregates, complete),
        "started_at_utc": run_started.isoformat(), "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "wall_time_ms": (time.perf_counter() - wall_started) * 1000,
        "question_ids": [row["case_id"] for row in cases], "condition_order": condition_order,
        "conditions": {mode: {"tool_mode": mode, "aggregate": aggregates[mode], "predictions": predictions[mode]} for mode in MODES},
        "provenance": provenance}
    _atomic_write(output_path, payload)
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the frozen paired Hermes Video Tutor evaluation")
    parser.add_argument("--cases", type=Path, default=ROOT / "evaluation" / "live_inference_cases.json")
    parser.add_argument("--gold", type=Path, default=ROOT / "evaluation" / "live_gold_labels.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    run_paired(cases_path=args.cases, gold_path=args.gold, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
