import json
from pathlib import Path
import subprocess

from video_tutor.activity import ActivityStore
from video_tutor.contracts import ActivityEvent
from video_tutor.evidence import EvidenceStore
from video_tutor.hermes_runtime import HermesCliRuntime, RuntimeRequest
from video_tutor.tutor import TutorService


def _course(tmp_path: Path) -> Path:
    media = tmp_path / "media"; media.mkdir()
    (media / "lecture.mp4").write_bytes(b"fixture-not-used-by-fake")
    (tmp_path / "transcript.json").write_text(json.dumps([
        {"segment_id":"s1","start_s":0,"end_s":5,"text":"The pipeline has three stages."}
    ]), encoding="utf-8")
    path = tmp_path / "course.json"
    path.write_text(json.dumps({
        "course_id":"demo", "title":"Demo", "video_path":"media/lecture.mp4", "transcript_path":"transcript.json"
    }), encoding="utf-8")
    return path


def test_hermes_runtime_uses_project_profile_and_project_plugin(monkeypatch, tmp_path):
    captured = {}
    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd; captured["env"] = kwargs["env"]; captured["cwd"] = kwargs["cwd"]
        return subprocess.CompletedProcess(cmd, 0, stdout="FINAL: answer [E1]\n", stderr="")
    monkeypatch.setattr(subprocess, "run", fake_run)
    root = Path(__file__).parents[1]
    runtime = HermesCliRuntime(repo_root=root, hermes_home=tmp_path / "hermes-home", executable="hermes")
    request = RuntimeRequest(question="What are the stages?", course_manifest=_course(tmp_path), session_dir=tmp_path / "session")
    result = runtime.ask(request)
    assert result == "FINAL: answer [E1]"
    assert captured["cmd"][:2] == ["hermes", "-z"]
    assert captured["cmd"][3:5] == ["--toolsets", "video_tutor"]
    assert captured["cmd"][5] == "--usage-file"
    assert Path(captured["cmd"][6]) == tmp_path / "session" / "hermes-usage.json"
    assert captured["env"]["HERMES_ENABLE_PROJECT_PLUGINS"] == "1"
    assert captured["env"]["VIDEO_TUTOR_COURSE"].endswith("course.json")
    assert captured["env"]["VIDEO_TUTOR_SESSION"].endswith("session")
    assert Path(captured["env"]["HERMES_HOME"]) == (tmp_path / "hermes-home").resolve()
    assert str((root / "src").resolve()) in captured["env"]["PYTHONPATH"]


def test_hermes_runtime_exposes_validated_tool_mode(monkeypatch, tmp_path):
    captured = {}
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: (captured.update(env=kwargs["env"]) or subprocess.CompletedProcess(cmd, 0, stdout="FINAL: ok [E1]", stderr="")))
    root = Path(__file__).parents[1]
    runtime = HermesCliRuntime(repo_root=root, hermes_home=tmp_path / "home", tool_mode="transcript_only")
    runtime.ask(RuntimeRequest("What?", _course(tmp_path), tmp_path / "session"))
    assert captured["env"]["VIDEO_TUTOR_TOOL_MODE"] == "transcript_only"


def test_hermes_runtime_rejects_unknown_tool_mode(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="tool_mode"):
        HermesCliRuntime(repo_root=Path(__file__).parents[1], hermes_home=tmp_path / "home", tool_mode="bogus")


class FakeRuntime:
    def __init__(self, mode="answer"):
        self.mode = mode
        self.requests = []
    def ask(self, request):
        self.requests.append(request)
        if self.mode == "answer":
            store = EvidenceStore(request.session_dir)
            e = store.add(kind="transcript", start_s=0, end_s=5, text="The pipeline has three stages.")
            ActivityStore(request.session_dir).add(ActivityEvent("search_transcript", "Found transcript evidence.", (e.evidence_id,)))
            (request.session_dir / "hermes-usage.json").write_text(
                json.dumps({"api_calls": 2, "input_tokens": 100, "output_tokens": 10}),
                encoding="utf-8",
            )
            return "FINAL: three stages [E1]"
        if self.mode == "uncited":
            return "The pipeline has three stages."
        return "INSUFFICIENT_EVIDENCE"


def test_tutor_service_delegates_agent_loop_and_returns_session_evidence(tmp_path):
    runtime = FakeRuntime("answer")
    service = TutorService(runtime=runtime, session_root=tmp_path / "sessions")
    answer = service.ask(question="What are the stages?", course_manifest=_course(tmp_path))
    assert answer.status == "answered"
    assert answer.text == "FINAL: three stages [E1]"
    assert [e.evidence_id for e in answer.evidence] == ["E1"]
    assert [a.tool for a in answer.activity] == ["search_transcript"]
    assert answer.usage == {"api_calls": 2, "input_tokens": 100, "output_tokens": 10}
    assert len(runtime.requests) == 1


def test_tutor_service_fails_closed_on_uncited_or_insufficient_answer(tmp_path):
    course = _course(tmp_path)
    uncited = TutorService(runtime=FakeRuntime("uncited"), session_root=tmp_path / "a").ask(
        question="What are the stages?", course_manifest=course
    )
    assert uncited.status == "insufficient_evidence"
    assert "insufficient evidence" in uncited.text.lower()

    explicit = TutorService(runtime=FakeRuntime("insufficient"), session_root=tmp_path / "b").ask(
        question="What is hidden off camera?", course_manifest=course
    )
    assert explicit.status == "insufficient_evidence"


def test_hermes_runtime_rejects_nonzero_exit_even_with_partial_stdout(monkeypatch, tmp_path):
    from video_tutor.hermes_runtime import HermesRuntimeError
    import pytest

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="partial answer [E1]\n", stderr="runtime failed")

    monkeypatch.setattr(subprocess, "run", fake_run)
    root = Path(__file__).parents[1]
    runtime = HermesCliRuntime(repo_root=root, hermes_home=tmp_path / "hermes-home", executable="hermes")
    request = RuntimeRequest(
        question="What are the stages?",
        course_manifest=_course(tmp_path),
        session_dir=tmp_path / "session",
    )
    with pytest.raises(HermesRuntimeError, match="Hermes failed"):
        runtime.ask(request)


def test_runtime_prompt_requires_exact_final_short_answer_contract():
    prompt = HermesCliRuntime._prompt("What is the codename?")
    assert "FINAL: <short answer> [E#]" in prompt
    assert "INSUFFICIENT_EVIDENCE" in prompt


def test_tutor_preserves_raw_answer_and_rejection_reason_on_fail_closed_format(tmp_path):
    class BadFormatRuntime:
        def ask(self, request):
            store = EvidenceStore(request.session_dir)
            store.add(kind="transcript", start_s=0, end_s=5, text="The codename is Orion.")
            return "The codename is Orion [E1]."

    answer = TutorService(runtime=BadFormatRuntime(), session_root=tmp_path / "sessions").ask(
        question="What is the codename?", course_manifest=_course(tmp_path)
    )
    assert answer.status == "insufficient_evidence"
    assert answer.raw_model_answer == "The codename is Orion [E1]."
    assert answer.rejection_reason == "invalid_final_format"
    assert "insufficient evidence" in answer.text.lower()
