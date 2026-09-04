from pathlib import Path
import json
import shutil
import sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))


def test_transcript_only_fixture_never_calls_visual_tools():
    from evaluation.run_demo_eval import load_fixture_predictions

    rows = load_fixture_predictions("transcript_only")
    visual_tools = {"inspect_frame", "inspect_clip"}
    assert rows
    assert all(visual_tools.isdisjoint(row.get("tool_calls", [])) for row in rows)


def test_aggregate_metrics_keep_answer_and_citation_correctness_separate():
    from evaluation.run_demo_eval import evaluate_fixture

    baseline = evaluate_fixture("transcript_only")
    multimodal = evaluate_fixture("multimodal")

    assert baseline["cases"] == 3
    assert baseline["answer_accuracy"] == 1 / 3
    assert baseline["full_pass_rate"] == 1 / 3
    assert baseline["visual_tool_usage_when_required"] == 0.0

    assert multimodal["answer_accuracy"] == 1.0
    assert multimodal["full_pass_rate"] == 1.0
    assert multimodal["visual_tool_usage_when_required"] == 1.0
    assert multimodal["unnecessary_visual_usage_on_transcript"] == 0.0
    assert multimodal["avg_tool_calls"] > baseline["avg_tool_calls"]


def test_frozen_aggregate_reports_modality_full_pass_tools_latency_and_failures():
    from evaluation.evaluate import evaluate_predictions
    gold = [
        {"case_id": "t", "reference_answer": "ready", "accepted_aliases": [], "required_modality": "transcript", "expected_evidence_window": [0, 5]},
        {"case_id": "v", "reference_answer": "blue", "accepted_aliases": [], "required_modality": "visual", "expected_evidence_window": [5, 10]},
    ]
    predictions = [
        {"case_id": "t", "answer": "FINAL: ready [E1]", "status": "answered", "evidence": [{"evidence_id": "E1", "kind": "transcript", "start_s": 1, "end_s": 2}], "tool_calls": ["search_transcript"], "latency_ms": 10, "usage": {"api_calls": 2, "input_tokens": 100, "output_tokens": 10, "total_tokens": 110, "estimated_cost_usd": 0}},
        {"case_id": "v", "answer": "FINAL: blue [E2]", "status": "answered", "evidence": [{"evidence_id": "E2", "kind": "frame", "start_s": 6, "end_s": 6}], "tool_calls": ["inspect_frame"], "latency_ms": 20, "usage": {"api_calls": 3, "input_tokens": 200, "output_tokens": 20, "total_tokens": 220, "estimated_cost_usd": 0}},
    ]
    result = evaluate_predictions(predictions, gold)
    assert result["answer_correct"] == {"overall": 1.0, "transcript_only": 1.0, "visual_required": 1.0}
    assert result["full_pass"] == {"overall": 1.0, "transcript_only": 1.0, "visual_required": 1.0}
    assert result["visual_tool_use_on_visual_required"] == 1.0
    assert result["unnecessary_visual_use_on_transcript"] == 0.0
    assert result["total_tool_calls"] == 2
    assert result["mean_latency_ms"] == 15
    assert result["failure_or_abstention_count"] == 0
    assert result["usage"] == {
        "api_calls": 5,
        "input_tokens": 300,
        "output_tokens": 30,
        "total_tokens": 330,
        "estimated_cost_usd": 0,
    }


def test_live_pair_runner_alternates_arms_and_refuses_overwrite(tmp_path):
    from video_tutor.contracts import TutorAnswer
    from evaluation.run_live_paired import run_paired
    cases = [{"case_id": str(i), "question": "q", "course": "course.json"} for i in range(12)]
    gold = [{"case_id": str(i), "reference_answer": "ready", "accepted_aliases": [], "required_modality": "transcript", "expected_evidence_window": [0, 5]} for i in range(12)]
    cases_path = tmp_path / "cases.json"; cases_path.write_text(json.dumps(cases), encoding="utf-8")
    gold_path = tmp_path / "gold.json"; gold_path.write_text(json.dumps(gold), encoding="utf-8")
    output = tmp_path / "report.json"
    calls = []
    class FakeService:
        def __init__(self, mode): self.mode = mode
        def ask(self, *, question, course_manifest):
            calls.append(self.mode)
            return TutorAnswer("FINAL: ready [E1]" if self.mode == "transcript_only" else "FINAL: blue [E1]", "answered", (), ())
    path = run_paired(
        cases_path=cases_path,
        gold_path=gold_path,
        output_path=output,
        service_factory=FakeService,
        repo_root=tmp_path,
    )
    assert path == output
    assert calls == [mode for i in range(12) for mode in (("transcript_only", "multimodal") if i % 2 == 0 else ("multimodal", "transcript_only"))]
    with __import__("pytest").raises(FileExistsError):
        run_paired(
            cases_path=cases_path,
            gold_path=gold_path,
            output_path=output,
            service_factory=FakeService,
            repo_root=tmp_path,
        )


