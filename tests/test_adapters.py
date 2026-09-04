from pathlib import Path
import importlib.util

from video_tutor.contracts import ActivityEvent, Evidence, TutorAnswer


class FakeTutorService:
    def __init__(self):
        self.calls = []

    def ask(self, *, question: str, course_manifest: str | Path) -> TutorAnswer:
        self.calls.append((question, Path(course_manifest)))
        evidence = (Evidence("E1", "transcript", 0.0, 2.0, "three stages"),)
        activity = (ActivityEvent("search_transcript", "Found transcript evidence.", ("E1",)),)
        return TutorAnswer("Three stages. [E1]", "answered", evidence, activity)


def _load_app_module():
    path = Path(__file__).parents[1] / "app.py"
    spec = importlib.util.spec_from_file_location("video_tutor_streamlit_app", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_cli_ask_and_inspect_use_injected_tutor_service(capsys, tmp_path):
    from video_tutor.cli import run_cli

    course = tmp_path / "course.json"
    course.write_text("{}", encoding="utf-8")
    service = FakeTutorService()

    assert run_cli(["ask", "What are the stages?", "--course", str(course)], service=service) == 0
    assert service.calls == [("What are the stages?", course)]
    assert "Three stages. [E1]" in capsys.readouterr().out

    service.calls.clear()
    assert run_cli(["inspect", "--question", "What are the stages?", "--course", str(course)], service=service) == 0
    out = capsys.readouterr().out
    assert service.calls == [("What are the stages?", course)]
    assert "search_transcript" in out
    assert "E1" in out


def test_streamlit_adapter_calls_same_tutor_service_without_importing_tool_layers(tmp_path):
    app = _load_app_module()
    service = FakeTutorService()
    course = tmp_path / "course.json"

    result = app.ask_tutor(service, question="What are the stages?", course_manifest=course)

    assert result.text == "Three stages. [E1]"
    assert service.calls == [("What are the stages?", course)]
    text = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")
    assert "video_tutor.tool_runtime" not in text
    assert "video_tutor.media" not in text
    assert "video_tutor.transcript" not in text