def test_live_pair_runner_resolves_relative_course_from_selected_repo_root(tmp_path):
    from video_tutor.contracts import TutorAnswer
    from evaluation.run_live_paired import run_paired

    cases = [{"case_id": str(i), "question": "q", "course": "course.json"} for i in range(12)]
    gold = [{"case_id": str(i), "reference_answer": "ready", "accepted_aliases": [], "required_modality": "transcript", "expected_evidence_window": [0, 5]} for i in range(12)]
    cases_path = tmp_path / "cases.json"
    gold_path = tmp_path / "gold.json"
    cases_path.write_text(json.dumps(cases), encoding="utf-8")
    gold_path.write_text(json.dumps(gold), encoding="utf-8")
    seen = []

    class FakeService:
        def __init__(self, mode):
            self.mode = mode

        def ask(self, *, question, course_manifest):
            seen.append(Path(course_manifest))
            return TutorAnswer("FINAL: ready [E1]", "answered", (), ())

    run_paired(
        cases_path=cases_path,
        gold_path=gold_path,
        output_path=tmp_path / "report.json",
        service_factory=FakeService,
        repo_root=tmp_path,
    )
    assert seen == [tmp_path / "course.json"] * 24


def test_keep_verdict_requires_no_transcript_full_pass_regression():
    from evaluation.run_live_paired import _verdict

    aggregates = {
        "transcript_only": {
            "answer_correct": {"overall": 0.5, "transcript_only": 1.0, "visual_required": 0.0},
            "full_pass": {"overall": 0.5, "transcript_only": 1.0, "visual_required": 0.0},
            "visual_tool_use_on_visual_required": 0.0,
            "unnecessary_visual_use_on_transcript": 0.0,
        },
        "multimodal": {
            "answer_correct": {"overall": 0.75, "transcript_only": 1.0, "visual_required": 0.5},
            "full_pass": {"overall": 0.5, "transcript_only": 0.5, "visual_required": 0.5},
            "visual_tool_use_on_visual_required": 1.0,
            "unnecessary_visual_use_on_transcript": 0.0,
        },
    }
    assert _verdict(aggregates, complete=True) == "REVISE"


def test_simplify_verdict_requires_transcript_only_to_be_at_least_as_good_on_both_overall_scores():
    from evaluation.run_live_paired import _verdict

    aggregates = {
        "transcript_only": {
            "answer_correct": {"overall": 0.5, "transcript_only": 1.0, "visual_required": 0.0},
            "full_pass": {"overall": 0.25, "transcript_only": 0.5, "visual_required": 0.0},
            "visual_tool_use_on_visual_required": 0.0,
            "unnecessary_visual_use_on_transcript": 0.0,
        },
        "multimodal": {
            "answer_correct": {"overall": 0.5, "transcript_only": 1.0, "visual_required": 0.0},
            "full_pass": {"overall": 0.5, "transcript_only": 1.0, "visual_required": 0.0},
            "visual_tool_use_on_visual_required": 0.0,
            "unnecessary_visual_use_on_transcript": 0.0,
        },
    }
    assert _verdict(aggregates, complete=True) == "REVISE"


def test_live_preflight_records_and_validates_exact_runtime_identity(tmp_path, monkeypatch):
    from evaluation import run_live_paired as runner

    for directory in ("src/video_tutor", ".hermes/plugins/video_tutor", "evaluation/fixture", "config", "scripts"):
        shutil.copytree(ROOT / directory, tmp_path / directory, dirs_exist_ok=True)
    for name in (
        "evaluation/evaluate.py", "evaluation/run_live_paired.py",
        "evaluation/live_inference_cases.json", "evaluation/live_gold_labels.json",
        "scripts/setup-hermes.ps1", "hermes.lock", "Modelfile.hermes",
        "pyproject.toml", "uv.lock",
    ):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    hermes_home = tmp_path / ".run" / "hermes-home"
    hermes_home.mkdir(parents=True)
    shutil.copy2(tmp_path / "config" / "hermes-project.yaml", hermes_home / "config.yaml")
    executable = tmp_path / ".run" / "hermes-venv" / "Scripts" / "hermes.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"hermes-test-executable")
    (tmp_path / ".run" / "hermes-agent" / ".git").mkdir(parents=True)

    ffmpeg_version = json.loads((tmp_path / "evaluation" / "fixture" / "provenance.json").read_text(encoding="utf-8"))["ffmpeg_version"]
    full_revision = "8911e2e0edf750b104edbdc106d63d6cdac88524"
    reported_revision = [full_revision]
    git_status = [""]

    def fake_run(command, **kwargs):
        if command[0] == "git":
            if command[-2:] == ["status", "--porcelain"]:
                return __import__("subprocess").CompletedProcess(command, 0, stdout=git_status[0], stderr="")
            if command[-2:] == ["sparse-checkout", "list"]:
                return __import__("subprocess").CompletedProcess(command, 0, stdout="/*\n!/contributors/\n", stderr="")
            return __import__("subprocess").CompletedProcess(command, 0, stdout=reported_revision[0] + "\n", stderr="")
        if command[0] == "ffprobe":
            return __import__("subprocess").CompletedProcess(command, 0, stdout="60.000000\n", stderr="")
        if command[:2] == ["ffmpeg", "-version"]:
            return __import__("subprocess").CompletedProcess(command, 0, stdout=ffmpeg_version + "\n", stderr="")
        if command[:3] == ["ollama", "show", "--parameters"]:
            return __import__("subprocess").CompletedProcess(command, 0, stdout="temperature 0\nnum_ctx 65536\n", stderr="")
        raise AssertionError(command)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"models": [
                {"name": "qwen3.5:4b", "digest": "a" * 64, "size": 10, "details": {"family": "qwen35"}},
                {"name": "qwen3.5-hermes:4b", "digest": "b" * 64, "size": 10, "details": {"parent_model": "qwen3.5:4b", "family": "qwen35"}, "capabilities": ["vision", "tools"]},
            ]}).encode()

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    monkeypatch.setattr(runner, "urlopen", lambda *args, **kwargs: Response())
    provenance = runner._preflight(
        repo_root=tmp_path,
        hermes_home=hermes_home,
        cases_path=tmp_path / "evaluation" / "live_inference_cases.json",
        gold_path=tmp_path / "evaluation" / "live_gold_labels.json",
    )

    assert provenance["model"]["digest"] == "b" * 64
    assert provenance["model"]["base_digest"] == "a" * 64
    assert provenance["model"]["parameters"]["num_ctx"] == "65536"
    assert provenance["model"]["parameters"]["temperature"] == "0"
    assert provenance["hermes"]["revision"] == full_revision
    assert provenance["hermes"]["sparse_checkout"] == ["/*", "!/contributors/"]
    assert provenance["tool_surfaces"] == {
        "transcript_only": ["expand_context", "search_transcript"],
        "multimodal": ["expand_context", "inspect_clip", "inspect_frame", "search_transcript"],
    }
    assert provenance["fixture"]["asset_sha256"]["media/lecture.mp4"]
    assert "evaluation/run_live_paired.py" in provenance["implementation_sha256"]

    reported_revision[0] = "8911e2e0ed000000000000000000000000000000"
    with __import__("pytest").raises(ValueError, match="Hermes checkout mismatch"):
        runner._preflight(
            repo_root=tmp_path,
            hermes_home=hermes_home,
            cases_path=tmp_path / "evaluation" / "live_inference_cases.json",
            gold_path=tmp_path / "evaluation" / "live_gold_labels.json",
        )
    reported_revision[0] = full_revision

    git_status[0] = " M agent/runtime.py\n"
    with __import__("pytest").raises(ValueError, match="Hermes checkout is dirty"):
        runner._preflight(
            repo_root=tmp_path,
            hermes_home=hermes_home,
            cases_path=tmp_path / "evaluation" / "live_inference_cases.json",
            gold_path=tmp_path / "evaluation" / "live_gold_labels.json",
        )
    git_status[0] = ""

    gold_path = tmp_path / "evaluation" / "live_gold_labels.json"
    gold_path.write_text(gold_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with __import__("pytest").raises(ValueError, match="frozen input hash"):
        runner._preflight(
            repo_root=tmp_path,
            hermes_home=hermes_home,
            cases_path=tmp_path / "evaluation" / "live_inference_cases.json",
            gold_path=gold_path,
        )


def test_live_runner_persists_raw_final_and_rejection_fields(tmp_path):
    from video_tutor.contracts import TutorAnswer
    from evaluation.run_live_paired import run_paired
    cases = [{"case_id": str(i), "question": "q", "course": "course.json"} for i in range(12)]
    gold = [{"case_id": str(i), "reference_answer": "ready", "accepted_aliases": [], "required_modality": "transcript", "expected_evidence_window": [0, 5]} for i in range(12)]
    cases_path = tmp_path / "cases.json"; cases_path.write_text(json.dumps(cases), encoding="utf-8")
    gold_path = tmp_path / "gold.json"; gold_path.write_text(json.dumps(gold), encoding="utf-8")
    class FakeService:
        def __init__(self, mode): self.mode = mode
        def ask(self, **kwargs):
            return TutorAnswer(
                text="Insufficient evidence to determine the answer from this lecture.",
                status="insufficient_evidence", raw_model_answer="bad raw",
                rejection_reason="invalid_final_format",
            )
    out = tmp_path / "report.json"
    run_paired(cases_path=cases_path, gold_path=gold_path, output_path=out, service_factory=FakeService, repo_root=tmp_path)
    payload = json.loads(out.read_text(encoding="utf-8"))
    row = payload["conditions"]["transcript_only"]["predictions"][0]
    assert row["raw_model_answer"] == "bad raw"
    assert row["final_product_answer"].startswith("Insufficient evidence")
    assert row["rejection_reason"] == "invalid_final_format"
